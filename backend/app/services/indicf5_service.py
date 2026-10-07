"""
IndicF5 Text-to-Speech Service for SmartCampus AI Video.
Provides local speech synthesis powered by F5-TTS / IndicF5 models
with CUDA acceleration, automatic CPU fallback, and audio metadata.
"""

import os
import re
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import soundfile as sf
import torch

from app.config import settings
from app.schemas.scene import EducationalVideoPlan
from app.services.narration_service import NarrationService

logger = logging.getLogger("smartcampus.tts")
logging.basicConfig(level=logging.INFO)


def _patch_torchaudio():
    """
    Patches torchaudio.load with a lightweight soundfile loader.
    This bypasses torchaudio 2.9+'s dependency on torchcodec (which lacks
    Windows shared libraries and crashes with ImportError).
    """
    try:
        import torchaudio

        def _soundfile_load(uri, **kwargs):
            data, sr = sf.read(uri, dtype="float32")
            tensor = torch.from_numpy(data)
            if tensor.ndim == 1:
                tensor = tensor.unsqueeze(0)
            elif tensor.ndim == 2:
                tensor = tensor.t()
            return tensor, sr

        torchaudio.load = _soundfile_load
    except Exception as e:
        logger.warning(f"[TTS] Warning patching torchaudio: {e}")


# Apply the safe loader patch at module import
_patch_torchaudio()


