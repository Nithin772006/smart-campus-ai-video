"""
Debug script to test narration localization with local Qwen2.5 3B via Ollama.
"""
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from app.services.narration_localizer import narration_localizer
from app.services.ollama_service import ollama_service

test_english_text = (
    "Understanding Newton's Second Law of Motion. "
    "The acceleration of an object is directly proportional to the net force acting on it, "
    "and inversely proportional to its mass. "
    "Mathematically, this is expressed as F equals m times a. "
    "To visualize this, remember that force causes change, while mass resists it."
)

print(f"Ollama available: {ollama_service.is_available()}")
print("\n--- Testing Hindi Localization ---")
hindi_res = narration_localizer.localize(test_english_text, target_language="hi")
print(f"Hindi Result:\n{hindi_res}")

print("\n--- Testing Tamil Localization ---")
tamil_res = narration_localizer.localize(test_english_text, target_language="ta")
print(f"Tamil Result:\n{tamil_res}")
