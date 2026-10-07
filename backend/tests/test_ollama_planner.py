"""
Comprehensive test suite for Ollama Service, LLM Academic Planner, and Manim rendering pipeline.
Includes unit tests (with mocks for offline/error cases) and real integration tests with Qwen2.5 3B.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import httpx
from app.config import settings
from app.schemas.scene import SceneType, AcademicDomain, EducationalVideoPlan
from app.schemas.video import LLMTopicRequest, LLMTopicResponse
from app.services.ollama_service import (
    OllamaService,
    OllamaConnectionError,
    OllamaTimeoutError,
    OllamaResponseError,
    ollama_service,
)
from app.services.llm_planner import LLMAcademicPlanner, llm_academic_planner
from app.services.manim_service import (
    _build_dynamic_scene_script_content,
    render_educational_plan_to_video,
)


class TestOllamaPlanner(unittest.TestCase):

    # 1. Ollama service configuration
    def test_01_ollama_service_configuration(self):
        service = OllamaService()
        self.assertEqual(service.base_url, settings.OLLAMA_BASE_URL.rstrip("/"))
        self.assertEqual(service.model, settings.OLLAMA_MODEL)
        self.assertEqual(service.timeout, settings.OLLAMA_TIMEOUT)

        # Custom config
        custom = OllamaService(base_url="http://localhost:12345", model="custom:model", timeout=15.0)
        self.assertEqual(custom.base_url, "http://localhost:12345")
        self.assertEqual(custom.model, "custom:model")
        self.assertEqual(custom.timeout, 15.0)
        print("  [PASS] Test 1: Ollama service configuration verified")

    # 2. Ollama connection failure
    @patch("httpx.Client.post")
    def test_02_ollama_connection_failure(self, mock_post):
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        service = OllamaService(base_url="http://127.0.0.1:99999")
        with self.assertRaises(OllamaConnectionError):
            service.generate("Test prompt")
        print("  [PASS] Test 2: Ollama connection failure correctly raises OllamaConnectionError")

    # 3. Ollama timeout
    @patch("httpx.Client.post")
    def test_03_ollama_timeout(self, mock_post):
        mock_post.side_effect = httpx.TimeoutException("Timed out")
        service = OllamaService()
        with self.assertRaises(OllamaTimeoutError):
            service.generate("Test prompt")
        print("  [PASS] Test 3: Ollama timeout correctly raises OllamaTimeoutError")

    # 4. Valid LLM JSON
    @patch("app.services.ollama_service.OllamaService.generate")
    def test_04_valid_llm_json(self, mock_generate):
        mock_generate.return_value = """{
            "topic": "Gravity",
            "title": "Understanding Universal Gravitation",
            "level": "beginner",
            "domain": "physics",
            "summary": "Gravitational attraction between masses.",
            "target_duration": 20.0,
            "scenes": [
                {
                    "id": 1,
                    "type": "title",
                    "duration": 4.0,
                    "title": "Universal Gravitation",
                    "subtitle": "Classical Mechanics",
                    "visual_engine": "manim"
                },
                {
                    "id": 2,
                    "type": "explanation",
                    "duration": 6.0,
                    "title": "Core Concept",
                    "content": "Every particle attracts every other particle with a force proportional to the product of their masses.",
                    "visual_engine": "manim"
                },
                {
                    "id": 3,
                    "type": "formula",
                    "duration": 6.0,
                    "title": "Newton's Gravitational Law",
                    "formula": "F = G * (m1 * m2) / r^2",
                    "formula_breakdown": ["F : Force", "G : Constant", "m : Masses", "r : Distance"],
                    "visual_engine": "manim"
                },
                {
                    "id": 4,
                    "type": "conclusion",
                    "duration": 4.0,
                    "title": "Summary",
                    "content": "Gravity governs the orbit of planets and cosmic structures.",
                    "visual_engine": "manim"
                }
            ]
        }"""
        planner = LLMAcademicPlanner()
        plan, used_fb, planner_name = planner.plan_with_fallback("Explain Gravity")
        self.assertFalse(used_fb)
        self.assertIn("ollama", planner_name)
        self.assertEqual(plan.topic, "Gravity")
        self.assertEqual(plan.domain, AcademicDomain.PHYSICS)
        self.assertEqual(len(plan.scenes), 4)
        print("  [PASS] Test 4: Valid LLM JSON parses cleanly into EducationalVideoPlan")

    # 5. Invalid JSON with retry and fallback
    @patch("app.services.ollama_service.OllamaService.generate")
    def test_05_invalid_json_fallback(self, mock_generate):
        # Always return gibberish
        mock_generate.return_value = "NOT VALID JSON AT ALL"
        planner = LLMAcademicPlanner()
        plan, used_fb, planner_name = planner.plan_with_fallback("Explain Photosynthesis")
        self.assertTrue(used_fb)
        self.assertEqual(planner_name, "rule_based")
        self.assertIn("Photosynthesis", plan.topic)
        print("  [PASS] Test 5: Malformed JSON triggers fallback to RuleBasedAcademicPlanner")

    # 6. Pydantic validation failure retry
    @patch("app.services.ollama_service.OllamaService.generate")
    def test_06_validation_failure_and_safe_retry(self, mock_generate):
        # First attempt returns invalid data (empty scenes array)
        # Second attempt (retry) returns valid data
        valid_response = """{
            "topic": "Entropy",
            "title": "Understanding Entropy",
            "level": "intermediate",
            "domain": "physics",
            "summary": "Measure of molecular disorder.",
            "target_duration": 18.0,
            "scenes": [
                {"id": 1, "type": "title", "title": "Entropy", "duration": 4.0},
                {"id": 2, "type": "explanation", "title": "Definition", "content": "Measure of thermal energy unavailable for work.", "duration": 6.0},
                {"id": 3, "type": "conclusion", "title": "Takeaway", "content": "Entropy of an isolated system always increases.", "duration": 4.0}
            ]
        }"""
        mock_generate.side_effect = ['{"topic": "Entropy", "scenes": []}', valid_response]

        planner = LLMAcademicPlanner()
        plan, used_fb, planner_name = planner.plan_with_fallback("Explain Entropy")
        self.assertFalse(used_fb)
        self.assertEqual(plan.topic, "Entropy")
        self.assertEqual(len(plan.scenes), 3)
        self.assertEqual(mock_generate.call_count, 2)
        print("  [PASS] Test 6: Validation failure successfully recovered via retry prompt")

    # 7. Rule-based fallback when Ollama is completely offline
    def test_07_offline_ollama_fallback(self):
        offline_service = OllamaService(base_url="http://127.0.0.1:99999", timeout=1.0)
        planner = LLMAcademicPlanner(ollama=offline_service)
        plan, used_fb, planner_name = planner.plan_with_fallback("Explain Binary Search")
        self.assertTrue(used_fb)
        self.assertEqual(planner_name, "rule_based")
        self.assertEqual(plan.topic, "Binary Search")
        self.assertGreaterEqual(len(plan.scenes), 4)
        print("  [PASS] Test 7: Offline Ollama server gracefully triggers rule-based fallback")

    # 8. Real Ollama Planning for all 5 required academic topics
    def test_08_real_qwen_planning_5_topics(self):
        if not ollama_service.is_available():
            self.skipTest("Local Ollama server is not running with qwen2.5:3b")

        test_topics = [
            "Explain Newton's Second Law",
            "How does photosynthesis work?",
            "Explain binary search",
            "Explain gradient descent",
            "Explain TCP three-way handshake",
        ]

        valid_types = {st.value for st in SceneType}

        for topic in test_topics:
            plan, used_fb, planner_name = llm_academic_planner.plan_with_fallback(topic)
            self.assertFalse(used_fb, f"Expected real LLM generation for '{topic}', got fallback")
            self.assertIn("qwen", planner_name)
            self.assertIsInstance(plan, EducationalVideoPlan)
            self.assertGreaterEqual(len(plan.scenes), 3)
            self.assertLessEqual(len(plan.scenes), 9)
            self.assertEqual(plan.scenes[0].type, SceneType.TITLE)
            self.assertEqual(plan.scenes[-1].type, SceneType.CONCLUSION)

            # Verify every scene type is officially supported
            for sc in plan.scenes:
                self.assertIn(sc.type.value, valid_types, f"Unsupported scene type: {sc.type}")

            # Verify script generation compiles into valid python
            script_code = _build_dynamic_scene_script_content(plan)
            self.assertIn("class Scene_01_Title", script_code)
            compile(script_code, "<dynamic_script>", "exec")

            print(f"  [PASS] Real Qwen: '{topic}' -> {plan.title} ({plan.domain.value}), {len(plan.scenes)} scenes, {plan.target_duration}s")

    # 9. Real End-to-End Render: Qwen Plan -> Manim CLI -> Concatenation -> MP4
    def test_09_real_end_to_end_render(self):
        if not ollama_service.is_available():
            self.skipTest("Local Ollama server is not running with qwen2.5:3b")

        question = "Explain binary search"
        plan, used_fb, planner_name = llm_academic_planner.plan_with_fallback(question)
        self.assertFalse(used_fb)

        # Render with low_quality for fast test execution
        result = render_educational_plan_to_video(
            plan=plan,
            question=question,
            quality="low_quality",
        )

        self.assertTrue(result["success"])
        self.assertGreater(result["duration_seconds"], 0)
        self.assertGreater(result["generation_time_seconds"], 0)
        self.assertGreater(result["scene_count"], 0)

        video_file = settings.BASE_DIR / result["video_path"] if not Path(result["video_path"]).is_absolute() else Path(result["video_path"])
        self.assertTrue(video_file.exists(), f"Output MP4 does not exist: {video_file}")
        self.assertGreater(video_file.stat().st_size, 0)
        print(f"  [PASS] Test 9: End-to-End video generated: {video_file.name} ({result['duration_seconds']}s, {result['generation_time_seconds']}s render time)")


if __name__ == "__main__":
    unittest.main()
