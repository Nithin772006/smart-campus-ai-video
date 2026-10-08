"""
ElevenLabs Multilingual Text-to-Speech Service for SmartCampus AI Video (Task 9G-A).
Provides cloud-based, high-fidelity multilingual speech synthesis with character-level
timestamp extraction for synchronized educational subtitle and video generation.
"""

import os
import re
import time
import json
import base64
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
import httpx
import soundfile as sf

from app.config import settings

logger = logging.getLogger("smartcampus.elevenlabs")

ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1"
DEFAULT_ELEVENLABS_MODEL = "eleven_multilingual_v2"
# Canonical premade default voice (Rachel) if no voice is configured
CANONICAL_DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"


# Custom Exceptions
class ElevenLabsError(Exception):
    """Base exception for ElevenLabs TTS operations."""
    pass


class ElevenLabsConfigError(ElevenLabsError):
    """Raised when configuration or API key is missing or invalid."""
    pass


class ElevenLabsAuthError(ElevenLabsError):
    """Raised on 401/403 authentication or permission failures."""
    pass


class ElevenLabsRateLimitError(ElevenLabsError):
    """Raised on 429 rate limit errors."""
    pass


class ElevenLabsTimeoutError(ElevenLabsError):
    """Raised on request timeout."""
    pass


class ElevenLabsServerError(ElevenLabsError):
    """Raised on ElevenLabs 5xx server errors."""
    pass


class ElevenLabsAudioError(ElevenLabsError):
    """Raised when audio response is empty, corrupted, or unparsable."""
    pass


class ElevenLabsVoiceError(ElevenLabsError):
    """Raised when voice is invalid or unavailable."""
    pass


PREMADE_VOICES = [
    {
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "name": "Rachel (Calm American)",
        "category": "premade",
        "labels": {"accent": "american", "gender": "female", "description": "calm"},
        "description": "Calm, clear American female educator (Default)",
    },
    {
        "voice_id": "AZnzlk1XvdvUeBnXmlld",
        "name": "Domi (Clear Confident)",
        "category": "premade",
        "labels": {"accent": "american", "gender": "female", "description": "confident"},
        "description": "Strong, clear, and confident narration",
    },
    {
        "voice_id": "EXAVITQu4vr4xnSDxMaL",
        "name": "Bella (Expressive Academic)",
        "category": "premade",
        "labels": {"accent": "american", "gender": "female", "description": "expressive"},
        "description": "Expressive academic educator style",
    },
    {
        "voice_id": "ErXwobaYiN019PkySvjV",
        "name": "Antoni (Engaging Male)",
        "category": "premade",
        "labels": {"accent": "american", "gender": "male", "description": "engaging"},
        "description": "Engaging, well-paced male narrator",
    },
    {
        "voice_id": "pNInz6obpgDQGcFmaJgB",
        "name": "Adam (Deep Narrator)",
        "category": "premade",
        "labels": {"accent": "american", "gender": "male", "description": "deep"},
        "description": "Deep, authoritative lecturer",
    },
    {
        "voice_id": "TxGEqnHWrfWFTfGW9XjX",
        "name": "Josh (Warm Educator)",
        "category": "premade",
        "labels": {"accent": "american", "gender": "male", "description": "warm"},
        "description": "Warm, accessible educator tone",
    },
]


