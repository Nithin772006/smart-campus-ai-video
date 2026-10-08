"""
Automated test suite for FFmpeg Service, video composition, and media validation.
Tests FFmpeg & ffprobe availability, media probing, duration extraction, composition,
subtitle burn-in, final MP4 validation, and timing synchronization without speed modification.
"""

import os
import subprocess
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.services.ffmpeg_service import (
    ffmpeg_service,
    find_ffmpeg_binary,
    is_ffmpeg_available,
    is_ffprobe_available,
    get_video_duration,
    validate_audio_video_sync,
    get_subtitle_final_timestamp,
    FFmpegBinaryNotFoundError,
    MediaNotFoundError,
    MediaProbeError,
    VideoCompositionError,
    AudioVideoSyncError,
)
from app.services.subtitle_service import SubtitleService


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# Requirement 1 & 2: FFmpeg and FFprobe Availability
# ==============================================================================

def test_ffmpeg_availability():
    """1. Verify FFmpeg binary availability and detection."""
    assert is_ffmpeg_available(), "FFmpeg binary must be accessible in system PATH or registry"
    ffmpeg_bin = find_ffmpeg_binary("ffmpeg")
    assert ffmpeg_bin is not None, "find_ffmpeg_binary('ffmpeg') must locate valid executable"
    assert Path(ffmpeg_bin).exists(), f"Located FFmpeg binary does not exist on disk: {ffmpeg_bin}"
    assert ffmpeg_service.is_available() is True, "FFmpegService.is_available() must return True"


def test_ffprobe_availability():
    """2. Verify ffprobe binary availability and detection."""
    assert is_ffprobe_available(), "ffprobe binary must be accessible in system PATH or registry"
    ffprobe_bin = find_ffmpeg_binary("ffprobe")
    assert ffprobe_bin is not None, "find_ffmpeg_binary('ffprobe') must locate valid executable"
    assert Path(ffprobe_bin).exists(), f"Located ffprobe binary does not exist on disk: {ffprobe_bin}"


def test_ffmpeg_configuration_settings():
    """Verify that FFmpeg configuration defaults in Settings are correctly set."""
    assert settings.FFMPEG_PATH == "ffmpeg"
    assert settings.FFPROBE_PATH == "ffprobe"
    assert settings.BURN_SUBTITLES is True
    assert settings.VIDEO_CODEC == "libx264"
    assert settings.AUDIO_CODEC == "aac"
    assert settings.VIDEO_CRF == 23
    assert settings.AUDIO_BITRATE == "128k"
    assert settings.PIXEL_FORMAT == "yuv420p"
    assert settings.MOVFLAGS == "+faststart"


# ==============================================================================
# Requirement 3: Media Probing
# ==============================================================================

def test_media_probing():
    """3. Verify media probing extracts comprehensive metadata (codecs, dimensions, durations, pixel format)."""
    # Use real existing assets
    candidates = list((settings.GENERATED_DIR / "scenes").glob("*/*.mp4")) + list((settings.GENERATED_DIR / "videos").glob("*/*.mp4"))
    assert len(candidates) > 0, "At least one real generated video must exist for probing test"
    sample_video = candidates[0]

    probe = ffmpeg_service.probe_media(sample_video)
    assert "duration" in probe, "Probe must contain duration"
    assert "has_video" in probe, "Probe must specify has_video"
    assert "has_audio" in probe, "Probe must specify has_audio"
    assert "size_mb" in probe, "Probe must specify size_mb"
    assert "video_codec" in probe, "Probe must extract video codec"
    assert "pixel_format" in probe, "Probe must extract pixel format"
    assert probe["duration"] > 0, "Video duration must be greater than 0"
    assert probe["has_video"] is True, "Sample file must have a video stream"


# ==============================================================================
# Requirement 4: Audio/Video Duration Extraction
# ==============================================================================

