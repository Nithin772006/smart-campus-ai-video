"""
Abstract Scene Renderer Base Class (Task 9C).
Defines the standard interface for rendering a RoutedScene into an independent MP4 file.
The renderer receives only the routed scene and target output directory.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional

from app.schemas.visual_scene import RoutedScene
from app.schemas.render import RenderedScene


class SceneRenderer(ABC):
    """
    Abstract interface for independent visual scene rendering engines.
    Decoupled from topic planning and final composition.
    """

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Identifier for the engine (e.g. 'manim', 'cloud_video', 'avatar', 'mixed')."""
        pass

    @abstractmethod
    def can_render(self, scene: RoutedScene) -> bool:
        """Determine if this renderer supports the given routed scene."""
        pass

    @abstractmethod
    def render(
        self,
        scene: RoutedScene,
        output_dir: Path,
        **kwargs: Any
    ) -> RenderedScene:
        """
        Render a single routed scene into an MP4 video file.
        
        Args:
            scene: The routed visual scene to render
            output_dir: Target directory path where scene.mp4 should be written
            **kwargs: Engine-specific parameters (e.g. quality, device, audio_path)

        Returns:
            RenderedScene detailing file location, duration, engine, and success status.
        """
        pass