def slugify_topic(topic: str) -> str:
    """Creates a filesystem-safe directory slug from topic name."""
    s = topic.strip().lower()
    s = re.sub(r"['\"]", "", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s or "educational_topic"


class ElevenLabsService:
    """
    Client service for ElevenLabs multilingual text-to-speech with timestamps.
    Handles secure configuration, voice resolution, timestamp parsing,
    and audio persistence.
    """

    _instance: Optional["ElevenLabsService"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ElevenLabsService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self.audio_base_dir: Path = settings.AUDIO_DIR
        self.audio_base_dir.mkdir(parents=True, exist_ok=True)
        self._cached_voices: Optional[List[Dict[str, Any]]] = None
        self._initialized = True

    @property
    def api_key(self) -> str:
        """Securely reads API key from settings without exposing it."""
        return (settings.ELEVENLABS_API_KEY or "").strip()

    def is_configured(self) -> bool:
        """Returns True if the ElevenLabs API key is non-empty."""
        return bool(self.api_key)

    def is_enabled(self) -> bool:
        """Returns True if ElevenLabs is both enabled and configured."""
        return bool(settings.ELEVENLABS_ENABLED) and self.is_configured()

    def _get_headers(self) -> Dict[str, str]:
        """Constructs secure request headers."""
        if not self.is_configured():
            raise ElevenLabsConfigError("ElevenLabs API key is not configured in environment.")
        return {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    def resolve_voice_id(self, requested_voice_id: Optional[str] = None) -> str:
        """
        Resolves voice ID in priority order:
        1. Explicitly requested voice_id
        2. Configured ELEVENLABS_VOICE_ID in settings
        3. Canonical default voice ID (Rachel)
        """
        if requested_voice_id and requested_voice_id.strip():
            return requested_voice_id.strip()
        if settings.ELEVENLABS_VOICE_ID and settings.ELEVENLABS_VOICE_ID.strip():
            return settings.ELEVENLABS_VOICE_ID.strip()
        return CANONICAL_DEFAULT_VOICE_ID

    def get_voices(self) -> List[Dict[str, Any]]:
        """
        Retrieves list of available voices from ElevenLabs synchronously.
        If the API key lacks voices_read permission scope, gracefully returns
        the catalog of standard premade ElevenLabs voices.
        """
        if not self.is_configured():
            raise ElevenLabsConfigError("ElevenLabs API key is not configured.")

        url = f"{ELEVENLABS_API_BASE}/voices"
        timeout = float(settings.ELEVENLABS_TIMEOUT)

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(url, headers=self._get_headers())
                if response.status_code in (401, 403):
                    # Check for missing permission
                    err_text = response.text.lower()
                    if "missing_permissions" in err_text or "voices_read" in err_text or "permission" in err_text:
                        logger.warning(
                            "[ElevenLabs] API key lacks 'voices_read' scope. "
                            "Returning standard premade ElevenLabs voices catalog."
                        )
                        return PREMADE_VOICES
                    self._handle_response_status(response, operation="fetch voices")
                elif response.status_code != 200:
                    self._handle_response_status(response, operation="fetch voices")
                data = response.json()
        except ElevenLabsAuthError:
            # If auth error on voice list, fall back to premade voices catalog
            logger.warning("[ElevenLabs] Authentication scoped to TTS only. Using premade voice catalog.")
            return PREMADE_VOICES
        except httpx.TimeoutException as te:
            raise ElevenLabsTimeoutError(f"ElevenLabs request timed out while fetching voices: {te}")
        except httpx.RequestError as re:
            raise ElevenLabsServerError(f"ElevenLabs connection failed while fetching voices: {re}")

        raw_voices = data.get("voices", [])
        sanitized_voices = []
        for v in raw_voices:
            sanitized_voices.append({
                "voice_id": v.get("voice_id"),
                "name": v.get("name"),
                "category": v.get("category", "premade"),
                "labels": v.get("labels", {}),
                "preview_url": v.get("preview_url"),
                "description": v.get("description") or (v.get("labels", {}).get("description") if isinstance(v.get("labels"), dict) else ""),
            })

        self._cached_voices = sanitized_voices or PREMADE_VOICES
        logger.info(f"[ElevenLabs] Successfully retrieved {len(self._cached_voices)} voices.")
        return self._cached_voices

    async def get_voices_async(self) -> List[Dict[str, Any]]:
        """Asynchronous variant of get_voices."""
        if not self.is_configured():
            raise ElevenLabsConfigError("ElevenLabs API key is not configured.")

        url = f"{ELEVENLABS_API_BASE}/voices"
        timeout = float(settings.ELEVENLABS_TIMEOUT)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, headers=self._get_headers())
                if response.status_code in (401, 403):
                    err_text = response.text.lower()
                    if "missing_permissions" in err_text or "voices_read" in err_text or "permission" in err_text:
                        logger.warning(
                            "[ElevenLabs] API key lacks 'voices_read' scope. "
                            "Returning standard premade ElevenLabs voices catalog."
                        )
                        return PREMADE_VOICES
                    self._handle_response_status(response, operation="fetch voices")
                elif response.status_code != 200:
                    self._handle_response_status(response, operation="fetch voices")
                data = response.json()
        except ElevenLabsAuthError:
            logger.warning("[ElevenLabs] Authentication scoped to TTS only. Using premade voice catalog.")
            return PREMADE_VOICES
        except httpx.TimeoutException as te:
            raise ElevenLabsTimeoutError(f"ElevenLabs request timed out while fetching voices: {te}")
        except httpx.RequestError as re:
            raise ElevenLabsServerError(f"ElevenLabs connection failed while fetching voices: {re}")

        raw_voices = data.get("voices", [])
        sanitized_voices = []
        for v in raw_voices:
            sanitized_voices.append({
                "voice_id": v.get("voice_id"),
                "name": v.get("name"),
                "category": v.get("category", "premade"),
                "labels": v.get("labels", {}),
                "preview_url": v.get("preview_url"),
                "description": v.get("description") or (v.get("labels", {}).get("description") if isinstance(v.get("labels"), dict) else ""),
            })

        self._cached_voices = sanitized_voices or PREMADE_VOICES
        return self._cached_voices

    def _handle_response_status(self, response: httpx.Response, operation: str = "request"):
        """Maps HTTP error codes to structured custom exceptions."""
        if response.status_code in (200, 201):
            return

        status = response.status_code
        try:
            error_json = response.json()
            err_detail = error_json.get("detail", error_json.get("message", response.text))
            if isinstance(err_detail, dict):
                err_detail = err_detail.get("message", str(err_detail))
        except Exception:
            err_detail = response.text[:200]

        if status in (401, 403):
            logger.error(f"[ElevenLabs] Authentication failed during {operation} (HTTP {status})")
            raise ElevenLabsAuthError(f"ElevenLabs authentication failed (HTTP {status}): {err_detail}")
        elif status == 429:
            logger.error(f"[ElevenLabs] Rate limit exceeded during {operation} (HTTP 429)")
            raise ElevenLabsRateLimitError(f"ElevenLabs rate limit exceeded: {err_detail}")
        elif 500 <= status <= 599:
            logger.error(f"[ElevenLabs] Server error during {operation} (HTTP {status})")
            raise ElevenLabsServerError(f"ElevenLabs server error (HTTP {status}): {err_detail}")
        else:
            logger.error(f"[ElevenLabs] API call failed during {operation} (HTTP {status})")
            raise ElevenLabsError(f"ElevenLabs API call failed (HTTP {status}): {err_detail}")

    def generate_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        language: str = "en",
        model_id: Optional[str] = None,
        topic: Optional[str] = None,
        output_dir: Optional[Path] = None,
        timestamps: bool = True,
        filename_prefix: str = "narration",
    ) -> Dict[str, Any]:
        """
        Synchronously synthesizes speech with ElevenLabs, optionally extracting character
        timestamps, and saves audio and alignment artifacts to backend/generated/audio/<topic_slug>/elevenlabs/.
        """
        cleaned_text = (text or "").strip()
        if not cleaned_text:
            raise ValueError("Narration text cannot be empty.")

        if not self.is_configured():
            raise ElevenLabsConfigError("ElevenLabs API key is not configured in backend environment.")

        vid = self.resolve_voice_id(voice_id)
        mid = model_id or settings.ELEVENLABS_TTS_MODEL or DEFAULT_ELEVENLABS_MODEL
        timeout = float(settings.ELEVENLABS_TIMEOUT)

        # Target directory: backend/generated/audio/<topic_slug>/elevenlabs/
        if output_dir:
            dest_dir = Path(output_dir)
        else:
            slug = slugify_topic(topic or f"tts_{int(time.time())}")
            dest_dir = self.audio_base_dir / slug / "elevenlabs"

        dest_dir.mkdir(parents=True, exist_ok=True)
        mp3_path = dest_dir / f"{filename_prefix}.mp3"
        wav_path = dest_dir / f"{filename_prefix}.wav"
        txt_path = dest_dir / f"{filename_prefix}.txt"
        json_path = dest_dir / f"{filename_prefix}_alignment.json"

        # Save narration text transcript
        txt_path.write_text(cleaned_text, encoding="utf-8")

        start_time = time.perf_counter()

        endpoint_url = (
            f"{ELEVENLABS_API_BASE}/text-to-speech/{vid}/with-timestamps"
            if timestamps
            else f"{ELEVENLABS_API_BASE}/text-to-speech/{vid}"
        )

        norm_lang = (language or "en").strip().lower()
        payload = {
            "text": cleaned_text,
            "model_id": mid,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }
        if norm_lang in ("en", "ta", "hi"):
            payload["language_code"] = norm_lang

        logger.info(
            f"[ElevenLabs] Requesting speech: voice_id={vid}, model={mid}, "
            f"lang={norm_lang}, chars={len(cleaned_text)}, timestamps={timestamps}"
        )

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    endpoint_url,
                    headers=self._get_headers(),
                    json=payload,
                    params={"output_format": "mp3_44100_128"},
                )
                self._handle_response_status(response, operation="speech synthesis")
        except httpx.TimeoutException as te:
            raise ElevenLabsTimeoutError(f"ElevenLabs TTS request timed out after {timeout}s: {te}")
        except httpx.RequestError as re:
            raise ElevenLabsServerError(f"ElevenLabs connection failed during synthesis: {re}")

        generation_time = round(time.perf_counter() - start_time, 2)

        alignment_data: Optional[Dict[str, Any]] = None

        if timestamps:
            try:
                resp_json = response.json()
            except Exception as e:
                raise ElevenLabsAudioError(f"Failed to parse JSON response from timestamped TTS: {e}")

            audio_b64 = resp_json.get("audio_base64")
            if not audio_b64:
                raise ElevenLabsAudioError("ElevenLabs response did not contain audio_base64 data.")

            try:
                audio_bytes = base64.b64decode(audio_b64)
            except Exception as e:
                raise ElevenLabsAudioError(f"Failed to decode base64 audio data: {e}")

            alignment_data = resp_json.get("alignment") or resp_json.get("normalized_alignment")
            if alignment_data:
                json_path.write_text(json.dumps(alignment_data, indent=2, ensure_ascii=False), encoding="utf-8")
        else:
            audio_bytes = response.content

        if not audio_bytes or len(audio_bytes) < 100:
            raise ElevenLabsAudioError(f"Generated audio is too small ({len(audio_bytes)} bytes).")

        # Save MP3 audio
        mp3_path.write_bytes(audio_bytes)

        # Transcode MP3 to WAV for universal audio compatibility (libsndfile / Whisper)
        self._transcode_mp3_to_wav(mp3_path, wav_path)

        # Measure audio duration
        duration, sample_rate = self._probe_audio(wav_path if wav_path.exists() else mp3_path)

        logger.info(
            f"[ElevenLabs] Audio generated successfully: {wav_path.name} "
            f"({duration:.2f}s, {generation_time}s elapsed)"
        )

        # Relative paths for client serving
        try:
            rel_audio_path = str(wav_path.relative_to(settings.BASE_DIR)).replace("\\", "/")
        except ValueError:
            rel_audio_path = str(wav_path).replace("\\", "/")

        try:
            rel_mp3_path = str(mp3_path.relative_to(settings.BASE_DIR)).replace("\\", "/")
        except ValueError:
            rel_mp3_path = str(mp3_path).replace("\\", "/")

        return {
            "success": True,
            "provider": "elevenlabs",
            "audio_path": rel_audio_path,
            "mp3_path": rel_mp3_path,
            "absolute_audio_path": str(wav_path),
            "transcript_path": str(txt_path),
            "duration_seconds": duration,
            "sample_rate": sample_rate,
            "text_length": len(cleaned_text),
            "generation_time_seconds": generation_time,
            "narration_text": cleaned_text,
            "language": language,
            "voice_id": vid,
            "model": mid,
            "timestamp_data_available": alignment_data is not None,
            "alignment": alignment_data,
        }

    async def generate_speech_async(
        self,
        text: str,
        voice_id: Optional[str] = None,
        language: str = "en",
        model_id: Optional[str] = None,
        topic: Optional[str] = None,
        output_dir: Optional[Path] = None,
        timestamps: bool = True,
        filename_prefix: str = "narration",
    ) -> Dict[str, Any]:
        """Asynchronous variant of generate_speech."""
        cleaned_text = (text or "").strip()
        if not cleaned_text:
            raise ValueError("Narration text cannot be empty.")

        if not self.is_configured():
            raise ElevenLabsConfigError("ElevenLabs API key is not configured in backend environment.")

        vid = self.resolve_voice_id(voice_id)
        mid = model_id or settings.ELEVENLABS_TTS_MODEL or DEFAULT_ELEVENLABS_MODEL
        timeout = float(settings.ELEVENLABS_TIMEOUT)

        if output_dir:
            dest_dir = Path(output_dir)
        else:
            slug = slugify_topic(topic or f"tts_{int(time.time())}")
            dest_dir = self.audio_base_dir / slug / "elevenlabs"

        dest_dir.mkdir(parents=True, exist_ok=True)
        mp3_path = dest_dir / f"{filename_prefix}.mp3"
        wav_path = dest_dir / f"{filename_prefix}.wav"
        txt_path = dest_dir / f"{filename_prefix}.txt"
        json_path = dest_dir / f"{filename_prefix}_alignment.json"

        txt_path.write_text(cleaned_text, encoding="utf-8")

        start_time = time.perf_counter()

        endpoint_url = (
            f"{ELEVENLABS_API_BASE}/text-to-speech/{vid}/with-timestamps"
            if timestamps
            else f"{ELEVENLABS_API_BASE}/text-to-speech/{vid}"
        )

        norm_lang = (language or "en").strip().lower()
        payload = {
            "text": cleaned_text,
            "model_id": mid,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }
        if norm_lang in ("en", "ta", "hi"):
            payload["language_code"] = norm_lang

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    endpoint_url,
                    headers=self._get_headers(),
                    json=payload,
                    params={"output_format": "mp3_44100_128"},
                )
                self._handle_response_status(response, operation="speech synthesis")
        except httpx.TimeoutException as te:
            raise ElevenLabsTimeoutError(f"ElevenLabs TTS request timed out after {timeout}s: {te}")
        except httpx.RequestError as re:
            raise ElevenLabsServerError(f"ElevenLabs connection failed during synthesis: {re}")

        generation_time = round(time.perf_counter() - start_time, 2)
        alignment_data: Optional[Dict[str, Any]] = None

        if timestamps:
            try:
                resp_json = response.json()
            except Exception as e:
                raise ElevenLabsAudioError(f"Failed to parse JSON response: {e}")

            audio_b64 = resp_json.get("audio_base64")
            if not audio_b64:
                raise ElevenLabsAudioError("ElevenLabs response did not contain audio_base64 data.")

            audio_bytes = base64.b64decode(audio_b64)
            alignment_data = resp_json.get("alignment") or resp_json.get("normalized_alignment")
            if alignment_data:
                json_path.write_text(json.dumps(alignment_data, indent=2, ensure_ascii=False), encoding="utf-8")
        else:
            audio_bytes = response.content

        if not audio_bytes or len(audio_bytes) < 100:
            raise ElevenLabsAudioError(f"Generated audio is too small ({len(audio_bytes)} bytes).")

        mp3_path.write_bytes(audio_bytes)
        self._transcode_mp3_to_wav(mp3_path, wav_path)
        duration, sample_rate = self._probe_audio(wav_path if wav_path.exists() else mp3_path)

        try:
            rel_audio_path = str(wav_path.relative_to(settings.BASE_DIR)).replace("\\", "/")
        except ValueError:
            rel_audio_path = str(wav_path).replace("\\", "/")

        try:
            rel_mp3_path = str(mp3_path.relative_to(settings.BASE_DIR)).replace("\\", "/")
        except ValueError:
            rel_mp3_path = str(mp3_path).replace("\\", "/")

        return {
            "success": True,
            "provider": "elevenlabs",
            "audio_path": rel_audio_path,
            "mp3_path": rel_mp3_path,
            "absolute_audio_path": str(wav_path),
            "transcript_path": str(txt_path),
            "duration_seconds": duration,
            "sample_rate": sample_rate,
            "text_length": len(cleaned_text),
            "generation_time_seconds": generation_time,
            "narration_text": cleaned_text,
            "language": language,
            "voice_id": vid,
            "model": mid,
            "timestamp_data_available": alignment_data is not None,
            "alignment": alignment_data,
        }

    @staticmethod
    def _transcode_mp3_to_wav(mp3_path: Path, wav_path: Path):
        """Converts MP3 to 24000Hz mono WAV using ffmpeg if available."""
        try:
            cmd = [
                "ffmpeg",
                "-y",
                "-i", str(mp3_path),
                "-ar", "24000",
                "-ac", "1",
                "-c:a", "pcm_s16le",
                str(wav_path),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode != 0:
                logger.warning(f"[ElevenLabs] FFmpeg transcode returned code {res.returncode}: {res.stderr[:200]}")
        except Exception as e:
            logger.warning(f"[ElevenLabs] Transcode error (will use MP3 directly): {e}")

    @staticmethod
    def _probe_audio(audio_path: Path) -> (float, int):
        """Measures duration and sample rate via soundfile or ffprobe."""
        try:
            info = sf.info(str(audio_path))
            return round(info.duration, 2), info.samplerate
        except Exception:
            # Fallback to ffprobe
            try:
                cmd = [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration,sample_rate",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(audio_path),
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, check=True)
                lines = [l.strip() for l in res.stdout.strip().split("\n") if l.strip()]
                dur = float(lines[0]) if len(lines) > 0 else 0.0
                sr = int(lines[1]) if len(lines) > 1 else 24000
                return round(dur, 2), sr
            except Exception as e:
                logger.warning(f"[ElevenLabs] Could not probe audio {audio_path}: {e}")
                return 0.0, 24000


elevenlabs_service = ElevenLabsService()
