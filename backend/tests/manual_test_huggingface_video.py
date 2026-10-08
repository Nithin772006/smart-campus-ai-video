"""
Manual integration test for Hugging Face Inference Providers video generation (Task 9A).
Performs a REAL API call using the configured HF_TOKEN.
NOT run as part of normal pytest.
"""

import os
import sys
import time
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from app.config import settings
from app.services.huggingface_video_service import (
    HuggingFaceVideoService,
    HuggingFaceVideoConfigError,
    HuggingFaceAPIError,
    HuggingFaceTimeoutError,
)
from app.services.ffmpeg_service import ffmpeg_service


def run_manual_test():
    print("=" * 70)
    print("TASK 9A — MANUAL HUGGING FACE INFERENCE VIDEO TEST")
    print("=" * 70)

    token = os.getenv("HF_TOKEN") or settings.HF_TOKEN
    if not token or not token.strip():
        print("[-] ERROR: HF_TOKEN is not set in environment or backend/.env")
        print("    Please set HF_TOKEN=<your_token> in backend/.env before running.")
        sys.exit(1)

    masked_token = token[:7] + "..." + token[-4:] if len(token) > 12 else "***"
    print(f"[*] HF_TOKEN detected: {masked_token}")

    provider = os.getenv("HF_VIDEO_PROVIDER") or settings.HF_VIDEO_PROVIDER or "fal-ai"
    model = os.getenv("HF_VIDEO_MODEL") or settings.HF_VIDEO_MODEL or "Wan-AI/Wan2.2-TI2V-5B"
    timeout = float(os.getenv("HF_VIDEO_TIMEOUT") or settings.HF_VIDEO_TIMEOUT or 300.0)

    print(f"[*] Inference Provider: {provider}")
    print(f"[*] Video Model:        {model}")
    print(f"[*] Timeout:            {timeout}s")

    prompt = (
        "A cinematic educational visualization of a ball falling toward the ground "
        "due to gravity, clean classroom-style visual, smooth motion, realistic lighting, "
        "no text, no subtitles, no watermark"
    )
    print(f"[*] Prompt:             \"{prompt}\"")

    output_dir = settings.CLOUD_VIDEO_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    target_path = output_dir / "hf_gravity_test.mp4"

    print(f"[*] Target Output File: {target_path}")
    print("[*] Contacting Hugging Face Inference Providers API...")
    print("    (This may take 30-180 seconds depending on provider cold start and queue)...")

    service = HuggingFaceVideoService(
        token=token,
        default_provider=provider,
        default_model=model,
        timeout=timeout,
        output_dir=output_dir,
    )

    start_time = time.time()
    try:
        # Use conservative settings
        result = service.generate_video(
            prompt=prompt,
            model=model,
            provider=provider,
            output_path=target_path,
            check_enabled=False,  # Allow manual test even if globally disabled in .env
        )
        elapsed = time.time() - start_time

        print("\n" + "=" * 70)
        print("[+] SUCCESS: Hugging Face video generation completed!")
        print("=" * 70)
        print(f"Provider:             {result['provider']}")
        print(f"Model:                {result['model']}")
        print(f"Generation Time:      {elapsed:.2f} seconds")
        print(f"Saved Path:           {target_path}")

        if target_path.exists():
            size_bytes = target_path.stat().st_size
            size_mb = size_bytes / (1024 * 1024)
            print(f"File Size:            {size_mb:.2f} MB ({size_bytes} bytes)")
        else:
            print("[-] Warning: Output file does not exist on disk!")
            sys.exit(1)

        # Inspect with ffprobe if available
        if ffmpeg_service.is_available():
            try:
                probe = ffmpeg_service.probe_media(target_path)
                print(f"Duration:             {probe.get('duration')}s")
                print(f"Resolution:           {probe.get('resolution')}")
                print(f"Video Codec:          {probe.get('video_codec')}")
                print(f"Audio Codec:          {probe.get('audio_codec', 'None (silent video)')}")
                print(f"FPS:                  {probe.get('fps')}")
            except Exception as pe:
                print(f"[-] ffprobe inspection notice: {pe}")
        else:
            print("[*] ffprobe is not installed; skipped stream inspection.")

        print("=" * 70)
        print(f"[+] Static URL: http://127.0.0.1:8000/generated/cloud_video/{target_path.name}")
        print("=" * 70)
        return 0

    except HuggingFaceVideoConfigError as ce:
        print(f"\n[-] CONFIGURATION ERROR: {ce}")
        return 1
    except HuggingFaceTimeoutError as te:
        print(f"\n[-] TIMEOUT ERROR: {te}")
        return 1
    except HuggingFaceAPIError as ae:
        print(f"\n[-] HUGGING FACE API ERROR: {ae}")
        return 1
    except Exception as e:
        print(f"\n[-] UNEXPECTED ERROR: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    exit_code = run_manual_test()
    sys.exit(exit_code)
