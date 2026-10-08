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
from PIL import Image

from app.config import settings
from app.main import app
from app.schemas.character import (
    CharacterPosition,
    CharacterExpression,
    CharacterGesture,
    CharacterState,
    CharacterSpec,
    AvatarPreviewRequest,
    AvatarPreviewResponse,
)
from app.schemas.scene import ScenePlanItem, SceneType
from app.schemas.video import FullVideoRequest, FullVideoResponse
from app.services.avatar_service import (
    avatar_service,
    AvatarProvider,
    MuseTalkAvatarProvider,
    TeacherAvatarOverlayProvider,
    AvatarProviderUnavailableError,
    CharacterAssetError,
)
from app.services.ffmpeg_service import ffmpeg_service
from app.pipelines.video_composition import (
    video_composition_pipeline,
    full_educational_video_pipeline,
)

client = TestClient(app)


# -------------------------------------------------------------
# Test 1: Avatar Configuration Defaults
# -------------------------------------------------------------
def test_avatar_configuration():
    """Verify avatar configuration defaults adhere strictly to Task 8 requirements."""
    assert hasattr(settings, "AVATAR_ENABLED")
    assert settings.AVATAR_ENABLED is False  # Must default to False (disabled)
    assert hasattr(settings, "AVATAR_PROVIDER")
    assert settings.AVATAR_PROVIDER == "musetalk"
    assert hasattr(settings, "AVATAR_CHARACTER")
    assert settings.AVATAR_CHARACTER == "teacher"
    assert hasattr(settings, "AVATAR_DEVICE")
    assert settings.AVATAR_MAX_VRAM_GB == 4
    assert settings.CHARACTER_DIR == settings.BASE_DIR / "assets" / "character"
    assert settings.CANONICAL_TEACHER_IMAGE == settings.CHARACTER_DIR / "teacher.png"


# -------------------------------------------------------------
# Test 2: Canonical Character Image Exists
# -------------------------------------------------------------
def test_canonical_character_exists():
    """Verify the canonical teacher.png is present in backend/assets/character/."""
    teacher_img = settings.CANONICAL_TEACHER_IMAGE
    assert teacher_img.exists(), f"Canonical teacher image missing at {teacher_img}"
    assert teacher_img.is_file()
    assert teacher_img.stat().st_size > 500_000, "Teacher image file size appears too small"


# -------------------------------------------------------------
# Test 3: Character Metadata Exists & Complies
# -------------------------------------------------------------
def test_character_metadata():
    """Verify character_spec.json and README.md conform to canonical specifications."""
    spec_path = settings.CHARACTER_DIR / "character_spec.json"
    readme_path = settings.CHARACTER_DIR / "README.md"

    assert spec_path.exists(), "character_spec.json missing"
    assert readme_path.exists(), "README.md missing in character directory"

    data = json.loads(spec_path.read_text(encoding="utf-8"))
    assert data["name"] == "SmartCampus Teacher"
    assert data["version"] == "1.0"
    assert data["style"] == "modern_educational_3d"
    assert data["view"] == "front_three_quarter"
    assert data["framing"] == "upper_body"
    assert data["background"] == "transparent"
    assert data["canonical_image"] == "teacher.png"
    assert data["intended_use"] == "talking_avatar"


# -------------------------------------------------------------
# Test 4: Character Image Integrity & Transparency Validation
# -------------------------------------------------------------
def test_character_image_validation():
    """Verify canonical teacher image format, transparency, and dimensions."""
    val = avatar_service.validate_canonical_character()
    assert val["width"] == 1145
    assert val["height"] == 1374
    assert val["mode"] == "RGBA"
    assert val["has_alpha"] is True
    assert val["size_bytes"] > 1_000_000


# -------------------------------------------------------------
# Test 5: Provider Abstraction & Interface
# -------------------------------------------------------------
def test_avatar_provider_interface():
    """Verify AvatarProvider abstract base class contracts."""
    assert issubclass(MuseTalkAvatarProvider, AvatarProvider)
    assert issubclass(TeacherAvatarOverlayProvider, AvatarProvider)

    overlay_provider = TeacherAvatarOverlayProvider()
    assert overlay_provider.get_name() == "overlay"
    assert isinstance(overlay_provider.is_available(), bool)

    musetalk_provider = MuseTalkAvatarProvider()
    assert musetalk_provider.get_name() == "musetalk"
    assert isinstance(musetalk_provider.is_available(), bool)


