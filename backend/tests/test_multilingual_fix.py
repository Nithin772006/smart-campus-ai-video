"""
Automated Mocked Tests for Multilingual Localization and Audio Synthesis (Task 9G-B).
Zero ElevenLabs credits consumed: all network calls and Ollama generations are strictly mocked.
"""

import pytest
import base64
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.config import settings
from app.services.narration_localizer import (
    narration_localizer,
    LocalizationError,
    LocalizationResult,
)
from app.services.narration_service import NarrationService
from app.services.elevenlabs_service import elevenlabs_service
from app.services.audio_provider import ElevenLabsAudioProvider, get_audio_provider
from app.services.subtitle_service import subtitle_service
from app.schemas.scene import EducationalVideoPlan, ScenePlanItem, SceneType, AcademicDomain


# =====================================================================
# 1. Hindi localization returns Devanagari
# =====================================================================
def test_hindi_localization_returns_devanagari():
    mock_hindi = "न्यूटन का दूसरा नियम बताता है कि F = m * a होता है।"
    with patch("app.services.ollama_service.ollama_service.is_available", return_value=True), \
         patch("app.services.ollama_service.ollama_service.generate", return_value=mock_hindi):
        result = narration_localizer.localize_with_status("Force equals mass times acceleration.", target_language="hi")
        assert result.is_valid is True
        assert result.actual_language == "hi"
        assert result.requested_language == "hi"
        assert result.script_ratio > 0.50
        assert "न्यूटन" in result.text
        assert result.fallback_used is False


# =====================================================================
# 2. Tamil localization returns Tamil script
# =====================================================================
def test_tamil_localization_returns_tamil_script():
    mock_tamil = "விசை என்பது நிறை மற்றும் முடுக்கத்தின் பெருக்கற்பலன் ஆகும், F = m * a."
    with patch("app.services.ollama_service.ollama_service.is_available", return_value=True), \
         patch("app.services.ollama_service.ollama_service.generate", return_value=mock_tamil):
        result = narration_localizer.localize_with_status("Force equals mass times acceleration.", target_language="ta")
        assert result.is_valid is True
        assert result.actual_language == "ta"
        assert result.requested_language == "ta"
        assert result.script_ratio > 0.50
        assert "விசை" in result.text
        assert result.fallback_used is False


# =====================================================================
# 3. English bypasses localization
# =====================================================================
def test_english_bypasses_localization():
    original = "Force equals mass multiplied by acceleration, F = m * a."
    with patch("app.services.ollama_service.ollama_service.generate") as mock_gen:
        result = narration_localizer.localize_with_status(original, target_language="en")
        assert result.text == original
        assert result.actual_language == "en"
        assert result.fallback_used is False
        mock_gen.assert_not_called()


# =====================================================================
# 4. English input is not accepted as successful Hindi localization
# =====================================================================
def test_english_input_rejected_as_hindi():
    english_output = "Force equals mass multiplied by acceleration."
    # When Ollama erroneously outputs English for a Hindi request
    with patch("app.services.ollama_service.ollama_service.is_available", return_value=True), \
         patch("app.services.ollama_service.ollama_service.generate", return_value=english_output):
        result = narration_localizer.localize_with_status("Original text", target_language="hi", allow_english_fallback=True)
        # Must NOT be marked as successful Hindi
        assert result.is_valid is False
        assert result.actual_language == "en"
        assert result.fallback_used is True
        assert "Insufficient Devanagari" in result.fallback_reason


# =====================================================================
# 5. English input is not accepted as successful Tamil localization
# =====================================================================
def test_english_input_rejected_as_tamil():
    english_output = "Force equals mass multiplied by acceleration."
    with patch("app.services.ollama_service.ollama_service.is_available", return_value=True), \
         patch("app.services.ollama_service.ollama_service.generate", return_value=english_output):
        result = narration_localizer.localize_with_status("Original text", target_language="ta", allow_english_fallback=True)
        assert result.is_valid is False
        assert result.actual_language == "en"
        assert result.fallback_used is True
        assert "Insufficient Tamil" in result.fallback_reason


