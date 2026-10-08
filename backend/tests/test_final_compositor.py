"""
Unit and integration test suite for FinalCompositor and timeline synchronization (Task 9D).
Tests cover:
A. Basic composition with sequential scene MP4s
B. Audio synchronization (Audio as Master Clock: sync delta <= 0.15s)
C. Video extension (tpad last-frame hold when narration audio exceeds visual length)
D. Subtitle burning into final MP4
E. Subtitle external mode (SRT preserved without hardcoding)
F. Aspect ratio and resolution normalization (854x480, portrait 1144x1374 -> uniform 1280x720)
G. Crossfade transitions between consecutive scenes
H. Cloud scene failure handling (graceful fallback without pipeline termination)
I. Verification of timeline.json and metadata.json schema exports
J. Single failed scene resilience in multi-scene batch
K. API endpoint testing (POST /api/video/compose)
"""

import os
import json
import shutil
import subprocess
import pytest
from pathlib import Path
from typing import Tuple

from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.schemas.render import RenderedScene
from app.services.final_compositor import FinalCompositor, final_compositor
from app.services.ffmpeg_service import ffmpeg_service, find_ffmpeg_binary


@pytest.fixture(scope="module")
def client():
    """FastAPI test client fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def ffmpeg_bin():
    """Locate ffmpeg binary."""
    bin_path = find_ffmpeg_binary("ffmpeg")
    assert bin_path is not None, "FFmpeg binary must be available for compositor tests"
    return bin_path


def make_test_video(path: Path, duration: float, width: int = 1280, height: int = 720, color: str = "blue"):
    """Creates a real lightweight H.264 MP4 clip with specified resolution and duration."""
    ffmpeg = find_ffmpeg_binary("ffmpeg")
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-f", "lavfi",
        "-i", f"color=c={color}:s={width}x{height}:d={duration:.2f}:r=30",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-an",
        str(path),
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert path.exists() and path.stat().st_size > 0


def make_test_audio(path: Path, duration: float):
    """Creates a real WAV audio file with specified duration."""
    ffmpeg = find_ffmpeg_binary("ffmpeg")
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-f", "lavfi",
        "-i", f"sine=frequency=440:sample_rate=44100:duration={duration:.2f}",
        "-c:a", "pcm_s16le",
        str(path),
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert path.exists() and path.stat().st_size > 0


def make_test_srt(path: Path):
    """Creates a standard test SRT subtitle file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "1\n"
        "00:00:00,500 --> 00:00:02,500\n"
        "Newton's Second Law describes how force accelerates mass.\n\n"
        "2\n"
        "00:00:02,800 --> 00:00:04,800\n"
        "The formula is F equals m times a.\n"
    )
    path.write_text(content, encoding="utf-8")
    assert path.exists()


# ==============================================================================
# Test A: Basic composition with 3 short scenes
# ==============================================================================

def test_a_basic_composition(tmp_path):
    compositor = FinalCompositor(output_base_dir=tmp_path)

    v1 = tmp_path / "sc1.mp4"
    v2 = tmp_path / "sc2.mp4"
    v3 = tmp_path / "sc3.mp4"
    audio = tmp_path / "narration.wav"

    make_test_video(v1, duration=2.0, color="red")
    make_test_video(v2, duration=2.0, color="green")
    make_test_video(v3, duration=2.0, color="blue")
    make_test_audio(audio, duration=6.0)

    scenes = [
        RenderedScene(scene_id="scene_1", video_path=str(v1), duration_seconds=2.0, engine="avatar", success=True),
        RenderedScene(scene_id="scene_2", video_path=str(v2), duration_seconds=2.0, engine="manim", success=True),
        RenderedScene(scene_id="scene_3", video_path=str(v3), duration_seconds=2.0, engine="manim", success=True),
    ]

    result = compositor.compose(
        topic="Test Basic",
        scenes=scenes,
        audio_path=audio,
        output_dir=tmp_path / "output",
        transition_enabled=False,
    )

    assert result.success is True
    out_file = Path(result.video_path)
    if not out_file.is_absolute():
        out_file = settings.BASE_DIR / out_file
    assert out_file.exists()
    assert out_file.stat().st_size > 0
    assert result.scene_count == 3
    assert result.video_codec == "h264"
    assert result.audio_codec == "aac"


# ==============================================================================
# Test B: Audio synchronization (Audio is Master Clock)
# ==============================================================================

