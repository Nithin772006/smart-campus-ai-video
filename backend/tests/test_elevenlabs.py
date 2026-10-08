"""
Unit and Integration Tests for ElevenLabs TTS and Timestamp Integration (Task 9G-A).
All tests in this suite strictly MOCK network calls to avoid consuming ElevenLabs API credits.
"""

import os
import json
import base64
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.config import settings
from app.services.elevenlabs_service import (
    ElevenLabsService,
    ElevenLabsConfigError,
    ElevenLabsAuthError,
    ElevenLabsRateLimitError,
    ElevenLabsTimeoutError,
    ElevenLabsServerError,
    ElevenLabsAudioError,
    elevenlabs_service,
)
from app.services.narration_localizer import narration_localizer
from app.services.subtitle_service import subtitle_service
from app.services.audio_provider import (
    get_audio_provider,
    IndicF5AudioProvider,
    ElevenLabsAudioProvider,
)
from app.schemas.scene import EducationalVideoPlan, ScenePlanItem, SceneType


# Synthetic short audio (1 second 24kHz mono PCM WAV encoded to MP3 or basic bytes)
MOCK_AUDIO_BYTES = b"\xFF\xFB\x90\x00" + b"\x00" * 2000
MOCK_AUDIO_BASE64 = base64.b64encode(MOCK_AUDIO_BYTES).decode("utf-8")

SAMPLE_ALIGNMENT = {
    "characters": [
        "T", "o", "d", "a", "y", " ",
        "w", "e", " ",
        "l", "e", "a", "r", "n", " ",
        "p", "h", "y", "s", "i", "c", "s", "."
    ],
    "character_start_times_seconds": [
        0.00, 0.05, 0.10, 0.15, 0.20, 0.25,
        0.30, 0.35, 0.40,
        0.45, 0.50, 0.55, 0.60, 0.65, 0.70,
        0.75, 0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10
    ],
    "character_end_times_seconds": [
        0.05, 0.10, 0.15, 0.20, 0.25, 0.30,
        0.35, 0.40, 0.45,
        0.50, 0.55, 0.60, 0.65, 0.70, 0.75,
        0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15
    ]
}


# =====================================================================
# 1. ElevenLabs service initialization
# =====================================================================
def test_elevenlabs_service_initialization():
    service = ElevenLabsService()
    assert service is not None
    assert service.audio_base_dir.exists()
    assert service.resolve_voice_id(None) is not None


# =====================================================================
# 2. API key missing
# =====================================================================
def test_api_key_missing(monkeypatch):
    monkeypatch.setattr(settings, "ELEVENLABS_API_KEY", "")
    service = ElevenLabsService()
    assert service.is_configured() is False
    with pytest.raises(ElevenLabsConfigError):
        service._get_headers()


# =====================================================================
# 3. API key configured
# =====================================================================
def test_api_key_configured(monkeypatch):
    monkeypatch.setattr(settings, "ELEVENLABS_API_KEY", "test_key_sample_12345")
    service = ElevenLabsService()
    assert service.is_configured() is True
    headers = service._get_headers()
    assert headers["xi-api-key"] == "test_key_sample_12345"
    assert "Content-Type" in headers


# =====================================================================
# 4. English TTS (Mocked)
# =====================================================================
@patch("httpx.Client.post")
def test_english_tts_mocked(mock_post, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ELEVENLABS_API_KEY", "mock_key")
    monkeypatch.setattr(settings, "ELEVENLABS_ENABLED", True)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "audio_base64": MOCK_AUDIO_BASE64,
        "alignment": SAMPLE_ALIGNMENT,
    }
    mock_post.return_value = mock_resp

    with patch.object(elevenlabs_service, "_probe_audio", return_value=(1.15, 24000)):
        result = elevenlabs_service.generate_speech(
            text="Today we learn physics.",
            voice_id="test_voice_en",
            language="en",
            topic="test_english_tts",
            output_dir=tmp_path,
            timestamps=True,
        )

    assert result["success"] is True
    assert result["provider"] == "elevenlabs"
    assert result["duration_seconds"] == 1.15
    assert result["language"] == "en"
    assert result["voice_id"] == "test_voice_en"
    assert result["timestamp_data_available"] is True
    assert (tmp_path / "narration.mp3").exists()
    assert (tmp_path / "narration.txt").exists()