def slugify_topic(topic: str) -> str:
    """Creates a filesystem-safe directory slug from topic name."""
    s = topic.strip().lower()
    s = re.sub(r"['\"]", "", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s or "educational_topic"


class IndicF5Service:
    """
    Local speech synthesis service using F5-TTS / IndicF5.
    Implements singleton/lazy initialization and resilient hardware fallback.
    """

    _instance: Optional["IndicF5Service"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(IndicF5Service, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self.audio_base_dir: Path = settings.AUDIO_DIR
        self.audio_base_dir.mkdir(parents=True, exist_ok=True)

        self.device = self._resolve_target_device(settings.TTS_DEVICE)
        self.model_type: str = settings.TTS_MODEL_TYPE
        self.ref_text: str = settings.TTS_REF_TEXT
        self.speed: float = settings.TTS_SPEED

        # Model instance (loaded lazily on first generation)
        self._f5_model = None
        self._current_model_device: Optional[str] = None
        self._ref_wav_path: Optional[str] = None

        self._initialized = True

    @staticmethod
    def _resolve_target_device(configured_device: str) -> str:
        """Determines initial target device (CUDA vs CPU)."""
        dev = (configured_device or "auto").lower()
        if dev == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        elif dev == "cuda" and not torch.cuda.is_available():
            logger.warning("[TTS] CUDA requested but unavailable. Falling back to CPU.")
            return "cpu"
        return dev

    def _locate_default_reference_audio(self) -> str:
        """Finds or extracts a packaged reference speech sample for F5-TTS."""
        # 1. Check custom path in models directory
        custom_ref = settings.MODELS_DIR / "indicf5" / "reference.wav"
        if custom_ref.exists():
            return str(custom_ref)

        # 2. Check f5_tts package basic reference sample
        try:
            import f5_tts
            pkg_dir = Path(f5_tts.__file__).parent
            builtin_ref = pkg_dir / "infer" / "examples" / "basic" / "basic_ref_en.wav"
            if builtin_ref.exists():
                return str(builtin_ref)
        except Exception:
            pass

        # 3. Fallback: create a tiny reference WAV if none exists
        fallback_ref = settings.AUDIO_DIR / "_default_ref.wav"
        if not fallback_ref.exists():
            import numpy as np
            sr = 24000
            # 1 second of silent/gentle sine tone placeholder
            tone = (np.sin(2 * np.pi * 440 * np.linspace(0, 1, sr)) * 0.1).astype(np.float32)
            sf.write(str(fallback_ref), tone, sr)
        return str(fallback_ref)

    def _load_model(self, target_device: str):
        """Loads or reloads the F5-TTS model on specified device."""
        from f5_tts.api import F5TTS

        logger.info(f"[TTS] Initializing IndicF5")
        logger.info(f"[TTS] Device: {target_device}")

        self._f5_model = F5TTS(
            model=self.model_type,
            device=target_device,
        )
        self._current_model_device = target_device
        self._ref_wav_path = self._locate_default_reference_audio()

    def get_model(self, target_device: Optional[str] = None):
        """Ensures the TTS model is initialized lazily and cached."""
        device = target_device or self.device
        if self._f5_model is None or self._current_model_device != device:
            self._load_model(device)
        return self._f5_model

    def generate_speech(
        self,
        text: str,
        output_dir: Optional[Path] = None,
        filename: str = "narration.wav",
        topic: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Synthesizes spoken narration from text, saves WAV and text transcripts,
        and returns measured duration and metadata.
        """
        cleaned_text = text.strip() if text else ""
        if not cleaned_text:
            raise ValueError("Narration text cannot be empty.")

        # Determine output directory
        if output_dir is None:
            slug = slugify_topic(topic or f"tts_{int(time.time())}")
            dest_dir = self.audio_base_dir / slug
        else:
            dest_dir = output_dir

        dest_dir.mkdir(parents=True, exist_ok=True)
        wav_path = dest_dir / filename
        txt_path = dest_dir / f"{wav_path.stem}.txt"

        # Save narration text transcript
        txt_path.write_text(cleaned_text, encoding="utf-8")

        logger.info(f"[TTS] Generating narration")
        start_time = time.perf_counter()

        # Attempt generation on preferred device with automatic CPU fallback on OOM
        try:
            model = self.get_model(self.device)
            model.infer(
                ref_file=self._ref_wav_path,
                ref_text=self.ref_text,
                gen_text=cleaned_text,
                file_wave=str(wav_path),
                speed=self.speed,
            )
        except (torch.cuda.OutOfMemoryError, RuntimeError) as e:
            err_msg = str(e).lower()
            if "out of memory" in err_msg or "cuda" in err_msg:
                logger.warning(f"[TTS] CUDA unavailable/OOM: {e}")
                logger.warning("[TTS] Falling back to CPU")
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

                # Force reload on CPU
                self.device = "cpu"
                model = self.get_model("cpu")
                model.infer(
                    ref_file=self._ref_wav_path,
                    ref_text=self.ref_text,
                    gen_text=cleaned_text,
                    file_wave=str(wav_path),
                    speed=self.speed,
                )
            else:
                raise

        generation_time = round(time.perf_counter() - start_time, 2)

        if not wav_path.exists() or wav_path.stat().st_size == 0:
            raise RuntimeError(f"TTS generation failed to write output file: {wav_path}")

        # Measure real duration and sample rate
        audio_info = sf.info(str(wav_path))
        duration = round(audio_info.duration, 2)
        sample_rate = audio_info.samplerate

        logger.info(f"[TTS] Audio generated")
        logger.info(f"[TTS] Duration: {duration} seconds")
        logger.info(f"[TTS] Saved: {wav_path}")

        # Compute relative URL path from GENERATED_DIR for client consumption
        try:
            rel_audio_path = str(wav_path.relative_to(settings.BASE_DIR)).replace("\\", "/")
        except ValueError:
            rel_audio_path = str(wav_path).replace("\\", "/")

        return {
            "success": True,
            "audio_path": rel_audio_path,
            "absolute_audio_path": str(wav_path),
            "transcript_path": str(txt_path),
            "duration_seconds": duration,
            "sample_rate": sample_rate,
            "text_length": len(cleaned_text),
            "generation_time_seconds": generation_time,
            "narration_text": cleaned_text,
            "device": self._current_model_device,
        }

    def generate_plan_narration(
        self,
        plan: EducationalVideoPlan,
    ) -> Dict[str, Any]:
        """
        Builds a comprehensive educational narration from an EducationalVideoPlan,
        synthesizes full audio narration, and returns detailed metadata.
        """
        # Step 1: Build natural narration using NarrationService
        narration_result = NarrationService.build_plan_narration(plan)
        full_script = narration_result["full_script"]

        if not full_script:
            raise ValueError(f"Could not generate narration script from plan for topic: {plan.topic}")

        # Step 2: Establish topic directory
        topic_slug = slugify_topic(plan.topic)
        topic_audio_dir = self.audio_base_dir / topic_slug
        topic_audio_dir.mkdir(parents=True, exist_ok=True)

        # Step 3: Synthesize audio
        speech_result = self.generate_speech(
            text=full_script,
            output_dir=topic_audio_dir,
            filename="narration.wav",
            topic=plan.topic,
        )

        # Step 4: Combine and return enriched metadata
        speech_result.update({
            "topic": plan.topic,
            "title": plan.title,
            "scene_scripts": narration_result["scene_scripts"],
            "word_count": narration_result["word_count"],
        })
        return speech_result


# Singleton access helper
indicf5_service = IndicF5Service()
