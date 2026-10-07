"""
LLM Academic Planner.
Converts arbitrary user academic questions into structured EducationalVideoPlans
using local Qwen2.5 3B via Ollama, with automatic fallback to RuleBasedAcademicPlanner.
"""
import json
import logging
import re
from typing import Optional, Dict, Any, Tuple, List

from app.config import settings
from app.schemas.scene import (
    SceneType,
    AcademicDomain,
    ScenePlanItem,
    EducationalVideoPlan,
)
from app.services.scene_planner import AcademicPlanner, RuleBasedAcademicPlanner
from app.services.ollama_service import (
    OllamaService,
    OllamaError,
    ollama_service as default_ollama_service,
)

logger = logging.getLogger(__name__)

ACADEMIC_SYSTEM_PROMPT = """You are an educational video planning assistant.
Convert the user's academic question into a concise, accurate educational video plan.

Your output MUST be valid JSON matching the provided schema.
Do not output Markdown fences (no ```json or ```).
Do not output explanations, greetings, or notes outside the JSON.
Do not invent unsupported scene types.

Supported scene types:
- title : Opening video title and domain
- explanation : Concept definition or conceptual explanation
- formula : Mathematical formula or chemical equation with variable breakdown
- bullet_points : Key principles or properties
- process : Sequential procedural stages or algorithm steps
- hierarchy : Stacked architectural layers (e.g. OSI model)
- cycle : Continuous circular process (e.g. Water cycle)
- conclusion : Summary takeaway

Supported domains:
- mathematics, physics, chemistry, biology, computer_science, engineering, general

Guidelines:
1. Break the explanation into 4 to 8 short visual scenes (total target duration between 20 and 40 seconds).
2. Each scene duration should be between 4.0 and 7.0 seconds.
3. Scene 1 MUST have type "title".
4. The final scene MUST have type "conclusion".
5. Prioritize academic correctness over creativity.
6. Use "formula" when equations exist (e.g. physics, math, chemistry). Provide "formula" string and "formula_breakdown" array.
7. Use "process" or "cycle" for multi-step mechanisms or algorithms. Provide "steps" array.
8. Use "bullet_points" for lists of principles. Provide "bullets" array.
9. Keep explanations clear and suitable for a college student.
10. Never fabricate facts, formulas, or terminology.

JSON Schema format:
{
  "topic": "Canonical Topic Name",
  "title": "Educational Video Title",
  "level": "beginner" | "intermediate" | "advanced",
  "domain": "physics" | "biology" | "computer_science" | "mathematics" | "chemistry" | "engineering" | "general",
  "summary": "Concise summary sentence",
  "target_duration": 25.0,
  "scenes": [
    {
      "id": 1,
      "type": "title",
      "duration": 4.0,
      "title": "Title of Scene",
      "subtitle": "Subtitle or topic focus",
      "visual_engine": "manim"
    },
    {
      "id": 2,
      "type": "explanation",
      "duration": 6.0,
      "title": "Concept Definition",
      "content": "Clear explanation of the core concept.",
      "visual_engine": "manim"
    },
    {
      "id": 3,
      "type": "formula",
      "duration": 6.0,
      "title": "Equation",
      "formula": "F = m * a",
      "formula_breakdown": ["F : Net Force (N)", "m : Mass (kg)", "a : Acceleration (m/s²)"],
      "visual_engine": "manim"
    },
    {
      "id": 4,
      "type": "conclusion",
      "duration": 4.0,
      "title": "Key Takeaway",
      "content": "Summary takeaway sentence.",
      "visual_engine": "manim"
    }
  ]
}
"""


