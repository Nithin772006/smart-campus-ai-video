"""
Regression runner for Newton's Second Law and Binary Search.
Generates full educational videos and extracts inspection frames.
"""

import time
import subprocess
from pathlib import Path
from app.pipelines.video_composition import full_educational_video_pipeline
from app.services.ffmpeg_service import ffmpeg_service

def run_topic(topic_name, slug):
    print(f"\n=== Generating Video for: {topic_name} ===")
    start_t = time.perf_counter()
    res = full_educational_video_pipeline.generate(
        topic=topic_name,
        quality="medium_quality",
        burn_subtitles=True,
        character=True,
        character_position="right",
        visual_style="educational",
    )
    elapsed = time.perf_counter() - start_t
    print(f"Generated {topic_name} in {elapsed:.2f}s")
    video_file = Path(res["video_path"])
    print(f"Video file: {video_file}")
    print(f"Duration: {res.get('duration_seconds')}s, Audio: {res.get('audio_duration_seconds')}s, Sync diff: {res.get('sync_delta_seconds')}s")

    probe = ffmpeg_service.probe_media(video_file)
    print(f"Probe: {probe.get('width')}x{probe.get('height')}, FPS: {probe.get('fps')}, Codec: {probe.get('video_codec')}")

    scratch_dir = Path("scratch")
    scratch_dir.mkdir(exist_ok=True)
    timestamps = [5.0, 15.0]
    for ts in timestamps:
        out_frame = scratch_dir / f"fixed_{slug}_frame_{int(ts)}s.png"
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(ts),
            "-i", str(video_file),
            "-vframes", "1",
            str(out_frame)
        ]
        subprocess.run(cmd, check=True)
        print(f"Extracted frame: {out_frame}")

if __name__ == "__main__":
    run_topic("Newton's Second Law", "newton")
    run_topic("Binary Search", "binary_search")
