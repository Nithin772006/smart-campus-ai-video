"""
Educational Narration Localizer for SmartCampus AI Video (Task 9G-B).
Localizes educational voiceovers into target languages (en, ta, hi)
using local Qwen2.5 3B via Ollama while preserving mathematical
notations, technical terms, and spoken educational tone.
Enforces strict language validation, script ratio checks, sentence
deduplication, and explicit fallback handling.
"""

import re
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

from app.services.ollama_service import ollama_service, OllamaError

logger = logging.getLogger("smartcampus.localizer")

SUPPORTED_LANGUAGES = {"en", "ta", "hi"}

LANGUAGE_NAMES = {
    "en": "English",
    "ta": "Tamil",
    "hi": "Hindi",
}

SCRIPT_NAMES = {
    "en": "Latin",
    "ta": "Tamil (தமிழ்)",
    "hi": "Devanagari (हिन्दी)",
}

DEVANAGARI_REGEX = re.compile(r"[\u0900-\u097F]")
TAMIL_REGEX = re.compile(r"[\u0B80-\u0BFF]")

DEFAULT_MIN_SCRIPT_RATIO = 0.35  # At least 35% characters in target script (allows formulas, numbers, terms)
DEFAULT_MIN_CHARS = 10


class LocalizationError(Exception):
    """Raised when multilingual localization fails validation and fallback is disabled."""
    pass


@dataclass
class LocalizationResult:
    """Detailed result of a localization operation."""
    text: str
    requested_language: str
    actual_language: str
    script_ratio: float
    is_valid: bool
    fallback_used: bool
    fallback_reason: Optional[str]
    attempts: int
    word_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "requested_language": self.requested_language,
            "actual_language": self.actual_language,
            "script_ratio": self.script_ratio,
            "is_valid": self.is_valid,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "attempts": self.attempts,
            "word_count": self.word_count,
        }


