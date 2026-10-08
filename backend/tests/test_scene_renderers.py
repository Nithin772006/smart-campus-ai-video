"""
Unit and Integration Tests for Visual Scene Renderer Layer (Task 9C).
Tests:
- RendererRegistry engine resolution and unknown engine error handling
- ManimRenderer rendering a real educational Newton's Second Law scene to MP4
- AvatarRenderer generating a teacher presenter video with overlay provider metadata
- CloudVideoRenderer error handling and mocked API responses (success, 402, timeout)
- SceneRenderService multi-engine batch rendering
- POST /api/video/render API endpoint
Zero cloud generation credits consumed.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.schemas.visual_scene import (
    VisualEngine,
    SceneType,
    TeacherPosition,
    VisualElement,
    AnimationInstruction,
    VisualScene,
    RoutedScene,
    VisualVideoPlan,
    RoutedVideoPlan,
)
from app.schemas.render import (
    RenderedScene,
    TopicRenderRequest,
    TopicRenderResponse,
)
from app.services.renderers.base import SceneRenderer
from app.services.renderers.manim_renderer import ManimRenderer
from app.services.renderers.cloud_video_renderer import CloudVideoRenderer
from app.services.renderers.avatar_renderer import AvatarRenderer
from app.services.renderer_registry import (
    RendererRegistry,
    renderer_registry,
    UnknownEngineError,
)
from app.services.scene_render_service import (
    SceneRenderService,
    scene_render_service,
)
from app.services.huggingface_video_service import (
    HuggingFaceAPIError,
    HuggingFaceTimeoutError,
)


@pytest.fixture
def client():
    return TestClient(app)


# A. Renderer Registry Tests
def test_renderer_registry_resolves_engines():
    registry = RendererRegistry()
    assert isinstance(registry.get_renderer("manim"), ManimRenderer)
    assert isinstance(registry.get_renderer("cloud_video"), CloudVideoRenderer)
    assert isinstance(registry.get_renderer("avatar"), AvatarRenderer)
    # Mixed routes to Manim vector renderer
    assert isinstance(registry.get_renderer("mixed"), ManimRenderer)


def test_renderer_registry_unknown_engine():
    registry = RendererRegistry()
    with pytest.raises(UnknownEngineError) as exc_info:
        registry.get_renderer("unsupported_engine_xyz")
    assert "Unknown visual engine" in str(exc_info.value)


# B. Manim Renderer Real Rendering Test
def test_manim_renderer_real_scene(tmp_path):
    renderer = ManimRenderer()
    scene = VisualScene(
        scene_id="scene_physics_1",
        scene_type=SceneType.PHYSICS_SIMULATION,
        visual_engine=VisualEngine.MANIM,
        narration="When a force is applied to a mass, it accelerates forward.",
        visual_description="Newton's Second Law box with mass m and force arrow accelerating rightward.",
        duration_seconds=4.0,
        teacher_enabled=False,
        teacher_position=TeacherPosition.NONE,
        visual_elements=[
            VisualElement(type="shape", label="Box", description="Mass block m = 5 kg"),
            VisualElement(type="arrow", label="Force", description="Force vector F = 20 N"),
        ],
        animations=[
            AnimationInstruction(action="move", target="Box", duration=1.5, description="Box accelerates forward")
        ],
        educational_goal="Understand F = ma through moving box simulation"
    )
    routed = RoutedScene(
        scene=scene,
        selected_engine=VisualEngine.MANIM,
        routing_reason="Physics simulations route to Manim",
        fallback_engine=VisualEngine.MANIM,
        cloud_generation_required=False,
    )

    result = renderer.render(routed, output_dir=tmp_path, quality="low_quality")

    assert result.success is True
    assert result.engine == "manim"
    assert result.scene_id == "scene_physics_1"
    assert result.duration_seconds > 0

    # Verify physical MP4 exists and has non-zero size
    out_file = tmp_path / "scene.mp4"
    assert out_file.exists()
    assert out_file.stat().st_size > 1024


# C. Avatar Renderer Test
def test_avatar_renderer_generates_video(tmp_path):
    renderer = AvatarRenderer()
    scene = VisualScene(
        scene_id="scene_intro_1",
        scene_type=SceneType.TEACHER_INTRO,
        visual_engine=VisualEngine.AVATAR,
        narration="Welcome to Physics class! Today we explore Newton's second law.",
        visual_description="SmartCampus AI Teacher presenting lesson introduction.",
        duration_seconds=3.0,
        teacher_enabled=True,
        teacher_position=TeacherPosition.CENTER,
    )
    routed = RoutedScene(
        scene=scene,
        selected_engine=VisualEngine.AVATAR,
        routing_reason="Teacher intro routed to Avatar",
        fallback_engine=VisualEngine.MANIM,
        cloud_generation_required=False,
    )

    result = renderer.render(routed, output_dir=tmp_path)

    assert result.success is True
    assert result.engine == "avatar"
    assert result.scene_id == "scene_intro_1"
    assert result.duration_seconds >= 2.8
    assert result.metadata.get("provider") == "teacher_overlay"
    assert result.metadata.get("character") == "SmartCampus Teacher"

    out_file = tmp_path / "scene.mp4"
    assert out_file.exists()
    assert out_file.stat().st_size > 1024


# D. Cloud Renderer Mocked Tests
def test_cloud_renderer_mocked_success(tmp_path):
    mock_service = MagicMock()
    mock_service.default_model = "Wan-AI/Wan2.2-TI2V-5B"
    mock_service.default_provider = "fal-ai"
    mock_service.generate_video.return_value = {
        "success": True,
        "provider": "fal-ai",
        "model": "Wan-AI/Wan2.2-TI2V-5B",
        "video_path": "generated/rendered_scenes/mock_scene/scene.mp4",
        "duration_seconds": 5.0,
        "resolution": "1280x720",
        "output_size_mb": 1.25,
        "generation_time_seconds": 8.4,
    }

    renderer = CloudVideoRenderer(service=mock_service)
    scene = VisualScene(
        scene_id="scene_cine_1",
        scene_type=SceneType.CINEMATIC,
        visual_engine=VisualEngine.CLOUD_VIDEO,
        narration="A heavy cart rolling across a warehouse floor.",
        visual_description="Heavy cart with high mass resistance.",
        visual_prompt="Cinematic shot of heavy warehouse cart accelerating under human force.",
        duration_seconds=5.0,
        teacher_enabled=False,
        teacher_position=TeacherPosition.NONE,
    )
    routed = RoutedScene(
        scene=scene,
        selected_engine=VisualEngine.CLOUD_VIDEO,
        routing_reason="Cinematic scene routed to Cloud Video",
        fallback_engine=VisualEngine.MANIM,
        cloud_generation_required=True,
    )

    result = renderer.render(routed, output_dir=tmp_path)

    assert result.success is True
    assert result.engine == "cloud_video"
    assert result.scene_id == "scene_cine_1"
    assert result.metadata["provider"] == "fal-ai"
    assert result.metadata["model"] == "Wan-AI/Wan2.2-TI2V-5B"
    mock_service.generate_video.assert_called_once()


def test_cloud_renderer_402_payment_failure(tmp_path):
    mock_service = MagicMock()
    mock_service.default_model = "Wan-AI/Wan2.2-TI2V-5B"
    mock_service.default_provider = "fal-ai"
    mock_service.generate_video.side_effect = HuggingFaceAPIError(
        "Hugging Face Inference API error (402): Client error '402 Payment Required' - You have no remaining credits."
    )

    renderer = CloudVideoRenderer(service=mock_service)
    scene = VisualScene(
        scene_id="scene_cine_402",
        scene_type=SceneType.CINEMATIC,
        visual_engine=VisualEngine.CLOUD_VIDEO,
        narration="A real-world physics scene.",
        visual_description="Rolling ball.",
        visual_prompt="Rolling ball cinematic.",
        duration_seconds=5.0,
        teacher_enabled=False,
        teacher_position=TeacherPosition.NONE,
    )
    routed = RoutedScene(
        scene=scene,
        selected_engine=VisualEngine.CLOUD_VIDEO,
        routing_reason="Cinematic scene routed to Cloud Video",
        fallback_engine=VisualEngine.MANIM,
        cloud_generation_required=True,
    )

    # Must NOT crash; must return clear error result
    result = renderer.render(routed, output_dir=tmp_path)

    assert result.success is False
    assert result.engine == "cloud_video"
    assert "402 Payment Required" in result.error or "credits" in result.error
    assert result.duration_seconds == 0.0


def test_cloud_renderer_timeout(tmp_path):
    mock_service = MagicMock()
    mock_service.default_model = "Wan-AI/Wan2.2-TI2V-5B"
    mock_service.default_provider = "fal-ai"
    mock_service.generate_video.side_effect = HuggingFaceTimeoutError("Generation timed out after 300s")

    renderer = CloudVideoRenderer(service=mock_service)
    scene = VisualScene(
        scene_id="scene_cine_to",
        scene_type=SceneType.CINEMATIC,
        visual_engine=VisualEngine.CLOUD_VIDEO,
        narration="A slow cloud generation.",
        visual_description="Slow scene.",
        duration_seconds=5.0,
        teacher_enabled=False,
        teacher_position=TeacherPosition.NONE,
    )
    routed = RoutedScene(
        scene=scene,
        selected_engine=VisualEngine.CLOUD_VIDEO,
        routing_reason="Cinematic scene routed to Cloud Video",
        fallback_engine=VisualEngine.MANIM,
        cloud_generation_required=True,
    )

    result = renderer.render(routed, output_dir=tmp_path)
    assert result.success is False
    assert "timed out" in result.error


# E. SceneRenderService Batch Test with Mixed Engines
def test_scene_render_service_mixed_batch(tmp_path):
    service = SceneRenderService(output_base_dir=tmp_path)

    # 1. Avatar scene
    sc1 = VisualScene(
        scene_id="scene_1",
        scene_type=SceneType.TEACHER_INTRO,
        visual_engine=VisualEngine.AVATAR,
        narration="Welcome to the lesson!",
        visual_description="Teacher welcome.",
        duration_seconds=2.0,
        teacher_enabled=True,
        teacher_position=TeacherPosition.CENTER,
    )
    # 2. Manim scene
    sc2 = VisualScene(
        scene_id="scene_2",
        scene_type=SceneType.EQUATION,
        visual_engine=VisualEngine.MANIM,
        narration="F equals m times a.",
        visual_description="Equation F = ma.",
        duration_seconds=2.0,
        teacher_enabled=False,
        teacher_position=TeacherPosition.NONE,
    )
    # 3. Cloud scene (we will mock cloud renderer to avoid external API calls)
    sc3 = VisualScene(
        scene_id="scene_3",
        scene_type=SceneType.CINEMATIC,
        visual_engine=VisualEngine.CLOUD_VIDEO,
        narration="A cinematic demonstration.",
        visual_description="Cart moving.",
        visual_prompt="Cart moving.",
        duration_seconds=3.0,
        teacher_enabled=False,
        teacher_position=TeacherPosition.NONE,
    )

    plan = VisualVideoPlan(
        topic="Newton's Second Law",
        title="Newton's Second Law Test",
        total_duration_seconds=7.0,
        scenes=[sc1, sc2, sc3],
        learning_objectives=["Understand Newton's Law"]
    )

    routed_plan = RoutedVideoPlan(
        original_plan=plan,
        routed_scenes=[
            RoutedScene(scene=sc1, selected_engine=VisualEngine.AVATAR, routing_reason="Avatar intro", fallback_engine=VisualEngine.MANIM),
            RoutedScene(scene=sc2, selected_engine=VisualEngine.MANIM, routing_reason="Manim equation", fallback_engine=VisualEngine.MANIM),
            RoutedScene(scene=sc3, selected_engine=VisualEngine.CLOUD_VIDEO, routing_reason="Cloud cinematic", fallback_engine=VisualEngine.MANIM, cloud_generation_required=True),
        ],
        engine_summary={"avatar": 1, "manim": 1, "cloud_video": 1}
    )

    # Mock the cloud renderer
    mock_cloud_result = RenderedScene(
        scene_id="scene_3",
        video_path="generated/rendered_scenes/mock/scene_3/scene.mp4",
        duration_seconds=3.0,
        engine="cloud_video",
        success=True,
    )
    with patch("app.services.renderers.cloud_video_renderer.CloudVideoRenderer.render", return_value=mock_cloud_result):
        response = service.render_plan(routed_plan, quality="low_quality")

    assert response.success is True
    assert response.scene_count == 3
    assert response.successful_scenes == 3
    assert response.failed_scenes == 0
    assert len(response.scenes) == 3

    # Check individual scenes
    engines_used = [s.engine for s in response.scenes]
    assert "avatar" in engines_used
    assert "manim" in engines_used
    assert "cloud_video" in engines_used


# F. API Endpoint POST /api/video/render
def test_api_render_endpoint(client, tmp_path):
    # Mock cloud rendering in case plan contains cloud scene
    mock_cloud_result = RenderedScene(
        scene_id="scene_mock",
        video_path="generated/rendered_scenes/mock/scene.mp4",
        duration_seconds=4.0,
        engine="cloud_video",
        success=True,
    )

    with patch("app.services.renderers.cloud_video_renderer.CloudVideoRenderer.render", return_value=mock_cloud_result):
        response = client.post(
            "/api/video/render",
            json={
                "topic": "Newton's Second Law",
                "quality": "low_quality",
                "planner": "rule_based"
            }
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Newton" in data["topic"]
    assert data["scene_count"] >= 3
    assert data["successful_scenes"] >= 3
    assert len(data["scenes"]) == data["scene_count"]


def test_api_render_empty_topic(client):
    response = client.post("/api/video/render", json={"topic": ""})
    assert response.status_code in (400, 422)
