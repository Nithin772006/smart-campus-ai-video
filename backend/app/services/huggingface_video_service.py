"""
Service for Hugging Face Inference Providers Cloud Video Generation (Task 9A Proof of Concept).
Provides a clean provider abstraction for generating AI educational scene clips via cloud inference.
"""

import os
import re
import time
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, List

from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError

from app.config import settings

logger = logging.getLogger(__name__)


class HuggingFaceVideoError(Exception):
    """Base exception for all Hugging Face video generation operations."""
    pass


class HuggingFaceVideoConfigError(HuggingFaceVideoError):
    """Raised when configuration or authentication credentials are missing."""
    pass


class HuggingFaceVideoDisabledError(HuggingFaceVideoError):
    """Raised when cloud video generation is invoked while globally disabled."""
    pass


class HuggingFaceAPIError(HuggingFaceVideoError):
    """Raised when Hugging Face Inference API returns an error or invalid payload."""
    pass


class HuggingFaceTimeoutError(HuggingFaceVideoError):
    """Raised when Hugging Face API call times out."""
    pass


class CloudVideoProvider(ABC):
    """Abstract base class for cloud text-to-video providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        output_path: Optional[Path] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Generate a video from text prompt and save to output_path.
        Returns metadata dictionary.
        """
        pass


def slugify_prompt(prompt: str, max_words: int = 5) -> str:
    """Create a clean, filesystem-safe slug from a prompt."""
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", prompt).strip().lower()
    words = cleaned.split()[:max_words]
    return "_".join(words) if words else "scene"