# =====================================================================
# 5. Tamil TTS (Mocked)
# =====================================================================
@patch("httpx.Client.post")
def test_tamil_tts_mocked(mock_post, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ELEVENLABS_API_KEY", "mock_key")
    monkeypatch.setattr(settings, "ELEVENLABS_ENABLED", True)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "audio_base64": MOCK_AUDIO_BASE64,
        "alignment": SAMPLE_ALIGNMENT,
    }
    mock_post.return_value = mock_resp

    tamil_text = "இன்று நாம் நியூட்டனின் இரண்டாவது இயக்க விதியைப் பற்றி கற்றுக்கொள்வோம்."
    with patch.object(elevenlabs_service, "_probe_audio", return_value=(3.20, 24000)):
        result = elevenlabs_service.generate_speech(
            text=tamil_text,
            voice_id="test_voice_ta",
            language="ta",
            topic="test_tamil_tts",
            output_dir=tmp_path,
            timestamps=True,
        )

    assert result["success"] is True
    assert result["language"] == "ta"
    assert result["duration_seconds"] == 3.20
    assert result["timestamp_data_available"] is True


# =====================================================================
# 6. Hindi TTS (Mocked)
# =====================================================================
@patch("httpx.Client.post")
def test_hindi_tts_mocked(mock_post, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ELEVENLABS_API_KEY", "mock_key")
    monkeypatch.setattr(settings, "ELEVENLABS_ENABLED", True)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "audio_base64": MOCK_AUDIO_BASE64,
        "alignment": SAMPLE_ALIGNMENT,
    }
    mock_post.return_value = mock_resp

    hindi_text = "आज हम न्यूटन के गति के दूसरे नियम के बारे में जानेंगे।"
    with patch.object(elevenlabs_service, "_probe_audio", return_value=(2.85, 24000)):
        result = elevenlabs_service.generate_speech(
            text=hindi_text,
            voice_id="test_voice_hi",
            language="hi",
            topic="test_hindi_tts",
            output_dir=tmp_path,
            timestamps=True,
        )

    assert result["success"] is True
    assert result["language"] == "hi"
    assert result["duration_seconds"] == 2.85
    assert result["timestamp_data_available"] is True


# =====================================================================
# 7. Timestamp parsing
# =====================================================================
def test_timestamp_parsing():
    segments = subtitle_service.convert_alignment_to_segments(SAMPLE_ALIGNMENT)
    assert len(segments) > 0
    first_seg = segments[0]
    assert "start" in first_seg
    assert "end" in first_seg
    assert "text" in first_seg
    assert first_seg["start"] <= first_seg["end"]

    # Monotonicity test across all segments
    prev_end = 0.0
    for seg in segments:
        assert seg["start"] >= prev_end or abs(seg["start"] - prev_end) < 0.001
        assert seg["end"] > seg["start"]
        prev_end = seg["end"]


# =====================================================================
# 8. Invalid timestamp handling
# =====================================================================
def test_invalid_timestamp_handling():
    with pytest.raises(ValueError):
        subtitle_service.convert_alignment_to_segments({})

    with pytest.raises(ValueError):
        subtitle_service.convert_alignment_to_segments({
            "characters": [],
            "character_start_times_seconds": [],
            "character_end_times_seconds": [],
        })

    with pytest.raises(ValueError):
        subtitle_service.convert_alignment_to_segments(None)


# =====================================================================
# 9. Voice listing (Mocked)
# =====================================================================
@patch("httpx.Client.get")
def test_voice_listing_mocked(mock_get, monkeypatch):
    monkeypatch.setattr(settings, "ELEVENLABS_API_KEY", "mock_key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "voices": [
            {
                "voice_id": "voice_1",
                "name": "Rachel",
                "category": "premade",
                "labels": {"accent": "american"},
                "preview_url": "https://example.com/rachel.mp3",
                "description": "Calm voice",
            },
            {
                "voice_id": "voice_2",
                "name": "Domi",
                "category": "premade",
                "labels": {},
                "preview_url": None,
                "description": "Engaging voice",
            }
        ]
    }
    mock_get.return_value = mock_resp

    voices = elevenlabs_service.get_voices()
    assert len(voices) == 2
    assert voices[0]["voice_id"] == "voice_1"
    assert voices[0]["name"] == "Rachel"
    assert "api_key" not in voices[0]


# =====================================================================
# 10. API failure handling (401, 429, 500)
# =====================================================================
@patch("httpx.Client.post")
def test_api_failure_401(mock_post, monkeypatch):
    monkeypatch.setattr(settings, "ELEVENLABS_API_KEY", "bad_key")
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"
    mock_resp.json.return_value = {"detail": "Invalid API key"}
    mock_post.return_value = mock_resp

    with pytest.raises(ElevenLabsAuthError):
        elevenlabs_service.generate_speech("Test text")


@patch("httpx.Client.post")
def test_api_failure_429(mock_post, monkeypatch):
    monkeypatch.setattr(settings, "ELEVENLABS_API_KEY", "key")
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "Rate limit"
    mock_resp.json.return_value = {"detail": "Too many requests"}
    mock_post.return_value = mock_resp

    with pytest.raises(ElevenLabsRateLimitError):
        elevenlabs_service.generate_speech("Test text")


