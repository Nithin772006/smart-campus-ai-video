"""
Test prototype of enhanced NarrationLocalizer logic.
"""
import re
from typing import Optional, Tuple, Dict, Any

DEVANAGARI_REGEX = re.compile(r"[\u0900-\u097F]")
TAMIL_REGEX = re.compile(r"[\u0B80-\u0BFF]")
WORD_CHAR_REGEX = re.compile(r"[\w]", re.UNICODE)

def normalize_language_code(language: Optional[str]) -> str:
    if not language:
        return "en"
    norm = language.strip().lower()
    if norm in ("ta", "tam", "tamil"):
        return "ta"
    if norm in ("hi", "hin", "hindi"):
        return "hi"
    return "en"

def calculate_script_ratio(text: str, target_language: str) -> float:
    if not text:
        return 0.0
    lang = normalize_language_code(target_language)
    if lang == "en":
        return 1.0
    cleaned = re.sub(r"[\s\d\.,!?;:\-_=+*\/\\()\[\]\"'’‘“”`~@#$%^&|<>{}]", "", text)
    if not cleaned:
        return 0.0
    if lang == "hi":
        matches = DEVANAGARI_REGEX.findall(cleaned)
        return len(matches) / len(cleaned)
    elif lang == "ta":
        matches = TAMIL_REGEX.findall(cleaned)
        return len(matches) / len(cleaned)
    return 0.0

def deduplicate_consecutive_phrases(text: str) -> str:
    if not text:
        return ""
    # 1. Deduplicate consecutive identical sentences
    sentences = re.split(r"(?<=[.!?।])\s+", text.strip())
    cleaned_sentences = []
    prev_norm = None
    for s in sentences:
        s_clean = s.strip()
        if not s_clean:
            continue
        norm = re.sub(r"[.!?।\s]+", "", s_clean.lower())
        if norm and norm == prev_norm:
            continue
        cleaned_sentences.append(s_clean)
        prev_norm = norm
    
    res = " ".join(cleaned_sentences).strip()

    # 2. Deduplicate consecutive repeating phrases (e.g. 3 to 8 words)
    words = res.split()
    if len(words) >= 6:
        for phrase_len in range(3, 9):
            i = 0
            new_words = []
            while i < len(words):
                phrase = words[i:i+phrase_len]
                next_phrase = words[i+phrase_len:i+2*phrase_len]
                if len(phrase) == phrase_len and phrase == next_phrase:
                    new_words.extend(phrase)
                    i += 2 * phrase_len
                    while i + phrase_len <= len(words) and words[i:i+phrase_len] == phrase:
                        i += phrase_len
                else:
                    new_words.append(words[i])
                    i += 1
            words = new_words
        res = " ".join(words)

    return res

def validate_localization(text: str, target_language: str, min_ratio: float = 0.35, min_length: int = 15) -> Tuple[bool, float, Optional[str]]:
    lang = normalize_language_code(target_language)
    if lang == "en":
        return True, 1.0, None
    if not text or len(text.strip()) < min_length:
        return False, 0.0, f"Translation text is too short ({len(text.strip()) if text else 0} chars < {min_length})."
    
    ratio = calculate_script_ratio(text, lang)
    if ratio < min_ratio:
        lang_name = "Hindi (Devanagari)" if lang == "hi" else "Tamil"
        return False, ratio, f"Insufficient {lang_name} script content: ratio is {ratio:.1%}, required at least {min_ratio:.1%}."
    
    return True, ratio, None

# Test validations
assert normalize_language_code("Hindi") == "hi"
assert normalize_language_code("Tamil") == "ta"
assert normalize_language_code("English") == "en"

# Validate Hindi
hi_valid, hi_r, err = validate_localization("न्यूटन का दूसरा नियम F = m * a है।", "hi")
assert hi_valid, f"Hindi validation failed: {err}"

# Validate English rejected as Hindi
en_as_hi_valid, r, err = validate_localization("Newton's second law is F = m * a.", "hi")
assert not en_as_hi_valid, "English was incorrectly accepted as Hindi!"

# Validate English rejected as Tamil
en_as_ta_valid, r, err = validate_localization("Newton's second law is F = m * a.", "ta")
assert not en_as_ta_valid, "English was incorrectly accepted as Tamil!"

# Validate Tamil accepted
ta_valid, ta_r, err = validate_localization("நியூட்டனின் இரண்டாவது விதி F = m * a ஆகும்.", "ta")
assert ta_valid, f"Tamil validation failed: {err}"

print("All prototype assertions passed successfully!")
