"""
Comprehensive test suite for IndicF5 local Text-to-Speech service.
Tests configuration, narration builder, validations, directory outputs,
real model generation, and full plan synthesis.
"""

import sys
import shutil
from pathlib import Path
import pytest
import soundfile as sf

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.schemas.scene import EducationalVideoPlan, ScenePlanItem, SceneType, AcademicDomain
from app.services.narration_service import NarrationService
from app.services.indicf5_service import IndicF5Service, indicf5_service, slugify_topic

client = TestClient(app)


# ==============================================================================
# TEST 1: Service Configuration Test
# ==============================================================================
def test_tts_service_configuration():
    """Verify default TTS settings and service initialization parameters."""
    assert hasattr(settings, "TTS_DEVICE")
    assert hasattr(settings, "TTS_MODEL_TYPE")
    assert hasattr(settings, "TTS_REF_TEXT")
    assert hasattr(settings, "AUDIO_DIR")
    assert settings.AUDIO_DIR.exists()

    service = IndicF5Service()
    assert service.audio_base_dir == settings.AUDIO_DIR
    assert service.device in ["cuda", "cpu"]
    assert service.speed == settings.TTS_SPEED
    assert service.model_type == settings.TTS_MODEL_TYPE


# ==============================================================================
# TEST 2: Narration Builder Tests
# ==============================================================================
def test_narration_builder_text_cleaning():
    """Verify markdown, headers, and labels are stripped cleanly."""
    dirty_text = "### Scene 1: **Newton's Law** with `acceleration` & 100% force."
    cleaned = NarrationService.clean_text_for_speech(dirty_text)
    assert "**" not in cleaned
    assert "`" not in cleaned
    assert "###" not in cleaned
    assert "Scene 1:" not in cleaned
    assert "and" in cleaned
    assert "percent" in cleaned
    assert cleaned.endswith(".")


def test_narration_builder_formula_conversion():
    """Verify formulas are translated into natural spoken English."""
    assert "equals" in NarrationService.convert_formula_to_speech("F = ma")
    assert "squared" in NarrationService.convert_formula_to_speech("E = mc^2")
    assert "plus" in NarrationService.convert_formula_to_speech("a + b = c")
    assert "divided by" in NarrationService.convert_formula_to_speech(r"\frac{a}{b}")


def test_narration_builder_plan_generation():
    """Verify EducationalVideoPlan is converted into natural teacher-like narration."""
    plan = EducationalVideoPlan(
        topic="Photosynthesis",
        title="Understanding Photosynthesis",
        domain=AcademicDomain.BIOLOGY,
        scenes=[
            ScenePlanItem(
                id=1,
                type=SceneType.TITLE,
                title="Photosynthesis",
                subtitle="Light Energy to Chemical Energy",
                content="Plants convert solar light into stored chemical energy."
            ),
            ScenePlanItem(
                id=2,
                type=SceneType.FORMULA,
                title="Chemical Reaction",
                content="Carbon dioxide and water produce glucose and oxygen.",
                formula=r"6CO_2 + 6H_2O \rightarrow C_6H_{12}O_6 + 6O_2"
            ),
            ScenePlanItem(
                id=3,
                type=SceneType.CONCLUSION,
                title="Summary",
                content="Photosynthesis sustains life on Earth by producing oxygen.",
                bullets=["Produces oxygen", "Generates glucose"]
            )
        ]
    )

    narration_data = NarrationService.build_plan_narration(plan)
    assert narration_data["topic"] == "Photosynthesis"
    assert len(narration_data["scene_scripts"]) == 3
    full_script = narration_data["full_script"]

    # Verify no markdown, json, or robotic greeting artifacts exist in output
    assert "{" not in full_script
    assert "}" not in full_script
    assert "**" not in full_script
    assert "Scene 1" not in full_script
    assert "Welcome to this lesson" not in full_script
    assert "Concept Definition" not in full_script
    assert narration_data["word_count"] > 10


# ==============================================================================
# TEST 3: Empty Text Validation Tests
# ==============================================================================
def test_tts_empty_text_validation():
    """Verify service raises ValueError on empty or whitespace strings."""
    with pytest.raises(ValueError, match="cannot be empty"):
        indicf5_service.generate_speech("")

    with pytest.raises(ValueError, match="cannot be empty"):
        indicf5_service.generate_speech("     \n\t   ")


