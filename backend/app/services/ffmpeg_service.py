"""
Service for FFmpeg media composition, subtitle burning, audio mixing, and format conversion.
100% local processing with automatic duration synchronization and browser-compatible output.
"""

import os
import sys
import shutil
import subprocess
import logging
import time
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

from app.config import settings

logger = logging.getLogger(__name__)


class FFmpegServiceError(Exception):
    """Base exception for all FFmpeg service operations."""
    pass


class FFmpegBinaryNotFoundError(FFmpegServiceError, RuntimeError):
    """Raised when ffmpeg or ffprobe executable is not found."""
    pass


class MediaNotFoundError(FFmpegServiceError, FileNotFoundError):
    """Raised when input media file does not exist."""
    pass


class MediaProbeError(FFmpegServiceError, RuntimeError):
    """Raised when probing media properties with ffprobe fails."""
    pass


class VideoCompositionError(FFmpegServiceError, RuntimeError):
    """Raised when FFmpeg muxing, encoding, or composition fails."""
    pass


class AudioVideoSyncError(FFmpegServiceError, ValueError):
    """Raised when audio and video durations differ beyond allowable tolerance."""
    pass


def find_ffmpeg_binary(binary_name: str = "ffmpeg") -> Optional[str]:
    """
    Locates FFmpeg or FFprobe executable.
    Checks PATH first, then Windows Registry if needed.
    """
    path = shutil.which(binary_name)
    if path:
        return path

    if sys.platform == "win32":
        try:
            import winreg
            registry_targets = [
                (winreg.HKEY_CURRENT_USER, r"Environment"),
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
            ]
            for hkey, subpath in registry_targets:
                try:
                    with winreg.OpenKey(hkey, subpath) as key:
                        val, _ = winreg.QueryValueEx(key, "Path")
                        for p in val.split(";"):
                            p = p.strip()
                            if not p:
                                continue
                            candidate = Path(p) / f"{binary_name}.exe"
                            if candidate.is_file():
                                if p not in os.environ.get("PATH", ""):
                                    os.environ["PATH"] = f"{p};{os.environ.get('PATH', '')}"
                                return str(candidate)
                except Exception:
                    pass
        except Exception:
            pass

    return None


def is_ffmpeg_available() -> bool:
    """Check if ffmpeg executable is available on the system."""
    return find_ffmpeg_binary("ffmpeg") is not None


def is_ffprobe_available() -> bool:
    """Check if ffprobe executable is available on the system."""
    return find_ffmpeg_binary("ffprobe") is not None


