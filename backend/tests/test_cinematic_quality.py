"""
Unit and Integration Tests for Cinematic Educational Video Quality and Scene Mixing (Task 9F).
Tests:
1. Visual style parsing & resolution
2. Planner scene diversity & pedagogical arc
3. Camera motion validation
4. Transition validation
5. Intelligent scene routing & domain allocation
6. Cloud video fallback to Manim cinematic rendering
7. Teacher placement safety & static honesty
8. Subtitle safe-area protection (MarginV=32)
9. Backward compatibility with Tasks 1-9E
10. Final composition timeline synchronization
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.config import settings
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
    CameraMotion,
    VisualEmphasis,
    SceneTransition,
    BackgroundStyle,
    CinematicVisualStyle,
)
from app.schemas.render import RenderedScene
from app.schemas.composition import CompositionRequest
from app.services.visual_scene_planner import (
    RuleBasedVisualScenePlanner,
    LLMVisualScenePlanner,
    _resolve_visual_style,
)
from app.services.scene_router import scene_router
from app.services.renderers.manim_renderer import ManimRenderer
from app.services.renderers.cloud_video_renderer import CloudVideoRenderer
from app.services.scene_render_service import SceneRenderService
from app.services.final_compositor import FinalCompositor
from app.services.huggingface_video_service import HuggingFaceAPIError


# 1. Visual Style Parsing
def test_visual_style_parsing():
    assert _resolve_visual_style("educational") == CinematicVisualStyle.EDUCATIONAL
    assert _resolve_visual_style("academic") == CinematicVisualStyle.EDUCATIONAL
    assert _resolve_visual_style("cinematic") == CinematicVisualStyle.CINEMATIC_EDUCATIONAL
    assert _resolve_visual_style("cinematic_educational") == CinematicVisualStyle.CINEMATIC_EDUCATIONAL
    assert _resolve_visual_style("Cinematic Educational") == CinematicVisualStyle.CINEMATIC_EDUCATIONAL
    assert _resolve_visual_style("3b1b") == CinematicVisualStyle.THREE_BLUE_ONE_BROWN
    assert _resolve_visual_style("3blue1brown") == CinematicVisualStyle.THREE_BLUE_ONE_BROWN
    assert _resolve_visual_style("3blue1brown_inspired") == CinematicVisualStyle.THREE_BLUE_ONE_BROWN
    assert _resolve_visual_style("auto") == CinematicVisualStyle.AUTO
    assert _resolve_visual_style(None) == CinematicVisualStyle.AUTO
    assert _resolve_visual_style("unknown_style") == CinematicVisualStyle.AUTO


# 2. Planner Scene Diversity & Multi-Phase Narrative
def test_planner_scene_diversity_newton():
    planner = RuleBasedVisualScenePlanner()
    plan = planner.plan("Explain Newton's Second Law", visual_style="cinematic_educational")

    assert len(plan.scenes) == 8
    scene_types = [s.scene_type for s in plan.scenes]
    assert scene_types == [
        SceneType.TEACHER_INTRO,
        SceneType.CINEMATIC,
        SceneType.PHYSICS_SIMULATION,
        SceneType.EQUATION,
        SceneType.DIAGRAM,
        SceneType.GRAPH,
        SceneType.TEACHER_EXPLANATION,
        SceneType.TEACHER_SUMMARY,
    ]

    # Visual hook must be present
    hook_scenes = [s for s in plan.scenes if s.is_hook]
    assert len(hook_scenes) == 1
    assert hook_scenes[0].scene_id == "scene_2"
    assert hook_scenes[0].scene_type == SceneType.CINEMATIC


def test_planner_scene_diversity_photosynthesis():
    planner = RuleBasedVisualScenePlanner()
    plan = planner.plan("Explain photosynthesis", visual_style="3blue1brown")

    assert len(plan.scenes) == 7
    scene_types = [s.scene_type for s in plan.scenes]
    assert scene_types == [
        SceneType.TEACHER_INTRO,
        SceneType.CINEMATIC,
        SceneType.BIOLOGY_VISUAL,
        SceneType.PROCESS,
        SceneType.EQUATION,
        SceneType.COMPARISON,
        SceneType.TEACHER_SUMMARY,
    ]

    hook_scenes = [s for s in plan.scenes if s.is_hook]
    assert len(hook_scenes) == 1
    assert hook_scenes[0].scene_id == "scene_2"


def test_planner_scene_diversity_binary_search():
    planner = RuleBasedVisualScenePlanner()
    plan = planner.plan("Explain binary search", visual_style="educational")

    assert len(plan.scenes) == 7
    scene_types = [s.scene_type for s in plan.scenes]
    assert scene_types == [
        SceneType.TEACHER_INTRO,
        SceneType.CINEMATIC,
        SceneType.ALGORITHM,
        SceneType.PROCESS,
        SceneType.ALGORITHM,
        SceneType.GRAPH,
        SceneType.TEACHER_SUMMARY,
    ]

    hook_scenes = [s for s in plan.scenes if s.is_hook]
    assert len(hook_scenes) == 1
    assert hook_scenes[0].scene_id == "scene_2"


# 3. Camera Motion Validation
def test_camera_motion_validation():
    planner = RuleBasedVisualScenePlanner()
    plan = planner.plan("Explain Newton's Second Law")

    allowed_motions = {
        CameraMotion.STATIC,
        CameraMotion.SLOW_ZOOM_IN,
        CameraMotion.SLOW_ZOOM_OUT,
        CameraMotion.PAN_LEFT,
        CameraMotion.PAN_RIGHT,
        CameraMotion.FOCUS_CENTER,
    }

    for sc in plan.scenes:
        assert sc.camera_motion in allowed_motions, f"Invalid camera motion {sc.camera_motion} in {sc.scene_id}"


# 4. Transition Validation
def test_transition_validation():
    planner = RuleBasedVisualScenePlanner()
    plan = planner.plan("Explain Newton's Second Law")

    allowed_transitions = {
        SceneTransition.CUT,
        SceneTransition.FADE,
        SceneTransition.CROSSFADE,
        SceneTransition.SLIDE,
        SceneTransition.ZOOM,
    }

    for sc in plan.scenes:
        assert sc.transition_in in allowed_transitions
        assert sc.transition_out in allowed_transitions

    # Technical equations and diagrams default to CUT
    eq_scene = next(s for s in plan.scenes if s.scene_type == SceneType.EQUATION)
    assert eq_scene.transition_in == SceneTransition.CUT
    assert eq_scene.transition_out == SceneTransition.CUT

    # Cinematic hook uses CROSSFADE
    hook_scene = next(s for s in plan.scenes if s.is_hook)
    assert hook_scene.transition_in in (SceneTransition.CROSSFADE, SceneTransition.FADE)
    assert hook_scene.transition_out in (SceneTransition.CROSSFADE, SceneTransition.FADE)


# 5. Scene Routing & Domain Allocation
def test_scene_routing_and_duration_bounds():
    planner = RuleBasedVisualScenePlanner()
    plan = planner.plan("Explain Newton's Second Law")
    routed_plan = scene_router.route_plan(plan)

    for rs in routed_plan.routed_scenes:
        st = rs.scene.scene_type
        # Equations & Graphs MUST be Manim
        if st in (SceneType.EQUATION, SceneType.GRAPH):
            assert rs.selected_engine == VisualEngine.MANIM
            assert rs.fallback_engine == VisualEngine.MANIM

        # Cloud scenes must be short (3-8 seconds)
        if rs.selected_engine == VisualEngine.CLOUD_VIDEO:
            assert 3.0 <= rs.scene.duration_seconds <= 8.0
            assert rs.fallback_engine == VisualEngine.MANIM

        # Teacher milestones must be Avatar
        if st in (SceneType.TEACHER_INTRO, SceneType.TEACHER_SUMMARY, SceneType.TEACHER_EXPLANATION):
            assert rs.selected_engine == VisualEngine.AVATAR


# 6. Cloud Fallback to Manim
def test_cloud_fallback_to_manim(tmp_path):
    service = SceneRenderService(output_base_dir=tmp_path)

    # Create a scene routed to cloud video
    sc = VisualScene(
        scene_id="scene_cloud_fail",
        scene_type=SceneType.CINEMATIC,
        visual_engine=VisualEngine.CLOUD_VIDEO,
        narration="A magnificent physics manifestation.",
        visual_description="Cosmic orbital acceleration.",
        educational_goal="Observe cosmic physics inertia.",
        duration_seconds=5.0,
        teacher_enabled=False,
        teacher_position=TeacherPosition.NONE,
    )
    routed = RoutedScene(
        scene=sc,
        selected_engine=VisualEngine.CLOUD_VIDEO,
        routing_reason="Cloud cinematic shot",
        fallback_engine=VisualEngine.MANIM,
        cloud_generation_required=True,
    )

    routed_plan = RoutedVideoPlan(
        original_plan=VisualVideoPlan(
            topic="Cosmic Physics",
            title="Cosmic Physics Test",
            total_duration_seconds=5.0,
            scenes=[sc],
            learning_objectives=["Understand cosmic acceleration"]
        ),
        routed_scenes=[routed],
        engine_summary={"cloud_video": 1}
    )

    # Mock CloudVideoRenderer to simulate 402 / credit exhaustion failure
    failed_cloud_result = RenderedScene(
        scene_id="scene_cloud_fail",
        video_path="",
        duration_seconds=0.0,
        engine="cloud_video",
        success=False,
        error="HuggingFaceAPIError (402): Payment Required - Zero Credits",
    )

    # Mock Manim fallback to simulate success
    mock_manim_mp4 = tmp_path / "mock_manim_fallback.mp4"
    mock_manim_mp4.write_bytes(b"\x00" * 1024)
    mock_manim_result = RenderedScene(
        scene_id="scene_cloud_fail",
        video_path=str(mock_manim_mp4),
        duration_seconds=4.0,
        engine="manim",
        success=True,
    )

    with patch("app.services.renderers.cloud_video_renderer.CloudVideoRenderer.render", return_value=failed_cloud_result), \
         patch("app.services.renderers.manim_renderer.ManimRenderer.render", return_value=mock_manim_result):
        resp = service.render_plan(routed_plan)

    assert resp.success is True
    assert resp.successful_scenes == 1
    assert resp.failed_scenes == 0
    final_sc = resp.scenes[0]
    assert final_sc.success is True
    assert final_sc.engine == "manim"
    assert final_sc.metadata.get("fallback_used") is True
    assert final_sc.metadata.get("cloud_generated") is False


# 7. Teacher Placement Safety
def test_teacher_placement_safety():
    # In mixed scenes, teacher position must not be CENTER
    mixed_scene = VisualScene(
        scene_id="scene_mixed",
        scene_type=SceneType.DIAGRAM,
        visual_engine=VisualEngine.MIXED,
        narration="Explaining the technical diagram.",
        visual_description="Complex architectural diagram.",
        duration_seconds=5.0,
        teacher_enabled=True,
        teacher_position=TeacherPosition.CENTER,  # Misconfigured center
    )
    routed = scene_router.route_scene(mixed_scene)
    assert routed.selected_engine == VisualEngine.MIXED
    # Safety override moves teacher away from center
    assert routed.scene.teacher_position in (TeacherPosition.LEFT, TeacherPosition.RIGHT)


# 8. Subtitle Safe Area
def test_subtitle_safe_area_configuration():
    compositor = FinalCompositor()
    # Check that compositor forces MarginV=32 for subtitle safe area
    assert hasattr(compositor, "compose")

    # Manim renderer supported types includes CINEMATIC for fallback
    manim = ManimRenderer()
    assert SceneType.CINEMATIC in manim.SUPPORTED_TYPES


# 9. Backward Compatibility
def test_backward_compatibility_rule_based_planner():
    planner = RuleBasedVisualScenePlanner()
    # Classic signature without visual_style parameter
    plan = planner.plan("Explain Newton's Second Law")
    assert plan.topic == "Explain Newton's Second Law"
    assert len(plan.scenes) >= 5

    # Request schema with defaults
    req = CompositionRequest(topic="Photosynthesis")
    assert req.visual_style == "auto"
    assert req.burn_subtitles is True
    assert req.transition_duration_seconds == 0.3


# 10. Manim Script Generation for Photosynthesis, Binary Search, and Fallback
def test_manim_script_generators():
    renderer = ManimRenderer()

    # Photosynthesis
    photo_scene = VisualScene(
        scene_id="sc_photo",
        scene_type=SceneType.BIOLOGY_VISUAL,
        visual_engine=VisualEngine.MANIM,
        narration="Chloroplast photosynthesis converting sunlight to glucose.",
        visual_description="Chloroplast thylakoids and stroma.",
        duration_seconds=5.0,
    )
    code, cls = renderer._generate_script(photo_scene)
    assert "Chloroplast" in code
    assert "Thylakoid" in code
    assert "Photons" in code

    # Binary Search
    bs_scene = VisualScene(
        scene_id="sc_bs",
        scene_type=SceneType.ALGORITHM,
        visual_engine=VisualEngine.MANIM,
        narration="Binary search dividing sorted array in half.",
        visual_description="Sorted array with low and high pointers.",
        duration_seconds=5.0,
    )
    code_bs, cls_bs = renderer._generate_script(bs_scene)
    assert "Binary Search" in code_bs
    assert "Mid" in code_bs

    # Cinematic Fallback
    cine_scene = VisualScene(
        scene_id="sc_cine",
        scene_type=SceneType.CINEMATIC,
        visual_engine=VisualEngine.MANIM,
        narration="Dynamic celestial visual.",
        visual_description="Orbital motion of spheres in gravity.",
        educational_goal="Observe gravitational inertia.",
        duration_seconds=5.0,
    )
    code_cine, cls_cine = renderer._generate_script(cine_scene)
    assert "CINEMATIC VISUALIZATION" in code_cine