def test_b_audio_synchronization_within_tolerance(tmp_path):
    compositor = FinalCompositor(output_base_dir=tmp_path)

    v1 = tmp_path / "sc1.mp4"
    audio = tmp_path / "narration.wav"

    make_test_video(v1, duration=4.0, color="purple")
    # Master audio is 4.05s
    make_test_audio(audio, duration=4.05)

    scenes = [
        RenderedScene(scene_id="scene_1", video_path=str(v1), duration_seconds=4.0, engine="manim", success=True),
    ]

    result = compositor.compose(
        topic="Test Sync",
        scenes=scenes,
        audio_path=audio,
        output_dir=tmp_path / "output",
        tolerance_seconds=0.15,
    )

    assert result.success is True
    # Verify sync delta <= 0.15s
    assert result.sync_delta_seconds <= 0.15
    assert abs(result.duration_seconds - result.audio_duration_seconds) <= 0.15


# ==============================================================================
# Test C: Longer audio (Visuals extended via tpad, audio NOT sped up)
# ==============================================================================

def test_c_longer_audio_extends_video(tmp_path):
    compositor = FinalCompositor(output_base_dir=tmp_path)

    v1 = tmp_path / "sc1.mp4"
    v2 = tmp_path / "sc2.mp4"
    audio = tmp_path / "narration_long.wav"

    # Total video is 4.0s (2.0 + 2.0)
    make_test_video(v1, duration=2.0, color="orange")
    make_test_video(v2, duration=2.0, color="yellow")
    # Audio is significantly longer: 6.5s
    make_test_audio(audio, duration=6.5)

    scenes = [
        RenderedScene(scene_id="scene_1", video_path=str(v1), duration_seconds=2.0, engine="avatar", success=True),
        RenderedScene(scene_id="scene_2", video_path=str(v2), duration_seconds=2.0, engine="manim", success=True),
    ]

    result = compositor.compose(
        topic="Test Extended",
        scenes=scenes,
        audio_path=audio,
        output_dir=tmp_path / "output",
        transition_enabled=False,
    )

    assert result.success is True
    # Video duration should be extended to match audio duration within 0.15s
    assert abs(result.duration_seconds - 6.5) <= 0.15
    assert result.sync_delta_seconds <= 0.15


# ==============================================================================
# Test D: Subtitle burning
# ==============================================================================

def test_d_subtitle_burning_enabled(tmp_path):
    compositor = FinalCompositor(output_base_dir=tmp_path)

    v1 = tmp_path / "sc1.mp4"
    audio = tmp_path / "narration.wav"
    srt = tmp_path / "subtitles.srt"

    make_test_video(v1, duration=4.0)
    make_test_audio(audio, duration=4.0)
    make_test_srt(srt)

    scenes = [
        RenderedScene(scene_id="scene_1", video_path=str(v1), duration_seconds=4.0, engine="manim", success=True),
    ]

    result = compositor.compose(
        topic="Test Subtitles Burned",
        scenes=scenes,
        audio_path=audio,
        subtitle_path=srt,
        output_dir=tmp_path / "output",
        burn_subtitles=True,
    )

    assert result.success is True
    assert result.subtitle_burned is True
    assert result.subtitle_path is not None


# ==============================================================================
# Test E: Subtitle external mode (burn_subtitles = False)
# ==============================================================================

def test_e_subtitle_external_mode(tmp_path):
    compositor = FinalCompositor(output_base_dir=tmp_path)

    v1 = tmp_path / "sc1.mp4"
    audio = tmp_path / "narration.wav"
    srt = tmp_path / "subtitles.srt"

    make_test_video(v1, duration=3.0)
    make_test_audio(audio, duration=3.0)
    make_test_srt(srt)

    scenes = [
        RenderedScene(scene_id="scene_1", video_path=str(v1), duration_seconds=3.0, engine="manim", success=True),
    ]

    result = compositor.compose(
        topic="Test Subtitles External",
        scenes=scenes,
        audio_path=audio,
        subtitle_path=srt,
        output_dir=tmp_path / "output",
        burn_subtitles=False,
    )

    assert result.success is True
    assert result.subtitle_burned is False
    # SRT should be preserved as final.srt in the output directory
    final_srt = (tmp_path / "output") / "final.srt"
    assert final_srt.exists()


# ==============================================================================
# Test F: Different resolutions normalized to uniform 1280x720
# ==============================================================================