# =====================================================================
# 6. One localization retry replaces, rather than appends to, the first result
# =====================================================================
def test_localization_retry_replaces_not_appends():
    attempt_1 = "This is invalid english output on attempt 1."
    attempt_2 = "न्यूटन का दूसरा नियम F = m * a है।"

    call_count = 0
    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return attempt_1
        return attempt_2

    with patch("app.services.ollama_service.ollama_service.is_available", return_value=True), \
         patch("app.services.ollama_service.ollama_service.generate", side_effect=side_effect):
        result = narration_localizer.localize_with_status("Some text", target_language="hi")

        assert call_count == 2
        assert result.is_valid is True
        assert result.actual_language == "hi"
        # The result must ONLY contain attempt 2, never concatenated with attempt 1
        assert result.text == attempt_2
        assert "attempt 1" not in result.text


# =====================================================================
# 7. Scene narration is not duplicated during assembly
# =====================================================================
def test_scene_narration_not_duplicated_during_assembly():
    repeated_input = (
        "Understanding Newton's Second Law. "
        "Understanding Newton's Second Law. "
        "Force equals mass times acceleration. "
        "Force equals mass times acceleration."
    )
    cleaned = NarrationService.deduplicate_consecutive_phrases(repeated_input)
    sentences = [s.strip() for s in cleaned.split(".") if s.strip()]
    assert len(sentences) == 2
    assert sentences[0] == "Understanding Newton's Second Law"
    assert sentences[1] == "Force equals mass times acceleration"


# =====================================================================
# 8. Repeated legitimate technical terms are preserved
# =====================================================================
def test_repeated_legitimate_technical_terms_preserved():
    # Terms across different educational sentences should be preserved
    script = (
        "Newton's Second Law explains how force causes acceleration. "
        "When mass increases, the object requires more force to accelerate. "
        "Therefore, force and acceleration are directly proportional."
    )
    deduped = NarrationService.deduplicate_consecutive_phrases(script)
    # 'force' appears legitimately in 3 separate sentences and must remain in all 3
    assert deduped.count("force") == 3
    assert "Newton's Second Law" in deduped


# =====================================================================
# 9. Selected language reaches the TTS service
# =====================================================================
# 9. Selected language reaches the TTS service
# =====================================================================
MOCK_AUDIO_BYTES = b"\xFF\xFB\x90\x00" + b"\x00" * 2000
MOCK_AUDIO_BASE64 = base64.b64encode(MOCK_AUDIO_BYTES).decode("utf-8")

@patch("httpx.Client.post")
def test_selected_language_reaches_tts_service(mock_post, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ELEVENLABS_API_KEY", "mock_key")
    monkeypatch.setattr(settings, "ELEVENLABS_ENABLED", True)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = MOCK_AUDIO_BYTES
    mock_resp.json.return_value = {
        "audio_base64": MOCK_AUDIO_BASE64,
        "alignment": {
            "characters": ["F", " ", "=", " ", "m", "a"],
            "character_start_times_seconds": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5],
            "character_end_times_seconds": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
        },
    }
    mock_post.return_value = mock_resp

    with patch.object(elevenlabs_service, "_probe_audio", return_value=(0.6, 24000)):
        res = elevenlabs_service.generate_speech(
            text="F = ma",
            language="hi",
            output_dir=tmp_path,
        )

    assert mock_post.called
    sent_payload = mock_post.call_args[1]["json"]
    assert sent_payload.get("language_code") == "hi"
    assert res["language"] == "hi"