def test_tts_api_empty_text_endpoint():
    """Verify POST /api/audio/test returns 400 Bad Request for empty string."""
    response = client.post("/api/audio/test", json={"text": ""})
    assert response.status_code == 400


# ==============================================================================
# TEST 4: Output Directory & Slugification Test
# ==============================================================================
def test_output_directory_structure():
    """Verify slug generation and dedicated directory structure."""
    assert slugify_topic("Newton's Second Law!") == "newtons_second_law"
    assert slugify_topic("Photosynthesis (Plant Biology)") == "photosynthesis_plant_biology"

    test_slug = "unit_test_topic_audio"
    test_dir = settings.AUDIO_DIR / test_slug
    if test_dir.exists():
        shutil.rmtree(test_dir)

    result = indicf5_service.generate_speech(
        text="A brief test of audio directory creation.",
        topic="unit_test_topic_audio"
    )

    expected_wav = test_dir / "narration.wav"
    expected_txt = test_dir / "narration.txt"

    assert Path(result["absolute_audio_path"]).exists()
    assert expected_wav.exists()
    assert expected_txt.exists()
    assert expected_txt.read_text(encoding="utf-8") == "A brief test of audio directory creation."

    # Cleanup
    shutil.rmtree(test_dir, ignore_errors=True)


# ==============================================================================
# TEST 5: Real IndicF5 Generation Test
# ==============================================================================
def test_real_indicf5_generation():
    """
    Synthesize audio using the real local IndicF5 / F5-TTS model.
    Verifies valid WAV format, non-zero duration, and sample rate.
    """
    sentence = "Newton's Second Law states that force equals mass multiplied by acceleration."
    result = indicf5_service.generate_speech(
        text=sentence,
        topic="test_real_speech"
    )

    assert result["success"] is True
    assert result["duration_seconds"] > 0
    assert result["sample_rate"] == 24000
    assert result["text_length"] == len(sentence)
    assert result["generation_time_seconds"] > 0

    wav_path = Path(result["absolute_audio_path"])
    assert wav_path.exists()
    assert wav_path.stat().st_size > 1000

    info = sf.info(str(wav_path))
    assert info.format == "WAV"
    assert info.samplerate == 24000
    assert info.duration > 0.5


# ==============================================================================
# TEST 6: Real EducationalVideoPlan -> Narration -> WAV Test
# ==============================================================================
def test_real_educational_plan_to_wav():
    """
    Full pipeline test: EducationalVideoPlan -> NarrationService -> IndicF5Service -> WAV.
    Verifies full plan synthesis and API endpoints.
    """
    plan = EducationalVideoPlan(
        topic="Newton's Second Law",
        title="Newton's Second Law of Motion",
        domain=AcademicDomain.PHYSICS,
        scenes=[
            ScenePlanItem(
                id=1,
                type=SceneType.TITLE,
                title="Newton's Second Law",
                subtitle="Force and Acceleration",
                content="The acceleration of an object is proportional to the net force applied."
            ),
            ScenePlanItem(
                id=2,
                type=SceneType.FORMULA,
                title="Governing Equation",
                content="Net force equals mass times acceleration.",
                formula="F = ma",
                formula_breakdown=["F = Force (N)", "m = Mass (kg)", "a = Acceleration (m/s^2)"]
            ),
            ScenePlanItem(
                id=3,
                type=SceneType.CONCLUSION,
                title="Conclusion",
                content="Force drives motion, while mass resists acceleration."
            )
        ]
    )

    # Test via service directly
    result = indicf5_service.generate_plan_narration(plan)
    assert result["success"] is True
    assert result["duration_seconds"] > 2.0
    assert result["sample_rate"] == 24000
    assert "scene_scripts" in result
    assert len(result["scene_scripts"]) == 3

    wav_file = Path(result["absolute_audio_path"])
    txt_file = Path(result["transcript_path"])
    assert wav_file.exists()
    assert txt_file.exists()

    # Test via FastAPI endpoint POST /api/audio/tts
    response = client.post("/api/audio/tts", json={"plan": plan.model_dump()})
    assert response.status_code == 200
    api_data = response.json()
    assert api_data["success"] is True
    assert api_data["duration_seconds"] > 0
    assert "audio_path" in api_data
    assert "narration_text" in api_data
