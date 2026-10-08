"""
Avatar Scene Renderer (Task 9E).
Renders educational teacher presenter scenes using the AvatarService abstraction,
supporting real neural talking avatar providers (e.g. MuseTalk, Cloud) with guaranteed
rock-solid fallback to TeacherAvatarOverlayProvider.
Accurately reports animation status, lip-sync, and gesture capabilities.
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
    Uses the canonical 3D transparent teacher asset with guaranteed local stability
    and support for automated talking avatar generation.
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

    def _prepare_scene_audio(
        self,
        duration_seconds: float,
        output_dir: Path,
        **kwargs: Any
    ) -> Path:
        """
        Resolves or extracts scene-specific audio for avatar animation.
        Ensures avatar provider receives only the audio for this specific scene segment.
        """
        audio_path = kwargs.get("audio_path")
        master_audio = kwargs.get("master_audio_path")
        start_time = kwargs.get("start_time")
        end_time = kwargs.get("end_time")

        ffmpeg_bin = self.overlay_provider.ffmpeg_bin

        # 1. Master audio with start and end times provided
        if master_audio and Path(master_audio).exists() and start_time is not None:
            slice_path = output_dir / "scene_audio_slice.wav"
            dur = (end_time - start_time) if (end_time is not None and end_time > start_time) else duration_seconds
            cmd = [
                ffmpeg_bin, "-y",
                "-ss", str(max(0.0, float(start_time))),
                "-t", str(max(0.5, float(dur))),
                "-i", str(master_audio),
                "-c:a", "pcm_s16le",
                str(slice_path)
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0 and slice_path.exists():
                return slice_path

        # 2. Direct scene audio provided
        if audio_path and Path(audio_path).exists():
            return Path(audio_path)

        # 3. Create silence audio clip of exact duration
        silence_path = output_dir / "scene_audio_silence.wav"
        cmd = [
            ffmpeg_bin, "-y",
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-t", str(max(1.0, float(duration_seconds))),
            "-c:a", "pcm_s16le",
            str(silence_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and silence_path.exists():
            return silence_path

        # Fallback to empty dummy path
        return output_dir / "silent.wav"

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

        # Resolve provider
        requested_provider = (
            kwargs.get("avatar_provider")
            or kwargs.get("provider")
            or settings.AVATAR_PROVIDER
            or "auto"
        )
        active_provider, fallback_used = self.service.get_provider_with_fallback(requested_provider)

        # Prepare scene-specific audio segment
        scene_audio = self._prepare_scene_audio(duration_seconds, output_dir, **kwargs)

        try:
            # Generate avatar video using active provider
            try:
                active_provider.generate(
                    image_path=canonical_image,
                    audio_path=scene_audio,
                    output_path=target_path,
                    options={
                        "duration": duration_seconds,
                        "fps": 30,
                        "position": visual_scene.teacher_position.value,
                    },
                )
            except Exception as pe:
                logger.warning(
                    "[AvatarRenderer] Primary provider '%s' failed for %s (%s). Falling back to TeacherAvatarOverlayProvider.",
                    active_provider.get_name(), scene_id, pe
                )
                fallback_used = True
                active_provider = self.overlay_provider
                self.overlay_provider.generate(
                    image_path=canonical_image,
                    audio_path=scene_audio,
                    output_path=target_path,
                    options={
                        "duration": duration_seconds,
                        "fps": 30,
                        "position": visual_scene.teacher_position.value,
                    },
                )

            # Probe media if ffprobe available
            probe_dur = duration_seconds
            width, height, codec = None, None, "h264"
            if ffmpeg_service.is_available() and target_path.exists():
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

            capabilities = active_provider.get_capabilities()
            is_animated = active_provider.is_animated() if not fallback_used else False
            prov_name = "teacher_overlay" if active_provider.get_name() in ("overlay", "teacher_overlay") else active_provider.get_name()

            return RenderedScene(
                scene_id=scene_id,
                video_path=rel_path,
                duration_seconds=probe_dur,
                engine=self.engine_name,
                success=True,
                error=None,
                metadata={
                    "provider": prov_name,
                    "avatar_provider": prov_name,
                    "animated": is_animated,
                    "lip_sync": capabilities.get("lip_sync", False) if not fallback_used else False,
                    "head_motion": capabilities.get("head_motion", False) if not fallback_used else False,
                    "full_body_gesture": capabilities.get("full_body_gesture", False) if not fallback_used else False,
                    "fallback_used": fallback_used,
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
                metadata={
                    "provider": "teacher_overlay",
                    "avatar_provider": "teacher_overlay",
                    "animated": False,
                    "lip_sync": False,
                    "head_motion": False,
                    "full_body_gesture": False,
                    "fallback_used": True,
                },
            )


