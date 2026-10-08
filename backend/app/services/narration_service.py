"""
Narration Builder Service for SmartCampus AI Video.
Converts EducationalVideoPlan scenes into natural, spoken educational scripts
with strict word-budgeting for ~160 WPM natural teacher-like speech.
"""

import re
import logging
from typing import List, Dict, Any, Optional

from app.config import settings
from app.schemas.scene import EducationalVideoPlan, ScenePlanItem, SceneType
from app.services.ollama_service import ollama_service, OllamaError

logger = logging.getLogger("smartcampus.narration")


class NarrationService:
    """
    Transforms structured EducationalVideoPlan scenes into fluent,
    teacher-like spoken narration suitable for Text-to-Speech synthesis.
    Enforces word budgets to ensure natural speaking rate (~140-180 WPM, default 160 WPM).
    """

    # Robotic / filler phrases to strip from spoken narration
    BOILERPLATE_PATTERNS = [
        r"(?:\b|^)welcome to this lesson(?: on [^,.]+)?(?:,|\.)?\s*",
        r"(?:\b|^)welcome to this video(?: on [^,.]+)?(?:,|\.)?\s*",
        r"(?:\b|^)in this video(?: we will| let us| we'll)\s+[^,.]+(?:,|\.)?\s*",
        r"(?:\b|^)now(?: let us| let's) explore\s+[^,.]+(?:,|\.)?\s*",
        r"(?:\b|^)let us examine\s+[^,.]+(?:,|\.)?\s*",
        r"(?:\b|^)let's examine\s+[^,.]+(?:,|\.)?\s*",
        r"(?:\b|^)here are the key aspects of\s+[^,.]+(?:,|\.)?\s*",
        r"(?:\b|^)in summary(?: we have covered)?\s+[^,.]+(?:,|\.)?\s*",
        r"(?:\b|^)to recap:?\s*",
        r"(?:\b|^)key takeaway:?\s*",
        r"(?:\b|^)concept definition:?\s*",
        r"(?:\b|^)key point:?\s*",
        r"thank you for watching(?: this explanation)?(?:\.|\!)?",
    ]

    @classmethod
    def calculate_word_budget(cls, target_duration_seconds: float, target_wpm: Optional[int] = None) -> int:
        """
        Calculates target word budget for narration given a duration in seconds.
        Formula: round((target_duration_seconds / 60.0) * target_wpm)

        Examples at 160 WPM:
        30 sec -> 80 words
        45 sec -> 120 words
        60 sec -> 160 words
        90 sec -> 240 words
        120 sec -> 320 words
        """
        wpm = target_wpm or settings.NARRATION_TARGET_WPM
        if target_duration_seconds <= 0:
            return 0
        return round((target_duration_seconds / 60.0) * wpm)

    @classmethod
    def estimate_speech_metrics(
        cls,
        text: str,
        target_duration_seconds: float,
        target_wpm: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Calculates word count, estimated duration, and estimated WPM.
        Flags narration as too dense if estimated_wpm > 190.
        """
        words = len(text.strip().split()) if text else 0
        wpm = target_wpm or settings.NARRATION_TARGET_WPM
        estimated_duration = round((words / wpm) * 60.0, 2) if wpm > 0 else 0.0
        estimated_wpm = (
            round((words / target_duration_seconds) * 60.0, 1)
            if target_duration_seconds > 0
            else 0.0
        )
        is_too_dense = estimated_wpm > 190.0

        return {
            "word_count": words,
            "target_wpm": wpm,
            "target_duration_seconds": target_duration_seconds,
            "estimated_duration_seconds": estimated_duration,
            "estimated_wpm": estimated_wpm,
            "is_too_dense": is_too_dense,
        }

    @classmethod
    def clean_text_for_speech(cls, text: Optional[str]) -> str:
        """
        Strips markdown formatting, code snippets, labels, boilerplate filler,
        and extra whitespace, ensuring the text sounds natural when vocalized.
        """
        if not text:
            return ""

        t = text.strip()

        # Remove markdown headers (# Title)
        t = re.sub(r"^#+\s*", "", t)

        # Remove bold/italic markdown (**text**, *text*, __text__, _text_)
        t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
        t = re.sub(r"\*([^*]+)\*", r"\1", t)
        t = re.sub(r"__([^_]+)__", r"\1", t)

        # Remove markdown inline code and code blocks
        t = re.sub(r"`([^`]+)`", r"\1", t)

        # Remove markdown links [anchor](url) -> anchor
        t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)

        # Remove scene/label prefixes like "Scene 1:", "Title:", "Note:", "Step 1:"
        t = re.sub(
            r"^(?:Scene\s*\d+\s*[:\-–]\s*|Title\s*[:\-–]\s*|Note\s*[:\-–]\s*|Step\s*\d+\s*[:\-–]\s*)",
            "",
            t,
            flags=re.IGNORECASE,
        )

        # Expand common symbols to spoken words
        t = t.replace("&", " and ")
        t = t.replace("%", " percent")
        t = t.replace("@", " at ")

        # Strip generic boilerplate patterns
        for pattern in cls.BOILERPLATE_PATTERNS:
            t = re.sub(pattern, "", t, flags=re.IGNORECASE).strip()

        # Normalize multiple spaces, tabs, and newlines to a single space
        t = re.sub(r"\s+", " ", t).strip()

        # Ensure sentence has ending punctuation
        if t and t[-1] not in ".!?":
            t += "."

        return t

    @classmethod
    def deduplicate_consecutive_phrases(cls, text: str) -> str:
        """
        Removes immediate consecutive duplicate sentences or repeating word loops.
        Preserves natural educational repetitions across different paragraphs while
        eliminating accidental assembly duplication.
        """
        if not text:
            return ""

        # Step 1: Consecutive sentence deduplication
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

        merged = " ".join(cleaned_sentences).strip()

        # Step 2: Consecutive repeating phrases of 3 to 10 words
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
                        while i + phrase_len <= len(words) and words[i:i + phrase_len] == phrase:
                            i += phrase_len
                    else:
                        new_words.append(words[i])
                        i += 1
                words = new_words
            merged = " ".join(words)

        return merged

    @classmethod
    def convert_formula_to_speech(cls, formula: Optional[str]) -> str:
        """
        Translates mathematical and scientific equations into spoken English.
        Example: 'F = ma' -> 'F equals m times a'
        """
        if not formula:
            return ""

        f = formula.strip()

        # Strip surrounding LaTeX dollar signs or brackets
        f = re.sub(r"^\$+|\$+$", "", f)
        f = re.sub(r"\\\[|\\\]|\\\(|\\\)", "", f)

        # LaTeX fractions: \frac{a}{b} -> a divided by b
        f = re.sub(r"\\frac\{([^}]+)\}\{([^}]+)\}", r"\1 divided by \2", f)

        # Square roots: \sqrt{x} -> square root of x
        f = re.sub(r"\\sqrt\{([^}]+)\}", r"square root of \1", f)
        f = re.sub(r"\\sqrt", "square root of ", f)

        # Common LaTeX commands
        f = re.sub(r"\\text\{([^}]+)\}", r"\1", f)
        f = re.sub(r"\\mathbf\{([^}]+)\}", r"\1", f)
        f = re.sub(r"\\mathit\{([^}]+)\}", r"\1", f)
        f = re.sub(r"\\vec\{([^}]+)\}", r"\1 vector", f)
        f = re.sub(r"\\left|\\right", "", f)

        # Greek letters
        greek_map = {
            r"\\alpha": "alpha",
            r"\\beta": "beta",
            r"\\gamma": "gamma",
            r"\\delta": "delta",
            r"\\Delta": "change in ",
            r"\\theta": "theta",
            r"\\lambda": "lambda",
            r"\\pi": "pi",
            r"\\sigma": "sigma",
            r"\\omega": "omega",
            r"\\mu": "mu",
        }
        for k, v in greek_map.items():
            f = re.sub(k, f" {v} ", f)

        # Reaction / arrow symbols
        f = re.sub(r"\\rightarrow|\\to|->|→", " yields ", f)

        # Powers and superscripts
        f = re.sub(r"\^2|\b\^\{2\}|²", " squared", f)
        f = re.sub(r"\^3|\b\^\{3\}|³", " cubed", f)
        f = re.sub(r"\^\{([^}]+)\}", r" to the power of \1", f)
        f = re.sub(r"\^(\d+)", r" to the power of \1", f)

        # Subscripts (e.g. CO_2 -> CO 2, v_0 -> v initial)
        f = re.sub(r"_\{0\}|_0", " initial", f)
        f = re.sub(r"_\{([^}]+)\}", r" \1", f)
        f = re.sub(r"_(\w)", r" \1", f)

        # Common operators
        f = re.sub(r"\\times|×|\*", " multiplied by ", f)
        f = re.sub(r"\\div|÷|/", " divided by ", f)
        f = re.sub(r"\\approx|≈", " is approximately ", f)
        f = re.sub(r"\\le|<=|≤", " is less than or equal to ", f)
        f = re.sub(r"\\ge|>=|≥", " is greater than or equal to ", f)
        f = re.sub(r"\\ne|!=|≠", " is not equal to ", f)
        f = re.sub(r"\\pm|±", " plus or minus ", f)
        f = re.sub(r"\+", " plus ", f)
        f = re.sub(r"-", " minus ", f)
        f = re.sub(r"=", " equals ", f)

        # Clean remaining LaTeX braces and slashes
        f = re.sub(r"[{}\\]", "", f)

        # Special casing for simple product formulas like "m a" or "m * a"
        f = re.sub(r"\bma\b", "m a", f)
        f = re.sub(r"\bmc\b", "m c", f)

        # Normalize whitespace
        f = re.sub(r"\s+", " ", f).strip()
        return f

    @classmethod
    def _format_formula_breakdown(cls, breakdown: Optional[List[str]]) -> str:
        """
        Converts formula breakdown legends (e.g. ['F = Force (N)', 'm = Mass (kg)'])
        into natural spoken phrases.
        """
        if not breakdown:
            return ""

        unit_map = {
            r"\(m/s\^2\)|\(m/s²\)": "measured in meters per second squared",
            r"\(m/s\)": "measured in meters per second",
            r"\(kg\)": "measured in kilograms",
            r"\(N\)": "measured in Newtons",
            r"\(J\)": "measured in Joules",
            r"\(W\)": "measured in Watts",
            r"\(s\)": "measured in seconds",
            r"\(m\)": "measured in meters",
            r"\(Hz\)": "measured in Hertz",
            r"\(K\)": "measured in Kelvin",
        }

        items = []
        for item in breakdown:
            text = item.strip()
            for pattern, spoken in unit_map.items():
                text = re.sub(pattern, spoken, text, flags=re.IGNORECASE)
            # Remove any other leftover parenthesized unit notes
            text = re.sub(r"\([^)]*\)", "", text).strip()
            cleaned = cls.clean_text_for_speech(text).rstrip(".")

            match = re.match(r"^([A-Za-z0-9_]+)\s*(?:=|:|-)\s*(.+)$", cleaned)
            if match:
                symbol, meaning = match.group(1), match.group(2).strip()
                items.append(f"{symbol} represents {meaning}")
            else:
                items.append(cleaned)

        if not items:
            return ""
        if len(items) == 1:
            return f"In this equation, {items[0]}."
        elif len(items) == 2:
            return f"In this equation, {items[0]}, while {items[1]}."
        else:
            return f"In this equation, {', '.join(items[:-1])}, and {items[-1]}."

    @classmethod
    def extract_essential_educational_points(cls, plan: EducationalVideoPlan) -> List[str]:
        """
        Extracts genuine educational explanations, formulas, and process steps
        from the plan, completely omitting boilerplate headers, metadata,
        and robotic transitions.
        """
        points: List[str] = []
        seen = set()

        def add_point(p: str):
            clean = cls.clean_text_for_speech(p)
            # Check length and avoid duplicates
            if clean and len(clean.split()) >= 3:
                norm = clean.lower().rstrip(".!?")
                if norm not in seen:
                    seen.add(norm)
                    points.append(clean)

        # Plan summary if available
        if plan.summary:
            add_point(plan.summary)

        # Scene content
        for scene in plan.scenes:
            # Skip title scene if it doesn't have substantive content
            if scene.type == SceneType.TITLE:
                if scene.content and scene.content.lower() != (scene.title or "").lower():
                    add_point(scene.content)
                continue

            # Core concept or explanation
            if scene.content:
                # Filter out generic titles like "Concept Definition", "Key Takeaway"
                c = scene.content.strip()
                if not any(
                    c.lower().startswith(b)
                    for b in ["concept definition", "key takeaway", "summary", "overview"]
                ):
                    add_point(c)

            # Formula
            if scene.formula:
                spoken_formula = cls.convert_formula_to_speech(scene.formula)
                if spoken_formula:
                    add_point(f"This is expressed by the equation: {spoken_formula}.")

            # Steps
            if scene.steps:
                for step in scene.steps:
                    add_point(step)

            # Bullets
            if scene.bullets:
                for bullet in scene.bullets:
                    add_point(bullet)

        return points

    @classmethod
    def generate_llm_concise_narration(
        cls,
        plan: EducationalVideoPlan,
        target_duration_seconds: float,
        target_wpm: Optional[int] = None,
    ) -> Optional[str]:
        """
        Uses Qwen2.5 3B via Ollama to generate concise, teacher-like spoken narration
        strictly tailored to the word budget and target duration.
        Includes an automatic shortening retry loop if narration exceeds 190 WPM.
        """
        if not ollama_service.is_available():
            logger.info("[NARRATION] Ollama not available; falling back to rule-based concise narration.")
            return None

        word_budget = cls.calculate_word_budget(target_duration_seconds, target_wpm)
        min_words = max(20, int(word_budget * 0.75))
        max_words = int(word_budget * 1.15)

        essential_points = cls.extract_essential_educational_points(plan)
        if not essential_points:
            return None

        points_text = "\n".join(f"- {pt}" for pt in essential_points)

        system_prompt = (
            "You are writing narration for an educational video.\n\n"
            "Speak like a clear university teacher explaining the concept to a student.\n\n"
            "Target approximately 160 words per minute.\n\n"
            "The narration MUST fit within the requested target duration.\n\n"
            "Do not cram information.\n\n"
            "Do not repeat the topic unnecessarily.\n\n"
            "Do not say things like:\n"
            "'Welcome to this lesson'\n"
            "'Now let's explore'\n"
            "'In this video we will'\n"
            "unless they are genuinely useful.\n\n"
            "Prioritize:\n"
            "1. Core concept\n"
            "2. Important explanation\n"
            "3. Example/formula when relevant\n"
            "4. Short conclusion\n\n"
            "Use natural spoken language.\n\n"
            "Never write textbook-like paragraphs that are too dense for speech."
        )

        user_prompt = (
            f"Write the spoken educational narration for this topic:\n"
            f"Topic: {plan.title or plan.topic}\n"
            f"Target duration: {target_duration_seconds:.1f} seconds\n"
            f"Target word budget: {word_budget} words (must be between {min_words} and {max_words} words)\n\n"
            f"Educational plan points:\n{points_text}\n\n"
            f"Write ONLY a single spoken teacher narration paragraph. "
            f"Do NOT include headings, quotes, scene labels, or greetings. "
            f"Ensure every sentence is grammatically complete."
        )

        max_retries = settings.MAX_NARRATION_RETRIES
        current_prompt = user_prompt

        for attempt in range(max_retries + 1):
            try:
                raw_response = ollama_service.generate(
                    prompt=current_prompt,
                    system_prompt=system_prompt,
                    temperature=0.2 if attempt == 0 else 0.1,
                )
                cleaned = cls.clean_text_for_speech(raw_response)
                metrics = cls.estimate_speech_metrics(cleaned, target_duration_seconds, target_wpm)

                # Check if generated script fits within acceptable speech rate
                if not metrics["is_too_dense"] and metrics["word_count"] <= max_words:
                    logger.info(
                        f"[NARRATION] LLM narration accepted on attempt {attempt + 1}: "
                        f"{metrics['word_count']} words, est {metrics['estimated_wpm']} WPM"
                    )
                    return cleaned

                # If too dense or too long, prompt Qwen to shorten
                if attempt < max_retries:
                    logger.warning(
                        f"[NARRATION] Script too dense ({metrics['word_count']} words, "
                        f"{metrics['estimated_wpm']} WPM > 190 WPM) on attempt {attempt + 1}. Requesting shortening..."
                    )
                    current_prompt = (
                        f"The previous narration had {metrics['word_count']} words ({metrics['estimated_wpm']} WPM), "
                        f"which is too fast for a {target_duration_seconds} second video.\n"
                        f"Please shorten the explanation to AT MOST {word_budget} words. "
                        f"Keep the core concept clear and complete:\n\n{cleaned}"
                    )
                else:
                    logger.warning(
                        f"[NARRATION] Max retries reached with LLM. Script words: {metrics['word_count']}. "
                        "Applying concise sentence pruning."
                    )
                    return cls._prune_to_word_budget(cleaned, target_duration_seconds, target_wpm)

            except OllamaError as e:
                logger.warning(f"[NARRATION] LLM generation failed: {e}. Falling back to rule-based narration.")
                return None

        return None

    @classmethod
    def _prune_to_word_budget(
        cls,
        text: str,
        target_duration_seconds: float,
        target_wpm: Optional[int] = None,
    ) -> str:
        """
        Prunes a longer text by selecting complete sentences until reaching the word budget,
        guaranteeing the result is grammatically intact and <= 190 WPM.
        """
        word_budget = cls.calculate_word_budget(target_duration_seconds, target_wpm)
        max_words = int(word_budget * 1.15)

        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        if not sentences:
            return text

        selected: List[str] = []
        current_words = 0

        for s in sentences:
            s_clean = s.strip()
            if not s_clean:
                continue
            s_words = len(s_clean.split())
            if current_words + s_words <= max_words or not selected:
                selected.append(s_clean)
                current_words += s_words
            else:
                break

        result = " ".join(selected).strip()
        if result and result[-1] not in ".!?":
            result += "."
        return result

    @classmethod
    def build_rule_based_concise_script(
        cls,
        plan: EducationalVideoPlan,
        target_duration_seconds: float,
        target_wpm: Optional[int] = None,
    ) -> str:
        """
        Deterministic, natural teacher narration builder that constructs a concise
        explanation directly from the plan without robotic boilerplate, strictly
        respecting the word budget.
        """
        word_budget = cls.calculate_word_budget(target_duration_seconds, target_wpm)
        max_words = int(word_budget * 1.15)

        points = cls.extract_essential_educational_points(plan)
        if not points:
            # Fallback simple educational sentence
            topic = plan.title or plan.topic
            return f"{topic} is an important concept in {plan.domain.value if hasattr(plan.domain, 'value') else plan.domain}."

        selected: List[str] = []
        current_words = 0

        for pt in points:
            pt_clean = cls.clean_text_for_speech(pt)
            if not pt_clean:
                continue
            pt_words = len(pt_clean.split())
            if current_words + pt_words <= max_words or not selected:
                selected.append(pt_clean)
                current_words += pt_words
            else:
                break

        full_script = " ".join(selected).strip()
        full_script = re.sub(r"\s+", " ", full_script).strip()
        if full_script and full_script[-1] not in ".!?":
            full_script += "."
        return full_script

    @classmethod
    def build_scene_narration(
        cls,
        scene: ScenePlanItem,
        is_first: bool = False,
        is_last: bool = False,
        topic_title: str = "",
    ) -> str:
        """
        Creates an educational, teacher-like narration snippet for an individual scene,
        omitting robotic greetings and boilerplate headings.
        """
        parts: List[str] = []

        clean_title = cls.clean_text_for_speech(scene.title)
        clean_content = cls.clean_text_for_speech(scene.content)

        if scene.type == SceneType.TITLE or is_first:
            if clean_content:
                parts.append(clean_content)
            elif clean_title:
                parts.append(f"{clean_title.rstrip('.')}.")

        elif scene.type == SceneType.FORMULA:
            if clean_content:
                parts.append(clean_content)
            if scene.formula:
                spoken_formula = cls.convert_formula_to_speech(scene.formula)
                parts.append(f"This is expressed as: {spoken_formula}.")
            if scene.formula_breakdown:
                parts.append(cls._format_formula_breakdown(scene.formula_breakdown))

        elif scene.type in (SceneType.PROCESS, SceneType.CYCLE):
            if clean_content:
                parts.append(clean_content)
            if scene.steps:
                transition_words = ["First,", "Next,", "Then,", "Subsequently,", "Finally,"]
                step_parts = []
                for i, step in enumerate(scene.steps):
                    prefix = transition_words[i] if i < len(transition_words) else f"Step {i + 1}:"
                    cleaned_step = cls.clean_text_for_speech(step)
                    step_parts.append(f"{prefix} {cleaned_step}")
                parts.append(" ".join(step_parts))

        elif scene.type == SceneType.BULLET_POINTS:
            if clean_content:
                parts.append(clean_content)
            if scene.bullets:
                bullet_phrases = [cls.clean_text_for_speech(b) for b in scene.bullets if b]
                parts.append(" ".join(bullet_phrases))

        elif scene.type == SceneType.CONCLUSION or is_last:
            if clean_content:
                parts.append(clean_content)
            elif clean_title and clean_title.lower() != "key takeaway":
                parts.append(f"In summary, {clean_title.rstrip('.')}.")

        else:
            if clean_content:
                parts.append(clean_content)
            elif clean_title and clean_title.lower() != "concept definition":
                parts.append(clean_title)

        return " ".join(parts).strip()

    @classmethod
    def build_plan_narration(
        cls,
        plan: EducationalVideoPlan,
        target_duration_seconds: Optional[float] = None,
        target_wpm: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Builds natural, teacher-like narration for an EducationalVideoPlan.
        Prioritizes concise LLM generation matching target word budget.
        Validates speech density before returning.
        """
        eff_duration = (
            target_duration_seconds
            or getattr(plan, "target_duration", None)
            or settings.DEFAULT_TARGET_DURATION_SECONDS
        )
        eff_wpm = target_wpm or settings.NARRATION_TARGET_WPM
        word_budget = cls.calculate_word_budget(eff_duration, eff_wpm)

        # 1. Attempt LLM generation
        full_script = cls.generate_llm_concise_narration(
            plan=plan,
            target_duration_seconds=eff_duration,
            target_wpm=eff_wpm,
        )

        # 2. Fallback to rule-based concise script if LLM did not produce valid script
        if not full_script:
            full_script = cls.build_rule_based_concise_script(
                plan=plan,
                target_duration_seconds=eff_duration,
                target_wpm=eff_wpm,
            )

        # 3. Clean, deduplicate, and normalize
        full_script = cls.deduplicate_consecutive_phrases(full_script)
        full_script = re.sub(r"\.\s*\.", ".", full_script)
        full_script = re.sub(r"\s+", " ", full_script).strip()

        # 4. Calculate metrics and log according to requirement #7
        metrics = cls.estimate_speech_metrics(full_script, eff_duration, eff_wpm)
        logger.info(
            f"\n[NARRATION]\n"
            f"Words: {metrics['word_count']}\n"
            f"Target WPM: {metrics['target_wpm']}\n"
            f"Estimated duration: {metrics['estimated_duration_seconds']:.2f}s"
        )

        # 5. Build scene_scripts list for backward compatibility with tests/API
        scene_narrations: List[Dict[str, Any]] = []
        total_scenes = len(plan.scenes)
        for idx, scene in enumerate(plan.scenes):
            scene_narrations.append({
                "scene_id": scene.id if scene.id is not None else (idx + 1),
                "scene_type": scene.type.value if hasattr(scene.type, "value") else str(scene.type),
                "title": scene.title,
                "narration": cls.build_scene_narration(
                    scene=scene,
                    is_first=(idx == 0),
                    is_last=(idx == total_scenes - 1),
                    topic_title=plan.title or plan.topic,
                ),
            })

        return {
            "topic": plan.topic,
            "title": plan.title,
            "full_script": full_script,
            "scene_scripts": scene_narrations,
            "word_count": metrics["word_count"],
            "character_count": len(full_script),
            "target_duration_seconds": eff_duration,
            "target_wpm": metrics["target_wpm"],
            "estimated_duration_seconds": metrics["estimated_duration_seconds"],
            "estimated_wpm": metrics["estimated_wpm"],
            "word_budget": word_budget,
            "is_too_dense": metrics["is_too_dense"],
        }


# Singleton service instance
narration_service = NarrationService()
