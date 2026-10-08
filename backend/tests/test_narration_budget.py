"""
Unit and integration tests for Narration Budgeting, Natural Teacher Rate Control,
and Audio/Video Timing Synchronization.
"""

import pytest
from app.config import settings
from app.schemas.scene import EducationalVideoPlan, ScenePlanItem, SceneType, AcademicDomain
from app.services.narration_service import NarrationService


def test_word_budget_calculation_30s():
    """Verify 30 sec target duration yields ~80 words at 160 WPM."""
    budget = NarrationService.calculate_word_budget(30.0, target_wpm=160)
    assert budget == 80


def test_word_budget_calculation_60s():
    """Verify 60 sec target duration yields ~160 words at 160 WPM."""
    budget = NarrationService.calculate_word_budget(60.0, target_wpm=160)
    assert budget == 160


def test_word_budget_calculation_various_durations():
    """Verify word budgets for 45s, 90s, and 120s."""
    assert NarrationService.calculate_word_budget(45.0, target_wpm=160) == 120
    assert NarrationService.calculate_word_budget(90.0, target_wpm=160) == 240
    assert NarrationService.calculate_word_budget(120.0, target_wpm=160) == 320


def test_dense_narration_detection():
    """
    Verify dense narration detection:
    200 words / 25 sec yields ~480 WPM, which is > 190 WPM and must be rejected as too fast.
    """
    dense_text = " ".join(["word"] * 200)
    metrics = NarrationService.estimate_speech_metrics(
        text=dense_text,
        target_duration_seconds=25.0,
        target_wpm=160,
    )
    assert metrics["word_count"] == 200
    assert metrics["estimated_wpm"] == 480.0
    assert metrics["is_too_dense"] is True


def test_normal_narration_accepted():
    """
    Verify normal narration acceptance:
    80 words / 30 sec yields ~160 WPM, which is <= 190 WPM and must be accepted.
    """
    normal_text = " ".join(["word"] * 80)
    metrics = NarrationService.estimate_speech_metrics(
        text=normal_text,
        target_duration_seconds=30.0,
        target_wpm=160,
    )
    assert metrics["word_count"] == 80
    assert metrics["estimated_wpm"] == 160.0
    assert metrics["is_too_dense"] is False
    assert metrics["estimated_duration_seconds"] == 30.0


def test_no_robotic_boilerplate_in_narration():
    """Verify robotic introductory and section markers are stripped."""
    dirty_text = (
        "Welcome to this lesson on RAG. Concept Definition: Retrieval-Augmented Generation "
        "combines search and generation. Now let's explore how it works. "
        "Key Takeaway: It grounds model responses in facts. Thank you for watching this explanation."
    )
    cleaned = NarrationService.clean_text_for_speech(dirty_text)

    assert "welcome to this lesson" not in cleaned.lower()
    assert "concept definition" not in cleaned.lower()
    assert "now let's explore" not in cleaned.lower()
    assert "key takeaway" not in cleaned.lower()
    assert "thank you for watching" not in cleaned.lower()
    assert "retrieval-augmented generation" in cleaned.lower()


def test_sentence_pruning_respects_boundaries():
    """Verify sentence pruning does not truncate mid-sentence."""
    long_text = (
        "Retrieval-Augmented Generation combines search and generation. "
        "First, the system retrieves relevant documents from a knowledge base. "
        "Then, the language model uses these documents to generate an accurate answer. "
        "This completely eliminates hallucinations and ensures factual accuracy."
    )
    # Prune to a 15-second budget (~40 words)
    pruned = NarrationService._prune_to_word_budget(long_text, target_duration_seconds=15.0, target_wpm=160)
    assert pruned.endswith((".", "!", "?"))
    assert len(pruned.split()) <= 46  # 40 * 1.15
    # Must preserve complete sentences
    assert "Retrieval-Augmented Generation" in pruned


def test_rule_based_concise_script_budget():
    """Verify rule-based concise script respects target duration word budget."""
    plan = EducationalVideoPlan(
        topic="Retrieval-Augmented Generation",
        title="Introduction to Retrieval-Augmented Generation",
        domain=AcademicDomain.COMPUTER_SCIENCE,
        target_duration=30.0,
        scenes=[
            ScenePlanItem(
                id=1,
                type=SceneType.TITLE,
                title="Retrieval-Augmented Generation",
                subtitle="Combining Search and Large Language Models",
                content="Retrieval-Augmented Generation enhances generative AI using external knowledge.",
            ),
            ScenePlanItem(
                id=2,
                type=SceneType.EXPLANATION,
                title="Concept Definition",
                content="When a user asks a question, the retriever searches an index for relevant passages.",
            ),
            ScenePlanItem(
                id=3,
                type=SceneType.PROCESS,
                title="Pipeline Steps",
                steps=[
                    "Retrieve candidate documents from vector database.",
                    "Pass retrieved context into the generative language model prompt.",
                ],
            ),
            ScenePlanItem(
                id=4,
                type=SceneType.CONCLUSION,
                title="Key Takeaway",
                content="This grounds model outputs in factual data and prevents hallucinations.",
            ),
        ],
    )

    narration_data = NarrationService.build_plan_narration(plan, target_duration_seconds=30.0)

    assert narration_data["target_duration_seconds"] == 30.0
    assert narration_data["target_wpm"] == 160
    assert narration_data["word_budget"] == 80
    assert narration_data["word_count"] <= 95  # Within budget tolerance
    assert narration_data["is_too_dense"] is False
    assert narration_data["estimated_wpm"] <= 190.0

    full_script = narration_data["full_script"]
    assert "welcome to this lesson" not in full_script.lower()
    assert "concept definition" not in full_script.lower()
    assert "key takeaway" not in full_script.lower()
    assert len(narration_data["scene_scripts"]) == 4
