"""
Automated Test Suite for Whisper Service and Subtitle Generation (Task 6).
Tests service configuration, device selection, timestamp formatting,
SRT/VTT formatting, segment validations, and real faster-whisper transcription.
"""

import sys
import shutil
from pathlib import Path
import pytest

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.services.whisper_service import WhisperService, whisper_service
from app.services.subtitle_service import (
    SubtitleService,
    subtitle_service,
    format_srt_timestamp,
    format_vtt_timestamp,
)

client = TestClient(app)


# ==============================================================================
# TEST 1: Service Configuration & Device Selection Tests
# ==============================================================================
def test_whisper_configuration():
    """Verify default Whisper settings and service initialization."""
    assert hasattr(settings, "WHISPER_MODEL")
    assert hasattr(settings, "WHISPER_DEVICE")
    assert hasattr(settings, "WHISPER_COMPUTE_TYPE")
    assert hasattr(settings, "SUBTITLES_DIR")
    assert settings.SUBTITLES_DIR.exists()

    service = WhisperService()
    assert service.model_name in ["base", "tiny", "small"]
    assert service.device in ["cuda", "cpu"]
    assert service.compute_type in ["float16", "int8", "int8_float16", "float32"]


def test_device_and_compute_type_resolution():
    """Verify safe fallback resolution for CUDA vs CPU."""
    # Test CPU resolution
    assert WhisperService._resolve_target_device("cpu") == "cpu"
    assert WhisperService._resolve_compute_type("cpu", "auto") == "int8"
    assert WhisperService._resolve_compute_type("cuda", "auto") == "float16"
    assert WhisperService._resolve_compute_type("cuda", "custom_type") == "custom_type"


# ==============================================================================
# TEST 2: Timestamp Formatting Tests (SRT vs VTT)
# ==============================================================================
def test_srt_timestamp_formatting():
    """Verify SRT timestamp format: HH:MM:SS,mmm"""
    assert format_srt_timestamp(0.0) == "00:00:00,000"
    assert format_srt_timestamp(3.25) == "00:00:03,250"
    assert format_srt_timestamp(65.123) == "00:01:05,123"
    assert format_srt_timestamp(3665.456) == "01:01:05,456"


def test_vtt_timestamp_formatting():
    """Verify WebVTT timestamp format: HH:MM:SS.mmm"""
    assert format_vtt_timestamp(0.0) == "00:00:00.000"
    assert format_vtt_timestamp(3.25) == "00:00:03.250"
    assert format_vtt_timestamp(65.123) == "00:01:05.123"
    assert format_vtt_timestamp(3665.456) == "01:01:05.456"


# ==============================================================================
# TEST 3: SRT & VTT Content Generation Tests
# ==============================================================================
def test_generate_srt_format():
    """Verify standard SubRip format structure with sequence indices."""
    segments = [
        {"id": 0, "start": 0.0, "end": 2.5, "text": "Newton's Second Law."},
        {"id": 1, "start": 2.5, "end": 5.0, "text": "Force equals mass times acceleration."},
    ]
    srt = SubtitleService.generate_srt(segments)

    assert "1\n00:00:00,000 --> 00:00:02,500\nNewton's Second Law." in srt
    assert "2\n00:00:02,500 --> 00:00:05,000\nForce equals mass times acceleration." in srt
    assert srt.endswith("\n")


def test_generate_vtt_format():
    """Verify standard WebVTT format structure starting with WEBVTT."""
    segments = [
        {"id": 0, "start": 0.0, "end": 2.5, "text": "Newton's Second Law."},
        {"id": 1, "start": 2.5, "end": 5.0, "text": "Force equals mass times acceleration."},
    ]
    vtt = SubtitleService.generate_vtt(segments)

    assert vtt.startswith("WEBVTT\n")
    assert "00:00:00.000 --> 00:00:02.500" in vtt
    assert "00:00:02.500 --> 00:00:05.000" in vtt
    assert "Newton's Second Law." in vtt


# ==============================================================================
# TEST 4: Empty Segments Validation
# ==============================================================================
def test_empty_segments_handling():
    """Verify empty segments return valid minimal structures."""
    assert SubtitleService.generate_srt([]) == ""
    vtt = SubtitleService.generate_vtt([])
    assert vtt.startswith("WEBVTT")


