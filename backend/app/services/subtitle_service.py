"""
Subtitle Service for SmartCampus AI Video.
Formats Whisper transcription segments into standard SRT and WebVTT subtitle files,
and persists timestamp metadata for video and player synchronization.
"""

import re
import time
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

    @staticmethod
    def convert_alignment_to_segments(
        alignment: Dict[str, Any],
        total_duration: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Converts ElevenLabs character-level timestamp alignment into
        monotonically increasing word-aligned subtitle segments.
        """
        if not alignment or not isinstance(alignment, dict):
            raise ValueError("Alignment data must be a non-empty dictionary.")

        chars = alignment.get("characters") or []
        starts = alignment.get("character_start_times_seconds") or []
        ends = alignment.get("character_end_times_seconds") or []

        if not chars or not starts or not ends:
            raise ValueError("Alignment is missing characters or timing arrays.")

        n = min(len(chars), len(starts), len(ends))
        if n == 0:
            raise ValueError("Alignment contains zero character entries.")

        # Step 1: Reconstruct words with start and end times
        words: List[Dict[str, Any]] = []
        curr_chars: List[str] = []
        word_start: Optional[float] = None
        word_end: Optional[float] = None

        for i in range(n):
            ch = chars[i]
            s = float(starts[i])
            e = float(ends[i])

            if ch.isspace():
                if curr_chars and word_start is not None and word_end is not None:
                    word_text = "".join(curr_chars).strip()
                    if word_text:
                        words.append({
                            "word": word_text,
                            "start": word_start,
                            "end": max(word_end, word_start + 0.05),
                        })
                    curr_chars = []
                    word_start = None
                    word_end = None
            else:
                if word_start is None:
                    word_start = s
                curr_chars.append(ch)
                word_end = e

        # Final word flush
        if curr_chars and word_start is not None and word_end is not None:
            word_text = "".join(curr_chars).strip()
            if word_text:
                words.append({
                    "word": word_text,
                    "start": word_start,
                    "end": max(word_end, word_start + 0.05),
                })

        if not words:
            raise ValueError("Could not extract any words from character alignment.")

        # Step 2: Group words into natural subtitle segments / cues
        segments: List[Dict[str, Any]] = []
        curr_words: List[str] = []
        seg_start: float = words[0]["start"]
        seg_end: float = words[0]["end"]
        prev_end: float = 0.0

        for i, w in enumerate(words):
            curr_words.append(w["word"])
            seg_end = max(seg_end, w["end"])

            # Boundary checks:
            # - Sentence terminator: ends with . ! ? (not abbreviations like Dr. or e.g.)
            # - Length limit: max 8 words or max 45 characters
            # - Pause: next word starts > 0.5s after current word ends
            is_sentence_end = bool(re.search(r"[.!?]$", w["word"]))
            is_max_length = len(curr_words) >= 8 or len(" ".join(curr_words)) >= 45
            is_last_word = (i == len(words) - 1)
            next_has_pause = False
            if not is_last_word:
                next_start = words[i + 1]["start"]
                if (next_start - w["end"]) >= 0.5:
                    next_has_pause = True

            if is_sentence_end or is_max_length or next_has_pause or is_last_word:
                # Monotonic validation
                clean_start = max(round(seg_start, 3), prev_end)
                clean_end = max(round(seg_end, 3), clean_start + 0.2)

                if total_duration and clean_end > total_duration:
                    clean_end = round(total_duration, 3)

                segments.append({
                    "id": len(segments) + 1,
                    "start": clean_start,
                    "end": clean_end,
                    "text": " ".join(curr_words).strip(),
                })
                prev_end = clean_end

                if not is_last_word:
                    curr_words = []
                    seg_start = words[i + 1]["start"]
                    seg_end = words[i + 1]["end"]

        return segments

    def create_subtitles_from_elevenlabs_alignment(
        self,
        audio_path: Union[str, Path],
        alignment_data: Dict[str, Any],
        language: str = "en",
        topic_slug: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Creates SRT & WebVTT subtitle files directly from ElevenLabs timestamp alignment,
        bypassing Whisper.
        """
        p = Path(audio_path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Audio file not found: {p}")

        resolved_slug = topic_slug or self.resolve_topic_slug_from_audio(p)
        target_dir = output_dir or (self.base_subtitles_dir / resolved_slug)
        target_dir.mkdir(parents=True, exist_ok=True)

        start_time = time.perf_counter()

        # Probe duration if possible
        duration = 0.0
        try:
            import soundfile as sf
            info = sf.info(str(p))
            duration = round(info.duration, 2)
        except Exception:
            pass

        segments = self.convert_alignment_to_segments(alignment_data, total_duration=duration)
        if not segments:
            raise ValueError("No subtitle segments could be constructed from alignment.")

        if duration <= 0.0 and segments:
            duration = segments[-1]["end"]

        full_text = " ".join(s["text"] for s in segments)

        # Generate SRT & VTT
        srt_content = self.generate_srt(segments)
        vtt_content = self.generate_vtt(segments)

        srt_file = target_dir / "subtitles.srt"
        vtt_file = target_dir / "subtitles.vtt"
        json_file = target_dir / "transcription.json"

        srt_file.write_text(srt_content, encoding="utf-8")
        vtt_file.write_text(vtt_content, encoding="utf-8")

        transcription_dict = {
            "text": full_text,
            "duration_seconds": duration,
            "language": language,
            "source": "elevenlabs_timestamps",
            "segments": segments,
        }
        json_file.write_text(
            json.dumps(transcription_dict, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        gen_time = round(time.perf_counter() - start_time, 3)
        logger.info(
            f"[Subtitle] Generated {len(segments)} subtitle segments directly from ElevenLabs timestamps."
        )

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
            "duration_seconds": duration,
            "segment_count": len(segments),
            "language": language,
            "generation_time_seconds": gen_time,
            "device": "elevenlabs_timestamps",
            "segments": segments,
            "source": "elevenlabs_timestamps",
        }

    def process_audio(
        self,
        audio_path: Union[str, Path],
        language: Optional[str] = "auto",
        topic_slug: Optional[str] = None,
        output_dir: Optional[Path] = None,
        alignment_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generates subtitles for audio.
        If ElevenLabs alignment data is provided, converts directly to subtitles.
        Otherwise, falls back to faster-whisper transcription.
        """
        # Step 1: Preferred path - ElevenLabs timestamps
        if alignment_data:
            try:
                logger.info("[Subtitle] Attempting subtitle generation via ElevenLabs timestamps...")
                return self.create_subtitles_from_elevenlabs_alignment(
                    audio_path=audio_path,
                    alignment_data=alignment_data,
                    language=language if language and language != "auto" else "en",
                    topic_slug=topic_slug,
                    output_dir=output_dir,
                )
            except Exception as e:
                logger.warning(
                    f"[Subtitle] ElevenLabs timestamp conversion failed: {e}. Falling back to faster-whisper."
                )

        # Step 2: Fallback path - faster-whisper
        logger.info("[Subtitle] Transcribing audio with faster-whisper...")
        p = Path(audio_path)
        if not p.is_absolute():
            candidate = settings.BASE_DIR / p
            if candidate.exists():
                p = candidate.resolve()
            else:
                p = p.resolve()

        if not p.exists():
            raise FileNotFoundError(f"Audio file not found: {p}")

        resolved_slug = topic_slug or self.resolve_topic_slug_from_audio(p)
        target_dir = output_dir or (self.base_subtitles_dir / resolved_slug)
        target_dir.mkdir(parents=True, exist_ok=True)

        transcription_result = self.whisper.transcribe(
            audio_path=p,
            language=language,
        )

        segments = transcription_result["segments"]
        full_text = transcription_result["text"]

        srt_content = self.generate_srt(segments)
        vtt_content = self.generate_vtt(segments)

        srt_file = target_dir / "subtitles.srt"
        vtt_file = target_dir / "subtitles.vtt"
        json_file = target_dir / "transcription.json"

        srt_file.write_text(srt_content, encoding="utf-8")
        vtt_file.write_text(vtt_content, encoding="utf-8")
        json_file.write_text(
            json.dumps(transcription_result, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        logger.info(f"[Subtitle] Saved faster-whisper subtitles to {target_dir}")

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
            "source": "faster_whisper",
        }


# Singleton service instance
subtitle_service = SubtitleService()