class NarrationLocalizer:
    """
    Localizes spoken educational narration into requested languages (en, ta, hi).
    Guarantees:
    - English completely bypasses translation with zero overhead.
    - Script ratio validation prevents unchanged English from being labeled as Hindi/Tamil.
    - Consecutive phrase deduplication prevents degenerative repetition loops.
    - Re-attempts replace rather than append previous outputs.
    - Explicit fallback reporting prevents silent English synthesis under foreign language labels.
    """

    @staticmethod
    def normalize_language_code(language: Optional[str]) -> str:
        """Normalizes language name or ISO code to standard 2-letter code."""
        if not language:
            return "en"
        norm = language.strip().lower()
        if norm in ("ta", "tam", "tamil"):
            return "ta"
        if norm in ("hi", "hin", "hindi"):
            return "hi"
        if norm in ("en", "eng", "english"):
            return "en"
        # Unknown/unsupported languages default to en
        return "en"

    @classmethod
    def is_english(cls, language: Optional[str]) -> bool:
        """Determines if the language is English or unspecified."""
        return cls.normalize_language_code(language) == "en"

    @classmethod
    def get_language_display_name(cls, language: Optional[str]) -> str:
        """Returns readable display name for language."""
        code = cls.normalize_language_code(language)
        return LANGUAGE_NAMES.get(code, "English")

    @classmethod
    def calculate_script_ratio(cls, text: str, target_language: str) -> float:
        """
        Calculates the ratio of characters belonging to the target script
        among non-punctuation, non-whitespace word characters.
        """
        if not text:
            return 0.0
        code = cls.normalize_language_code(target_language)
        if code == "en":
            return 1.0

        # Strip spaces, numbers, punctuation, and common math operators
        cleaned = re.sub(r"[\s\d\.,!?;:\-_=+*\/\\()\[\]\"'’‘“”`~@#$%^&|<>{}]", "", text)
        if not cleaned:
            return 0.0

        if code == "hi":
            matches = DEVANAGARI_REGEX.findall(cleaned)
            return len(matches) / len(cleaned)
        elif code == "ta":
            matches = TAMIL_REGEX.findall(cleaned)
            return len(matches) / len(cleaned)

        return 0.0

    @classmethod
    def deduplicate_consecutive_phrases(cls, text: str) -> str:
        """
        Removes immediate consecutive duplicate sentences and looping word phrases.
        Preserves natural educational repetitions across different paragraphs while
        eliminating degenerate model repetition loops.
        """
        if not text:
            return ""

        # Step 1: Deduplicate consecutive identical sentences
        sentences = re.split(r"(?<=[.!?।])\s+", text.strip())
        cleaned_sentences = []
        prev_norm = None
        for s in sentences:
            s_clean = s.strip()
            if not s_clean:
                continue
            norm = re.sub(r"[.!?।\s]+", "", s_clean.lower())
            if norm and norm == prev_norm:
                # Direct duplicate sentence
                continue
            cleaned_sentences.append(s_clean)
            prev_norm = norm

        merged = " ".join(cleaned_sentences).strip()

        # Step 2: Prune consecutive repeating phrases of 3 to 10 words
        words = merged.split()
        if len(words) >= 6:
            for phrase_len in range(3, 11):
                i = 0
                new_words = []
                while i < len(words):
                    phrase = words[i:i + phrase_len]
                    next_phrase = words[i + phrase_len:i + 2 * phrase_len]
                    if len(phrase) == phrase_len and phrase == next_phrase:
                        new_words.extend(phrase)
                        i += 2 * phrase_len
                        # Skip all further consecutive repeats of this exact phrase
                        while i + phrase_len <= len(words) and words[i:i + phrase_len] == phrase:
                            i += phrase_len
                    else:
                        new_words.append(words[i])
                        i += 1
                words = new_words
            merged = " ".join(words)

        return merged

    @classmethod
    def clean_translated_text(cls, text: str) -> str:
        """Cleans LLM response formatting artifacts and dedupes loops."""
        if not text:
            return ""
        t = text.strip()

        # Remove quotes surrounding whole response
        if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
            t = t[1:-1].strip()

        # Remove markdown bold/italics
        t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
        t = re.sub(r"\*([^*]+)\*", r"\1", t)

        # Remove preamble markers in English, Hindi, and Tamil
        t = re.sub(
            r"^(?:Translation|Tamil Translation|Hindi Translation|Here is the translation|Spoken text|"
            r"Hindi|Tamil|English|अनुवाद|हिन्दी अनुवाद|மொழிபெயர்ப்பு|தமிழில்)\s*[:\-–]\s*",
            "",
            t,
            flags=re.IGNORECASE,
        )

        # Remove stray CJK characters that Qwen may occasionally emit
        t = re.sub(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]", "", t)

        # Apply consecutive phrase and sentence deduplication
        t = cls.deduplicate_consecutive_phrases(t)

        # Normalize multiple spaces
        t = re.sub(r" +", " ", t)

        return t.strip()

    @classmethod
    def validate_localization(
        cls,
        text: str,
        target_language: str,
        min_ratio: float = DEFAULT_MIN_SCRIPT_RATIO,
        min_length: int = DEFAULT_MIN_CHARS,
    ) -> Tuple[bool, float, Optional[str]]:
        """
        Validates that localization produced genuine content in the target script.
        Returns: (is_valid, script_ratio, error_reason)
        """
        code = cls.normalize_language_code(target_language)
        if code == "en":
            return True, 1.0, None

        if not text or len(text.strip()) < min_length:
            return False, 0.0, f"Translation text is too short ({len(text.strip()) if text else 0} chars < {min_length})."

        ratio = cls.calculate_script_ratio(text, code)
        if ratio < min_ratio:
            script_label = SCRIPT_NAMES.get(code, code)
            return (
                False,
                ratio,
                f"Insufficient {script_label} script content: ratio is {ratio:.1%}, required >= {min_ratio:.1%}."
            )

        return True, ratio, None

    @classmethod
    def _build_prompts(cls, text: str, target_language: str, is_retry: bool = False) -> Tuple[str, str]:
        """Constructs system and user prompts tailored to the language."""
        code = cls.normalize_language_code(target_language)
        lang_name = LANGUAGE_NAMES.get(code, "English")
        script_name = SCRIPT_NAMES.get(code, "native")

        if code == "hi":
            sys_prompt = (
                "You are an expert multilingual academic translator for educational science videos.\n"
                "Translate spoken educational narration into natural, teacher-like Hindi in Devanagari script (हिन्दी).\n\n"
                "STRICT RULES:\n"
                "1. Translate accurately into standard Hindi using Devanagari script.\n"
                "2. Preserve technical terminology, scientific concepts, and equations accurately (e.g. F = m * a, F = ma, vectors, m/s^2, Newton, kg).\n"
                "3. Never alter or corrupt mathematical formulas.\n"
                "4. Do not output English sentences or Latin script (except scientific symbols/equations).\n"
                "5. Do not add introductory greetings ('नमस्ते'), scene notes, markdown, or commentary.\n"
                "6. Do not repeat sentences or phrases.\n"
                "7. Output ONLY the translated Hindi spoken narration text.\n\n"
                "Example:\n"
                "English: Newton's Second Law states that force equals mass times acceleration.\n"
                "Hindi: न्यूटन का दूसरा नियम बताता है कि बल द्रव्यमान और त्वरण के गुणनफल के बराबर होता है।"
            )
        elif code == "ta":
            sys_prompt = (
                "You are an expert multilingual academic translator for educational science videos.\n"
                "Translate spoken educational narration into natural, teacher-like Tamil in Tamil script (தமிழ்).\n\n"
                "STRICT RULES:\n"
                "1. Translate accurately into standard Tamil using Tamil script.\n"
                "2. Preserve technical terminology, scientific concepts, and equations accurately (e.g. F = m * a, F = ma, vectors, m/s^2, Newton, kg).\n"
                "3. Never alter or corrupt mathematical formulas.\n"
                "4. Do not output foreign characters (such as Chinese or Hindi) or English sentences.\n"
                "5. Do not add introductory greetings ('வணக்கம்'), scene notes, markdown, or commentary.\n"
                "6. Do not repeat sentences or phrases.\n"
                "7. Output ONLY the translated Tamil spoken narration text.\n\n"
                "Example:\n"
                "English: Newton's Second Law states that force equals mass times acceleration.\n"
                "Tamil: விசை என்பது நிறை மற்றும் முடுக்கத்தின் பெருக்கற்பலனுக்கு சமம் என்று நியூட்டனின் இரண்டாவது விதி கூறுகிறது."
            )
        else:
            sys_prompt = "You are a professional educational translator. Output only the translation."

        if is_retry:
            user_prompt = (
                f"CRITICAL RETRY: The previous output failed validation. You MUST translate into pure {script_name} script.\n"
                f"Do NOT output English sentences. Do NOT repeat phrases.\n"
                f"Translate this exact narration now into {lang_name}:\n\n"
                f"{text}"
            )
        else:
            user_prompt = (
                f"Translate this educational narration into spoken {lang_name} ({script_name}):\n\n"
                f"{text}"
            )

        return sys_prompt, user_prompt

    @classmethod
    def localize_with_status(
        cls,
        text: str,
        target_language: Optional[str] = "en",
        allow_english_fallback: bool = True,
    ) -> LocalizationResult:
        """
        Localizes narration into target language with validation and retry.
        If validation fails, retries once with a stronger prompt.
        Attempt 2 replaces Attempt 1 completely (never appends).
        If both attempts fail, either falls back explicitly to English with warning
        or raises LocalizationError.
        """
        cleaned_text = (text or "").strip()
        if not cleaned_text:
            return LocalizationResult(
                text="",
                requested_language="en",
                actual_language="en",
                script_ratio=1.0,
                is_valid=True,
                fallback_used=False,
                fallback_reason=None,
                attempts=0,
                word_count=0,
            )

        target_code = cls.normalize_language_code(target_language)
        words_count = len(cleaned_text.split())

        # English bypass: zero overhead
        if cls.is_english(target_code):
            return LocalizationResult(
                text=cleaned_text,
                requested_language="en",
                actual_language="en",
                script_ratio=1.0,
                is_valid=True,
                fallback_used=False,
                fallback_reason=None,
                attempts=0,
                word_count=words_count,
            )

        lang_name = LANGUAGE_NAMES.get(target_code, target_code)
        logger.info(
            f"[Localizer] Localizing narration into {lang_name} ({target_code}). "
            f"Input: {words_count} words, {len(cleaned_text)} chars."
        )

        if not ollama_service.is_available():
            reason = f"Ollama service unavailable for localizing into {lang_name}."
            logger.warning(f"[Localizer] {reason}")
            if allow_english_fallback:
                return LocalizationResult(
                    text=cleaned_text,
                    requested_language=target_code,
                    actual_language="en",
                    script_ratio=0.0,
                    is_valid=False,
                    fallback_used=True,
                    fallback_reason=reason,
                    attempts=0,
                    word_count=words_count,
                )
            raise LocalizationError(reason)

        last_error = None
        best_output = ""
        best_ratio = 0.0

        for attempt in range(1, 3):
            is_retry = (attempt > 1)
            sys_prompt, user_prompt = cls._build_prompts(cleaned_text, target_code, is_retry=is_retry)
            temperature = 0.15 if attempt == 1 else 0.10

            try:
                raw_result = ollama_service.generate(
                    prompt=user_prompt,
                    system_prompt=sys_prompt,
                    temperature=temperature,
                    options={
                        "repeat_penalty": 1.25,
                        "top_p": 0.85,
                    },
                )
                # Attempt strictly replaces previous candidate
                candidate = cls.clean_translated_text(raw_result)
                is_valid, ratio, error_msg = cls.validate_localization(candidate, target_code)

                if is_valid:
                    cand_words = len(candidate.split())
                    logger.info(
                        f"[Localizer] Successfully localized into {lang_name} on attempt {attempt} "
                        f"(script ratio: {ratio:.1%}, words: {cand_words}, chars: {len(candidate)})."
                    )
                    return LocalizationResult(
                        text=candidate,
                        requested_language=target_code,
                        actual_language=target_code,
                        script_ratio=ratio,
                        is_valid=True,
                        fallback_used=False,
                        fallback_reason=None,
                        attempts=attempt,
                        word_count=cand_words,
                    )

                logger.warning(
                    f"[Localizer] Attempt {attempt} validation failed for {lang_name}: {error_msg} "
                    f"(candidate: {len(candidate)} chars, ratio: {ratio:.1%})."
                )
                last_error = error_msg
                best_output = candidate
                best_ratio = ratio

            except OllamaError as oe:
                last_error = f"Ollama generation error: {oe}"
                logger.warning(f"[Localizer] Attempt {attempt} failed with Ollama: {oe}")

        # Both attempts failed validation
        fallback_msg = (
            f"Localization into {lang_name} failed validation after 2 attempts: {last_error} "
            f"(best script ratio: {best_ratio:.1%})."
        )
        logger.error(f"[Localizer] {fallback_msg}")

        if allow_english_fallback:
            logger.warning(f"[Localizer] Explicitly falling back to English narration.")
            return LocalizationResult(
                text=cleaned_text,
                requested_language=target_code,
                actual_language="en",
                script_ratio=best_ratio,
                is_valid=False,
                fallback_used=True,
                fallback_reason=fallback_msg,
                attempts=2,
                word_count=words_count,
            )

        raise LocalizationError(fallback_msg)

    @classmethod
    def localize(
        cls,
        text: str,
        target_language: Optional[str] = "en",
        allow_english_fallback: bool = True,
    ) -> str:
        """
        Backwards-compatible convenience wrapper returning only the localized text string.
        """
        result = cls.localize_with_status(
            text=text,
            target_language=target_language,
            allow_english_fallback=allow_english_fallback,
        )
        return result.text


narration_localizer = NarrationLocalizer()