def test_missing_audio_file_raises_error():
    """Verify attempting to transcribe non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        whisper_service.transcribe("non_existent_audio_file_xyz.wav")


# ==============================================================================
# TEST 5: Topic Slug Resolution Test
# ==============================================================================
def test_resolve_topic_slug_from_audio():
    """Verify slug extraction from audio path."""
    p1 = "backend/generated/audio/newtons_second_law/narration.wav"
    assert SubtitleService.resolve_topic_slug_from_audio(p1) == "newtons_second_law"

    p2 = "backend/generated/audio/photosynthesis/narration.wav"
    assert SubtitleService.resolve_topic_slug_from_audio(p2) == "photosynthesis"


# ==============================================================================
# TEST 6: Real faster-whisper Audio Transcription Test
# ==============================================================================
def test_real_whisper_transcription():
    """
    Perform a real transcription on an existing generated audio file.
    Verifies timestamps, duration, segment count, and non-empty text.
    """
    sample_audio = settings.AUDIO_DIR / "newtons_second_law" / "narration.wav"
    if not sample_audio.exists():
        # Fallback to any available WAV in audio directory
        wavs = list(settings.AUDIO_DIR.rglob("*.wav"))
        assert len(wavs) > 0, "No WAV files available for test"
        sample_audio = wavs[0]

    result = whisper_service.transcribe(sample_audio)

    assert len(result["text"]) > 0
    assert result["duration_seconds"] > 0
    assert len(result["segments"]) > 0
    assert result["generation_time_seconds"] > 0
    assert result["device"] in ["cuda", "cpu"]

    # Verify timestamps are monotonically increasing
    prev_end = 0.0
    for seg in result["segments"]:
        assert seg["start"] >= 0.0
        assert seg["end"] >= seg["start"]
        assert seg["start"] >= prev_end - 0.5
        prev_end = seg["end"]


# ==============================================================================
# TEST 7: Subtitle File Generation & Persistence Test
# ==============================================================================
def test_subtitle_service_process_audio_and_file_creation():
    """
    Verify complete process_audio pipeline writes subtitles.srt, subtitles.vtt,
    and transcription.json to the expected output folder.
    """
    sample_audio = settings.AUDIO_DIR / "newtons_second_law" / "narration.wav"
    if not sample_audio.exists():
        wavs = list(settings.AUDIO_DIR.rglob("*.wav"))
        sample_audio = wavs[0]

    test_slug = "test_unit_subtitle_out"
    test_dir = settings.SUBTITLES_DIR / test_slug
    if test_dir.exists():
        shutil.rmtree(test_dir)

    res = subtitle_service.process_audio(
        audio_path=sample_audio,
        topic_slug=test_slug,
    )

    assert res["success"] is True
    assert (test_dir / "subtitles.srt").exists()
    assert (test_dir / "subtitles.vtt").exists()
    assert (test_dir / "transcription.json").exists()

    srt_content = (test_dir / "subtitles.srt").read_text(encoding="utf-8")
    assert "-->" in srt_content

    vtt_content = (test_dir / "subtitles.vtt").read_text(encoding="utf-8")
    assert vtt_content.startswith("WEBVTT")

    # Cleanup
    shutil.rmtree(test_dir, ignore_errors=True)


# ==============================================================================
# TEST 8: API Endpoint Tests
# ==============================================================================
def test_subtitle_api_test_endpoint():
    """Verify POST /api/subtitle/test returns 200 with structured response."""
    sample_audio = "generated/audio/newtons_second_law/narration.wav"
    response = client.post("/api/subtitle/test", json={"audio_path": sample_audio})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["segment_count"] > 0
    assert "subtitle_srt_path" in data
    assert "subtitle_vtt_path" in data


def test_subtitle_api_invalid_audio_returns_404():
    """Verify passing a non-existent audio file returns HTTP 404."""
    response = client.post("/api/subtitle/transcribe", json={"audio_path": "invalid/path/test.wav"})
    assert response.status_code == 404