# -------------------------------------------------------------
# Test 6: Provider Selection & Fallback Logic
# -------------------------------------------------------------
def test_provider_selection_and_fallback():
    """Verify graceful fallback when MuseTalk is unavailable."""
    # When requesting overlay directly
    prov = avatar_service.get_provider("overlay")
    assert prov.get_name() == "overlay"

    # When requesting musetalk on hardware without full toolchain, falls back to overlay
    active_prov = avatar_service.get_provider("musetalk")
    assert active_prov is not None
    # On target 4GB Windows machine, fallback to overlay is activated
    assert active_prov.get_name() in ("musetalk", "overlay")


# -------------------------------------------------------------
# Test 7: MuseTalk Availability Detection (Isolated Feasibility)
# -------------------------------------------------------------
def test_musetalk_availability_check():
    """Verify MuseTalk provider correctly reports its status without crashing."""
    musetalk_provider = MuseTalkAvatarProvider()
    avail = musetalk_provider.is_available()
    assert isinstance(avail, bool)

    # If unavailable, generate() must raise informative AvatarProviderUnavailableError
    if not avail:
        with pytest.raises(AvatarProviderUnavailableError) as exc_info:
            musetalk_provider.generate(
                image_path=settings.CANONICAL_TEACHER_IMAGE,
                audio_path=Path("dummy.wav"),
                output_path=Path("dummy.mp4"),
            )
        assert "FEASIBILITY_REPORT" in str(exc_info.value) or "MuseTalk is not available" in str(exc_info.value)


# -------------------------------------------------------------
# Test 8: Character Metadata & Scene Schema Compatibility
# -------------------------------------------------------------
def test_character_scene_metadata():
    """Verify future-compatible character state metadata in scene plan schema."""
    item = ScenePlanItem(
        id=1,
        type=SceneType.FORMULA,
        duration=5.0,
        title="Newton's Law",
        formula="F = ma",
        character_expression="friendly",
        character_gesture="explain",
        character_visible=True,
    )
    assert item.character_expression == "friendly"
    assert item.character_gesture == "explain"
    assert item.character_visible is True


# -------------------------------------------------------------
# Test 9: Avatar Preview API via HTTP Client
# -------------------------------------------------------------
def test_avatar_preview_api_endpoint():
    """Test POST /api/avatar/preview endpoint generates valid response."""
    response = client.post("/api/avatar/preview", json={"duration": 5.0, "position": "right"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["provider"] in ("musetalk", "overlay")
    assert data["character_name"] == "SmartCampus Teacher"
    assert data["duration_seconds"] > 0
    assert data["generation_time_seconds"] >= 0
    assert "video_path" in data


# -------------------------------------------------------------
# Test 10: Character Metadata API Endpoint
# -------------------------------------------------------------
def test_avatar_character_metadata_api():
    """Test GET /api/avatar/character endpoint returns character inspection."""
    response = client.get("/api/avatar/character")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    char = data["character"]
    assert char["width"] == 1145
    assert char["height"] == 1374
    assert char["has_alpha"] is True
    assert char["spec"]["name"] == "SmartCampus Teacher"


# -------------------------------------------------------------
# Test 11: Disabled Character Backward Compatibility
# -------------------------------------------------------------
def test_disabled_character_compatibility():
    """Verify full video request with character=False functions identically."""
    req = FullVideoRequest(
        topic="Explain Newton's Second Law",
        character=False,
        character_position="auto",
    )
    assert req.character is False
    assert req.character_position == "auto"


# -------------------------------------------------------------
# Test 12: Full Pipeline Request & Response Schema Validation
# -------------------------------------------------------------
def test_full_pipeline_character_schemas():
    """Verify FullVideoRequest and FullVideoResponse support character fields."""
    req = FullVideoRequest(
        topic="Photosynthesis",
        character=True,
        character_position="right",
        visual_style="academic",
    )
    assert req.character is True
    assert req.character_position == "right"
    assert req.visual_style == "academic"

    resp = FullVideoResponse(
        success=True,
        topic="Photosynthesis",
        video_path="generated/videos/photosynthesis/final.mp4",
        duration_seconds=25.0,
        scene_count=4,
        audio_duration_seconds=25.0,
        subtitle_segment_count=5,
        generation_time_seconds=12.5,
        character_enabled=True,
        character_position="right",
        character_video_path="assets/character/teacher.png",
    )
    assert resp.character_enabled is True
    assert resp.character_position == "right"


if __name__ == "__main__":
    pytest.main(["-v", str(Path(__file__))])
