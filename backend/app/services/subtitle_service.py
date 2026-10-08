"""
Subtitle Service for SmartCampus AI Video.
Formats Whisper transcription segments into standard SRT and WebVTT subtitle files,
and persists timestamp metadata for video and player synchronization.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from app.config import settings
from app.services.whisper_service import whisper_service, WhisperService

logger = logging.getLogger("smartcampus.subtitle")
logging.basicConfig(level=logging.INFO)


def format_srt_timestamp(seconds: float) -> str:
    """
    Formats a floating-point seconds value into standard SRT timestamp format:
    HH:MM:SS,mmm
    Example: 3.2 -> "00:00:03,200"
    """
    total_ms = int(round(max(0.0, seconds) * 1000))
    ms = total_ms % 1000
    total_seconds = total_ms // 1000
    s = total_seconds % 60
    total_minutes = total_seconds // 60
    m = total_minutes % 60
    h = total_minutes // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def format_vtt_timestamp(seconds: float) -> str:
    """
    Formats a floating-point seconds value into standard WebVTT timestamp format:
    HH:MM:SS.mmm
    Example: 3.2 -> "00:00:03.200"
    """
    total_ms = int(round(max(0.0, seconds) * 1000))
    ms = total_ms % 1000
    total_seconds = total_ms // 1000
    s = total_seconds % 60
    total_minutes = total_seconds // 60
    m = total_minutes % 60
    h = total_minutes // 60
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


class SubtitleService:
    """
    Generates and saves standard SRT, WebVTT, and JSON transcription files
    from Whisper audio transcription segments.
    """

    def __init__(self, whisper_svc: Optional[WhisperService] = None):
        self.whisper = whisper_svc or whisper_service
        self.base_subtitles_dir: Path = settings.SUBTITLES_DIR
        self.base_subtitles_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def generate_srt(segments: List[Dict[str, Any]]) -> str:
        """
        Converts speech segments into standard SubRip (SRT) format.
        """
        if not segments:
            return ""

        lines = []
        for i, seg in enumerate(segments, start=1):
            start_ts = format_srt_timestamp(seg.get("start", 0.0))
            end_ts = format_srt_timestamp(seg.get("end", 0.0))
            text = (seg.get("text") or "").strip()

            lines.append(f"{i}")
            lines.append(f"{start_ts} --> {end_ts}")
            lines.append(text)
            lines.append("")  # Blank separator

        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def generate_vtt(segments: List[Dict[str, Any]]) -> str:
        """
        Converts speech segments into standard WebVTT format for HTML5 video.
        """
        lines = ["WEBVTT", ""]

        for i, seg in enumerate(segments, start=1):
            start_ts = format_vtt_timestamp(seg.get("start", 0.0))
            end_ts = format_vtt_timestamp(seg.get("end", 0.0))
            text = (seg.get("text") or "").strip()

            lines.append(f"{i}")
            lines.append(f"{start_ts} --> {end_ts}")
            lines.append(text)
            lines.append("")  # Blank separator

        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def resolve_topic_slug_from_audio(audio_path: Union[str, Path], fallback: str = "default_topic") -> str:
        """
        Infers topic directory slug from audio filepath.
        e.g., 'backend/generated/audio/newtons_second_law/narration.wav' -> 'newtons_second_law'
        """
        p = Path(audio_path)
        # Check parent folder name if it is not 'audio' or root
        parent_name = p.parent.name
        if parent_name and parent_name.lower() not in ["audio", "generated", ""]:
            return parent_name
        # Fallback to file stem
        stem = p.stem.replace("narration", "").strip("_")
        return stem or fallback

    def process_audio(
        self,
        audio_path: Union[str, Path],
        language: Optional[str] = "auto",
        topic_slug: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Transcribes audio via faster-whisper, formats SRT & WebVTT subtitles,
        saves all artifacts to disk, and returns detailed synchronization metadata.
        """
        # Resolve filesystem audio path
        p = Path(audio_path)
        if not p.is_absolute():
            # Check relative to BASE_DIR or current working dir
            candidate = settings.BASE_DIR / p
            if candidate.exists():
                p = candidate.resolve()
            else:
                p = p.resolve()

        if not p.exists():
            raise FileNotFoundError(f"Audio file not found: {p}")

        # Resolve topic directory
        resolved_slug = topic_slug or self.resolve_topic_slug_from_audio(p)
        if output_dir:
            target_dir = output_dir
        else:
            target_dir = self.base_subtitles_dir / resolved_slug
        target_dir.mkdir(parents=True, exist_ok=True)

        # Transcribe audio with Whisper
        transcription_result = self.whisper.transcribe(
            audio_path=p,
            language=language,
        )

        segments = transcription_result["segments"]
        full_text = transcription_result["text"]

        # Generate SRT & VTT strings
        srt_content = self.generate_srt(segments)
        vtt_content = self.generate_vtt(segments)

        # File paths
        srt_file = target_dir / "subtitles.srt"
        vtt_file = target_dir / "subtitles.vtt"
        json_file = target_dir / "transcription.json"

        # Save files to disk (UTF-8)
        srt_file.write_text(srt_content, encoding="utf-8")
        vtt_file.write_text(vtt_content, encoding="utf-8")
        json_file.write_text(
            json.dumps(transcription_result, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        logger.info(f"[Subtitle] Saved subtitles to {target_dir}")

        # Construct relative paths for HTTP serving
        try:
            rel_audio = str(p.relative_to(settings.BASE_DIR)).replace("\\", "/")
        except ValueError:
            rel_audio = str(p).replace("\\", "/")

        try:
            rel_srt = str(srt_file.relative_to(settings.BASE_DIR)).replace("\\", "/")
            rel_vtt = str(vtt_file.relative_to(settings.BASE_DIR)).replace("\\", "/")
            rel_json = str(json_file.relative_to(settings.BASE_DIR)).replace("\\", "/")
        except ValueError:
            rel_srt = str(srt_file).replace("\\", "/")
            rel_vtt = str(vtt_file).replace("\\", "/")
            rel_json = str(json_file).replace("\\", "/")

        return {
            "success": True,
            "audio_path": rel_audio,
            "absolute_audio_path": str(p),
            "subtitle_srt_path": rel_srt,
            "subtitle_vtt_path": rel_vtt,
            "transcription_path": rel_json,
            "text": full_text,
            "duration_seconds": transcription_result["duration_seconds"],
            "segment_count": len(segments),
            "language": transcription_result["language"],
            "generation_time_seconds": transcription_result["generation_time_seconds"],
            "device": transcription_result["device"],
            "segments": segments,
        }


# Singleton service instance
subtitle_service = SubtitleService()