class LLMAcademicPlanner(AcademicPlanner):
    """
    LLM-driven academic video planner powered by local Qwen2.5 3B via Ollama.
    Falls back gracefully to RuleBasedAcademicPlanner if Ollama is unavailable,
    times out, or returns invalid schemas.
    """

    def __init__(
        self,
        ollama: Optional[OllamaService] = None,
        fallback_planner: Optional[AcademicPlanner] = None,
    ):
        self.ollama = ollama or default_ollama_service
        self.fallback_planner = fallback_planner or RuleBasedAcademicPlanner()

    def plan(self, question: str) -> EducationalVideoPlan:
        """
        Produce an EducationalVideoPlan using local LLM, or fallback to rule-based planner.
        Complies with AcademicPlanner abstract interface.
        """
        plan, _, _ = self.plan_with_fallback(question)
        return plan

    def plan_with_fallback(self, question: str) -> Tuple[EducationalVideoPlan, bool, str]:
        """
        Plan the educational video with explicit tracking of whether fallback occurred.

        :return: (plan: EducationalVideoPlan, used_fallback: bool, planner_name: str)
        """
        logger.info(f"[LLM] Generating educational plan for question: '{question}'")

        # 1. Attempt LLM generation
        try:
            plan = self._generate_and_validate_plan(question)
            logger.info(f"[LLM] Plan validated successfully: {plan.title} ({len(plan.scenes)} scenes)")
            return plan, False, f"ollama/{self.ollama.model}"
        except Exception as e:
            fallback_reason = str(e)
            logger.warning(f"[LLM] Falling back to rule-based planner: {fallback_reason}")

        # 2. Graceful Fallback
        fallback_plan = self.fallback_planner.plan(question)
        return fallback_plan, True, "rule_based"

    def _generate_and_validate_plan(self, question: str) -> EducationalVideoPlan:
        """
        Query Ollama, parse JSON, sanitize, validate against Pydantic schema,
        and perform one safe retry if initial response fails validation.
        """
        user_prompt = f"Create an educational video plan for the following topic/question:\n\n\"{question}\""

        # Pass Pydantic schema to Ollama for structured output enforcement
        json_schema = EducationalVideoPlan.model_json_schema()

        raw_response = self.ollama.generate(
            prompt=user_prompt,
            system_prompt=ACADEMIC_SYSTEM_PROMPT,
            format=json_schema,
            temperature=0.1,
        )

        try:
            return self._parse_and_validate_json(raw_response, fallback_topic=question)
        except Exception as first_error:
            logger.warning(
                f"[LLM] Initial response validation failed: {first_error}. Attempting one safe retry with correction prompt."
            )

            # Retry with correction prompt
            retry_prompt = (
                f"Your previous JSON output for topic '{question}' failed validation with error:\n"
                f"{str(first_error)}\n\n"
                f"Previous response was:\n{raw_response[:500]}\n\n"
                "Please correct the error and output valid JSON matching the schema strictly."
            )

            corrected_response = self.ollama.generate(
                prompt=retry_prompt,
                system_prompt=ACADEMIC_SYSTEM_PROMPT,
                format=json_schema,
                temperature=0.1,
            )

            return self._parse_and_validate_json(corrected_response, fallback_topic=question)

    def _parse_and_validate_json(self, raw_text: str, fallback_topic: str) -> EducationalVideoPlan:
        """Extract JSON, normalize scenes, and validate with Pydantic."""
        cleaned_text = self._strip_markdown_fences(raw_text)

        try:
            data = json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Malformed JSON from LLM: {e}") from e

        if not isinstance(data, dict):
            raise ValueError(f"LLM JSON root is not an object, got {type(data).__name__}")

        # Normalize and sanitize fields before Pydantic parsing
        sanitized_data = self._sanitize_plan_dict(data, fallback_topic)

        # Validate with Pydantic
        plan = EducationalVideoPlan(**sanitized_data)
        logger.info("[LLM] Plan validated")
        return plan

    def _strip_markdown_fences(self, text: str) -> str:
        """Strip possible markdown ```json ... ``` enclosures."""
        s = text.strip()
        # Find first '{' and last '}'
        start_idx = s.find("{")
        end_idx = s.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return s[start_idx : end_idx + 1]
        return s

    def _sanitize_plan_dict(self, data: Dict[str, Any], default_topic: str) -> Dict[str, Any]:
        """
        Ensure data conforms strictly to EducationalVideoPlan and Manim renderer requirements:
        - Valid domain enum
        - Valid scene types mapped from common synonyms
        - Required scene fields populated
        - Appropriate scene durations
        """
        # 1. Topic & Title
        topic = str(data.get("topic") or default_topic).strip()
        title = str(data.get("title") or f"Understanding {topic}").strip()
        data["topic"] = topic
        data["title"] = title

        # 2. Domain
        valid_domains = [d.value for d in AcademicDomain]
        raw_domain = str(data.get("domain", "general")).lower().strip().replace(" ", "_")
        domain_mapping = {
            "math": "mathematics",
            "cs": "computer_science",
            "comp_sci": "computer_science",
            "bio": "biology",
            "chem": "chemistry",
            "phys": "physics",
        }
        raw_domain = domain_mapping.get(raw_domain, raw_domain)
        if raw_domain not in valid_domains:
            raw_domain = "general"
        data["domain"] = raw_domain

        # 3. Scenes
        raw_scenes = data.get("scenes", [])
        if not isinstance(raw_scenes, list) or not raw_scenes:
            raise ValueError("LLM plan contained no scenes array")

        # Map non-standard scene type aliases
        type_aliases = {
            "intro": SceneType.TITLE.value,
            "heading": SceneType.TITLE.value,
            "definition": SceneType.EXPLANATION.value,
            "overview": SceneType.EXPLANATION.value,
            "concept": SceneType.EXPLANATION.value,
            "example": SceneType.EXPLANATION.value,
            "equation": SceneType.FORMULA.value,
            "math": SceneType.FORMULA.value,
            "bullets": SceneType.BULLET_POINTS.value,
            "steps": SceneType.PROCESS.value,
            "workflow": SceneType.PROCESS.value,
            "flowchart": SceneType.PROCESS.value,
            "algorithm": SceneType.PROCESS.value,
            "stack": SceneType.HIERARCHY.value,
            "layers": SceneType.HIERARCHY.value,
            "summary": SceneType.CONCLUSION.value,
            "takeaway": SceneType.CONCLUSION.value,
            "outro": SceneType.CONCLUSION.value,
        }

        valid_scene_types = [st.value for st in SceneType]

        sanitized_scenes: List[Dict[str, Any]] = []
        for i, sc in enumerate(raw_scenes, start=1):
            if not isinstance(sc, dict):
                continue

            raw_type = str(sc.get("type", "explanation")).lower().strip()
            resolved_type = type_aliases.get(raw_type, raw_type)
            if resolved_type not in valid_scene_types:
                resolved_type = SceneType.EXPLANATION.value

            # Clean and ensure durations
            dur = sc.get("duration")
            try:
                dur = float(dur) if dur is not None else 5.0
            except (ValueError, TypeError):
                dur = 5.0
            dur = max(3.0, min(8.0, dur))

            scene_title = str(sc.get("title") or f"Scene {i}").strip()
            visual_engine = str(sc.get("visual_engine") or "manim").strip()

            item: Dict[str, Any] = {
                "id": i,
                "type": resolved_type,
                "duration": dur,
                "title": scene_title,
                "visual_engine": visual_engine,
            }

            # Optional / type-specific fields
            if sc.get("subtitle"):
                item["subtitle"] = str(sc["subtitle"]).strip()

            content = sc.get("content")
            if content:
                item["content"] = str(content).strip()

            # Formula handling
            if resolved_type == SceneType.FORMULA.value:
                formula_val = sc.get("formula") or sc.get("content") or "F = m * a"
                item["formula"] = str(formula_val).strip()
                breakdown = sc.get("formula_breakdown")
                if isinstance(breakdown, list) and breakdown:
                    item["formula_breakdown"] = [str(b).strip() for b in breakdown]
                else:
                    item["formula_breakdown"] = ["Core equation breakdown"]

            # Bullet points handling
            if resolved_type in (SceneType.BULLET_POINTS.value, SceneType.CONCEPT.value):
                bullets = sc.get("bullets")
                if isinstance(bullets, list) and bullets:
                    item["bullets"] = [str(b).strip() for b in bullets]
                elif content:
                    item["bullets"] = [content]
                else:
                    item["bullets"] = [f"Key aspect of {topic}"]

            # Process / steps handling
            if resolved_type in (SceneType.PROCESS.value, SceneType.CYCLE.value):
                steps = sc.get("steps")
                if isinstance(steps, list) and steps:
                    item["steps"] = [str(s).strip() for s in steps]
                elif content:
                    item["steps"] = [content]
                else:
                    item["steps"] = ["Stage 1: Input", "Stage 2: Process", "Stage 3: Output"]

            # Hierarchy handling
            if resolved_type == SceneType.HIERARCHY.value:
                layers = sc.get("layers") or sc.get("steps")
                if isinstance(layers, list) and layers:
                    item["layers"] = [str(l).strip() for l in layers]
                else:
                    item["layers"] = ["Layer 3: Top", "Layer 2: Middle", "Layer 1: Base"]

            # Content fallback for explanation and conclusion
            if resolved_type in (SceneType.EXPLANATION.value, SceneType.CONCLUSION.value):
                if not item.get("content"):
                    item["content"] = sc.get("subtitle") or f"Core concept of {topic}."

            sanitized_scenes.append(item)

        # Enforce that scene 1 is TITLE and last is CONCLUSION if not already
        if sanitized_scenes:
            if sanitized_scenes[0]["type"] != SceneType.TITLE.value:
                sanitized_scenes.insert(
                    0,
                    {
                        "id": 1,
                        "type": SceneType.TITLE.value,
                        "duration": 4.0,
                        "title": title,
                        "subtitle": f"Understanding {topic}",
                        "visual_engine": "manim",
                    },
                )
                # Re-index
                for idx, s in enumerate(sanitized_scenes, start=1):
                    s["id"] = idx

            if sanitized_scenes[-1]["type"] != SceneType.CONCLUSION.value:
                sanitized_scenes.append(
                    {
                        "id": len(sanitized_scenes) + 1,
                        "type": SceneType.CONCLUSION.value,
                        "duration": 4.0,
                        "title": "Key Takeaway",
                        "content": f"Mastering {topic} provides fundamental insight into {raw_domain}.",
                        "visual_engine": "manim",
                    }
                )

        # Cap total scenes to reasonable limit (between 4 and 8)
        if len(sanitized_scenes) > 8:
            # Keep title (first), conclusion (last), and intermediate scenes
            sanitized_scenes = [sanitized_scenes[0]] + sanitized_scenes[1:7] + [sanitized_scenes[-1]]
            for idx, s in enumerate(sanitized_scenes, start=1):
                s["id"] = idx

        total_dur = sum(s["duration"] for s in sanitized_scenes)
        data["target_duration"] = round(total_dur, 1)
        data["scenes"] = sanitized_scenes
        return data


# Global planner instance
llm_academic_planner = LLMAcademicPlanner()
