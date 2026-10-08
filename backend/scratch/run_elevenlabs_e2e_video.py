"""
Controlled End-to-End Verification of Full Educational Video Pipeline with ElevenLabs TTS.
Topic: "Newton's Second Law of Motion"
Language: "en"
Provider: "elevenlabs"
Character: False
"""

import sys
import os
import time
import subprocess
from pathlib import Path

# Fix Windows console UTF-8 output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from app.pipelines.video_composition import full_educational_video_pipeline
from app.services.ffmpeg_service import ffmpeg_service

def run_e2e():
    topic = "Newton's Second Law of Motion"
    print(f"\n=======================================================")
    print(f"STARTING FULL E2E VIDEO GENERATION")
    print(f"Topic: {topic}")
    print(f"Provider: elevenlabs")
    print(f"Language: en")
    print(f"Character: False")
    print(f"=======================================================\n")

    start_time = time.perf_counter()
    res = full_educational_video_pipeline.generate(
        topic=topic,
        quality="medium_quality",
        burn_subtitles=True,
        language="en",
        character=False,
        voice_provider="elevenlabs",
    )
    total_duration = time.perf_counter() - start_time

    print(f"\n=======================================================")
    print(f"FULL E2E VIDEO GENERATION COMPLETED IN {total_duration:.2f}s")
    print(f"=======================================================")
    print(f"Success: {res.get('success')}")
    print(f"Video Path: {res.get('video_path')}")
    print(f"Video URL: {res.get('video_url')}")
    print(f"Final MP4 Duration: {res.get('duration_seconds')}s")
    print(f"Manim Video Duration: {res.get('video_duration_seconds')}s")
    print(f"Audio Duration: {res.get('audio_duration_seconds')}s")
    print(f"Sync Difference: {res.get('sync_difference')}s")
    print(f"Audio Speed: {res.get('audio_speed')}")
    print(f"Subtitle Segment Count: {res.get('subtitle_segment_count')}")
    print(f"Subtitles Burned: {res.get('subtitles_burned')}")
    print(f"Speech Rate (WPM): {res.get('speech_rate_wpm')}")
    print(f"Narration Words: {res.get('narration_words')}")
    print(f"Fallback Used: {res.get('fallback_used')}")
    print(f"Provider Used: {res.get('provider_used')}")

    video_file = Path(res["video_path"])
    assert video_file.exists(), f"Final video file does not exist: {video_file}"
    assert video_file.stat().st_size > 0, f"Final video file is empty: {video_file}"

    # Probe final video with ffprobe
    probe = ffmpeg_service.probe_media(video_file)
    print(f"\nFFprobe Media Details:")
    print(f"- Resolution: {probe.get('width')}x{probe.get('height')}")
    print(f"- FPS: {probe.get('fps')}")
    print(f"- Video Codec: {probe.get('video_codec')}")
    print(f"- Audio Codec: {probe.get('audio_codec')}")
    print(f"- Duration: {probe.get('duration')}s")
    print(f"- File Size: {video_file.stat().st_size / (1024 * 1024):.2f} MB")

    # Extract verification frames
    scratch_dir = Path("scratch")
    scratch_dir.mkdir(exist_ok=True)
    probe_dur = probe.get("duration", 20.0)
    sample_timestamps = [3.0, min(10.0, probe_dur * 0.5), min(20.0, probe_dur * 0.8)]
    for ts in sample_timestamps:
        out_frame = scratch_dir / f"newton_elevenlabs_frame_{int(ts)}s.png"
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(ts),
            "-i", str(video_file),
            "-vframes", "1",
            str(out_frame)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"Extracted verification frame at {ts}s -> {out_frame} ({out_frame.stat().st_size} bytes)")

    print("\nALL E2E CHECKS PASSED SUCCESSFULLY!\n")

if __name__ == "__main__":
    run_e2e()
