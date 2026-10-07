"""
Narration Builder Service for SmartCampus AI Video.
Converts EducationalVideoPlan scenes into natural, spoken educational scripts.
"""

import re
from typing import List, Dict, Any, Optional
from app.schemas.scene import EducationalVideoPlan, ScenePlanItem, SceneType


class NarrationService:
    """
    Transforms structured EducationalVideoPlan scenes into fluent,
    teacher-like spoken narration suitable for Text-to-Speech synthesis.
    """

    @staticmethod
    def clean_text_for_speech(text: Optional[str]) -> str:
        """
        Strips markdown formatting, code snippets, labels, and extra whitespace,
        ensuring the text sounds natural when vocalized.
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
        t = re.sub(r"^(?:Scene\s*\d+\s*[:\-–]\s*|Title\s*[:\-–]\s*|Note\s*[:\-–]\s*)", "", t, flags=re.IGNORECASE)

        # Expand common symbols to spoken words
        t = t.replace("&", " and ")
        t = t.replace("%", " percent")
        t = t.replace("@", " at ")

        # Normalize multiple spaces, tabs, and newlines to a single space
        t = re.sub(r"\s+", " ", t).strip()

        # Ensure sentence has ending punctuation
        if t and t[-1] not in ".!?":
            t += "."

        return t

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
    def build_scene_narration(
        cls,
        scene: ScenePlanItem,
        is_first: bool = False,
        is_last: bool = False,
        topic_title: str = ""
    ) -> str:
        """
        Creates an educational, teacher-like narration paragraph for a single scene.
        """
        parts: List[str] = []

        clean_title = cls.clean_text_for_speech(scene.title)
        clean_subtitle = cls.clean_text_for_speech(scene.subtitle)
        clean_content = cls.clean_text_for_speech(scene.content)

        # Handle Scene Types
        if scene.type == SceneType.TITLE or is_first:
            intro_title = clean_title.rstrip(".") if clean_title else topic_title
            if intro_title:
                if clean_subtitle:
                    parts.append(f"Welcome to this lesson on {intro_title}, focusing on {clean_subtitle.rstrip('.')}.")
                else:
                    parts.append(f"Welcome to this lesson on {intro_title}.")

            if clean_content and clean_content.lower() != clean_title.lower():
                parts.append(clean_content)

        elif scene.type == SceneType.FORMULA:
            if clean_title:
                parts.append(f"Let's examine the mathematical foundation of {clean_title.rstrip('.')}.")
            if clean_content:
                parts.append(clean_content)
            if scene.formula:
                spoken_formula = cls.convert_formula_to_speech(scene.formula)
                parts.append(f"Mathematically, this is expressed as: {spoken_formula}.")
            if scene.formula_breakdown:
                parts.append(cls._format_formula_breakdown(scene.formula_breakdown))

        elif scene.type in (SceneType.PROCESS, SceneType.CYCLE):
            if clean_title:
                parts.append(f"Now, let's explore the process of {clean_title.rstrip('.')}.")
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
            if clean_title:
                parts.append(f"Here are the key aspects of {clean_title.rstrip('.')}.")
            if clean_content:
                parts.append(clean_content)
            if scene.bullets:
                bullet_phrases = []
                for i, b in enumerate(scene.bullets):
                    cleaned_b = cls.clean_text_for_speech(b)
                    if i == 0:
                        bullet_phrases.append(f"Key point: {cleaned_b}")
                    elif i == len(scene.bullets) - 1:
                        bullet_phrases.append(f"Finally, {cleaned_b}")
                    else:
                        bullet_phrases.append(f"Additionally, {cleaned_b}")
                parts.append(" ".join(bullet_phrases))

        elif scene.type == SceneType.COMPARISON and scene.comparison:
            if clean_title:
                parts.append(f"Let's compare the characteristics of {clean_title.rstrip('.')}.")
            if clean_content:
                parts.append(clean_content)
            for side, points in scene.comparison.items():
                side_points = [cls.clean_text_for_speech(p) for p in points if p]
                if side_points:
                    parts.append(f"Regarding {side}: {' '.join(side_points)}")

        elif scene.type == SceneType.CONCLUSION or is_last:
            if clean_title:
                parts.append(f"In summary, we have covered {clean_title.rstrip('.')}.")
            if clean_content:
                parts.append(clean_content)
            if scene.bullets:
                summary_points = [cls.clean_text_for_speech(b) for b in scene.bullets if b]
                parts.append(f"To recap: {' '.join(summary_points)}")
            parts.append("Thank you for watching this explanation.")

        else:
            # General EXPLANATION / CONCEPT / DIAGRAM
            if clean_title and clean_title.lower() != (topic_title or "").lower():
                parts.append(f"Understanding {clean_title.rstrip('.')}.")
            if clean_content:
                parts.append(clean_content)
            if scene.formula:
                spoken_formula = cls.convert_formula_to_speech(scene.formula)
                parts.append(f"This is represented by the equation: {spoken_formula}.")
            if scene.bullets:
                bullet_phrases = [cls.clean_text_for_speech(b) for b in scene.bullets if b]
                parts.append(" ".join(bullet_phrases))
            if scene.steps:
                step_phrases = [cls.clean_text_for_speech(s) for s in scene.steps if s]
                parts.append(" ".join(step_phrases))

        # Filter out empty or duplicate strings and join
        unique_parts: List[str] = []
        for p in parts:
            p_clean = p.strip()
            if p_clean and (not unique_parts or p_clean.lower() != unique_parts[-1].lower()):
                unique_parts.append(p_clean)

        return " ".join(unique_parts)

    @classmethod
    def build_plan_narration(cls, plan: EducationalVideoPlan) -> Dict[str, Any]:
        """
        Processes all scenes in an EducationalVideoPlan to create scene-by-scene
        narration and a cohesive full narration script.
        """
        scene_narrations: List[Dict[str, Any]] = []
        total_scenes = len(plan.scenes)

        for idx, scene in enumerate(plan.scenes):
            is_first = (idx == 0)
            is_last = (idx == total_scenes - 1)
            narration = cls.build_scene_narration(
                scene=scene,
                is_first=is_first,
                is_last=is_last,
                topic_title=plan.title or plan.topic
            )
            scene_narrations.append({
                "scene_id": scene.id if scene.id is not None else (idx + 1),
                "scene_type": scene.type.value if hasattr(scene.type, "value") else str(scene.type),
                "title": scene.title,
                "narration": narration
            })

        full_script = " ".join([sn["narration"] for sn in scene_narrations if sn["narration"]]).strip()

        # Final cleanup pass: remove double periods or irregular spacing
        full_script = re.sub(r"\.\s*\.", ".", full_script)
        full_script = re.sub(r"\s+", " ", full_script).strip()

        return {
            "topic": plan.topic,
            "title": plan.title,
            "full_script": full_script,
            "scene_scripts": scene_narrations,
            "word_count": len(full_script.split()) if full_script else 0,
            "character_count": len(full_script)
        }
