"""
Test prompt strategies for Qwen2.5 3B localization into Hindi and Tamil.
"""
import sys
import httpx
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

english_text = (
    "Understanding Newton's Second Law of Motion. "
    "The acceleration of an object depends on the net force acting upon it and the mass of the object. "
    "Mathematically, force equals mass times acceleration, written as F = m * a. "
    "In summary, a larger force creates a greater acceleration, while a larger mass requires more force."
)

def test_ollama(prompt, system_prompt="", options=None):
    payload = {
        "model": "qwen2.5:3b",
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": options or {"temperature": 0.3, "repeat_penalty": 1.2}
    }
    with httpx.Client(timeout=60.0) as client:
        res = client.post("http://127.0.0.1:11434/api/generate", json=payload)
        return res.json().get("response", "")

print("=== Strategy 1: Explicit Devanagari Hindi ===")
sys_hi = (
    "You are a professional Hindi translator and science educator. "
    "Translate the English educational narration into fluent, natural Hindi using Devanagari script (हिन्दी). "
    "Keep scientific symbols like F = m * a unchanged. "
    "Output ONLY the translated Hindi text in Devanagari. No English commentary, no intro."
)
p_hi = f"Translate the following educational text into clear Hindi:\n\n{english_text}"
res_hi = test_ollama(p_hi, sys_hi)
print("Result Hindi:\n", res_hi)

print("\n=== Strategy 1: Explicit Tamil with repeat_penalty ===")
sys_ta = (
    "You are a professional Tamil translator and science educator. "
    "Translate the English educational narration into natural, spoken Tamil script (தமிழ்). "
    "Translate accurately sentence by sentence. "
    "Keep scientific symbols like F = m * a unchanged. "
    "Do NOT repeat sentences. Output ONLY the translated Tamil text. No English commentary."
)
p_ta = f"Translate the following educational text into clear spoken Tamil:\n\n{english_text}"
res_ta = test_ollama(p_ta, sys_ta, options={"temperature": 0.3, "repeat_penalty": 1.3, "top_p": 0.9})
print("Result Tamil:\n", res_ta)
