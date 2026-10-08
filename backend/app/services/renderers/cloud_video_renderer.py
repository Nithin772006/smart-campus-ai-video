"""
Cloud Video Scene Renderer (Task 9C).
Wraps the existing HuggingFaceVideoService to generate photorealistic AI video scenes.
Gracefully handles provider errors (such as 402 Payment Required / Zero Credit balance)
without crashing or faking generation results.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from app.config import settings
from app.schemas.visual_scene import (
    VisualEngine,
    RoutedScene,
)
from app.schemas.render import RenderedScene
from app.services.renderers.base import SceneRenderer
from app.services.huggingface_video_service import (
    hf_video_service,
    HuggingFaceVideoService,
    HuggingFaceVideoError,
)

logger = logging.getLogger(__name__)


class CloudVideoRenderer(SceneRenderer):
    """
    Renders RoutedScenes using Hugging Face Inference Providers text-to-video API.
    Reuses existing HuggingFaceVideoService client.
    """

    def __init__(self, service: Optional[HuggingFaceVideoService] = None):
        self.service = service or hf_video_service

    @property
    def engine_name(self) -> str:
        return "cloud_video"

    def can_render(self, scene: RoutedScene) -> bool:
        """Checks if the scene is targeted for Cloud Video."""
        return scene.selected_engine == VisualEngine.CLOUD_VIDEO

    def render(
        self,
        scene: RoutedScene,
        output_dir: Path,
        **kwargs: Any
    ) -> RenderedScene:
        """
        Call the Hugging Face text-to-video provider to generate scene MP4.
        If provider is unavailable, returns clean failure metadata.
        """
        visual_scene = scene.scene
        scene_id = visual_scene.scene_id

        output_dir.mkdir(parents=True, exist_ok=True)
        target_path = output_dir / "scene.mp4"

        # Determine generation prompt
        prompt = (visual_scene.visual_prompt or visual_scene.visual_description or "").strip()
        if not prompt:
            prompt = f"Educational visualization of {visual_scene.narration[:80]}"

        model = kwargs.get("model", self.service.default_model)
        provider = kwargs.get("provider", self.service.default_provider)
        check_enabled = kwargs.get("check_enabled", True)

        logger.info(
            "[CloudVideoRenderer] Rendering scene %s via provider '%s' (model: %s)",
            scene_id, provider, model
        )

        try:
            result = self.service.generate_video(
                prompt=prompt,
                model=model,
                provider=provider,
                output_path=target_path,
                check_enabled=check_enabled,
            )

            # Compute relative path
            try:
                rel_path = str(target_path.relative_to(settings.BASE_DIR)).replace("\\", "/")
            except ValueError:
                rel_path = f"generated/rendered_scenes/{target_path.parent.name}/{target_path.name}"

            return RenderedScene(
                scene_id=scene_id,
                video_path=rel_path,
                duration_seconds=result.get("duration_seconds") or visual_scene.duration_seconds,
                engine=self.engine_name,
                success=True,
                error=None,
                metadata={
                    "provider": result.get("provider", provider),
                    "model": result.get("model", model),
                    "resolution": result.get("resolution"),
                    "output_size_mb": result.get("output_size_mb"),
                    "generation_time_seconds": result.get("generation_time_seconds"),
                },
            )

        except HuggingFaceVideoError as hfe:
            logger.warning("[CloudVideoRenderer] Cloud generation failed for scene %s: %s", scene_id, hfe)
            return RenderedScene(
                scene_id=scene_id,
                video_path="",
                duration_seconds=0.0,
                engine=self.engine_name,
                success=False,
                error=str(hfe),
                metadata={
                    "provider": provider,
                    "model": model,
                    "error_type": type(hfe).__name__,
                },
            )
        except Exception as e:
            logger.error("[CloudVideoRenderer] Unexpected error for scene %s: %s", scene_id, e, exc_info=True)
            return RenderedScene(
                scene_id=scene_id,
                video_path="",
                duration_seconds=0.0,
                engine=self.engine_name,
                success=False,
                error=f"Cloud video generation exception: {str(e)}",
                metadata={
                    "provider": provider,
                    "model": model,
                    "error_type": type(e).__name__,
                },
            )