def test_f_different_resolutions_normalized(tmp_path):
    compositor = FinalCompositor(output_base_dir=tmp_path)

    # 1. 854x480 (Manim standard resolution)
    v_manim = tmp_path / "manim.mp4"
    make_test_video(v_manim, duration=2.0, width=854, height=480, color="navy")

    # 2. 1144x1374 (Portrait Avatar resolution)
    v_avatar = tmp_path / "avatar.mp4"
    make_test_video(v_avatar, duration=2.0, width=1144, height=1374, color="darkgreen")

    # 3. 1920x1080 (HD clip)
    v_hd = tmp_path / "hd.mp4"
    make_test_video(v_hd, duration=2.0, width=1920, height=1080, color="darkred")

    audio = tmp_path / "narration.wav"
    make_test_audio(audio, duration=6.0)

    scenes = [
        RenderedScene(scene_id="scene_manim", video_path=str(v_manim), duration_seconds=2.0, engine="manim", success=True),
        RenderedScene(scene_id="scene_avatar", video_path=str(v_avatar), duration_seconds=2.0, engine="avatar", success=True),
        RenderedScene(scene_id="scene_hd", video_path=str(v_hd), duration_seconds=2.0, engine="cloud_video", success=True),
    ]

    result = compositor.compose(
        topic="Test Resolutions",
        scenes=scenes,
        audio_path=audio,
        output_dir=tmp_path / "output",
        transition_enabled=False,
    )

    assert result.success is True
    assert result.resolution == "1280x720"
    out_file = Path(result.video_path)
    if not out_file.is_absolute():
        out_file = settings.BASE_DIR / out_file
    probe = ffmpeg_service.probe_media(out_file)
    assert probe["width"] == 1280
    assert probe["height"] == 720
    assert probe["pixel_format"] == "yuv420p"


# ==============================================================================
# Test G: Crossfade transitions
# ==============================================================================

def test_g_transitions_enabled(tmp_path):
    compositor = FinalCompositor(output_base_dir=tmp_path)

    v1 = tmp_path / "sc1.mp4"
    v2 = tmp_path / "sc2.mp4"
    audio = tmp_path / "narration.wav"

    make_test_video(v1, duration=3.0, color="maroon")
    make_test_video(v2, duration=3.0, color="teal")
    make_test_audio(audio, duration=5.8)

    scenes = [
        RenderedScene(scene_id="scene_1", video_path=str(v1), duration_seconds=3.0, engine="avatar", success=True),
        RenderedScene(scene_id="scene_2", video_path=str(v2), duration_seconds=3.0, engine="manim", success=True),
    ]

    result = compositor.compose(
        topic="Test Transition",
        scenes=scenes,
        audio_path=audio,
        output_dir=tmp_path / "output",
        transition_enabled=True,
        transition_duration_seconds=0.3,
    )

    assert result.success is True
    assert result.sync_delta_seconds <= 0.15


# ==============================================================================
# Test H: Cloud failure handled cleanly with educational fallback
# ==============================================================================

def test_h_cloud_failure_handled_cleanly(tmp_path):
    compositor = FinalCompositor(output_base_dir=tmp_path)

    v1 = tmp_path / "sc1.mp4"
    audio = tmp_path / "narration.wav"

    make_test_video(v1, duration=2.5, color="indigo")
    make_test_audio(audio, duration=5.5)

    # Scene 2 represents a cloud scene that failed with HTTP 402 Payment Required
    scenes = [
        RenderedScene(scene_id="scene_1", video_path=str(v1), duration_seconds=2.5, engine="manim", success=True),
        RenderedScene(
            scene_id="scene_2",
            video_path="",
            duration_seconds=3.0,
            engine="cloud_video",
            success=False,
            error="Cloud video provider credit balance exhausted (HTTP 402 Payment Required).",
            metadata={"visual_description": "Mass acceleration under applied force"}
        ),
    ]

    result = compositor.compose(
        topic="Test Cloud Fallback",
        scenes=scenes,
        audio_path=audio,
        output_dir=tmp_path / "output",
        transition_enabled=False,
    )

    assert result.success is True
    assert result.cloud_fallback_used is True
    assert result.scene_count == 2
    out_file = Path(result.video_path)
    if not out_file.is_absolute():
        out_file = settings.BASE_DIR / out_file
    assert out_file.exists()


# ==============================================================================
# Test I: Timeline.json and metadata.json export
# ==============================================================================

