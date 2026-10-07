"""
Service for FFmpeg media stitching, subtitle burning, and audio mixing.
Provides utility functions for FFmpeg binary detection and media probing.
"""
import os
import sys
import shutil
import subprocess
import logging
from pathlib import Path
from typing import Optional, List
from app.config import settings

logger = logging.getLogger(__name__)


def find_ffmpeg_binary(binary_name: str = "ffmpeg") -> Optional[str]:
    """
    Locates FFmpeg or FFprobe executable.
    Checks the current environment PATH first.
    On Windows, inspects User/Machine registry environment paths to discover
    recently installed packages without permanently modifying Windows PATH.
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


def get_video_duration(video_path: Path | str) -> float:
    """
    Probe the duration of a video file in seconds using ffprobe.
    """
    ffprobe_bin = find_ffmpeg_binary("ffprobe")
    if not ffprobe_bin:
        raise RuntimeError("ffprobe binary is not available. Please ensure FFmpeg is installed.")

    video_path = Path(video_path).resolve()
    if not video_path.exists():
        raise FileNotFoundError(f"Video file does not exist: {video_path}")

    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return round(float(res.stdout.strip()), 2)


def concatenate_scene_clips(clip_paths: List[Path | str], output_path: Path | str) -> Path:
    """
    Concatenate a list of video clips into a single video file using FFmpeg concat demuxer.
    Falls back to re-encoding if stream copy fails.
    """
    ffmpeg_bin = find_ffmpeg_binary("ffmpeg")
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
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
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
    def __init__(self):
        self.output_dir = settings.GENERATED_DIR / "videos"

    def is_available(self) -> bool:
        return is_ffmpeg_available()

    def concatenate_clips(self, clip_paths: List[Path | str], output_path: Path | str) -> Path:
        return concatenate_scene_clips(clip_paths, output_path)

    async def concatenate_scenes(
        self,
        scene_paths: List[str],
        audio_path: str,
        output_filename: str = "final_video.mp4"
    ) -> str:
        # Placeholder for FFmpeg concatenation and audio multiplexing
        final_path = str(self.output_dir / output_filename)
        return final_path

