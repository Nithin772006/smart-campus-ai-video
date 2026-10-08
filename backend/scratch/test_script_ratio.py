"""
Test script ratio detection for Hindi, Tamil, and English.
"""
import re

DEVANAGARI_REGEX = re.compile(r"[\u0900-\u097F]")
TAMIL_REGEX = re.compile(r"[\u0B80-\u0BFF]")
WORD_CHAR_REGEX = re.compile(r"[\w]", re.UNICODE)

def get_script_ratio(text: str, target_lang: str) -> float:
    if not text:
        return 0.0
    # Strip spaces and punctuation
    cleaned = re.sub(r"[\s\d\.,!?;:\-_=+*\/\\()\[\]\"']", "", text)
    if not cleaned:
        return 0.0
    if target_lang in ("hi", "hindi"):
        matches = DEVANAGARI_REGEX.findall(cleaned)
        return len(matches) / len(cleaned)
    elif target_lang in ("ta", "tamil"):
        matches = TAMIL_REGEX.findall(cleaned)
        return len(matches) / len(cleaned)
    elif target_lang in ("en", "english"):
        return 1.0
    return 0.0

# Test sample texts
hindi_sample = "न्यूटन का दूसरा गति नियम बताता है कि F = m * a होता है।"
tamil_sample = "நியூட்டனின் இரண்டாவது இயக்க விதி F = m * a என்பதை விளக்குகிறது."
english_sample = "Newton's Second Law of Motion states that F = m * a."
mixed_bad_sample = "Hello world this is english with one word न्यूटन"

print("Hindi sample ratio (hi):", get_script_ratio(hindi_sample, "hi"))
print("Hindi sample ratio on English (hi):", get_script_ratio(english_sample, "hi"))
print("Tamil sample ratio (ta):", get_script_ratio(tamil_sample, "ta"))
print("Tamil sample ratio on English (ta):", get_script_ratio(english_sample, "ta"))
print("Mixed sample ratio (hi):", get_script_ratio(mixed_bad_sample, "hi"))
