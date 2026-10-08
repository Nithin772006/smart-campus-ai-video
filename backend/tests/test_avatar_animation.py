import sys
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.schemas.character import (
    AvatarCapabilities,
    AvatarStatusResponse,
    AvatarPreviewRequest,
    AvatarPreviewResponse,
)
from app.schemas.visual_scene import (
    VisualEngine,
    SceneType,
    TeacherPosition,
    VisualScene,
    RoutedScene,
)
from app.services.avatar_service import (
    avatar_service,
    AvatarProvider,
    MuseTalkAvatarProvider,
    TeacherAvatarOverlayProvider,
    CloudAvatarProvider,
    AvatarError,
    AvatarProviderUnavailableError,
    CharacterAssetError,
)
from app.services.renderers.avatar_renderer import AvatarRenderer
from app.services.ffmpeg_service import ffmpeg_service

client = TestClient(app)


# -------------------------------------------------------------
# Test 1: Provider Discovery
# -------------------------------------------------------------
def test_provider_discovery():
    """Verify avatar service discovers all configured avatar providers."""
    providers = avatar_service.get_available_providers()
    assert "overlay" in providers
    assert "musetalk" in providers
    assert "cloud" in providers

    assert isinstance(avatar_service.providers["overlay"], TeacherAvatarOverlayProvider)
    assert isinstance(avatar_service.providers["musetalk"], MuseTalkAvatarProvider)
    assert isinstance(avatar_service.providers["cloud"], CloudAvatarProvider)


# -------------------------------------------------------------
# Test 2: Provider Availability
# -------------------------------------------------------------
def test_provider_availability():
    """Verify is_available() returns accurate status and detailed diagnostics."""
    overlay = avatar_service.providers["overlay"]
    musetalk = avatar_service.providers["musetalk"]
    cloud = avatar_service.providers["cloud"]

    # Overlay should be available if ffmpeg is in path
    assert isinstance(overlay.is_available(), bool)

    # MuseTalk on RTX 2050 4GB without MSVC should accurately report False
    assert musetalk.is_available() is False
    reason = musetalk.get_unavailability_reason()
    assert reason is not None
    assert "FEASIBILITY_REPORT" in reason or "MuseTalk is not available" in reason

    # Cloud should be False if API key is not configured
    if not settings.AVATAR_CLOUD_API_KEY:
        assert cloud.is_available() is False
        assert "unconfigured" in cloud.get_unavailability_reason().lower()



# -------------------------------------------------------------
# Test 3: Static Fallback
# -------------------------------------------------------------
def test_static_fallback():
    """Verify requesting an unavailable neural provider safely falls back to overlay."""
    provider, fallback_used = avatar_service.get_provider_with_fallback("musetalk")
    assert provider.get_name() == "overlay"
    assert fallback_used is True
    assert provider.is_animated() is False


# -------------------------------------------------------------
# Test 4: Mocked Animated Provider
# -------------------------------------------------------------
def test_mocked_animated_provider(tmp_path):
    """Verify that when an animated provider is available, it produces animated=True without fallback."""
    class MockAnimatedProvider(AvatarProvider):
        def get_name(self) -> str:
            return "mock_neural"
        def is_animated(self) -> bool:
            return True
        def get_capabilities(self):
            return {"lip_sync": True, "head_motion": True, "full_body_gesture": False}
        def is_available(self) -> bool:
            return True
        def get_unavailability_reason(self):
            return None
        def generate(self, image_path, audio_path, output_path, options=None):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(b"\x00" * 1024)
            return output_path

    mock_prov = MockAnimatedProvider()
    with patch.dict(avatar_service.providers, {"mock_neural": mock_prov}):
        prov, fallback = avatar_service.get_provider_with_fallback("mock_neural")
        assert prov.get_name() == "mock_neural"
        assert fallback is False
        assert prov.is_animated() is True
        assert prov.get_capabilities()["lip_sync"] is True
        assert prov.get_capabilities()["head_motion"] is True
        assert prov.get_capabilities()["full_body_gesture"] is False


# -------------------------------------------------------------
# Test 5: Real Animated Provider Status Endpoint
# -------------------------------------------------------------
def test_real_animated_provider_status_api():
    """Test GET /api/avatar/status returns structured status without crashing."""
    response = client.get("/api/avatar/status")
    assert response.status_code == 200
    data = response.json()
    assert "enabled" in data
    assert "active_provider" in data
    assert "capabilities" in data
    assert isinstance(data["capabilities"], dict)
    assert "lip_sync" in data["capabilities"]
    assert "head_motion" in data["capabilities"]
    assert "full_body_gesture" in data["capabilities"]


# -------------------------------------------------------------
# Test 6: Audio Duration
# -------------------------------------------------------------
def test_audio_duration():
    """Verify input narration audio has measurable valid duration."""
    sample_audio = avatar_service._find_sample_audio(max_duration=10.0)
    assert sample_audio.exists()
    audio_probe = ffmpeg_service.probe_media(sample_audio)
    audio_dur = float(audio_probe["duration"])
    assert audio_dur > 0


