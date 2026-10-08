"""
Renderer Registry Service (Task 9C).
Maintains and resolves visual scene renderers by engine identifier.
Centralizes engine selection to prevent scattered dispatch logic.
"""

import logging
from typing import Dict, List, Optional

from app.services.renderers.base import SceneRenderer
from app.services.renderers.manim_renderer import ManimRenderer
from app.services.renderers.cloud_video_renderer import CloudVideoRenderer
from app.services.renderers.avatar_renderer import AvatarRenderer

logger = logging.getLogger(__name__)


class UnknownEngineError(ValueError):
    """Raised when an unknown or unsupported visual engine is requested."""
    pass


class RendererRegistry:
    """
    Central registry mapping visual engine identifiers to SceneRenderer instances.
    """

    def __init__(self):
        self._renderers: Dict[str, SceneRenderer] = {}
        self._initialize_defaults()

    def _initialize_defaults(self):
        """Register the core standard renderers for Manim, Cloud Video, and Avatar."""
        manim_inst = ManimRenderer()
        cloud_inst = CloudVideoRenderer()
        avatar_inst = AvatarRenderer()

        self.register("manim", manim_inst)
        self.register("cloud_video", cloud_inst)
        self.register("avatar", avatar_inst)
        # Mixed scenes render primary visual elements via Manim vector graphics
        self.register("mixed", manim_inst)

    def register(self, engine_name: str, renderer: SceneRenderer) -> None:
        """Register a renderer under an engine identifier."""
        key = engine_name.strip().lower()
        self._renderers[key] = renderer
        logger.debug("[RendererRegistry] Registered renderer for '%s': %s", key, renderer.__class__.__name__)

    def get_renderer(self, engine: str) -> SceneRenderer:
        """
        Retrieve the registered renderer for the given engine identifier.
        Raises UnknownEngineError if no renderer is registered for the engine.
        """
        if not engine:
            raise UnknownEngineError("Visual engine identifier cannot be empty.")

        key = engine.strip().lower()
        if key not in self._renderers:
            available = list(self._renderers.keys())
            raise UnknownEngineError(
                f"Unknown visual engine '{engine}'. Registered engines: {available}"
            )
        return self._renderers[key]

    def available_engines(self) -> List[str]:
        """List all registered engine names."""
        return list(self._renderers.keys())


# Singleton registry instance
renderer_registry = RendererRegistry()
