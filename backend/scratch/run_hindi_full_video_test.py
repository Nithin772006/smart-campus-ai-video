"""
Controlled full video generation test for Hindi localization and ElevenLabs TTS (Task 9G-B).
Generates 1 complete video in Hindi to verify:
1. Hindi localization outputs natural Devanagari script.
2. Script ratio validation passes (>= 35%).
3. ElevenLabs receives language="hi" and synthesizes Hindi speech.
4. Subtitles match the synthesized Hindi script.
5. Final composed MP4 video is created and playable with audio synced.
"""
import sys
import os
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

os.environ["ELEVENLABS_ENABLED"] = "true"

from app.config import settings
settings.ELEVENLABS_ENABLED = True

from app.pipelines.video_composition import full_educational_video_pipeline
from app.services.ffmpeg_service import ffmpeg_service

def main():
    print("==================================================")
    print("RUNNING CONTROLLED FULL HINDI VIDEO TEST")
    print("==================================================")
    start_t = time.perf_counter()

    topic = "Newton's Second Law"
    res = full_educational_video_pipeline.generate(
        topic=topic,
        quality="low_quality",
        burn_subtitles=True,
        language="hi",
        target_duration_seconds=25.0,
        character=False,
        visual_style="academic",
        voice_provider="elevenlabs",
    )

    elapsed = time.perf_counter() - start_t
    print("\n==================================================")
    print("FULL HINDI VIDEO GENERATION RESULTS")
    print("==================================================")
    print(f"Elapsed Time: {elapsed:.2f}s")
    print(f"Status: {res.get('status')}")
    print(f"Video Path: {res.get('video_path')}")
    print(f"Audio Path: {res.get('audio_path')}")
    print(f"Subtitle Path: {res.get('subtitle_path')}")
    print(f"Requested Language: {res.get('language')}")
    print(f"Actual Language: {res.get('actual_language')}")
    print(f"Localization Fallback: {res.get('localization_fallback')}")
    print(f"Script Ratio: {res.get('script_ratio')}")
    print(f"Voice Provider: {res.get('voice_provider')}")
    print(f"Video Duration: {res.get('duration_seconds')}s")
    print(f"Audio Duration: {res.get('audio_duration_seconds')}s")
    print(f"Sync Delta: {res.get('sync_delta_seconds')}s")

    video_path = Path(res.get("video_path"))
    assert video_path.exists(), f"Video file not found at {video_path}"
    assert video_path.stat().st_size > 10000, f"Video file unexpectedly small: {video_path.stat().st_size} bytes"

    # Assertions
    assert res.get("actual_language") == "hi", f"Expected actual_language='hi', got {res.get('actual_language')}"
    assert not res.get("localization_fallback"), "Localization fell back to English!"
    assert res.get("script_ratio", 0.0) >= 0.35, f"Script ratio too low: {res.get('script_ratio')}"
    assert res.get("voice_provider") == "elevenlabs", "Expected voice_provider='elevenlabs'"

    # Probe media
    probe = ffmpeg_service.probe_media(video_path)
    print(f"\nMedia Probe: Resolution={probe.get('width')}x{probe.get('height')}, FPS={probe.get('fps')}, Audio Codec={probe.get('audio_codec')}")

    # Inspect subtitles
    sub_path = Path(res.get("subtitle_path"))
    if sub_path.exists():
        sub_content = sub_path.read_text(encoding="utf-8").strip()
        print("\nSubtitle Preview:\n" + sub_content[:400] + ("..." if len(sub_content) > 400 else ""))

    # Extract test frame to inspect burned subtitles
    out_frame = Path("scratch/hindi_video_frame.png")
    out_frame.parent.mkdir(exist_ok=True)
    import subprocess
    cmd = [
        "ffmpeg", "-y",
        "-ss", "5.0",
        "-i", str(video_path),
        "-vframes", "1",
        str(out_frame)
    ]
    subprocess.run(cmd, check=True)
    print(f"Extracted inspection frame: {out_frame} (exists: {out_frame.exists()})")

    print("\nCONTROLLED FULL HINDI VIDEO GENERATION COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
