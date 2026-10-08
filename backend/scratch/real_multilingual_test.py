"""
Controlled real ElevenLabs test for Hindi and Tamil localization and synthesis (Task 9G-B).
At most 1 short Hindi test, and 1 short Tamil test.
"""
import sys
import os
import subprocess
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure ElevenLabs is enabled
os.environ["ELEVENLABS_ENABLED"] = "true"

from app.config import settings
settings.ELEVENLABS_ENABLED = True

from app.services.narration_localizer import narration_localizer
from app.services.elevenlabs_service import elevenlabs_service
from app.services.subtitle_service import subtitle_service

short_text = "Today we will learn Newton's Second Law of Motion."
total_chars = 0

print("==================================================")
print("1. SHORT HINDI CONTROLLED TEST")
print("==================================================")
loc_hi = narration_localizer.localize_with_status(short_text, target_language="hi")
print(f"Hindi Text: {loc_hi.text}")
print(f"Requested Language: {loc_hi.requested_language}")
print(f"Actual Language: {loc_hi.actual_language}")
print(f"Script Ratio (Devanagari): {loc_hi.script_ratio:.2%}")
print(f"Fallback Used: {loc_hi.fallback_used}")
print(f"Fallback Reason: {loc_hi.fallback_reason}")

assert loc_hi.is_valid, f"Hindi validation failed: {loc_hi.fallback_reason}"
assert loc_hi.actual_language == "hi", "Hindi localization did not produce Hindi!"
assert loc_hi.script_ratio >= 0.35, f"Hindi script ratio too low: {loc_hi.script_ratio}"

# Synthesize short Hindi text with ElevenLabs
res_hi = elevenlabs_service.generate_speech(
    text=loc_hi.text,
    language="hi",
    topic="hindi_controlled_test",
    timestamps=True,
    filename_prefix="narration",
)
total_chars += len(loc_hi.text)
print(f"Hindi Audio Path: {res_hi['audio_path']}")
print(f"Hindi Audio Duration: {res_hi['duration_seconds']}s")
print(f"Hindi Alignment Available: {res_hi['timestamp_data_available']}")

sub_hi = subtitle_service.process_audio(
    audio_path=res_hi["audio_path"],
    language="hi",
    alignment_data=res_hi.get("alignment"),
)
print(f"Hindi Subtitle Segments: {sub_hi['segment_count']} (source: {sub_hi['source']})")
print(f"Hindi SRT Path: {sub_hi['subtitle_srt_path']}")
if Path(sub_hi['subtitle_srt_path']).exists():
    print("Hindi SRT Preview:\n", Path(sub_hi['subtitle_srt_path']).read_text(encoding="utf-8").strip())


print("\n==================================================")
print("2. SHORT TAMIL CONTROLLED TEST")
print("==================================================")
loc_ta = narration_localizer.localize_with_status(short_text, target_language="ta")
print(f"Tamil Text: {loc_ta.text}")
print(f"Requested Language: {loc_ta.requested_language}")
print(f"Actual Language: {loc_ta.actual_language}")
print(f"Script Ratio (Tamil): {loc_ta.script_ratio:.2%}")
print(f"Fallback Used: {loc_ta.fallback_used}")
print(f"Fallback Reason: {loc_ta.fallback_reason}")

assert loc_ta.is_valid, f"Tamil validation failed: {loc_ta.fallback_reason}"
assert loc_ta.actual_language == "ta", "Tamil localization did not produce Tamil!"
assert loc_ta.script_ratio >= 0.35, f"Tamil script ratio too low: {loc_ta.script_ratio}"

# Check for consecutive repetition
words_ta = loc_ta.text.split()
for i in range(len(words_ta) - 3):
    phrase = " ".join(words_ta[i:i+3])
    rest = " ".join(words_ta[i+3:])
    assert phrase not in rest[:len(phrase)*2], f"Repetitive loop detected: {phrase}"

# Synthesize short Tamil text with ElevenLabs
res_ta = elevenlabs_service.generate_speech(
    text=loc_ta.text,
    language="ta",
    topic="tamil_controlled_test",
    timestamps=True,
    filename_prefix="narration",
)
total_chars += len(loc_ta.text)
print(f"Tamil Audio Path: {res_ta['audio_path']}")
print(f"Tamil Audio Duration: {res_ta['duration_seconds']}s")
print(f"Tamil Alignment Available: {res_ta['timestamp_data_available']}")

sub_ta = subtitle_service.process_audio(
    audio_path=res_ta["audio_path"],
    language="ta",
    alignment_data=res_ta.get("alignment"),
)
print(f"Tamil Subtitle Segments: {sub_ta['segment_count']} (source: {sub_ta['source']})")
print(f"Tamil SRT Path: {sub_ta['subtitle_srt_path']}")
if Path(sub_ta['subtitle_srt_path']).exists():
    print("Tamil SRT Preview:\n", Path(sub_ta['subtitle_srt_path']).read_text(encoding="utf-8").strip())

print(f"\nTotal characters consumed across short tests: {total_chars}")
print("BOTH CONTROLLED TESTS PASSED SUCCESSFULLY!")