@patch("httpx.Client.post")
def test_api_failure_500(mock_post, monkeypatch):
    monkeypatch.setattr(settings, "ELEVENLABS_API_KEY", "key")
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal server error"
    mock_resp.json.return_value = {"message": "Server error"}
    mock_post.return_value = mock_resp

    with pytest.raises(ElevenLabsServerError):
        elevenlabs_service.generate_speech("Test text")


# =====================================================================
# 11. Timeout handling
# =====================================================================
@patch("httpx.Client.post")
def test_timeout_handling(mock_post, monkeypatch):
    import httpx
    monkeypatch.setattr(settings, "ELEVENLABS_API_KEY", "key")
    mock_post.side_effect = httpx.TimeoutException("Connection timed out")

    with pytest.raises(ElevenLabsTimeoutError):
        elevenlabs_service.generate_speech("Test text")


# =====================================================================
# 12. Fallback to IndicF5
# =====================================================================
def test_fallback_to_indicf5_when_disabled(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ELEVENLABS_ENABLED", False)
    provider = ElevenLabsAudioProvider()

    # Mock the fallback IndicF5 provider
    with patch.object(provider.fallback_provider, "generate_speech") as mock_fallback:
        mock_fallback.return_value = {
            "success": True,
            "provider": "indicf5",
            "provider_requested": "elevenlabs",
            "provider_used": "indicf5",
            "fallback_used": True,
            "fallback_reason": "ElevenLabs is disabled in configuration (ELEVENLABS_ENABLED=false).",
            "audio_path": "mock/narration.wav",
            "duration_seconds": 4.5,
        }

        res = provider.generate_speech("Newton's second law", topic="newton")
        assert res["fallback_used"] is True
        assert res["provider_used"] == "indicf5"
        assert res["provider_requested"] == "elevenlabs"


def test_fallback_to_indicf5_on_api_error(monkeypatch):
    monkeypatch.setattr(settings, "ELEVENLABS_ENABLED", True)
    monkeypatch.setattr(settings, "ELEVENLABS_API_KEY", "key")
    provider = ElevenLabsAudioProvider()

    with patch.object(provider.service, "generate_speech", side_effect=ElevenLabsServerError("Server down")):
        with patch.object(provider.fallback_provider, "generate_speech") as mock_fallback:
            mock_fallback.return_value = {
                "success": True,
                "provider": "indicf5",
                "provider_requested": "elevenlabs",
                "provider_used": "indicf5",
                "fallback_used": True,
                "fallback_reason": "ElevenLabs synthesis failed: Server down",
                "audio_path": "mock/narration.wav",
                "duration_seconds": 4.5,
            }
            res = provider.generate_speech("Newton's second law")
            assert res["fallback_used"] is True
            assert res["provider_used"] == "indicf5"


# =====================================================================
# 13. Provider selection
# =====================================================================
def test_provider_selection():
    p1 = get_audio_provider("indicf5")
    assert isinstance(p1, IndicF5AudioProvider)
    assert p1.name == "indicf5"

    p2 = get_audio_provider("elevenlabs")
    assert isinstance(p2, ElevenLabsAudioProvider)
    assert p2.name == "elevenlabs"

    p3 = get_audio_provider("unknown_default")
    assert isinstance(p3, IndicF5AudioProvider)


# =====================================================================
# 14. Subtitle generation from ElevenLabs timestamps
# =====================================================================
def test_subtitle_generation_from_elevenlabs_timestamps(tmp_path):
    audio_file = tmp_path / "test_audio.wav"
    audio_file.write_bytes(b"RIFF" + b"\x00" * 40)  # Dummy audio header

    result = subtitle_service.create_subtitles_from_elevenlabs_alignment(
        audio_path=audio_file,
        alignment_data=SAMPLE_ALIGNMENT,
        language="en",
        output_dir=tmp_path,
    )

    assert result["success"] is True
    assert result["source"] == "elevenlabs_timestamps"
    assert (tmp_path / "subtitles.srt").exists()
    assert (tmp_path / "subtitles.vtt").exists()
    assert (tmp_path / "transcription.json").exists()

    srt_content = (tmp_path / "subtitles.srt").read_text(encoding="utf-8")
    assert "-->" in srt_content
    assert "Today we learn physics." in srt_content


# =====================================================================
# 15. Narration Localizer (English bypass and Multilingual)
# =====================================================================
def test_narration_localizer_english_bypass():
    original = "Force equals mass multiplied by acceleration."
    # English should NOT call LLM
    with patch("app.services.ollama_service.ollama_service.generate") as mock_gen:
        result = narration_localizer.localize(original, target_language="en")
        assert result == original
        mock_gen.assert_not_called()