# =====================================================================
# 10. Hindi and Tamil use expected ElevenLabs model and language settings
# =====================================================================
@patch("httpx.Client.post")
def test_hindi_and_tamil_model_and_language_settings(mock_post, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ELEVENLABS_API_KEY", "mock_key")
    monkeypatch.setattr(settings, "ELEVENLABS_ENABLED", True)
    monkeypatch.setattr(settings, "ELEVENLABS_TTS_MODEL", "eleven_multilingual_v2")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = MOCK_AUDIO_BYTES
    mock_resp.json.return_value = {
        "audio_base64": MOCK_AUDIO_BASE64,
        "alignment": None,
    }
    mock_post.return_value = mock_resp

    with patch.object(elevenlabs_service, "_probe_audio", return_value=(1.0, 24000)):
        # Test Tamil
        elevenlabs_service.generate_speech(text="வணக்கம்", language="ta", timestamps=False, output_dir=tmp_path)
        payload_ta = mock_post.call_args[1]["json"]
        assert payload_ta["model_id"] == "eleven_multilingual_v2"
        assert payload_ta["language_code"] == "ta"

        # Test Hindi
        elevenlabs_service.generate_speech(text="नमस्ते", language="hi", timestamps=False, output_dir=tmp_path)
        payload_hi = mock_post.call_args[1]["json"]
        assert payload_hi["model_id"] == "eleven_multilingual_v2"
        assert payload_hi["language_code"] == "hi"


# =====================================================================
# 11. Subtitles correspond to the exact synthesized text
# =====================================================================
def test_subtitles_correspond_to_exact_synthesized_text(tmp_path):
    alignment = {
        "characters": list("F = m * a"),
        "character_start_times_seconds": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
        "character_end_times_seconds": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
    }
    dummy_wav = tmp_path / "narration.wav"
    dummy_wav.write_bytes(b"RIFF" + b"\x00" * 40)

    sub_res = subtitle_service.create_subtitles_from_elevenlabs_alignment(
        audio_path=dummy_wav,
        alignment_data=alignment,
        language="hi",
        output_dir=tmp_path,
    )
    assert sub_res["success"] is True
    srt_content = (tmp_path / "subtitles.srt").read_text(encoding="utf-8")
    assert "F = m * a" in srt_content


# =====================================================================
# 12. Localization failure is reported explicitly
# =====================================================================
def test_localization_failure_reported_explicitly():
    # If Ollama returns empty or error twice
    with patch("app.services.ollama_service.ollama_service.is_available", return_value=True), \
         patch("app.services.ollama_service.ollama_service.generate", return_value=""):
        res = narration_localizer.localize_with_status("Original script", target_language="hi", allow_english_fallback=True)
        assert res.is_valid is False
        assert res.fallback_used is True
        assert res.actual_language == "en"
        assert res.fallback_reason is not None
        assert "failed validation" in res.fallback_reason


# =====================================================================
# 13. Existing IndicF5 provider works as fallback
# =====================================================================
def test_indicf5_fallback_provider():
    provider = get_audio_provider("indicf5")
    assert provider.name == "indicf5"


# =====================================================================
# 14. Existing English ElevenLabs behavior works
# =====================================================================
def test_english_elevenlabs_provider():
    provider = get_audio_provider("elevenlabs")
    assert provider.name == "elevenlabs"


# =====================================================================
# 15. End-to-end plan narration propagates actual_language
# =====================================================================
def test_plan_narration_propagates_actual_language(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ELEVENLABS_API_KEY", "mock_key")
    monkeypatch.setattr(settings, "ELEVENLABS_ENABLED", True)

    plan = EducationalVideoPlan(
        topic="Newton's Law",
        title="Newton's Law",
        domain=AcademicDomain.PHYSICS,
        scenes=[
            ScenePlanItem(
                id=1,
                title="Introduction",
                type=SceneType.TITLE,
                content="Newton's Second Law",
                duration=5.0,
            )
        ],
        target_duration=10.0,
    )

    mock_hindi = "न्यूटन का दूसरा नियम F = m * a है।"
    with patch("app.services.ollama_service.ollama_service.is_available", return_value=True), \
         patch("app.services.ollama_service.ollama_service.generate", return_value=mock_hindi), \
         patch("app.services.elevenlabs_service.elevenlabs_service.generate_speech") as mock_speech:
        mock_speech.return_value = {
            "success": True,
            "provider": "elevenlabs",
            "audio_path": "audio/path.wav",
            "duration_seconds": 3.0,
            "voice_id": "mock_voice",
            "alignment": None,
        }

        provider = ElevenLabsAudioProvider()
        result = provider.generate_plan_narration(plan=plan, language="hi")

        assert result["language"] == "hi"
        assert result["actual_language"] == "hi"
        assert result["fallback_used"] is False
        mock_speech.assert_called_once()
        assert mock_speech.call_args[1]["language"] == "hi"
