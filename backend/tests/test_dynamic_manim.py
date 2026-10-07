import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.scene_planner import RuleBasedAcademicPlanner
from app.services.manim_service import generate_dynamic_topic_video
from app.schemas.scene import SceneType, AcademicDomain
from app.config import settings


def test_academic_planner_subjects():
    """Verify scene planner across multiple required academic subjects."""
    planner = RuleBasedAcademicPlanner()

    test_cases = [
        # 1. Newton's Second Law
        ("Explain Newton's Second Law", "Newton's Second Law", AcademicDomain.PHYSICS),
        # 2. Photosynthesis
        ("What is photosynthesis?", "Photosynthesis", AcademicDomain.BIOLOGY),
        # 3. Binary Search
        ("How does binary search work?", "Binary Search", AcademicDomain.COMPUTER_SCIENCE),
        # 4. OSI Model
        ("Explain the OSI model", "OSI Model", AcademicDomain.COMPUTER_SCIENCE),
        # 5. Water Cycle
        ("Explain the water cycle", "The Water Cycle", AcademicDomain.CHEMISTRY),
        # 6. Simple mathematical concept (Bayes theorem)
        ("Explain Bayes theorem", "Bayes' Theorem", AcademicDomain.MATHEMATICS),
    ]

    for question, expected_topic, expected_domain in test_cases:
        plan = planner.plan(question)
        assert plan.topic == expected_topic, f"Expected {expected_topic}, got {plan.topic}"
        assert plan.domain == expected_domain, f"Expected {expected_domain}, got {plan.domain}"
        assert len(plan.scenes) >= 3, f"Plan should have at least 3 scenes, got {len(plan.scenes)}"
        assert plan.target_duration > 0, "Target duration must be positive"
        assert plan.scenes[0].type == SceneType.TITLE, "First scene must be TITLE"
        print(f"  [PASS] Planner: '{question}' -> {plan.topic} ({plan.domain.value}), {len(plan.scenes)} scenes")


def test_question_phrasing_variations():
    """Verify that varied phrasing resolves to the same underlying topic."""
    planner = RuleBasedAcademicPlanner()

    photosynthesis_variants = [
        "Explain photosynthesis",
        "What is photosynthesis?",
        "How does photosynthesis work?",
        "Teach me photosynthesis",
        "Explain photosynthesis in plants",
        "Explain photosynthesis for a beginner",
    ]
    for q in photosynthesis_variants:
        plan = planner.plan(q)
        assert "Photosynthesis" in plan.topic, f"Failed variation: '{q}' -> {plan.topic}"

    binary_search_variants = [
        "What is binary search?",
        "Explain binary search",
        "How does binary search work?",
        "Explain binary search step by step",
    ]
    for q in binary_search_variants:
        plan = planner.plan(q)
        assert "Binary Search" in plan.topic, f"Failed variation: '{q}' -> {plan.topic}"

    print("  [PASS] Natural language question variations resolved successfully")


def test_fallback_unknown_topic():
    """Verify fallback mechanism never crashes on novel topics."""
    planner = RuleBasedAcademicPlanner()
    novel_q = "Explain Quantum Cryptography"
    plan = planner.plan(novel_q)
    assert plan.topic == "Quantum Cryptography"
    assert len(plan.scenes) >= 4
    assert plan.scenes[0].type == SceneType.TITLE
    assert plan.scenes[-1].type == SceneType.CONCLUSION
    print(f"  [PASS] Novel fallback plan generated: {plan.title} ({len(plan.scenes)} scenes)")


def test_render_physics_example():
    """Render a physics/math topic (Newton's Second Law) through dynamic pipeline."""
    res = generate_dynamic_topic_video("Explain Newton's Second Law", quality="medium_quality")
    assert res["success"] is True
    assert res["topic"] == "Newton's Second Law"
    assert res["duration_seconds"] > 0
    assert res["generation_time_seconds"] > 0

    video_path = settings.BASE_DIR / res["video_path"] if not Path(res["video_path"]).is_absolute() else Path(res["video_path"])
    assert video_path.exists(), f"Video file not found: {video_path}"
    assert video_path.stat().st_size > 0
    print(f"  [PASS] Rendered Physics: {video_path.name} ({res['duration_seconds']}s, {res['generation_time_seconds']}s gen time)")


def test_render_non_mathematical_example():
    """Render a non-mathematical academic topic (Photosynthesis) through dynamic pipeline."""
    res = generate_dynamic_topic_video("Explain photosynthesis", quality="medium_quality")
    assert res["success"] is True
    assert "Photosynthesis" in res["topic"]
    assert res["duration_seconds"] > 0
    assert res["generation_time_seconds"] > 0
    assert res["scene_count"] >= 3

    video_path = settings.BASE_DIR / res["video_path"] if not Path(res["video_path"]).is_absolute() else Path(res["video_path"])
    assert video_path.exists(), f"Video file not found: {video_path}"
    assert video_path.stat().st_size > 0
    print(f"  [PASS] Rendered Non-math (Photosynthesis): {video_path.name} ({res['duration_seconds']}s, {res['scene_count']} scenes, {res['generation_time_seconds']}s gen time)")


if __name__ == "__main__":
    print("\n--- Running Academic Planner Tests ---")
    test_academic_planner_subjects()
    test_question_phrasing_variations()
    test_fallback_unknown_topic()

    print("\n--- Running Dynamic Video Rendering Tests ---")
    test_render_physics_example()
    test_render_non_mathematical_example()

    print("\nALL DYNAMIC MANIM TESTS PASSED SUCCESSFULLY!")
