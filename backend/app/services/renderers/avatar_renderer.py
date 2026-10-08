"""
Avatar Scene Renderer (Task 9C).
Renders educational teacher presenter scenes using the existing AvatarService
and TeacherAvatarOverlayProvider local fallback.
Clearly identifies provider as 'teacher_overlay' without claiming lip-sync animation.
"""

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from app.config import settings
from app.schemas.visual_scene import (
    VisualEngine,
    SceneType,
    TeacherPosition,
    RoutedScene,
)
from app.schemas.render import RenderedScene
from app.services.renderers.base import SceneRenderer
from app.services.avatar_service import (
    avatar_service,
    AvatarService,
    TeacherAvatarOverlayProvider,
    AvatarError,
)
from app.services.ffmpeg_service import ffmpeg_service

logger = logging.getLogger(__name__)


class AvatarRenderer(SceneRenderer):
    """
    Renders teacher introduction, explanation, and summary scenes.
    Uses the canonical 3D transparent teacher asset with guaranteed local stability.
    """

    SUPPORTED_TYPES = {
        SceneType.TEACHER_INTRO,
        SceneType.TEACHER_EXPLANATION,
        SceneType.TEACHER_SUMMARY,
        SceneType.EXPLANATION,
        SceneType.TITLE,
    }

    def __init__(self, service: Optional[AvatarService] = None):
        self.service = service or avatar_service
        self.overlay_provider = TeacherAvatarOverlayProvider()

    @property
    def engine_name(self) -> str:
        return "avatar"

    def can_render(self, scene: RoutedScene) -> bool:
        """Checks if the scene is targeted for Avatar or has teacher enabled."""
        return scene.selected_engine == VisualEngine.AVATAR or scene.scene.teacher_enabled

    def render(
        self,
        scene: RoutedScene,
        output_dir: Path,
        **kwargs: Any
    ) -> RenderedScene:
        """
        Generate avatar video for the scene matching the target duration.
        Saves output to output_dir / "scene.mp4".
        """
        visual_scene = scene.scene
        scene_id = visual_scene.scene_id
        duration_seconds = visual_scene.duration_seconds

        output_dir.mkdir(parents=True, exist_ok=True)
        target_path = output_dir / "scene.mp4"

        canonical_image = settings.CANONICAL_TEACHER_IMAGE
        if not canonical_image.exists():
            return RenderedScene(
                scene_id=scene_id,
                video_path="",
                duration_seconds=0.0,
                engine=self.engine_name,
                success=False,
                error=f"Canonical teacher image missing at {canonical_image}",
            )

        # Check if an audio track was provided (e.g. from TTS)
        audio_path = kwargs.get("audio_path")
        ffmpeg_bin = self.overlay_provider.ffmpeg_bin

        try:
            if audio_path and Path(audio_path).exists():
                # Render avatar locked to narration audio track
                self.overlay_provider.generate(
                    image_path=canonical_image,
                    audio_path=Path(audio_path),
                    output_path=target_path,
                )
            else:
                # Render avatar video loop for duration_seconds with silent audio track
                cmd = [
                    ffmpeg_bin,
                    "-y",
                    "-loop", "1",
                    "-framerate", "30",
                    "-i", str(canonical_image),
                    "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                    "-t", str(duration_seconds),
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                    "-c:v", settings.VIDEO_CODEC,
                    "-pix_fmt", settings.PIXEL_FORMAT,
                    "-c:a", settings.AUDIO_CODEC,
                    "-b:a", settings.AUDIO_BITRATE,
                    "-movflags", settings.MOVFLAGS,
                    str(target_path),
                ]

                logger.info("[AvatarRenderer] Generating avatar scene video: %s (%.2fs)", scene_id, duration_seconds)
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode != 0:
                    raise AvatarError(f"Avatar FFmpeg generation failed: {res.stderr[-300:]}")

            # Probe media if ffprobe available
            probe_dur = duration_seconds
            width, height, codec = None, None, "h264"
            if ffmpeg_service.is_available():
                try:
                    probe = ffmpeg_service.probe_media(target_path)
                    probe_dur = probe.get("duration", duration_seconds)
                    width = probe.get("width")
                    height = probe.get("height")
                    codec = probe.get("video_codec", "h264")
                except Exception as pe:
                    logger.warning("Optional probe failed: %s", pe)

            # Compute relative path
            try:
                rel_path = str(target_path.relative_to(settings.BASE_DIR)).replace("\\", "/")
            except ValueError:
                rel_path = f"generated/rendered_scenes/{target_path.parent.name}/{target_path.name}"

            return RenderedScene(
                scene_id=scene_id,
                video_path=rel_path,
                duration_seconds=probe_dur,
                engine=self.engine_name,
                success=True,
                error=None,
                metadata={
                    "provider": "teacher_overlay",
                    "character": "SmartCampus Teacher",
                    "position": visual_scene.teacher_position.value,
                    "resolution": f"{width}x{height}" if width and height else "1144x1374",
                    "codec": codec,
                    "has_alpha": True,
                },
            )

        except Exception as e:
            logger.error("[AvatarRenderer] Failed to render avatar scene %s: %s", scene_id, e, exc_info=True)
            return RenderedScene(
                scene_id=scene_id,
                video_path="",
                duration_seconds=0.0,
                engine=self.engine_name,
                success=False,
                error=f"AvatarRenderer error: {str(e)}",
                metadata={"provider": "teacher_overlay"},
            )