class HuggingFaceVideoService(CloudVideoProvider):
    """
    Client and generator for Hugging Face Inference Providers text-to-video API.
    Uses official huggingface_hub.InferenceClient.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        default_provider: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: Optional[float] = None,
        output_dir: Optional[Path] = None,
    ):
        self.token = token if token is not None else (os.getenv("HF_TOKEN") or settings.HF_TOKEN or "")
        self.default_provider = default_provider or settings.HF_VIDEO_PROVIDER or "fal-ai"
        self.default_model = default_model or settings.HF_VIDEO_MODEL or "Wan-AI/Wan2.2-TI2V-5B"
        self.timeout = timeout or settings.HF_VIDEO_TIMEOUT or 300.0
        self.output_dir = output_dir or settings.CLOUD_VIDEO_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def is_configured(self) -> bool:
        """Returns True if a non-empty HF token is present."""
        return bool(self.token and self.token.strip())

    def is_enabled(self) -> bool:
        """Returns True if the cloud video feature is enabled."""
        return bool(settings.HF_VIDEO_ENABLED)

    def get_status(self) -> Dict[str, Any]:
        """Returns non-sensitive status information for the health/status endpoint."""
        return {
            "enabled": self.is_enabled(),
            "provider": self.default_provider,
            "model": self.default_model,
            "token_configured": self.is_configured(),
        }

    def _get_unique_output_path(self, prompt: str) -> Path:
        """Generate a collision-free output MP4 filepath."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        slug = slugify_prompt(prompt)
        base_name = f"cloud_{timestamp}_{slug}"
        candidate = self.output_dir / f"{base_name}.mp4"
        counter = 1
        while candidate.exists():
            candidate = self.output_dir / f"{base_name}_{counter}.mp4"
            counter += 1
        return candidate

    def _get_client(self, provider: str) -> InferenceClient:
        """Instantiate an official InferenceClient for the selected provider."""
        if not self.is_configured():
            raise HuggingFaceVideoConfigError(
                "HF_TOKEN is missing or empty. Please set HF_TOKEN in your backend/.env file."
            )
        return InferenceClient(
            provider=provider,
            api_key=self.token,
            timeout=self.timeout,
        )

    def generate(
        self,
        prompt: str,
        output_path: Optional[Path] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Implementation of CloudVideoProvider interface.
        Delegates to generate_video.
        """
        return self.generate_video(prompt=prompt, output_path=output_path, **kwargs)

    def generate_video(
        self,
        prompt: str,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        num_frames: Optional[int] = None,
        num_inference_steps: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        negative_prompt: Optional[str] = None,
        seed: Optional[int] = None,
        output_path: Optional[Path] = None,
        check_enabled: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate text-to-video using Hugging Face Inference Providers.
        Saves resulting MP4 to output_path (or auto-generates unique path) and returns metadata.
        """
        if check_enabled and not self.is_enabled():
            raise HuggingFaceVideoDisabledError(
                "Hugging Face Cloud Video generation is currently disabled (HF_VIDEO_ENABLED=false). "
                "Set HF_VIDEO_ENABLED=true in backend/.env to enable."
            )

        if not self.is_configured():
            raise HuggingFaceVideoConfigError(
                "HF_TOKEN is not configured. Provide a valid Hugging Face token in backend/.env."
            )

        effective_model = (model or self.default_model).strip()
        effective_provider = (provider or self.default_provider).strip()

        target_path = output_path or self._get_unique_output_path(prompt)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Initiating Hugging Face video generation with model '%s' via provider '%s' (prompt: %.60s...)",
            effective_model, effective_provider, prompt
        )

        # Prepare parameters for InferenceClient.text_to_video
        client = self._get_client(effective_provider)
        client_kwargs: Dict[str, Any] = {}
        if guidance_scale is not None:
            client_kwargs["guidance_scale"] = float(guidance_scale)
        if num_frames is not None:
            client_kwargs["num_frames"] = int(num_frames)
        if num_inference_steps is not None:
            client_kwargs["num_inference_steps"] = int(num_inference_steps)
        if seed is not None:
            client_kwargs["seed"] = int(seed)
        if negative_prompt:
            if isinstance(negative_prompt, str):
                client_kwargs["negative_prompt"] = [negative_prompt]
            else:
                client_kwargs["negative_prompt"] = list(negative_prompt)

        start_time = time.time()
        try:
            video_bytes = client.text_to_video(
                prompt=prompt,
                model=effective_model,
                **client_kwargs,
            )
        except HfHubHTTPError as e:
            status_code = getattr(getattr(e, "response", None), "status_code", "HTTP_ERROR")
            err_msg = str(e)
            logger.error("Hugging Face API returned error [%s]: %s", status_code, err_msg)
            raise HuggingFaceAPIError(
                f"Hugging Face Inference API error ({status_code}): {err_msg}"
            ) from e
        except TimeoutError as e:
            logger.error("Hugging Face generation timed out after %.1f seconds", self.timeout)
            raise HuggingFaceTimeoutError(
                f"Hugging Face generation timed out after {self.timeout}s"
            ) from e
        except Exception as e:
            err_type = type(e).__name__
            logger.error("Unexpected error during Hugging Face video generation: %s (%s)", err_type, e)
            raise HuggingFaceAPIError(
                f"Failed to generate video with Hugging Face ({err_type}): {e}"
            ) from e

        generation_time = round(time.time() - start_time, 2)

        if not video_bytes or len(video_bytes) == 0:
            raise HuggingFaceAPIError("Hugging Face API returned empty (0 bytes) payload.")

        # Save to disk
        try:
            with open(target_path, "wb") as f:
                f.write(video_bytes)
        except Exception as e:
            raise HuggingFaceVideoError(f"Failed to write generated video to {target_path}: {e}") from e

        # Validate saved file
        if not target_path.exists() or target_path.stat().st_size == 0:
            raise HuggingFaceVideoError(f"Saved video file is empty or missing: {target_path}")

        file_size_bytes = target_path.stat().st_size
        output_size_mb = max(round(file_size_bytes / (1024 * 1024), 2), 0.01) if file_size_bytes > 0 else 0.0

        # Probe video properties if ffprobe is available
        duration_seconds: Optional[float] = None
        resolution: Optional[str] = None
        codec: Optional[str] = None
        try:
            from app.services.ffmpeg_service import ffmpeg_service
            if ffmpeg_service.is_available():
                probe = ffmpeg_service.probe_media(target_path)
                duration_seconds = probe.get("duration")
                resolution = probe.get("resolution")
                codec = probe.get("video_codec")
        except Exception as e:
            logger.warning("Optional ffprobe inspection skipped: %s", e)

        # Compute web-friendly relative path
        try:
            rel_path = str(target_path.relative_to(settings.BASE_DIR)).replace("\\", "/")
        except ValueError:
            rel_path = f"generated/cloud_video/{target_path.name}"

        logger.info(
            "Hugging Face video generated successfully: %s (%.2f MB, %.2fs)",
            target_path.name, output_size_mb, generation_time
        )

        return {
            "success": True,
            "provider": effective_provider,
            "model": effective_model,
            "prompt": prompt,
            "video_path": rel_path,
            "absolute_path": str(target_path.resolve()),
            "generation_time_seconds": generation_time,
            "output_size_mb": output_size_mb,
            "duration_seconds": duration_seconds,
            "resolution": resolution,
            "codec": codec,
        }


# Singleton service instance
hf_video_service = HuggingFaceVideoService()