# -------------------------------------------------------------
# Test 7: Video Duration
# -------------------------------------------------------------
def test_video_duration():
    """Verify generated preview video has valid duration matching requested clip."""
    sample_audio = avatar_service._find_sample_audio(max_duration=10.0)
    response = client.post(
        "/api/avatar/preview",
        json={"audio_path": str(sample_audio), "duration": 5.0, "position": "right"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["duration_seconds"] > 0



# -------------------------------------------------------------
# Test 8: Duration Delta (Audio vs Video Duration Tolerance)
# -------------------------------------------------------------
def test_duration_delta():
    """Verify difference between audio duration and generated avatar video is within 0.5s."""
    sample_audio = avatar_service._find_sample_audio(max_duration=10.0)
    audio_probe = ffmpeg_service.probe_media(sample_audio)
    audio_dur = float(audio_probe["duration"])

    response = client.post(
        "/api/avatar/preview",
        json={"audio_path": str(sample_audio), "duration": 5.0, "position": "left"}
    )
    assert response.status_code == 200
    data = response.json()
    video_dur = data["duration_seconds"]

    delta = abs(video_dur - audio_dur)
    assert delta <= 0.5, f"Duration delta {delta}s exceeds 0.5s tolerance"


# -------------------------------------------------------------
# Test 9: Invalid Image Handling
# -------------------------------------------------------------
def test_invalid_image_handling(tmp_path):
    """Verify CharacterAssetError is raised when the character image does not exist."""
    overlay = TeacherAvatarOverlayProvider()
    fake_img = tmp_path / "non_existent_teacher.png"
    sample_audio = avatar_service._find_sample_audio(max_duration=5.0)

    with pytest.raises(CharacterAssetError):
        overlay.generate(
            image_path=fake_img,
            audio_path=sample_audio,
            output_path=tmp_path / "out.mp4",
        )


# -------------------------------------------------------------
# Test 10: Invalid Audio Handling
# -------------------------------------------------------------
def test_invalid_audio_handling(tmp_path):
    """Verify AvatarError is raised when the input audio file does not exist."""
    overlay = TeacherAvatarOverlayProvider()
    fake_audio = tmp_path / "non_existent_audio.wav"

    with pytest.raises(AvatarError):
        overlay.generate(
            image_path=settings.CANONICAL_TEACHER_IMAGE,
            audio_path=fake_audio,
            output_path=tmp_path / "out.mp4",
        )


# -------------------------------------------------------------
# Test 11: Provider Failure Recovery
# -------------------------------------------------------------
def test_provider_failure_recovery(tmp_path):
    """Verify that if an active provider fails during render(), AvatarRenderer falls back safely."""
    class FailingProvider(AvatarProvider):
        def get_name(self) -> str:
            return "failing_engine"
        def is_animated(self) -> bool:
            return True
        def get_capabilities(self):
            return {"lip_sync": True, "head_motion": True, "full_body_gesture": False}
        def is_available(self) -> bool:
            return True
        def get_unavailability_reason(self):
            return None
        def generate(self, image_path, audio_path, output_path, options=None):
            raise RuntimeError("Simulated neural inference crash!")

    failing_prov = FailingProvider()
    with patch.dict(avatar_service.providers, {"failing_engine": failing_prov}):
        renderer = AvatarRenderer(service=avatar_service)
        routed_scene = RoutedScene(
            scene=VisualScene(
                scene_id="test_fail_scene",
                scene_type=SceneType.TEACHER_INTRO,
                visual_engine=VisualEngine.AVATAR,
                title="Teacher Intro",
                visual_description="Teacher explains",
                narration="Welcome to class",
                duration_seconds=3.0,
                teacher_enabled=True,
                teacher_position=TeacherPosition.RIGHT,
            ),
            selected_engine=VisualEngine.AVATAR,
            routing_reason="Teacher intro scene",
        )

        res = renderer.render(
            scene=routed_scene,
            output_dir=tmp_path / "test_fail_out",
            provider="failing_engine",
        )

        # Scene should still succeed using fallback overlay
        assert res.success is True
        assert res.metadata["fallback_used"] is True
        assert res.metadata["animated"] is False


# -------------------------------------------------------------
# Test 12: Fallback Behavior and Metadata
# -------------------------------------------------------------
def test_fallback_behavior_and_metadata(tmp_path):
    """Verify accurate metadata reporting: animated=False, fallback_used=True, full_body_gesture=False."""
    renderer = AvatarRenderer()
    routed_scene = RoutedScene(
        scene=VisualScene(
            scene_id="test_meta_scene",
            scene_type=SceneType.TEACHER_SUMMARY,
            visual_engine=VisualEngine.AVATAR,
            title="Teacher Summary",
            visual_description="Teacher concludes",
            narration="To summarize Newton's second law",
            duration_seconds=3.0,
            teacher_enabled=True,
            teacher_position=TeacherPosition.LEFT,
        ),
        selected_engine=VisualEngine.AVATAR,
        routing_reason="Summary scene",
    )


    res = renderer.render(
        scene=routed_scene,
        output_dir=tmp_path / "test_meta_out",
        avatar_provider="musetalk",
    )

    assert res.success is True
    assert res.metadata["provider"] in ("overlay", "teacher_overlay")
    assert res.metadata["animated"] is False

    assert res.metadata["lip_sync"] is False
    assert res.metadata["head_motion"] is False
    assert res.metadata["full_body_gesture"] is False
    assert res.metadata["fallback_used"] is True
    assert res.metadata["character"] == "SmartCampus Teacher"
    assert res.metadata["position"] == "left"
