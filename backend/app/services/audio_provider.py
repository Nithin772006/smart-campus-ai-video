"""
Audio Provider Abstraction for SmartCampus AI Video (Task 9G-A).
Defines a unified audio synthesis interface with concrete implementations:
- IndicF5AudioProvider: Local neural TTS using F5-TTS / IndicF5
- ElevenLabsAudioProvider: Cloud multilingual TTS with timestamps & resilient IndicF5 fallback
"""

import time
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, Union

from app.config import settings
from app.schemas.scene import EducationalVideoPlan
from app.services.narration_service import NarrationService
from app.services.indicf5_service import indicf5_service, IndicF5Service
from app.services.elevenlabs_service import (
    elevenlabs_service,
    ElevenLabsService,
    ElevenLabsError,
    ElevenLabsConfigError,
)
from app.services.narration_localizer import narration_localizer

logger = logging.getLogger("smartcampus.audio_provider")


class AudioProvider(ABC):
    """Abstract base class for speech synthesis providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g., 'indicf5', 'elevenlabs')."""
        pass

    @abstractmethod
    def generate_speech(
        self,
        text: str,
        output_dir: Optional[Path] = None,
        filename: str = "narration.wav",
        topic: Optional[str] = None,
        language: str = "en",
        voice_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Synthesizes audio for arbitrary input text."""
        pass

    @abstractmethod
    def generate_plan_narration(
        self,
        plan: EducationalVideoPlan,
        target_duration_seconds: Optional[float] = None,
        language: str = "en",
        voice_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Builds and synthesizes narration voiceover for an EducationalVideoPlan."""
        pass


class IndicF5AudioProvider(AudioProvider):
    """Local speech synthesis provider powered by IndicF5 / F5-TTS."""

    def __init__(self, service: Optional[IndicF5Service] = None):
        self.service = service or indicf5_service

    @property
    def name(self) -> str:
        return "indicf5"

    def generate_speech(
        self,
        text: str,
        output_dir: Optional[Path] = None,
        filename: str = "narration.wav",
        topic: Optional[str] = None,
        language: str = "en",
        voice_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        result = self.service.generate_speech(
            text=text,
            output_dir=output_dir,
            filename=filename,
            topic=topic,
        )
        result.update({
            "provider": self.name,
            "provider_requested": kwargs.get("provider_requested", self.name),
            "provider_used": self.name,
            "fallback_used": kwargs.get("fallback_used", False),
            "fallback_reason": kwargs.get("fallback_reason", None),
            "language": language,
            "timestamp_data_available": False,
        })
        return result

    def generate_plan_narration(
        self,
        plan: EducationalVideoPlan,
        target_duration_seconds: Optional[float] = None,
        language: str = "en",
        voice_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        result = self.service.generate_plan_narration(
            plan=plan,
            target_duration_seconds=target_duration_seconds,
        )
        result.update({
            "provider": self.name,
            "provider_requested": kwargs.get("provider_requested", self.name),
            "provider_used": self.name,
            "fallback_used": kwargs.get("fallback_used", False),
            "fallback_reason": kwargs.get("fallback_reason", None),
            "language": language,
            "timestamp_data_available": False,
        })
        return result


class ElevenLabsAudioProvider(AudioProvider):
    """
    Cloud multilingual speech synthesis provider powered by ElevenLabs.
    Automatically extracts character-level timestamps and falls back
    to IndicF5 if ElevenLabs is disabled or encounters an API failure.
    """

    def __init__(
        self,
        service: Optional[ElevenLabsService] = None,
        fallback_service: Optional[IndicF5AudioProvider] = None,
    ):
        self.service = service or elevenlabs_service
        self.fallback_provider = fallback_service or IndicF5AudioProvider()

    @property
    def name(self) -> str:
        return "elevenlabs"

    def _should_fallback(self) -> (bool, Optional[str]):
        """Evaluates whether to immediately fall back to IndicF5."""
        if not self.service.is_configured():
            return True, "ElevenLabs API key is missing from environment."
        if not settings.ELEVENLABS_ENABLED:
            return True, "ElevenLabs is disabled in configuration (ELEVENLABS_ENABLED=false)."
        return False, None

    def generate_speech(
        self,
        text: str,
        output_dir: Optional[Path] = None,
        filename: str = "narration.wav",
        topic: Optional[str] = None,
        language: str = "en",
        voice_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        should_fallback, fallback_reason = self._should_fallback()
        if should_fallback:
            logger.warning(
                f"[AudioProvider] ElevenLabs unavailable: {fallback_reason}. "
                "Gracefully falling back to IndicF5."
            )
            return self.fallback_provider.generate_speech(
                text=text,
                output_dir=output_dir,
                filename=filename,
                topic=topic,
                language=language,
                provider_requested="elevenlabs",
                fallback_used=True,
                fallback_reason=fallback_reason,
            )

        try:
            # Check if text is already localized to target script to prevent double-localization
            script_ratio = narration_localizer.calculate_script_ratio(text, target_language=language)
            if script_ratio >= 0.35 or narration_localizer.is_english(language):
                spoken_text = text
                actual_lang = language
                fallback_used = False
                fallback_reason = None
            else:
                loc_res = narration_localizer.localize_with_status(text, target_language=language)
                spoken_text = loc_res.text
                actual_lang = loc_res.actual_language
                fallback_used = loc_res.fallback_used
                fallback_reason = loc_res.fallback_reason
                script_ratio = loc_res.script_ratio

            result = self.service.generate_speech(
                text=spoken_text,
                voice_id=voice_id,
                language=actual_lang,
                topic=topic,
                output_dir=output_dir,
                timestamps=kwargs.get("timestamps", True),
                filename_prefix=Path(filename).stem,
            )
            result.update({
                "provider_requested": "elevenlabs",
                "provider_used": "elevenlabs",
                "language": language,
                "actual_language": actual_lang,
                "script_ratio": script_ratio,
                "fallback_used": fallback_used,
                "fallback_reason": fallback_reason,
                "localization_fallback": fallback_used,
            })
            return result

        except Exception as e:
            err_msg = f"ElevenLabs synthesis failed: {str(e)}"
            logger.error(f"[AudioProvider] {err_msg}. Gracefully falling back to IndicF5.")
            return self.fallback_provider.generate_speech(
                text=text,
                output_dir=output_dir,
                filename=filename,
                topic=topic,
                language=language,
                provider_requested="elevenlabs",
                fallback_used=True,
                fallback_reason=err_msg,
            )

    def generate_plan_narration(
        self,
        plan: EducationalVideoPlan,
        target_duration_seconds: Optional[float] = None,
        language: str = "en",
        voice_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        should_fallback, fallback_reason = self._should_fallback()
        if should_fallback:
            logger.warning(
                f"[AudioProvider] ElevenLabs unavailable: {fallback_reason}. "
                "Gracefully falling back to IndicF5."
            )
            return self.fallback_provider.generate_plan_narration(
                plan=plan,
                target_duration_seconds=target_duration_seconds,
                language=language,
                provider_requested="elevenlabs",
                fallback_used=True,
                fallback_reason=fallback_reason,
            )

        eff_duration = (
            target_duration_seconds
            or getattr(plan, "target_duration", None)
            or settings.DEFAULT_TARGET_DURATION_SECONDS
        )

        try:
            # Step 1: Build educational narration script with word budgeting
            narration_result = NarrationService.build_plan_narration(
                plan=plan,
                target_duration_seconds=eff_duration,
            )
            base_script = narration_result["full_script"]

            # Step 2: Multilingual localization with script validation & retry
            loc_res = narration_localizer.localize_with_status(base_script, target_language=language)
            spoken_script = loc_res.text
            actual_lang = loc_res.actual_language
            loc_fallback_used = loc_res.fallback_used
            loc_fallback_reason = loc_res.fallback_reason

            # Step 3: ElevenLabs timestamped speech synthesis
            speech_result = self.service.generate_speech(
                text=spoken_script,
                voice_id=voice_id,
                language=actual_lang,
                topic=plan.topic,
                timestamps=True,
                filename_prefix="narration",
            )

            actual_dur = speech_result["duration_seconds"]
            words_count = len(spoken_script.split())
            actual_wpm = round((words_count / actual_dur) * 60.0, 1) if actual_dur > 0 else 0.0

            logger.info(
                f"\n[NARRATION (ELEVENLABS)]\n"
                f"Words: {words_count}\n"
                f"Duration: {actual_dur:.2f}s\n"
                f"Actual WPM: {actual_wpm}\n"
                f"Requested Language: {language}\n"
                f"Actual Language: {actual_lang}\n"
                f"Localization Fallback: {loc_fallback_used}\n"
                f"Voice: {speech_result.get('voice_id')}"
            )

            speech_result.update({
                "topic": plan.topic,
                "title": plan.title,
                "scene_scripts": narration_result["scene_scripts"],
                "word_count": words_count,
                "target_duration_seconds": eff_duration,
                "target_wpm": narration_result["target_wpm"],
                "estimated_duration_seconds": narration_result["estimated_duration_seconds"],
                "estimated_wpm": narration_result["estimated_wpm"],
                "actual_wpm": actual_wpm,
                "speech_rate_wpm": actual_wpm,
                "provider_requested": "elevenlabs",
                "provider_used": "elevenlabs",
                "language": language,
                "actual_language": actual_lang,
                "script_ratio": loc_res.script_ratio,
                "fallback_used": loc_fallback_used,
                "fallback_reason": loc_fallback_reason,
                "localization_fallback": loc_fallback_used,
            })
            return speech_result

        except Exception as e:
            err_msg = f"ElevenLabs plan narration failed: {str(e)}"
            logger.error(f"[AudioProvider] {err_msg}. Gracefully falling back to IndicF5.")
            return self.fallback_provider.generate_plan_narration(
                plan=plan,
                target_duration_seconds=eff_duration,
                language=language,
                provider_requested="elevenlabs",
                fallback_used=True,
                fallback_reason=err_msg,
            )


def get_audio_provider(provider_name: Optional[str] = None) -> AudioProvider:
    """
    Factory function returning the configured or requested AudioProvider.
    Defaults to IndicF5AudioProvider.
    """
    name = (provider_name or "indicf5").strip().lower()
    if name == "elevenlabs":
        return ElevenLabsAudioProvider()
    return IndicF5AudioProvider()
