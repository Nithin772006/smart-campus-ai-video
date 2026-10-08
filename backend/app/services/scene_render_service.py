"""
Scene Render Service (Task 9C).
Orchestrates independent per-scene rendering across Manim, Cloud Video, and Avatar renderers.
Does NOT compose or stitch scenes together into a final video (reserved for Task 9D).
Handles per-scene failures gracefully without terminating the batch.
"""

import time
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.config import settings
from app.schemas.visual_scene import (
    RoutedScene,
    RoutedVideoPlan,
)
from app.schemas.render import (
    RenderedScene,
    TopicRenderResponse,
)
from app.services.renderer_registry import renderer_registry, UnknownEngineError

logger = logging.getLogger(__name__)


def slugify_topic(topic: str) -> str:
    """Produce filesystem-safe directory slug for a topic."""
    cleaned = re.sub(r"[^a-zA-Z0-9\s_]", "", topic).strip().lower()
    slug = re.sub(r"\s+", "_", cleaned)
    return slug if slug else "educational_topic"


class SceneRenderService:
    """
    Coordinates multi-engine rendering of a RoutedVideoPlan into individual scene MP4s.
    """

    def __init__(self, output_base_dir: Optional[Path] = None):
        self.output_base_dir = output_base_dir or settings.RENDERED_SCENES_DIR
        self.output_base_dir.mkdir(parents=True, exist_ok=True)

    def render_plan(
        self,
        plan: RoutedVideoPlan,
        quality: str = "medium_quality",
        **kwargs: Any
    ) -> TopicRenderResponse:
        """
        Iterate through all routed scenes and render each independently.
        Outputs are saved in: output_base_dir / <topic_slug> / <scene_id> / scene.mp4.
        """
        raw_topic = plan.original_plan.topic
        topic_slug = slugify_topic(raw_topic)
        topic_output_dir = self.output_base_dir / topic_slug
        topic_output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "[SceneRenderService] Starting render batch for topic '%s' (%d scenes)",
            raw_topic, len(plan.routed_scenes)
        )

        rendered_scenes: List[RenderedScene] = []
        start_time = time.perf_counter()

        for idx, routed_scene in enumerate(plan.routed_scenes):
            scene_id = routed_scene.scene.scene_id or f"scene_{idx + 1}"
            scene_dir = topic_output_dir / scene_id
            engine_name = routed_scene.selected_engine.value

            logger.info(
                "[SceneRenderService] Rendering [%d/%d] '%s' using engine '%s'",
                idx + 1, len(plan.routed_scenes), scene_id, engine_name
            )

            try:
                renderer = renderer_registry.get_renderer(engine_name)
                rendered_scene = renderer.render(
                    scene=routed_scene,
                    output_dir=scene_dir,
                    quality=quality,
                    **kwargs,
                )
            except UnknownEngineError as uee:
                logger.error("[SceneRenderService] Unknown engine error for %s: %s", scene_id, uee)
                rendered_scene = RenderedScene(
                    scene_id=scene_id,
                    video_path="",
                    duration_seconds=0.0,
                    engine=engine_name,
                    success=False,
                    error=str(uee),
                )
            except Exception as e:
                logger.error("[SceneRenderService] Unexpected error rendering %s: %s", scene_id, e, exc_info=True)
                rendered_scene = RenderedScene(
                    scene_id=scene_id,
                    video_path="",
                    duration_seconds=0.0,
                    engine=engine_name,
                    success=False,
                    error=f"Uncaught render exception: {str(e)}",
                )

            rendered_scenes.append(rendered_scene)

        total_elapsed = round(time.perf_counter() - start_time, 2)
        successful_count = sum(1 for rs in rendered_scenes if rs.success)
        failed_count = len(rendered_scenes) - successful_count
        total_duration = round(sum(rs.duration_seconds for rs in rendered_scenes if rs.success), 2)
        overall_success = successful_count > 0

        logger.info(
            "[SceneRenderService] Batch complete for '%s': %d/%d succeeded in %.2fs",
            raw_topic, successful_count, len(rendered_scenes), total_elapsed
        )

        return TopicRenderResponse(
            success=overall_success,
            topic=raw_topic,
            scene_count=len(rendered_scenes),
            successful_scenes=successful_count,
            failed_scenes=failed_count,
            scenes=rendered_scenes,
            total_duration_seconds=total_duration,
            execution_time_seconds=total_elapsed,
        )


# Singleton service instance
scene_render_service = SceneRenderService()
