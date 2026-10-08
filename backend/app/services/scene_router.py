"""
Scene Router Service (Task 9B).
Deterministically routes visual educational scenes to the optimal rendering engine:
- Manim (equations, formulas, graphs, coordinate systems, algorithms, diagrams)
- Cloud Video (cinematic environments, real-world demonstrations, physics metaphors)
- Avatar (teacher intro, explanation, summary, direct camera address)
- Mixed (composite scenes featuring Manim graphics with teacher overlay)

Enforces safety overrides and explicit fallback engines without generating media.
"""

import logging
from typing import Dict, Any, Optional

from app.schemas.visual_scene import (
    VisualEngine,
    SceneType,
    TeacherPosition,
    VisualScene,
    VisualVideoPlan,
    RoutedScene,
    RoutedVideoPlan,
)

logger = logging.getLogger(__name__)


class SceneRouter:
    """
    Deterministic rule engine that validates and assigns rendering engines to educational scenes.
    Ensures educational rigor by preventing generative cloud models from rendering equations/graphs.
    """

    def route_scene(self, scene: VisualScene) -> RoutedScene:
        """
        Evaluate a single visual scene and produce a RoutedScene decision.
        Applies strict pedagogical engine allocation and safety overrides.
        """
        scene_type = scene.scene_type
        requested_engine = scene.visual_engine

        selected_engine: VisualEngine
        routing_reason: str
        fallback_engine: Optional[VisualEngine] = VisualEngine.MANIM
        cloud_generation_required: bool = False

        # RULE 1: Mathematical Equations & Coordinate Graphs MUST use Manim
        if scene_type in (SceneType.EQUATION, SceneType.GRAPH):
            selected_engine = VisualEngine.MANIM
            if requested_engine == VisualEngine.CLOUD_VIDEO:
                routing_reason = (
                    "Override: Equations and coordinate graphs require exact LaTeX typography and vector curves; "
                    "cloud generative video cannot guarantee mathematical accuracy."
                )
            else:
                routing_reason = "Equations and coordinate graphs are routed to Manim for precise mathematical and vector rendering."
            fallback_engine = VisualEngine.MANIM
            cloud_generation_required = False

        # RULE 2: Algorithms, Flowcharts, Diagrams, Processes, and Timelines
        elif scene_type in (SceneType.ALGORITHM, SceneType.DIAGRAM, SceneType.PROCESS, SceneType.TIMELINE, SceneType.COMPARISON) and requested_engine != VisualEngine.MIXED:
            if requested_engine == VisualEngine.CLOUD_VIDEO:
                selected_engine = VisualEngine.MANIM
                routing_reason = (
                    "Override: Algorithmic structures, logic flowcharts, and technical diagrams require deterministic vector graphics."
                )
            else:
                selected_engine = VisualEngine.MANIM
                routing_reason = "Technical process diagrams and algorithms render deterministically via Manim."
            fallback_engine = VisualEngine.MANIM
            cloud_generation_required = False

        # RULE 3: AI Teacher Intros, Summaries, and Spoken Highlights
        elif scene_type in (SceneType.TEACHER_INTRO, SceneType.TEACHER_EXPLANATION, SceneType.TEACHER_SUMMARY) or (
            requested_engine == VisualEngine.AVATAR and scene.teacher_enabled
        ):
            selected_engine = VisualEngine.AVATAR
            routing_reason = "Direct educational address and lecture milestones are routed to the AI teacher avatar."
            # Ensure teacher presence is configured
            if not scene.teacher_enabled:
                scene.teacher_enabled = True
            if scene.teacher_position == TeacherPosition.NONE:
                scene.teacher_position = TeacherPosition.CENTER if scene_type == SceneType.TEACHER_INTRO else TeacherPosition.RIGHT
            fallback_engine = VisualEngine.MANIM  # Safe local fallback to Manim slide if avatar unavailable
            cloud_generation_required = False

        # RULE 4: Cinematic Shots, Natural Environments & Metaphors
        elif scene_type == SceneType.CINEMATIC or (
            requested_engine == VisualEngine.CLOUD_VIDEO and scene_type in (
                SceneType.PHYSICS_SIMULATION, SceneType.CHEMISTRY_VISUAL, SceneType.BIOLOGY_VISUAL, SceneType.EXPLANATION
            )
        ):
            selected_engine = VisualEngine.CLOUD_VIDEO
            routing_reason = "Photorealistic environment and dynamic real-world motion benefit from generative cloud video synthesis."
            fallback_engine = VisualEngine.MANIM  # If cloud video unavailable/unfunded, fall back to vector diagram
            cloud_generation_required = True

            # Task 9F: Enforce short cloud duration (3–8s)
            if scene.duration_seconds > 8.0:
                scene.duration_seconds = 8.0
            elif scene.duration_seconds < 3.0:
                scene.duration_seconds = 3.0

            # Ensure cloud prompt is available
            if not scene.visual_prompt or not scene.visual_prompt.strip():
                scene.visual_prompt = (
                    f"A cinematic educational visualization of {scene.visual_description}, "
                    "clean classroom visual, smooth motion, realistic lighting, no text, no watermark"
                )

        # RULE 5: Composite / Mixed Scenes
        elif requested_engine == VisualEngine.MIXED or (
            scene.teacher_enabled and scene_type not in (SceneType.TEACHER_INTRO, SceneType.TEACHER_SUMMARY)
        ):
            selected_engine = VisualEngine.MIXED
            routing_reason = "Composite layout combining primary Manim educational graphics with secondary AI teacher overlay."
            fallback_engine = VisualEngine.MANIM
            cloud_generation_required = False
            # Ensure teacher is docked to side so central diagrams remain visible
            if scene.teacher_position in (TeacherPosition.NONE, TeacherPosition.CENTER):
                scene.teacher_position = TeacherPosition.RIGHT

        # RULE 6: Title and Transition Cards
        elif scene_type in (SceneType.TITLE, SceneType.TRANSITION):
            selected_engine = VisualEngine.MANIM
            routing_reason = "Title cards and topic transitions are rendered with clean geometric typography via Manim."
            fallback_engine = VisualEngine.MANIM
            cloud_generation_required = False

        # RULE 7: General Educational Default
        else:
            selected_engine = VisualEngine.MANIM
            routing_reason = "Educational visual content defaults to Manim vector graphics for verified precision."
            fallback_engine = VisualEngine.MANIM
            cloud_generation_required = False

        return RoutedScene(
            scene=scene,
            selected_engine=selected_engine,
            routing_reason=routing_reason,
            fallback_engine=fallback_engine,
            cloud_generation_required=cloud_generation_required,
        )

    def route_plan(self, plan: VisualVideoPlan) -> RoutedVideoPlan:
        """
        Route an entire VisualVideoPlan scene by scene.
        Aggregates summary statistics of engine allocations.
        """
        routed_scenes = [self.route_scene(scene) for scene in plan.scenes]

        engine_counts: Dict[str, int] = {
            VisualEngine.MANIM.value: 0,
            VisualEngine.CLOUD_VIDEO.value: 0,
            VisualEngine.AVATAR.value: 0,
            VisualEngine.MIXED.value: 0,
        }

        for routed in routed_scenes:
            engine_key = routed.selected_engine.value
            engine_counts[engine_key] = engine_counts.get(engine_key, 0) + 1

        # Prune zero-count engines for cleaner output
        engine_summary = {k: v for k, v in engine_counts.items() if v > 0}

        logger.info(
            "Visual plan routed for topic '%s' (%d scenes): %s",
            plan.topic, len(routed_scenes), engine_summary
        )

        return RoutedVideoPlan(
            original_plan=plan,
            routed_scenes=routed_scenes,
            engine_summary=engine_summary,
        )


# Singleton router instance
scene_router = SceneRouter()