def get_video_duration(video_path: Path | str) -> float:
    """
    Probe the duration of a video or audio file in seconds using ffprobe.
    """
    ffprobe_bin = find_ffmpeg_binary(settings.FFPROBE_PATH) or find_ffmpeg_binary("ffprobe")
    if not ffprobe_bin:
        raise FFmpegBinaryNotFoundError("ffprobe binary is not available. Please ensure FFmpeg is installed.")

    resolved_path = Path(video_path).resolve()
    if not resolved_path.exists():
        raise MediaNotFoundError(f"Media file does not exist: {resolved_path}")

    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(resolved_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return round(float(res.stdout.strip()), 2)


def get_subtitle_final_timestamp(subtitle_path: Path | str) -> Optional[float]:
    """
    Parses an SRT or VTT file and returns the highest end timestamp in seconds.
    """
    p = Path(subtitle_path)
    if not p.exists() or p.stat().st_size == 0:
        return None
    try:
        content = p.read_text(encoding="utf-8")
        matches = re.findall(r"-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})", content)
        if not matches:
            return None
        last = matches[-1]
        h, m, s, ms = int(last[0]), int(last[1]), int(last[2]), int(last[3])
        return round(h * 3600 + m * 60 + s + ms / 1000.0, 3)
    except Exception as e:
        logger.warning("Could not parse subtitle end timestamp from %s: %s", p, e)
        return None


def validate_audio_video_sync(
    composed_video_path: Path | str,
    original_audio_path: Path | str,
    tolerance_seconds: float = 0.15,
) -> Dict[str, Any]:
    """
    Validates audio/video synchronization of a final composed video against the original narration.
    Verifies:
    1. abs(video_duration - audio_duration) <= tolerance_seconds for the final MP4.
    2. abs(final_audio_duration - original_narration_duration) <= tolerance_seconds (ensuring no audio speed modification).

    Raises AudioVideoSyncError if sync difference exceeds tolerance.
    Returns sync metrics dictionary.
    """
    composed_probe = ffmpeg_service.probe_media(composed_video_path)
    orig_audio_probe = ffmpeg_service.probe_media(original_audio_path)

    final_video_dur = composed_probe.get("video_duration") or composed_probe["duration"]
    final_audio_dur = composed_probe.get("audio_duration") or composed_probe["duration"]
    orig_audio_dur = orig_audio_probe.get("audio_duration") or orig_audio_probe["duration"]

    diff_av = round(abs(final_video_dur - final_audio_dur), 3)
    diff_audio_orig = round(abs(final_audio_dur - orig_audio_dur), 3)

    if diff_av > tolerance_seconds:
        raise AudioVideoSyncError(
            f"A/V sync mismatch: final video ({final_video_dur:.2f}s) and audio ({final_audio_dur:.2f}s) "
            f"differ by {diff_av:.3f}s (max tolerance: {tolerance_seconds}s)"
        )

    if diff_audio_orig > tolerance_seconds:
        raise AudioVideoSyncError(
            f"Audio speed/duration altered: final audio ({final_audio_dur:.2f}s) differs from original narration "
            f"({orig_audio_dur:.2f}s) by {diff_audio_orig:.3f}s (max tolerance: {tolerance_seconds}s)"
        )

    return {
        "video_duration": round(final_video_dur, 2),
        "audio_duration": round(final_audio_dur, 2),
        "duration_difference": diff_av,
        "original_audio_duration": round(orig_audio_dur, 2),
        "audio_duration_difference": diff_audio_orig,
        "audio_speed": "1.00x",
        "is_synchronized": True,
        "tolerance_seconds": tolerance_seconds,
    }


def concatenate_scene_clips(clip_paths: List[Path | str], output_path: Path | str) -> Path:
    """
    Concatenate a list of video clips into a single video file using FFmpeg concat demuxer.
    Falls back to re-encoding if stream copy fails.
    """
    ffmpeg_bin = find_ffmpeg_binary(settings.FFMPEG_PATH) or find_ffmpeg_binary("ffmpeg")
    if not ffmpeg_bin:
        raise RuntimeError("ffmpeg binary is not available. Please ensure FFmpeg is installed.")

    resolved_clips = [Path(p).resolve() for p in clip_paths]
    for p in resolved_clips:
        if not p.exists():
            raise FileNotFoundError(f"Clip file does not exist: {p}")

    out_path = Path(output_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if len(resolved_clips) == 1:
        shutil.copy2(resolved_clips[0], out_path)
        return out_path

    concat_file = out_path.parent / f".concat_{out_path.stem}.txt"
    try:
        with open(concat_file, "w", encoding="utf-8") as f:
            for clip in resolved_clips:
                f.write(f"file '{clip.as_posix()}'\n")

        cmd = [
            ffmpeg_bin,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(out_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)

        if res.returncode != 0:
            cmd_reencode = [
                ffmpeg_bin,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c:v", settings.VIDEO_CODEC,
                "-pix_fmt", "yuv420p",
                "-crf", str(settings.VIDEO_CRF),
                "-movflags", "+faststart",
                str(out_path),
            ]
            subprocess.run(cmd_reencode, capture_output=True, text=True, check=True)

        return out_path
    finally:
        if concat_file.exists():
            try:
                concat_file.unlink()
            except Exception:
                pass


class FFmpegService:
    """
    Core video and audio composition service.
    Orchestrates FFmpeg mixing, duration alignment, subtitle burning, and output validation.
    """

    def __init__(self):
        self.output_dir = settings.VIDEOS_DIR
        self.ffmpeg_bin = find_ffmpeg_binary(settings.FFMPEG_PATH) or find_ffmpeg_binary("ffmpeg")
        self.ffprobe_bin = find_ffmpeg_binary(settings.FFPROBE_PATH) or find_ffmpeg_binary("ffprobe")

    def is_available(self) -> bool:
        """Check if both ffmpeg and ffprobe are ready."""
        return bool(self.ffmpeg_bin and self.ffprobe_bin)

    def probe_media(self, file_path: Path | str) -> Dict[str, Any]:
        """
        Deep inspection of media container and stream properties using ffprobe.
        Returns duration, resolution, codecs, bitrates, and stream details.
        """
        if not self.ffprobe_bin:
            self.ffprobe_bin = find_ffmpeg_binary("ffprobe")
            if not self.ffprobe_bin:
                raise FFmpegBinaryNotFoundError("ffprobe binary is not available. Please ensure FFmpeg is installed.")

        resolved = Path(file_path).resolve()
        if not resolved.exists():
            raise MediaNotFoundError(f"Media file does not exist: {resolved}")

        cmd = [
            self.ffprobe_bin,
            "-v", "error",
            "-show_entries", "format=duration,size,bit_rate:stream=index,codec_type,codec_name,pix_fmt,width,height,r_frame_rate,sample_rate,channels,duration",
            "-of", "json",
            str(resolved),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise MediaProbeError(f"ffprobe failed for {resolved.name}: {res.stderr}")

        try:
            data = json.loads(res.stdout)
        except json.JSONDecodeError as err:
            raise MediaProbeError(f"Failed to parse ffprobe JSON output: {err}")

        streams = data.get("streams", [])
        fmt = data.get("format", {})

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        duration = float(fmt.get("duration", 0.0))
        size_bytes = int(fmt.get("size", 0))

        fps = None
        if video_stream and "r_frame_rate" in video_stream:
            try:
                num, den = video_stream["r_frame_rate"].split("/")
                fps = round(float(num) / float(den), 2)
            except Exception:
                pass

        stream_video_dur = None
        if video_stream and "duration" in video_stream:
            try:
                stream_video_dur = round(float(video_stream["duration"]), 2)
            except Exception:
                pass

        stream_audio_dur = None
        if audio_stream and "duration" in audio_stream:
            try:
                stream_audio_dur = round(float(audio_stream["duration"]), 2)
            except Exception:
                pass

        return {
            "path": str(resolved),
            "duration": round(duration, 2),
            "video_duration": stream_video_dur if stream_video_dur is not None else round(duration, 2),
            "audio_duration": stream_audio_dur if stream_audio_dur is not None else round(duration, 2),
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / (1024 * 1024), 2),
            "has_video": video_stream is not None,
            "has_audio": audio_stream is not None,
            "width": video_stream.get("width") if video_stream else None,
            "height": video_stream.get("height") if video_stream else None,
            "fps": fps,
            "video_codec": video_stream.get("codec_name") if video_stream else None,
            "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
            "pixel_format": video_stream.get("pix_fmt") if video_stream else None,
            "audio_sample_rate": int(audio_stream.get("sample_rate")) if audio_stream and audio_stream.get("sample_rate") else None,
            "audio_channels": int(audio_stream.get("channels")) if audio_stream and audio_stream.get("channels") else None,
            "streams": streams,
        }

    def validate_sync(
        self,
        composed_video_path: Path | str,
        original_audio_path: Path | str,
        tolerance_seconds: float = 0.15,
    ) -> Dict[str, Any]:
        """Convenience method calling validate_audio_video_sync."""
        return validate_audio_video_sync(
            composed_video_path=composed_video_path,
            original_audio_path=original_audio_path,
            tolerance_seconds=tolerance_seconds,
        )

    def compose(
        self,
        video_path: Path | str,
        audio_path: Path | str,
        subtitle_path: Optional[Path | str] = None,
        output_path: Optional[Path | str] = None,
        output_name: Optional[str] = None,
        burn_subtitles: Optional[bool] = None,
        character_enabled: bool = False,
        character_position: str = "auto",
        character_image_path: Optional[Path | str] = None,
    ) -> Dict[str, Any]:
        """
        Combine Manim educational visual video with IndicF5 narration audio, subtitles,
        and optional AI Teacher avatar presenter layer.

        Intelligent Duration Synchronization:
        - If audio duration > video duration: extend final video by freezing last frame with `tpad`
        - If video duration > audio duration: pad audio with silence up to video duration with `apad`
        - If subtitle_path is provided and burn_subtitles is True: burn readable subtitles with libass
        - If character_enabled is True: overlay canonical teacher without obscuring equations or subtitles

        Returns structured metadata for the final composed MP4.
        """
        start_time = time.time()

        if not self.ffmpeg_bin:
            self.ffmpeg_bin = find_ffmpeg_binary("ffmpeg")
            if not self.ffmpeg_bin:
                raise FFmpegBinaryNotFoundError("ffmpeg binary is not available. Please ensure FFmpeg is installed.")

        # Resolve input paths (handle relative paths from repository root or backend)
        resolved_video = self._resolve_path(video_path)
        resolved_audio = self._resolve_path(audio_path)

        if not resolved_video.exists():
            raise MediaNotFoundError(f"Input video file not found: {video_path}")
        if not resolved_audio.exists():
            raise MediaNotFoundError(f"Input audio file not found: {audio_path}")

        # Probe inputs to extract real durations and properties
        video_probe = self.probe_media(resolved_video)
        audio_probe = self.probe_media(resolved_audio)

        video_dur = video_probe["duration"]
        audio_dur = audio_probe["duration"]

        if video_dur <= 0.0:
            raise MediaProbeError(f"Input video has invalid duration ({video_dur}s): {resolved_video}")
        if audio_dur <= 0.0:
            raise MediaProbeError(f"Input audio has invalid duration ({audio_dur}s): {resolved_audio}")

        # Resolve output destination
        if output_path:
            resolved_output = self._resolve_output_path(output_path)
            if resolved_output.is_dir() and output_name:
                filename = output_name if output_name.endswith(".mp4") else f"{output_name}.mp4"
                resolved_output = resolved_output / filename
        else:
            # Auto-derive topic directory from video or audio parent directory
            topic_slug = resolved_audio.parent.name
            if not topic_slug or topic_slug == "audio":
                topic_slug = resolved_video.parent.name
            if not topic_slug or topic_slug in ("scenes", "videos"):
                topic_slug = "final_video"
            filename = output_name if output_name else "final.mp4"
            if not filename.endswith(".mp4"):
                filename = f"{filename}.mp4"
            resolved_output = settings.VIDEOS_DIR / topic_slug / filename

        resolved_output.parent.mkdir(parents=True, exist_ok=True)

        # Determine whether to burn subtitles and inspect subtitle final timestamp
        should_burn = settings.BURN_SUBTITLES if burn_subtitles is None else bool(burn_subtitles)
        resolved_subtitle: Optional[Path] = None
        sub_final_ts: Optional[float] = None
        if subtitle_path:
            candidate_sub = self._resolve_path(subtitle_path)
            if candidate_sub.exists() and candidate_sub.stat().st_size > 0:
                resolved_subtitle = candidate_sub
                sub_final_ts = get_subtitle_final_timestamp(candidate_sub)
            else:
                logger.warning("Subtitle path specified but not found or empty: %s", subtitle_path)
                should_burn = False
        else:
            should_burn = False

        # Resolve optional character image
        resolved_character: Optional[Path] = None
        if character_enabled:
            char_target = Path(character_image_path) if character_image_path else settings.CANONICAL_TEACHER_IMAGE
            resolved_char = self._resolve_path(char_target)
            if resolved_char.exists():
                resolved_character = resolved_char
                logger.info("[Character] Canonical educator enabled from: %s", resolved_char.name)
            else:
                logger.warning("Character image not found at %s; proceeding without character", char_target)
                character_enabled = False

        # --- LOG TIMELINE STATUS (Audio as Master Clock) ---
        logger.info("[SYNC] Manim video duration: %.2fs", video_dur)
        logger.info("[SYNC] IndicF5 audio duration: %.2fs", audio_dur)
        if sub_final_ts is not None:
            logger.info("[SYNC] Whisper final timestamp: %.2fs", sub_final_ts)
        logger.info("[SYNC] Master duration: %.2fs", audio_dur)
        logger.info("[SYNC] Audio speed modification: NONE")

        # Build video filters - adjust video timeline to match master audio clock
        video_filters: List[str] = []

        if audio_dur > video_dur:
            diff = round(audio_dur - video_dur, 3)
            video_filters.append(f"tpad=stop_mode=clone:stop_duration={diff}")
            logger.info("[SYNC] Extending video by: %.2fs", diff)
        elif video_dur > audio_dur:
            diff = round(video_dur - audio_dur, 3)
            video_filters.append(f"trim=duration={audio_dur},setpts=PTS-STARTPTS")
            logger.info("[SYNC] Trimming video by: %.2fs", diff)
        else:
            logger.info("[SYNC] Video and audio durations match; no adjustment needed")

        logger.info("[SYNC] Final duration target: %.2fs", audio_dur)

        # Assemble FFmpeg command
        cmd: List[str] = [
            self.ffmpeg_bin,
            "-y",
            "-i", str(resolved_video),
            "-i", str(resolved_audio),
        ]

        if character_enabled and resolved_character:
            pos = (character_position or "auto").lower()
            if pos not in ("left", "right"):
                pos = "right"  # auto defaults to right

            # Configure subtitle margins so subtitles never collide with teacher
            if should_burn and resolved_subtitle:
                escaped_srt = resolved_subtitle.as_posix().replace(":", r"\:")
                if pos == "left":
                    sub_style = "FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,MarginV=25,MarginL=360,MarginR=50"
                else:
                    sub_style = "FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,MarginV=25,MarginR=360,MarginL=50"
                video_filters.append(f"subtitles='{escaped_srt}':force_style='{sub_style}'")
                logger.info("[FFmpeg] Burning positioned subtitles for character %s", pos)

            base_chain = ",".join(video_filters) if video_filters else "null"
            width = video_probe.get("width") or 1280
            char_w = max(280, int(width * 0.26))

            if pos == "left":
                overlay_coords = "x=20:y=H-h"
            else:
                overlay_coords = "x=W-w-10:y=H-h"

            filter_complex = f"[0:v]{base_chain}[vbase];[2:v]scale={char_w}:-1[vchar];[vbase][vchar]overlay={overlay_coords}:shortest=1[vout]"

            cmd.extend([
                "-loop", "1",
                "-i", str(resolved_character),
                "-filter_complex", filter_complex,
                "-map", "[vout]",
                "-map", "1:a",
            ])
        else:
            # Standard composition without character
            if should_burn and resolved_subtitle:
                escaped_srt = resolved_subtitle.as_posix().replace(":", r"\:")
                style = "FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,MarginV=25"
                video_filters.append(f"subtitles='{escaped_srt}':force_style='{style}'")
                logger.info("[FFmpeg] Burning SRT subtitles: %s", resolved_subtitle.name)

            if video_filters:
                cmd.extend(["-vf", ",".join(video_filters)])


        # Video stream encoding (H.264, yuv420p, web-compatible)
        cmd.extend([
            "-c:v", settings.VIDEO_CODEC,
            "-pix_fmt", settings.PIXEL_FORMAT,
            "-crf", str(settings.VIDEO_CRF),
            "-preset", "medium",
        ])

        # Audio stream encoding (AAC, preserve original sample rate and native timing)
        cmd.extend([
            "-c:a", settings.AUDIO_CODEC,
            "-b:a", settings.AUDIO_BITRATE,
        ])

        # Enable faststart for instant web streaming
        cmd.extend([
            "-movflags", settings.MOVFLAGS,
            str(resolved_output),
        ])

        logger.info("[FFmpeg] Running command: %s", " ".join(cmd))
        run_res = subprocess.run(cmd, capture_output=True, text=True)

        if run_res.returncode != 0:
            logger.error("[FFmpeg] Execution failed: %s", run_res.stderr)
            raise VideoCompositionError(f"FFmpeg composition failed with exit code {run_res.returncode}: {run_res.stderr[-600:]}")

        if not resolved_output.exists() or resolved_output.stat().st_size == 0:
            raise VideoCompositionError(f"FFmpeg exited 0 but final output file was not created: {resolved_output}")

        # Probe final output to validate integrity
        out_probe = self.probe_media(resolved_output)
        if not out_probe["has_video"] or not out_probe["has_audio"]:
            raise VideoCompositionError(
                f"Generated MP4 lacks required streams: has_video={out_probe['has_video']}, has_audio={out_probe['has_audio']}"
            )

        # Validate A/V synchronization and master audio clock preservation
        sync_report = self.validate_sync(
            composed_video_path=resolved_output,
            original_audio_path=resolved_audio,
            tolerance_seconds=0.15,
        )
        logger.info(
            "[SYNC] Validation PASSED: final_video=%.2fs, final_audio=%.2fs, diff=%.3fs, orig_audio=%.2fs",
            sync_report["video_duration"],
            sync_report["audio_duration"],
            sync_report["duration_difference"],
            sync_report["original_audio_duration"],
        )

        elapsed = round(time.time() - start_time, 2)
        rel_path = self._to_relative_web_path(resolved_output)

        return {
            "success": True,
            "video_path": rel_path,
            "video_url": f"/{rel_path}",
            "duration_seconds": out_probe["duration"],
            "video_duration_seconds": video_dur,
            "audio_duration_seconds": audio_dur,
            "sync_difference": sync_report["duration_difference"],
            "audio_speed": "1.00x",
            "is_synchronized": sync_report["is_synchronized"],
            "sync_report": sync_report,
            "file_size_mb": out_probe["size_mb"],
            "output_size_mb": out_probe["size_mb"],
            "has_video": out_probe["has_video"],
            "has_audio": out_probe["has_audio"],
            "has_subtitles": bool(should_burn and resolved_subtitle),
            "subtitles_burned": bool(should_burn and resolved_subtitle),
            "generation_time_seconds": elapsed,
            "width": out_probe["width"],
            "height": out_probe["height"],
            "fps": out_probe["fps"],
            "video_codec": out_probe["video_codec"],
            "audio_codec": out_probe["audio_codec"],
            "pixel_format": out_probe.get("pixel_format", settings.PIXEL_FORMAT),
            "character_enabled": bool(character_enabled and resolved_character),
            "character_position": character_position if (character_enabled and resolved_character) else None,
            "character_path": str(resolved_character) if (character_enabled and resolved_character) else None,
        }



    def _resolve_path(self, p: Path | str) -> Path:
        """Resolve arbitrary relative path against backend or workspace."""
        path_obj = Path(p)
        if path_obj.is_absolute():
            return path_obj
        # Check relative to BASE_DIR (backend)
        c1 = settings.BASE_DIR / path_obj
        if c1.exists():
            return c1.resolve()
        # Check relative to current working directory
        c2 = Path.cwd() / path_obj
        if c2.exists():
            return c2.resolve()
        # Check workspace root
        c3 = settings.BASE_DIR.parent / path_obj
        if c3.exists():
            return c3.resolve()
        return c1.resolve()

    def _resolve_output_path(self, p: Path | str) -> Path:
        """Resolve target destination path for final output MP4."""
        path_obj = Path(p)
        if path_obj.is_absolute():
            return path_obj
        return (settings.BASE_DIR / path_obj).resolve()

    def _to_relative_web_path(self, absolute_path: Path) -> str:
        """Convert absolute path to relative web path starting with 'generated/'."""
        try:
            rel = absolute_path.relative_to(settings.BASE_DIR)
            return rel.as_posix()
        except ValueError:
            try:
                rel = absolute_path.relative_to(settings.GENERATED_DIR)
                return f"generated/{rel.as_posix()}"
            except ValueError:
                return absolute_path.as_posix()


# Singleton service instance
ffmpeg_service = FFmpegService()