def test_i_timeline_and_metadata_files_created(tmp_path):
    compositor = FinalCompositor(output_base_dir=tmp_path)

    v1 = tmp_path / "sc1.mp4"
    audio = tmp_path / "narration.wav"

    make_test_video(v1, duration=3.0)
    make_test_audio(audio, duration=3.0)

    scenes = [
        RenderedScene(scene_id="scene_1", video_path=str(v1), duration_seconds=3.0, engine="manim", success=True),
    ]

    out_dir = tmp_path / "output"
    result = compositor.compose(
        topic="Newton's Second Law",
        scenes=scenes,
        audio_path=audio,
        output_dir=out_dir,
    )

    assert result.success is True
    timeline_file = out_dir / "timeline.json"
    metadata_file = out_dir / "metadata.json"

    assert timeline_file.exists(), "timeline.json must be created"
    assert metadata_file.exists(), "metadata.json must be created"

    timeline_data = json.loads(timeline_file.read_text(encoding="utf-8"))
    assert timeline_data["topic"] == "Newton's Second Law"
    assert "audio_duration" in timeline_data
    assert "final_duration" in timeline_data
    assert len(timeline_data["scenes"]) == 1

    metadata_data = json.loads(metadata_file.read_text(encoding="utf-8"))
    assert metadata_data["video_codec"] == "h264"
    assert metadata_data["audio_codec"] == "aac"
    assert metadata_data["resolution"] == "1280x720"


# ==============================================================================
# Test J: Single failed scene resilience in multi-scene batch
# ==============================================================================

def test_j_single_failed_scene_resilience(tmp_path):
    compositor = FinalCompositor(output_base_dir=tmp_path)

    v1 = tmp_path / "sc1.mp4"
    v3 = tmp_path / "sc3.mp4"
    audio = tmp_path / "narration.wav"

    make_test_video(v1, duration=2.0, color="crimson")
    make_test_video(v3, duration=2.0, color="royalblue")
    make_test_audio(audio, duration=6.0)

    # Scene 2 had an error (e.g. invalid syntax or missing file)
    scenes = [
        RenderedScene(scene_id="scene_1", video_path=str(v1), duration_seconds=2.0, engine="avatar", success=True),
        RenderedScene(scene_id="scene_2", video_path="", duration_seconds=2.0, engine="manim", success=False, error="Syntax error"),
        RenderedScene(scene_id="scene_3", video_path=str(v3), duration_seconds=2.0, engine="manim", success=True),
    ]

    result = compositor.compose(
        topic="Test Error Resilience",
        scenes=scenes,
        audio_path=audio,
        output_dir=tmp_path / "output",
        transition_enabled=False,
    )

    assert result.success is True
    assert result.scene_count == 3
    assert result.sync_delta_seconds <= 0.15


# ==============================================================================
# Test K: POST /api/video/compose endpoint
# ==============================================================================

def test_k_api_compose_endpoint_topic(client, tmp_path, monkeypatch):
    """Verify POST /api/video/compose endpoint responds successfully with ComposedVideoResult."""
    # Mock compose_topic to avoid generating fresh long media during API unit test
    mock_result = {
        "success": True,
        "topic": "Newton's Second Law",
        "video_path": "generated/videos/newtons_second_law/final.mp4",
        "duration_seconds": 24.5,
        "audio_duration_seconds": 24.5,
        "sync_delta_seconds": 0.0,
        "scene_count": 4,
        "output_size_mb": 2.5,
        "video_codec": "h264",
        "audio_codec": "aac",
        "pixel_format": "yuv420p",
        "resolution": "1280x720",
        "fps": 30.0,
        "subtitle_burned": True,
        "subtitle_path": "generated/subtitles/newtons_second_law/subtitles.srt",
        "timeline_path": "generated/videos/newtons_second_law/timeline.json",
        "metadata_path": "generated/videos/newtons_second_law/metadata.json",
        "cloud_fallback_used": False,
        "scenes": [],
        "execution_time_seconds": 1.2,
    }

    monkeypatch.setattr(
        "app.services.final_compositor.FinalCompositor.compose_topic",
        lambda *args, **kwargs: mock_result
    )

    response = client.post("/api/video/compose", json={
        "topic": "Newton's Second Law",
        "quality": "low_quality",
        "subtitle_enabled": True,
        "burn_subtitles": True,
        "transition_enabled": True,
    })

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["topic"] == "Newton's Second Law"
    assert data["resolution"] == "1280x720"
    assert data["sync_delta_seconds"] <= 0.15
