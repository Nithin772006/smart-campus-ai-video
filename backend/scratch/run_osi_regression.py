"""
Regression execution script for OSI Model video generation and inspection.
"""

import time
import subprocess
from pathlib import Path
from app.pipelines.video_composition import full_educational_video_pipeline
from app.services.ffmpeg_service import ffmpeg_service

def main():
    print("=== Generating Fixed OSI Model Video ===")
    start_t = time.perf_counter()
    res = full_educational_video_pipeline.generate(
        topic="OSI Model",
        quality="medium_quality",
        burn_subtitles=True,
        character=True,
        character_position="right",
        visual_style="educational",
    )
    elapsed = time.perf_counter() - start_t
    print(f"OSI Model generation finished in {elapsed:.2f}s")
    print(f"Video path: {res.get('video_path')}")
    print(f"Duration: {res.get('duration_seconds')}s, Audio Duration: {res.get('audio_duration_seconds')}s")
    print(f"Sync delta: {res.get('sync_delta_seconds')}s")

    video_file = Path(res["video_path"])
    probe = ffmpeg_service.probe_media(video_file)
    print(f"Probed Resolution: {probe.get('width')}x{probe.get('height')}, FPS: {probe.get('fps')}, Codec: {probe.get('video_codec')}")

    # Extract inspection frames
    scratch_dir = Path("scratch")
    scratch_dir.mkdir(exist_ok=True)
    timestamps = [5.0, 15.0, 25.0, 40.0]
    for ts in timestamps:
        out_frame = scratch_dir / f"fixed_osi_frame_{int(ts)}s.png"
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(ts),
            "-i", str(video_file),
            "-vframes", "1",
            str(out_frame)
        ]
        subprocess.run(cmd, check=True)
        print(f"Extracted inspection frame: {out_frame}")

if __name__ == "__main__":
    main()