def test_audio_video_duration_extraction():
    """4. Verify audio and video duration extraction using ffprobe."""
    video_candidates = list((settings.GENERATED_DIR / "scenes").glob("*/*.mp4")) + list((settings.GENERATED_DIR / "videos").glob("*/*.mp4"))
    audio_candidates = list((settings.GENERATED_DIR / "audio").glob("*/*.wav"))

    assert len(video_candidates) > 0, "Existing video asset required"
    assert len(audio_candidates) > 0, "Existing audio asset required"

    v_dur = get_video_duration(video_candidates[0])
    assert isinstance(v_dur, float)
    assert v_dur > 0, f"Video duration must be > 0, got {v_dur}"

    a_probe = ffmpeg_service.probe_media(audio_candidates[0])
    a_dur = a_probe["duration"]
    assert isinstance(a_dur, float)
    assert a_dur > 0, f"Audio duration must be > 0, got {a_dur}"
    assert a_probe["has_audio"] is True, "Audio file must contain audio stream"


# ==============================================================================
# Requirement 5: Composition
# ==============================================================================

def test_composition(tmp_path):
    """5. Verify composition of video and audio into synchronized MP4 without modifying audio speed."""
    video_candidates = list((settings.GENERATED_DIR / "scenes").glob("*/*.mp4"))
    audio_candidates = list((settings.GENERATED_DIR / "audio").glob("*/*.wav"))

    assert len(video_candidates) > 0, "Existing scenes MP4 required"
    assert len(audio_candidates) > 0, "Existing audio WAV required"

    v_in = video_candidates[0]
    a_in = audio_candidates[0]
    out_file = tmp_path / "composed_output.mp4"

    result = ffmpeg_service.compose(
        video_path=v_in,
        audio_path=a_in,
        output_path=out_file,
        burn_subtitles=False,
    )

    assert result["success"] is True
    assert out_file.exists()
    assert out_file.stat().st_size > 0
    assert result["has_video"] is True
    assert result["has_audio"] is True
    assert result["video_codec"] == "h264"
    assert result["audio_codec"] == "aac"
    assert result["audio_speed"] == "1.00x"
    assert abs(result["duration_seconds"] - result["audio_duration_seconds"]) <= 0.15


# ==============================================================================
# Requirement 6: Subtitle Burn-In
# ==============================================================================

def test_subtitle_burn_in(tmp_path):
    """6. Verify subtitle burning with FFmpeg libass subtitles filter onto composed video."""
    video_candidates = list((settings.GENERATED_DIR / "scenes").glob("*/*.mp4"))
    audio_candidates = list((settings.GENERATED_DIR / "audio").glob("*/*.wav"))
    sub_candidates = list((settings.GENERATED_DIR / "subtitles").glob("*/*.srt"))

    assert len(video_candidates) > 0, "Existing scenes MP4 required"
    assert len(audio_candidates) > 0, "Existing audio WAV required"
    assert len(sub_candidates) > 0, "Existing subtitles SRT required"

    v_in = video_candidates[0]
    a_in = audio_candidates[0]
    s_in = sub_candidates[0]
    out_file = tmp_path / "subtitled_output.mp4"

    result = ffmpeg_service.compose(
        video_path=v_in,
        audio_path=a_in,
        subtitle_path=s_in,
        output_path=out_file,
        burn_subtitles=True,
    )

    assert result["success"] is True
    assert out_file.exists()
    assert result["has_subtitles"] is True
    assert result["subtitles_burned"] is True
    assert result["has_video"] is True
    assert result["has_audio"] is True


# ==============================================================================
# Requirement 7: Final MP4 Validation
# ==============================================================================

def test_final_mp4_validation(tmp_path):
    """7. Deep validation of final MP4: H.264 video, AAC audio, yuv420p, faststart, and duration sync."""
    video_candidates = list((settings.GENERATED_DIR / "scenes").glob("*/*.mp4"))
    audio_candidates = list((settings.GENERATED_DIR / "audio").glob("*/*.wav"))
    sub_candidates = list((settings.GENERATED_DIR / "subtitles").glob("*/*.srt"))

    v_in = video_candidates[0]
    a_in = audio_candidates[0]
    s_in = sub_candidates[0] if sub_candidates else None
    out_file = tmp_path / "validated_final.mp4"

    result = ffmpeg_service.compose(
        video_path=v_in,
        audio_path=a_in,
        subtitle_path=s_in,
        output_path=out_file,
        burn_subtitles=bool(s_in),
    )

    # Inspect final file with ffprobe
    probe = ffmpeg_service.probe_media(out_file)
    assert probe["has_video"] is True, "Final MP4 must have a video stream"
    assert probe["has_audio"] is True, "Final MP4 must have an audio stream"
    assert probe["video_codec"] == "h264", f"Expected h264, got {probe['video_codec']}"
    assert probe["audio_codec"] == "aac", f"Expected aac, got {probe['audio_codec']}"
    assert probe["pixel_format"] == "yuv420p", f"Expected yuv420p, got {probe['pixel_format']}"

    # Verify duration synchronization with master audio timeline
    sync = validate_audio_video_sync(out_file, a_in, tolerance_seconds=0.15)
    assert sync["is_synchronized"] is True
    assert sync["duration_difference"] <= 0.15
    assert sync["audio_speed"] == "1.00x"


