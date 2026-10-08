"""
Unit and Integration Tests for Visual Scene Planner & Scene Router (Task 9B).
Verifies:
- Visual scene schemas and validation
- Deterministic SceneRouter rules (equations -> Manim, cinematic -> Cloud Video, teacher -> Avatar)
- Five core academic test topics:
  1. Newton's Second Law (Physics)
  2. Photosynthesis (Biology)
  3. Binary Search (Computer Science)
  4. Gradient Descent (Mathematics / Machine Learning)
  5. TCP Three-Way Handshake (Networking)
- LLMVisualScenePlanner behavior and rule-based fallback
- POST /api/video/plan endpoint
Zero cloud generation credits or media rendering invoked.
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.visual_scene import (
    VisualEngine,
    SceneType,
    TeacherPosition,
    VisualElement,
    AnimationInstruction,
    VisualScene,
    VisualVideoPlan,
    RoutedScene,
    RoutedVideoPlan,
    VisualPlanRequest,
    VisualPlanResponse,
)
from app.services.visual_scene_planner import (
    VisualScenePlanner,
    RuleBasedVisualScenePlanner,
    LLMVisualScenePlanner,
    visual_scene_planner,
)
from app.services.scene_router import SceneRouter, scene_router


@pytest.fixture
def client():
    return TestClient(app)


# 1. Schema Validation
def test_visual_scene_schema_validation():
    scene = VisualScene(
        scene_id="scene_eq",
        scene_type=SceneType.EQUATION,
        visual_engine=VisualEngine.MANIM,
        narration="F equals m times a.",
        visual_description="LaTeX formula F = ma rendered in cyan.",
        duration_seconds=5.0,
        teacher_enabled=False,
        teacher_position=TeacherPosition.NONE,
        visual_elements=[
            VisualElement(type="formula", label="Fma", description="LaTeX F=ma", properties={"color": "CYAN"})
        ],
        animations=[
            AnimationInstruction(action="create", target="Fma", duration=1.5, description="Formula appears")
        ],
        educational_goal="Understand basic formula"
    )
    assert scene.scene_id == "scene_eq"
    assert scene.scene_type == SceneType.EQUATION
    assert scene.visual_engine == VisualEngine.MANIM
    assert len(scene.visual_elements) == 1
    assert len(scene.animations) == 1


def test_teacher_position_normalization():
    # If teacher is disabled but position was set, it normalizes to NONE
    scene = VisualScene(
        scene_id="scene_norm",
        scene_type=SceneType.EXPLANATION,
        visual_engine=VisualEngine.MANIM,
        narration="Testing teacher normalization.",
        visual_description="Visual plane.",
        duration_seconds=4.0,
        teacher_enabled=False,
        teacher_position=TeacherPosition.CENTER,
    )
    assert scene.teacher_position == TeacherPosition.NONE

    # If teacher is enabled but position is NONE, it defaults to RIGHT
    scene2 = VisualScene(
        scene_id="scene_norm2",
        scene_type=SceneType.EXPLANATION,
        visual_engine=VisualEngine.MANIM,
        narration="Testing teacher enabled default.",
        visual_description="Visual plane.",
        duration_seconds=4.0,
        teacher_enabled=True,
        teacher_position=TeacherPosition.NONE,
    )
    assert scene2.teacher_position == TeacherPosition.RIGHT


# 2. SceneRouter Deterministic Overrides
def test_router_overrides_equation_from_cloud_to_manim():
    router = SceneRouter()
    # Erroneous scene where Qwen requested cloud_video for an equation
    scene = VisualScene(
        scene_id="scene_bad_engine",
        scene_type=SceneType.EQUATION,
        visual_engine=VisualEngine.CLOUD_VIDEO,
        narration="E equals m c squared.",
        visual_description="Equation E = mc^2",
        duration_seconds=5.0,
        teacher_enabled=False,
        teacher_position=TeacherPosition.NONE,
    )
    routed = router.route_scene(scene)
    # Router must override to Manim
    assert routed.selected_engine == VisualEngine.MANIM
    assert "Override" in routed.routing_reason
    assert routed.cloud_generation_required is False
    assert routed.fallback_engine == VisualEngine.MANIM


def test_router_routes_cinematic_to_cloud_video():
    router = SceneRouter()
    scene = VisualScene(
        scene_id="scene_cine",
        scene_type=SceneType.CINEMATIC,
        visual_engine=VisualEngine.CLOUD_VIDEO,
        narration="A droplet falling into clear water.",
        visual_description="Water droplet impact creating ripples.",
        duration_seconds=5.0,
        teacher_enabled=False,
        teacher_position=TeacherPosition.NONE,
    )
    routed = router.route_scene(scene)
    assert routed.selected_engine == VisualEngine.CLOUD_VIDEO
    assert routed.cloud_generation_required is True
    # Safe fallback exists if cloud generation is unavailable
    assert routed.fallback_engine == VisualEngine.MANIM
    assert routed.scene.visual_prompt is not None


def test_router_routes_teacher_intro_to_avatar():
    router = SceneRouter()
    scene = VisualScene(
        scene_id="scene_intro",
        scene_type=SceneType.TEACHER_INTRO,
        visual_engine=VisualEngine.AVATAR,
        narration="Welcome to class!",
        visual_description="Teacher introducing lesson.",
        duration_seconds=5.0,
        teacher_enabled=True,
        teacher_position=TeacherPosition.CENTER,
    )
    routed = router.route_scene(scene)
    assert routed.selected_engine == VisualEngine.AVATAR
    assert routed.scene.teacher_enabled is True
    assert routed.cloud_generation_required is False


# 3. Topic 1: Newton's Second Law
def test_topic_newton_second_law():
    planner = RuleBasedVisualScenePlanner()
    plan = planner.plan("Explain Newton's Second Law")
    routed_plan = scene_router.route_plan(plan)

    assert routed_plan.original_plan.topic == "Explain Newton's Second Law"
    assert len(routed_plan.routed_scenes) >= 5
    assert len(routed_plan.original_plan.learning_objectives) >= 2

    # Check engine allocations
    engines = [rs.selected_engine for rs in routed_plan.routed_scenes]
    assert VisualEngine.MANIM in engines
    assert VisualEngine.AVATAR in engines
    assert VisualEngine.CLOUD_VIDEO in engines

    # Equations and graphs routed to Manim
    eq_scenes = [rs for rs in routed_plan.routed_scenes if rs.scene.scene_type in (SceneType.EQUATION, SceneType.GRAPH)]
    for eq_scene in eq_scenes:
        assert eq_scene.selected_engine == VisualEngine.MANIM
        assert eq_scene.fallback_engine == VisualEngine.MANIM

    # Cinematic cart routed to Cloud Video
    cine_scenes = [rs for rs in routed_plan.routed_scenes if rs.scene.scene_type == SceneType.CINEMATIC]
    for cs in cine_scenes:
        assert cs.selected_engine == VisualEngine.CLOUD_VIDEO
        assert cs.cloud_generation_required is True

    # Teacher intro & summary routed to Avatar
    avatar_scenes = [rs for rs in routed_plan.routed_scenes if rs.scene.scene_type in (SceneType.TEACHER_INTRO, SceneType.TEACHER_SUMMARY)]
    for avs in avatar_scenes:
        assert avs.selected_engine == VisualEngine.AVATAR
        assert avs.scene.teacher_enabled is True


# 4. Topic 2: Photosynthesis
def test_topic_photosynthesis():
    planner = RuleBasedVisualScenePlanner()
    plan = planner.plan("Explain photosynthesis")
    routed_plan = scene_router.route_plan(plan)

    assert "Photosynthesis" in routed_plan.original_plan.title
    assert len(routed_plan.routed_scenes) >= 5

    engines = [rs.selected_engine for rs in routed_plan.routed_scenes]
    assert VisualEngine.MANIM in engines
    assert VisualEngine.CLOUD_VIDEO in engines
    assert VisualEngine.AVATAR in engines

    # Check chemical equation
    eq_scene = next(rs for rs in routed_plan.routed_scenes if rs.scene.scene_type == SceneType.EQUATION)
    assert eq_scene.selected_engine == VisualEngine.MANIM
    assert "CO2" in eq_scene.scene.narration or "carbon dioxide" in eq_scene.scene.narration.lower()


# 5. Topic 3: Binary Search
def test_topic_binary_search():
    planner = RuleBasedVisualScenePlanner()
    plan = planner.plan("Explain binary search")
    routed_plan = scene_router.route_plan(plan)

    assert "Binary Search" in routed_plan.original_plan.title
    assert len(routed_plan.routed_scenes) >= 5

    # Algorithmic arrays and decision trees MUST route to Manim
    algo_scenes = [rs for rs in routed_plan.routed_scenes if rs.scene.scene_type in (SceneType.ALGORITHM, SceneType.PROCESS, SceneType.DIAGRAM)]
    assert len(algo_scenes) >= 2
    for sc in algo_scenes:
        assert sc.selected_engine == VisualEngine.MANIM

    # Teacher presence verified
    assert routed_plan.routed_scenes[0].selected_engine == VisualEngine.AVATAR
    assert routed_plan.routed_scenes[-1].selected_engine == VisualEngine.AVATAR


# 6. Topic 4: Gradient Descent
def test_topic_gradient_descent():
    planner = RuleBasedVisualScenePlanner()
    plan = planner.plan("Explain gradient descent")
    routed_plan = scene_router.route_plan(plan)

    assert "Gradient Descent" in routed_plan.original_plan.title
    assert len(routed_plan.routed_scenes) >= 5

    # Equation & 3D Loss surface graph routed to Manim
    graph_scene = next(rs for rs in routed_plan.routed_scenes if rs.scene.scene_type == SceneType.GRAPH)
    assert graph_scene.selected_engine == VisualEngine.MANIM

    # Valley rolling ball metaphor routed to Cloud Video
    cine_scene = next(rs for rs in routed_plan.routed_scenes if rs.scene.scene_type == SceneType.CINEMATIC)
    assert cine_scene.selected_engine == VisualEngine.CLOUD_VIDEO


# 7. Topic 5: TCP Three-Way Handshake
def test_topic_tcp_handshake():
    planner = RuleBasedVisualScenePlanner()
    plan = planner.plan("Explain TCP three-way handshake")
    routed_plan = scene_router.route_plan(plan)

    assert "TCP" in routed_plan.original_plan.title
    assert len(routed_plan.routed_scenes) >= 5

    # Packet exchange lifelines & diagrams route to Manim
    process_scenes = [rs for rs in routed_plan.routed_scenes if rs.scene.scene_type in (SceneType.PROCESS, SceneType.DIAGRAM)]
    for ps in process_scenes:
        assert ps.selected_engine == VisualEngine.MANIM


# 8. LLMVisualScenePlanner Mocked Success
def test_llm_visual_scene_planner_mocked():
    sample_json = {
        "topic": "Quantum Tunneling",
        "title": "Quantum Tunneling Explained",
        "total_duration_seconds": 25.0,
        "learning_objectives": ["Understand wave functions", "Define potential barrier"],
        "scenes": [
            {
                "scene_id": "scene_1",
                "scene_type": "teacher_intro",
                "visual_engine": "avatar",
                "narration": "Welcome to Quantum Mechanics!",
                "visual_description": "Teacher welcoming class.",
                "duration_seconds": 5.0,
                "teacher_enabled": True,
                "teacher_position": "center",
                "visual_elements": [],
                "animations": [],
                "educational_goal": "Introduce concept"
            },
            {
                "scene_id": "scene_2",
                "scene_type": "equation",
                "visual_engine": "manim",
                "narration": "The Schrodinger equation governs probability amplitude.",
                "visual_description": "Schrodinger equation in purple LaTeX.",
                "duration_seconds": 6.0,
                "teacher_enabled": False,
                "teacher_position": "none",
                "visual_elements": [],
                "animations": [],
                "educational_goal": "Formula breakdown"
            }
        ]
    }

    mock_ollama = MagicMock()
    mock_ollama.is_available.return_value = True
    import json
    mock_ollama.generate.return_value = json.dumps(sample_json)

    planner = LLMVisualScenePlanner(ollama_service_instance=mock_ollama)
    plan = planner.plan("Quantum Tunneling")

    assert plan.topic == "Quantum Tunneling"
    assert len(plan.scenes) == 2
    assert plan.scenes[0].visual_engine == VisualEngine.AVATAR
    assert plan.scenes[1].visual_engine == VisualEngine.MANIM


# 9. LLMVisualScenePlanner Fallback on Connection Failure
def test_llm_visual_scene_planner_fallback_on_error():
    mock_ollama = MagicMock()
    mock_ollama.is_available.return_value = False  # Ollama offline

    planner = LLMVisualScenePlanner(ollama_service_instance=mock_ollama)
    # Should fall back cleanly without raising an exception
    plan = planner.plan("Newton's Second Law")
    assert plan.topic == "Newton's Second Law"
    assert len(plan.scenes) >= 5


# 10. API Endpoint POST /api/video/plan
def test_api_video_plan_endpoint(client):
    response = client.post(
        "/api/video/plan",
        json={"topic": "Explain Newton's Second Law", "planner": "rule_based"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["topic"] == "Explain Newton's Second Law"
    assert "Newton" in data["title"]
    assert len(data["scenes"]) >= 5
    assert "manim" in data["engine_summary"]
    assert "avatar" in data["engine_summary"]
    assert "cloud_video" in data["engine_summary"]

    # Check structure of routed scene in response
    first_scene = data["scenes"][0]
    assert "scene" in first_scene
    assert "selected_engine" in first_scene
    assert "routing_reason" in first_scene
    assert "fallback_engine" in first_scene
    assert "cloud_generation_required" in first_scene


def test_api_video_plan_empty_topic(client):
    response = client.post("/api/video/plan", json={"topic": ""})
    assert response.status_code in (400, 422)
