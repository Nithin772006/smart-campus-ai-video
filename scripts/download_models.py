"""
Model Download Script for SmartCampus AI Video
Downloads checkpoints for LTX-Video and IndicF5 TTS.
"""

import os
import argparse
from pathlib import Path

def download_models(target_dir: Path):
    print("==================================================")
    print("SmartCampus AI Video - Model Checkpoint Downloader")
    print("==================================================")
    ltx_dir = target_dir / "backend" / "models" / "ltx"
    indicf5_dir = target_dir / "backend" / "models" / "indicf5"
    
    ltx_dir.mkdir(parents=True, exist_ok=True)
    indicf5_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"[+] LTX Model directory: {ltx_dir}")
    print(f"[+] IndicF5 Model directory: {indicf5_dir}")
    print("[*] To download LTX-Video, refer to Hugging Face: Lightricks/LTX-Video")
    print("[*] To download IndicF5, refer to AI4Bharat / IndicF5 repository")
    print("[✓] Model directory setup complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download model weights for video generation")
    parser.add_argument("--dir", type=str, default=".", help="Base project directory")
    args = parser.parse_args()
    download_models(Path(args.dir).resolve())