# ==============================================================================
# Error Handling & Custom Exceptions Tests
# ==============================================================================

def test_missing_input_raises_media_not_found():
    """Ensure composing with missing files raises MediaNotFoundError (which inherits from FileNotFoundError)."""
    with pytest.raises(MediaNotFoundError):
        ffmpeg_service.compose(
            video_path="non_existent_video_123.mp4",
            audio_path="non_existent_audio_123.wav",
        )


def test_api_compose_endpoint(client):
    """Test the POST /api/video/compose endpoint via TestClient."""
    video_candidates = list((settings.GENERATED_DIR / "scenes").glob("*/*.mp4"))
    audio_candidates = list((settings.GENERATED_DIR / "audio").glob("*/*.wav"))
    sub_candidates = list((settings.GENERATED_DIR / "subtitles").glob("*/*.srt"))

    assert len(video_candidates) > 0
    assert len(audio_candidates) > 0

    payload = {
        "video_path": str(video_candidates[0]),
        "audio_path": str(audio_candidates[0]),
        "subtitle_path": str(sub_candidates[0]) if sub_candidates else None,
        "burn_subtitles": bool(sub_candidates),
        "output_name": "api_test_output.mp4",
    }

    response = client.post("/api/video/compose", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "duration_seconds" in data
    assert "video_path" in data
    assert data["has_video"] is True
    assert data["has_audio"] is True
    assert "output_size_mb" in data or "file_size_mb" in data
    assert "subtitles_burned" in data


def test_api_compose_missing_file_returns_404(client):
    """Test that POST /api/video/compose returns 404 on missing media."""
    payload = {
        "video_path": "non_existent_file_abc.mp4",
        "audio_path": "non_existent_file_def.wav",
    }
    response = client.post("/api/video/compose", json=payload)
    assert response.status_code == 404


# ==============================================================================
# Synchronization & Timing Rule Verification (Audio is Master Clock)
# ==============================================================================

def _generate_synthetic_video(output_path: Path, duration_sec: float) -> Path:
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"testsrc=duration={duration_sec}:size=320x240:rate=15",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def _generate_synthetic_audio(output_path: Path, duration_sec: float, sample_rate: int = 24000) -> Path:
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"sine=frequency=440:duration={duration_sec}:sample_rate={sample_rate}",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def test_sync_case_1_video_20s_audio_25s_extends_video(tmp_path):
    """
    CASE 1: visual = 20 sec, audio = 25 sec
    Expected: final ≈ 25 sec, audio remains normal speed (1.00x)
    """
    v_path = _generate_synthetic_video(tmp_path / "v20.mp4", 20.0)
    a_path = _generate_synthetic_audio(tmp_path / "a25.wav", 25.0)
    out_path = tmp_path / "out_case1.mp4"

    result = ffmpeg_service.compose(
        video_path=v_path,
        audio_path=a_path,
        output_path=out_path,
    )

    assert result["success"] is True
    assert abs(result["duration_seconds"] - 25.0) <= 0.15
    assert abs(result["audio_duration_seconds"] - 25.0) <= 0.15
    assert result["audio_speed"] == "1.00x"
    assert result["is_synchronized"] is True

    sync = validate_audio_video_sync(out_path, a_path, tolerance_seconds=0.15)
    assert abs(sync["video_duration"] - 25.0) <= 0.15
    assert abs(sync["audio_duration"] - 25.0) <= 0.15
    assert abs(sync["duration_difference"]) <= 0.15


def test_sync_case_2_video_30s_audio_25s_trims_video(tmp_path):
    """
    CASE 2: visual = 30 sec, audio = 25 sec
    Expected: final ≈ 25 sec, trimmed visual stream, audio remains normal speed (1.00x)
    """
    v_path = _generate_synthetic_video(tmp_path / "v30.mp4", 30.0)
    a_path = _generate_synthetic_audio(tmp_path / "a25.wav", 25.0)
    out_path = tmp_path / "out_case2.mp4"

    result = ffmpeg_service.compose(
        video_path=v_path,
        audio_path=a_path,
        output_path=out_path,
    )

    assert result["success"] is True
    assert abs(result["duration_seconds"] - 25.0) <= 0.15
    assert abs(result["audio_duration_seconds"] - 25.0) <= 0.15
    assert result["audio_speed"] == "1.00x"
    assert result["is_synchronized"] is True

    sync = validate_audio_video_sync(out_path, a_path, tolerance_seconds=0.15)
    assert abs(sync["video_duration"] - 25.0) <= 0.15
    assert abs(sync["audio_duration"] - 25.0) <= 0.15
    assert abs(sync["duration_difference"]) <= 0.15


def test_sync_case_3_video_25s_audio_25s_direct_compose(tmp_path):
    """
    CASE 3: visual = 25 sec, audio = 25 sec
    Expected: directly compose, final ≈ 25 sec
    """
    v_path = _generate_synthetic_video(tmp_path / "v25.mp4", 25.0)
    a_path = _generate_synthetic_audio(tmp_path / "a25.wav", 25.0)
    out_path = tmp_path / "out_case3.mp4"

    result = ffmpeg_service.compose(
        video_path=v_path,
        audio_path=a_path,
        output_path=out_path,
    )

    assert result["success"] is True
    assert abs(result["duration_seconds"] - 25.0) <= 0.15
    assert abs(result["audio_duration_seconds"] - 25.0) <= 0.15
    assert result["is_synchronized"] is True


def test_no_audio_speed_changing_filters(tmp_path, monkeypatch):
    """Verify that NO audio speed-changing filter (atempo, asetrate, rubberband, asetpts) is ever used."""
    v_path = _generate_synthetic_video(tmp_path / "v10.mp4", 10.0)
    a_path = _generate_synthetic_audio(tmp_path / "a15.wav", 15.0)
    out_path = tmp_path / "out_case4.mp4"

    executed_cmds = []
    original_run = subprocess.run

    def intercept_run(cmd, *args, **kwargs):
        executed_cmds.append(cmd)
        return original_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", intercept_run)

    ffmpeg_service.compose(
        video_path=v_path,
        audio_path=a_path,
        output_path=out_path,
    )

    prohibited_filters = ["atempo", "asetrate", "rubberband", "asetpts"]
    for cmd in executed_cmds:
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
        for prohibited in prohibited_filters:
            assert prohibited not in cmd_str, f"Found prohibited audio filter '{prohibited}' in command: {cmd_str}"
        if "-af" in cmd:
            af_idx = cmd.index("-af")
            af_val = cmd[af_idx + 1]
            for prohibited in prohibited_filters:
                assert prohibited not in af_val, f"Found prohibited filter '{prohibited}' in -af: {af_val}"


def test_subtitle_timestamps_remain_on_original_audio_timeline(tmp_path):
    """Verify subtitle timestamps remain based on original audio timing without rescaling or compression."""
    segments = [
        {"id": 0, "start": 0.5, "end": 4.2, "text": "Newton's Second Law of Motion."},
        {"id": 1, "start": 5.0, "end": 12.8, "text": "Force equals mass multiplied by acceleration."},
        {"id": 2, "start": 14.1, "end": 28.97, "text": "F equals m times a."},
    ]

    srt_content = SubtitleService.generate_srt(segments)
    srt_file = tmp_path / "sample.srt"
    srt_file.write_text(srt_content, encoding="utf-8")

    final_ts = get_subtitle_final_timestamp(srt_file)
    assert final_ts == 28.97, f"Expected final timestamp 28.97s, got {final_ts}s"
    assert "00:00:28,970" in srt_content
    assert "00:00:00,500" in srt_content
