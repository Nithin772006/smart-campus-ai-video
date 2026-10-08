"""
Whisper Transcription Service for SmartCampus AI Video.
Provides local audio transcription and segment timestamping powered by faster-whisper
with CUDA acceleration, automatic CPU fallback, and accurate audio duration.
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

from app.config import settings

logger = logging.getLogger("smartcampus.whisper")
logging.basicConfig(level=logging.INFO)


def _setup_cuda_dlls():
    """
    On Windows, ensure CUDA and cuBLAS DLLs (shipped within PyTorch or CUDA toolkit)
    are discoverable by CTranslate2.
    """
    if sys.platform == "win32":
        try:
            import torch
            torch_lib = Path(torch.__file__).parent / "lib"
            if torch_lib.exists():
                str_path = str(torch_lib.resolve())
                if hasattr(os, "add_dll_directory"):
                    os.add_dll_directory(str_path)
                if str_path not in os.environ.get("PATH", ""):
                    os.environ["PATH"] = str_path + os.pathsep + os.environ.get("PATH", "")
        except Exception as e:
            logger.warning(f"[Whisper] Warning configuring CUDA DLLs: {e}")


# Run DLL setup on import
_setup_cuda_dlls()


class WhisperService:
    """
    Local speech transcription service powered by faster-whisper.
    Implements singleton / lazy initialization, CUDA execution with resilient CPU fallback.
    """

    _instance: Optional["WhisperService"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(WhisperService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self.model_name: str = getattr(settings, "WHISPER_MODEL", "base")
        self.device_config: str = getattr(settings, "WHISPER_DEVICE", "auto")
        self.compute_type_config: str = getattr(settings, "WHISPER_COMPUTE_TYPE", "auto")

        self.device: str = self._resolve_target_device(self.device_config)
        self.compute_type: str = self._resolve_compute_type(self.device, self.compute_type_config)

        self._model = None
        self._current_device: Optional[str] = None
        self._current_compute_type: Optional[str] = None

        self._initialized = True

    @staticmethod
    def _resolve_target_device(configured_device: str) -> str:
        """Determines target device (CUDA vs CPU)."""
        dev = (configured_device or "auto").lower()
        if dev == "auto":
            try:
                import ctranslate2
                if ctranslate2.get_cuda_device_count() > 0:
                    return "cuda"
            except Exception:
                pass
            return "cpu"
        elif dev == "cuda":
            try:
                import ctranslate2
                if ctranslate2.get_cuda_device_count() == 0:
                    logger.warning("[Whisper] CUDA requested but unavailable. Falling back to CPU.")
                    return "cpu"
            except Exception:
                return "cpu"
            return "cuda"
        return "cpu"

    @staticmethod
    def _resolve_compute_type(device: str, configured_compute_type: str) -> str:
        """Resolves memory-safe compute type for RTX 2050 4GB GPU or CPU."""
        cfg = (configured_compute_type or "auto").lower()
        if cfg != "auto":
            return cfg

        if device == "cuda":
            # float16 is optimal for RTX 2050 (Ampere architecture)
            return "float16"
        else:
            # int8 is optimal for CPU inference
            return "int8"

    def _load_model(self, target_device: str, target_compute_type: str):
        """Loads faster-whisper WhisperModel instance."""
        from faster_whisper import WhisperModel

        logger.info(f"[Whisper] Initializing Whisper model ({self.model_name}) on {target_device} ({target_compute_type})")
        self._model = WhisperModel(
            self.model_name,
            device=target_device,
            compute_type=target_compute_type,
        )
        self._current_device = target_device
        self._current_compute_type = target_compute_type

    def get_model(self, target_device: Optional[str] = None, target_compute_type: Optional[str] = None):
        """Ensures the Whisper model is initialized lazily and cached."""
        dev = target_device or self.device
        ctype = target_compute_type or self.compute_type

        if self._model is None or self._current_device != dev or self._current_compute_type != ctype:
            self._load_model(dev, ctype)
        return self._model

    def transcribe(
        self,
        audio_path: Union[str, Path],
        language: Optional[str] = None,
        beam_size: int = 5,
    ) -> Dict[str, Any]:
        """
        Transcribes an audio file into timestamped segments and full text.
        Includes automatic fallback to CPU if CUDA encounters an error or OOM.
        """
        p = Path(audio_path).resolve()
        if not p.exists() or p.stat().st_size == 0:
            raise FileNotFoundError(f"Audio file not found or empty: {audio_path}")

        logger.info(f"[Whisper] Transcribing audio: {p.name}")
        start_time = time.perf_counter()

        lang = None if (not language or language == "auto") else language

        try:
            model = self.get_model(self.device, self.compute_type)
            segments_gen, info = model.transcribe(
                str(p),
                beam_size=beam_size,
                language=lang,
                vad_filter=True,
                condition_on_previous_text=False,
            )
            segments_list = list(segments_gen)
        except Exception as e:
            if self.device == "cuda":
                logger.warning(f"[Whisper] CUDA execution failed: {e}")
                logger.warning("[Whisper] Falling back to CPU")
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except Exception:
                    pass

                self.device = "cpu"
                self.compute_type = "int8"
                model = self.get_model("cpu", "int8")
                segments_gen, info = model.transcribe(
                    str(p),
                    beam_size=beam_size,
                    language=lang,
                    vad_filter=True,
                    condition_on_previous_text=False,
                )
                segments_list = list(segments_gen)
            else:
                raise

        elapsed = round(time.perf_counter() - start_time, 2)
        measured_duration = round(info.duration, 2)

        # Parse segments into serializable structured dicts with safety clamping
        parsed_segments: List[Dict[str, Any]] = []
        full_text_parts: List[str] = []
        prev_text = ""

        for seg in segments_list:
            cleaned_text = seg.text.strip()
            if not cleaned_text:
                continue
            # Filter consecutive duplicate hallucination loops if any
            if cleaned_text == prev_text:
                continue
            prev_text = cleaned_text

            start_t = max(0.0, round(seg.start, 3))
            end_t = min(measured_duration, round(seg.end, 3))
            if start_t > end_t:
                start_t = end_t

            full_text_parts.append(cleaned_text)
            parsed_segments.append({
                "id": len(parsed_segments),
                "start": start_t,
                "end": end_t,
                "text": cleaned_text,
            })

        full_transcription = " ".join(full_text_parts).strip()
        measured_duration = round(info.duration, 2)

        logger.info(
            f"[Whisper] Transcription completed in {elapsed}s ({len(parsed_segments)} segments, {measured_duration}s audio)"
        )

        return {
            "text": full_transcription,
            "duration_seconds": measured_duration,
            "language": info.language,
            "language_probability": round(info.language_probability, 4),
            "segments": parsed_segments,
            "generation_time_seconds": elapsed,
            "device": self._current_device,
            "compute_type": self._current_compute_type,
            "model": self.model_name,
        }


# Singleton instance helper
whisper_service = WhisperService()
