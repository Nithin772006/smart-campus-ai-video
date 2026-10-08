import os
import re
import json
import time
import shutil
import logging
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from app.config import settings
from app.schemas.character import (
    CharacterPosition,
    CharacterSpec,
    AvatarPreviewResponse,
)

logger = logging.getLogger(__name__)


class AvatarError(Exception):
    """Base exception for avatar and presenter generation failures."""
    pass


class AvatarProviderUnavailableError(AvatarError):
    """Raised when the selected avatar provider is not available or supported."""
    pass


class CharacterAssetError(AvatarError):
    """Raised when canonical character asset is missing or corrupted."""
    pass


class AvatarProvider(ABC):
    """
    Abstract base provider for talking avatar generation.
    Enables pluggable backends (MuseTalk, LivePortrait, SadTalker, Cloud, Overlay).
    """

    @abstractmethod
    def get_name(self) -> str:
        """Unique identifier for this avatar provider."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Verify whether this provider's dependencies and weights are ready."""
        pass

    def is_animated(self) -> bool:
        """Indicates whether this provider genuinely generates neural/lip-sync animation."""
        return False

    def get_capabilities(self) -> Dict[str, bool]:
        """Granular dictionary of animation capabilities supported by this provider."""
        return {
            "lip_sync": False,
            "head_motion": False,
            "full_body_gesture": False,
        }

    def get_unavailability_reason(self) -> Optional[str]:
        """Human-readable explanation if this provider is unavailable."""
        return None

    @abstractmethod
    def generate(
        self,
        image_path: Path,
        audio_path: Path,
        output_path: Path,
        options: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Generate talking avatar video from static image and audio track.

        Args:
            image_path: Canonical character image (PNG with transparency)
            audio_path: Narration audio track (WAV)
            output_path: Destination path for rendered video
            options: Optional provider-specific settings

        Returns:
            Path to the generated video file
        """
        pass


class MuseTalkAvatarProvider(AvatarProvider):
    """
    MuseTalk lip-sync talking avatar provider.
    Evaluated in backend/avatar_lab/.
    """

    def __init__(self):
        self.lab_dir = settings.BASE_DIR / "avatar_lab" / "MuseTalk"
        self.weights_dir = self.lab_dir / "models"

    def get_name(self) -> str:
        return "musetalk"

    def is_animated(self) -> bool:
        return True

    def get_capabilities(self) -> Dict[str, bool]:
        return {
            "lip_sync": True,
            "head_motion": True,
            "full_body_gesture": False,
        }

    def get_unavailability_reason(self) -> Optional[str]:
        if not self.lab_dir.exists():
            return "MuseTalk repository not found at backend/avatar_lab/MuseTalk"

        import importlib
        try:
            mmcv_ext = importlib.util.find_spec("mmcv._ext")
            if mmcv_ext is None:
                return (
                    "MuseTalk is not available on this host: missing compiled mmcv._ext native extensions "
                    "on Windows (requires MSVC/nvcc toolchain) and exceeds 4.0 GB VRAM limit of RTX 2050 "
                    "(requires ~5.0-6.2 GB VRAM). See backend/avatar_lab/FEASIBILITY_REPORT.md."
                )
        except Exception:
            return (
                "MuseTalk is not available on this host: missing compiled mmcv._ext native extensions "
                "on Windows (requires MSVC/nvcc toolchain) and exceeds 4.0 GB VRAM limit of RTX 2050 "
                "(requires ~5.0-6.2 GB VRAM). See backend/avatar_lab/FEASIBILITY_REPORT.md."
            )


        unet_weight = self.weights_dir / "musetalk" / "pytorch_model.bin"
        vae_weight = self.weights_dir / "sd-vae" / "diffusion_pytorch_model.bin"
        if not (unet_weight.exists() and vae_weight.exists()):
            return "MuseTalk model weights missing in avatar_lab/MuseTalk/models"

        return None

    def is_available(self) -> bool:
        """
        Checks if MuseTalk codebase, weights, and compiled C++ dependencies (mmcv._ext) are present.
        """
        # 1. Codebase presence
        if not self.lab_dir.exists():
            return False

        # 2. Check compiled MMCV C++ extensions
        # On Windows, mmcv._ext is missing when Visual C++ / CUDA toolkit is not installed.
        try:
            import importlib
            mmcv_ext = importlib.util.find_spec("mmcv._ext")
            if mmcv_ext is None:
                return False
        except Exception:
            return False

        # 3. Model weights presence
        unet_weight = self.weights_dir / "musetalk" / "pytorch_model.bin"
        vae_weight = self.weights_dir / "sd-vae" / "diffusion_pytorch_model.bin"
        if not (unet_weight.exists() and vae_weight.exists()):
            return False

        return True

    def generate(
        self,
        image_path: Path,
        audio_path: Path,
        output_path: Path,
        options: Optional[Dict[str, Any]] = None,
    ) -> Path:
        if not self.is_available():
            reason = self.get_unavailability_reason() or "MuseTalk is not available on this system."
            raise AvatarProviderUnavailableError(reason)

        logger.info("[MuseTalk] Running inference for %s with %s", image_path.name, audio_path.name)
        raise NotImplementedError("MuseTalk inference execution requires full MMCV CUDA toolchain.")


class CloudAvatarProvider(AvatarProvider):
    """
    Cloud / Remote Talking Avatar Provider.
    Configurable via environment variables (AVATAR_CLOUD_PROVIDER, AVATAR_CLOUD_API_URL, AVATAR_CLOUD_API_KEY).
    Handles remote neural lip-sync generation without local VRAM limitations.
    """

    def __init__(self):
        self.provider_type = getattr(settings, "AVATAR_CLOUD_PROVIDER", "replicate")
        self.api_url = getattr(settings, "AVATAR_CLOUD_API_URL", "")
        self.api_key = getattr(settings, "AVATAR_CLOUD_API_KEY", "")

    def get_name(self) -> str:
        return "cloud"

    def is_animated(self) -> bool:
        return True

    def get_capabilities(self) -> Dict[str, bool]:
        return {
            "lip_sync": True,
            "head_motion": True,
            "full_body_gesture": False,
        }

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def get_unavailability_reason(self) -> Optional[str]:
        if not self.is_available():
            return "Cloud Avatar Provider is unconfigured (set AVATAR_CLOUD_API_KEY in backend/.env)."
        return None

    def generate(
        self,
        image_path: Path,
        audio_path: Path,
        output_path: Path,
        options: Optional[Dict[str, Any]] = None,
    ) -> Path:
        if not self.is_available():
            raise AvatarProviderUnavailableError(self.get_unavailability_reason())

        logger.info("[CloudAvatar] Submitting %s and %s to %s", image_path.name, audio_path.name, self.provider_type)
        raise NotImplementedError("Cloud Avatar remote endpoint not configured or active.")


class TeacherAvatarOverlayProvider(AvatarProvider):
    """
    Local Educational Teacher Presenter Provider.
    High-fidelity, zero-OOM, rock-solid fallback provider that renders
    the canonical transparent 3D teacher with exact audio synchronization.
    """

    def __init__(self):
        self.ffmpeg_bin = self._find_ffmpeg()

    def _find_ffmpeg(self) -> str:
        candidates = [
            settings.FFMPEG_PATH,
            "ffmpeg",
            "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe",
            "C:\\ffmpeg\\bin\\ffmpeg.exe",
        ]
        for c in candidates:
            if shutil.which(c):
                return c
        return "ffmpeg"

    def get_name(self) -> str:
        return "overlay"

    def is_animated(self) -> bool:
        return False

    def get_capabilities(self) -> Dict[str, bool]:
        return {
            "lip_sync": False,
            "head_motion": False,
            "full_body_gesture": False,
        }

    def is_available(self) -> bool:
        return bool(shutil.which(self.ffmpeg_bin))

    def get_unavailability_reason(self) -> Optional[str]:
        if not self.is_available():
            return "FFmpeg binary is not accessible for TeacherAvatarOverlayProvider"
        return None

    def generate(
        self,
        image_path: Path,
        audio_path: Path,
        output_path: Path,
        options: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Generates an avatar video clip of the canonical teacher matching
        the audio duration, with AAC audio and H.264 video.
        """
        if not image_path.exists():
            raise CharacterAssetError(f"Teacher image not found at {image_path}")
        if not audio_path.exists():
            raise AvatarError(f"Narration audio not found at {audio_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        opts = options or {}
        fps = opts.get("fps", 30)

        # Audio is Master Clock: ensure video duration matches audio duration exactly
        target_dur = opts.get("duration")
        if target_dur is None:
            try:
                from app.services.ffmpeg_service import ffmpeg_service
                probe = ffmpeg_service.probe_media(audio_path)
                target_dur = float(probe.get("duration", 0))
            except Exception:
                target_dur = None

        # Build clean loop video matching audio length with web-compatible H.264
        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-loop", "1",
            "-framerate", str(fps),
            "-i", str(image_path),
            "-i", str(audio_path),
        ]
        if target_dur and target_dur > 0:
            cmd.extend(["-t", str(target_dur)])
        cmd.extend([
            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-c:v", settings.VIDEO_CODEC,
            "-pix_fmt", settings.PIXEL_FORMAT,
            "-c:a", settings.AUDIO_CODEC,
            "-b:a", settings.AUDIO_BITRATE,
            "-shortest",
            "-movflags", settings.MOVFLAGS,
            str(output_path),
        ])

        logger.info("[TeacherAvatar] Generating avatar video: %s", " ".join(cmd))
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise AvatarError(f"Teacher avatar generation failed: {res.stderr[-400:]}")

        return output_path


class AvatarService:
    """
    Central orchestration service for character assets, preview generation,
    and talking avatar provider management.
    """

    def __init__(self):
        self.canonical_image_path = settings.CANONICAL_TEACHER_IMAGE
        self.spec_path = settings.CHARACTER_DIR / "character_spec.json"
        self.output_dir = settings.AVATAR_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Register providers
        self.providers: Dict[str, AvatarProvider] = {
            "musetalk": MuseTalkAvatarProvider(),
            "cloud": CloudAvatarProvider(),
            "overlay": TeacherAvatarOverlayProvider(),
            "teacher_overlay": TeacherAvatarOverlayProvider(),
        }

    def get_available_providers(self) -> List[str]:
        """Returns list of registered avatar provider identifiers."""
        return list(self.providers.keys())

    def get_provider(self, name: Optional[str] = None) -> AvatarProvider:
        """
        Retrieves requested provider, falling back gracefully to the
        overlay provider if requested provider is unavailable.
        """
        prov, _ = self.get_provider_with_fallback(name)

        return prov

    def get_provider_with_fallback(
        self,
        name: Optional[str] = None,
    ) -> Tuple[AvatarProvider, bool]:
        """
        Retrieves requested provider along with a boolean indicating whether
        fallback to TeacherAvatarOverlayProvider was activated.
        Returns: (active_provider, fallback_used)
        """
        raw_name = (name or settings.AVATAR_PROVIDER or "auto").lower()

        if raw_name in ("overlay", "teacher_overlay"):
            return self.providers["overlay"], False

        if raw_name == "auto":
            # Priority: MuseTalk -> Cloud -> Overlay
            for cand in ("musetalk", "cloud"):
                p = self.providers.get(cand)
                if p and p.is_available():
                    return p, False
            logger.info("Auto avatar selection: Neural providers unavailable; using TeacherAvatarOverlayProvider.")
            return self.providers["overlay"], True

        provider = self.providers.get(raw_name)
        if provider and provider.is_available():
            return provider, False

        # Fallback to overlay
        fallback = self.providers["overlay"]
        logger.info("Provider '%s' unavailable; falling back to '%s'", raw_name, fallback.get_name())
        return fallback, True

    def get_status(self, requested_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Provides comprehensive provider diagnostic status for GET /api/avatar/status.
        """
        selected = (requested_name or settings.AVATAR_PROVIDER or "auto").lower()
        active_prov, fallback_used = self.get_provider_with_fallback(selected)

        # Inspect target provider specifically
        target_prov = self.providers.get(selected)
        if selected == "auto":
            target_prov = self.providers.get("musetalk")

        is_avail = target_prov.is_available() if target_prov else False
        reason = target_prov.get_unavailability_reason() if (target_prov and not is_avail) else None

        import torch
        device_name = "cuda" if torch.cuda.is_available() else "cpu"

        return {
            "enabled": True,
            "selected_provider": selected,
            "active_provider": active_prov.get_name(),
            "available": is_avail,
            "device": device_name,
            "animated": active_prov.is_animated(),
            "reason": reason,
            "fallback_provider": "teacher_overlay",
            "fallback_used": fallback_used,
            "capabilities": active_prov.get_capabilities(),
        }

    def validate_canonical_character(self) -> Dict[str, Any]:
        """
        Verifies that canonical character image and spec file are intact.
        """
        if not self.canonical_image_path.exists():
            raise CharacterAssetError(f"Canonical teacher image missing: {self.canonical_image_path}")

        spec_data = {}
        if self.spec_path.exists():
            try:
                spec_data = json.loads(self.spec_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Could not parse character_spec.json: %s", e)

        # Verify image properties using PIL
        try:
            from PIL import Image
            with Image.open(self.canonical_image_path) as img:
                width, height = img.size
                mode = img.mode
                has_alpha = "A" in mode
        except Exception as e:
            raise CharacterAssetError(f"Could not open canonical teacher image: {e}")

        return {
            "image_path": str(self.canonical_image_path),
            "width": width,
            "height": height,
            "mode": mode,
            "has_alpha": has_alpha,
            "size_bytes": self.canonical_image_path.stat().st_size,
            "spec": spec_data,
        }

    def _find_sample_audio(self, max_duration: float = 15.0) -> Path:
        """
        Discovers a short existing IndicF5 narration WAV from generated/audio/.
        Prefers clips around 10-20 seconds.
        """
        audio_dir = settings.AUDIO_DIR
        candidates = list(audio_dir.glob("*/narration.wav"))

        if not candidates:
            raise AvatarError("No existing narration audio found in generated/audio/ to use for avatar preview.")

        # Try to find one near the requested duration
        best_candidate = candidates[0]
        # Prioritize newtons_second_law or newtons_second_law_of_motion
        for c in candidates:
            if "newtons_second_law" in c.parent.name:
                best_candidate = c
                break

        return best_candidate

    def generate_preview(
        self,
        duration: float = 10.0,
        position: str = "auto",
        provider_name: Optional[str] = None,
        audio_path: Optional[str] = None,
    ) -> AvatarPreviewResponse:
        """
        Generates an avatar preview video using the canonical teacher and sample audio.
        Endpoint: POST /api/avatar/preview
        """
        start_time = time.time()
        self.validate_canonical_character()

        if audio_path and Path(audio_path).exists():
            sample_audio = Path(audio_path).resolve()
        else:
            sample_audio = self._find_sample_audio(max_duration=duration)

        provider, fallback_used = self.get_provider_with_fallback(provider_name)
        fallback_reason = None
        if fallback_used:
            target_p = self.providers.get((provider_name or settings.AVATAR_PROVIDER or "auto").lower())
            fallback_reason = target_p.get_unavailability_reason() if target_p else "Requested provider unavailable"

        preview_dir = self.output_dir / "previews"
        preview_dir.mkdir(parents=True, exist_ok=True)
        preview_output = preview_dir / f"preview_{int(time.time())}.mp4"

        # Generate avatar video
        generated_path = provider.generate(
            image_path=self.canonical_image_path,
            audio_path=sample_audio,
            output_path=preview_output,
            options={"position": position, "fps": 30},
        )

        elapsed = round(time.time() - start_time, 2)

        # Probe output video properties
        from app.services.ffmpeg_service import get_video_duration
        measured_dur = get_video_duration(generated_path)

        rel_path = str(generated_path.relative_to(settings.BASE_DIR)).replace("\\", "/") if generated_path.is_relative_to(settings.BASE_DIR) else str(generated_path)
        video_url = f"/api/files/{rel_path}"

        return AvatarPreviewResponse(
            success=True,
            provider=provider.get_name(),
            video_path=rel_path,
            video_url=video_url,
            duration_seconds=measured_dur,
            generation_time_seconds=elapsed,
            character_name="SmartCampus Teacher",
            resolution="1145x1374",
            fps=30.0,
            is_animated=provider.is_animated(),
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            capabilities=provider.get_capabilities(),
        )


# Global singleton instance
avatar_service = AvatarService()
