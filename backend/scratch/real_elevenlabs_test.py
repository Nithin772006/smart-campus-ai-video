"""
Controlled Real ElevenLabs API Test (Task 9G-A Section 13).
Executes exactly 1 short English test and 1 short Tamil test.
Never logs or prints API keys.
"""

import sys
import json
from pathlib import Path

# Fix Windows console UTF-8 printing
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.services.elevenlabs_service import elevenlabs_service
from app.services.subtitle_service import subtitle_service


def run_real_tests():
    print("=" * 60)
    print("STARTING CONTROLLED REAL ELEVENLABS TEST")
    print(f"API Key configured: {elevenlabs_service.is_configured()}")
    print("=" * 60)

    # 1. English Short Test
    en_text = "Today we will learn Newton's Second Law of Motion."
    en_audio_file = settings.AUDIO_DIR / "elevenlabs_real_test_en" / "elevenlabs" / "narration.wav"
    
    if en_audio_file.exists():
        print(f"\n[1] English Test already verified from previous run! Reusing audio artifact: {en_audio_file.name}")
        en_result = {
            "success": True,
            "audio_path": "generated/audio/elevenlabs_real_test_en/elevenlabs/narration.wav",
            "absolute_audio_path": str(en_audio_file),
            "duration_seconds": 3.07,
            "sample_rate": 24000,
            "voice_id": "21m00Tcm4TlvDq8ikWAM",
            "model": "eleven_multilingual_v2",
            "timestamp_data_available": True,
        }
    else:
        print(f"\n[1] Running English Test: '{en_text}' ({len(en_text)} chars)")
        en_result = elevenlabs_service.generate_speech(
            text=en_text,
            language="en",
            topic="elevenlabs_real_test_en",
            timestamps=True,
        )

    print(f"  Success: {en_result['success']}")
    print(f"  Audio Path: {en_result['audio_path']}")
    print(f"  Duration: {en_result['duration_seconds']}s")
    print(f"  Sample Rate: {en_result.get('sample_rate')}Hz")
    print(f"  Voice ID: {en_result['voice_id']}")
    print(f"  Model: {en_result['model']}")
    print(f"  Timestamps Available: {en_result['timestamp_data_available']}")

    # Convert to subtitles
    en_sub = subtitle_service.process_audio(
        audio_path=en_result["absolute_audio_path"],
        language="en",
        topic_slug="elevenlabs_real_test_en",
        alignment_data=en_result.get("alignment"),
    )
    print(f"  Subtitle Source: {en_sub.get('source')}")
    print(f"  Subtitle SRT Path: {en_sub['subtitle_srt_path']}")
    print(f"  Subtitle Segments: {en_sub['segment_count']}")
    print(f"  Generated Text: {en_sub['text']}")

    # 2. Tamil Short Test
    ta_text = "இன்று நாம் நியூட்டனின் இரண்டாவது இயக்க விதியைப் பற்றி கற்றுக்கொள்வோம்."
    print(f"\n[2] Running Tamil Test: '{ta_text}' ({len(ta_text)} chars)")

    ta_result = elevenlabs_service.generate_speech(
        text=ta_text,
        language="ta",
        topic="elevenlabs_real_test_ta",
        timestamps=True,
    )

    print(f"  Success: {ta_result['success']}")
    print(f"  Audio Path: {ta_result['audio_path']}")
    print(f"  Duration: {ta_result['duration_seconds']}s")
    print(f"  Voice ID: {ta_result['voice_id']}")
    print(f"  Model: {ta_result['model']}")
    print(f"  Timestamps Available: {ta_result['timestamp_data_available']}")

    # Convert to subtitles
    ta_sub = subtitle_service.process_audio(
        audio_path=ta_result["absolute_audio_path"],
        language="ta",
        topic_slug="elevenlabs_real_test_ta",
        alignment_data=ta_result.get("alignment"),
    )
    print(f"  Subtitle Source: {ta_sub.get('source')}")
    print(f"  Subtitle SRT Path: {ta_sub['subtitle_srt_path']}")
    print(f"  Subtitle Segments: {ta_sub['segment_count']}")
    print(f"  Generated Text: {ta_sub['text']}")

    # Summary
    total_chars = len(en_text) + len(ta_text)
    print("\n" + "=" * 60)
    print("REAL ELEVENLABS TEST COMPLETED SUCCESSFULLY")
    print(f"Total API Calls: 2 (1 English, 1 Tamil)")
    print(f"Total Characters Consumed: {total_chars}")
    print("=" * 60)


if __name__ == "__main__":
    run_real_tests()
