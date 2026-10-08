"""
Test few-shot prompting for Qwen2.5 3B Hindi and Tamil localization.
"""
import sys
import httpx
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

english_text = (
    "Understanding Newton's Second Law of Motion. "
    "The acceleration of an object is directly proportional to the net force acting on it. "
    "And inversely proportional to its mass. "
    "Mathematically, this is expressed as F equals m times a. "
    "In summary, force causes acceleration, while mass resists it."
)

def test_ollama(prompt, system_prompt="", options=None):
    payload = {
        "model": "qwen2.5:3b",
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": options or {"temperature": 0.1, "repeat_penalty": 1.25}
    }
    with httpx.Client(timeout=60.0) as client:
        res = client.post("http://127.0.0.1:11434/api/generate", json=payload)
        return res.json().get("response", "")

sys_hi = """You are an educational translator. Translate English into clear, natural Hindi (Devanagari script).
Rules:
- Translate meaning accurately into standard Hindi.
- Keep formulas and equations as-is (e.g., F = m * a, F = ma).
- Do not repeat sentences.
- Do not add any English commentary, preamble, or notes.
- Output ONLY pure Hindi text.

Example:
English: Energy cannot be created or destroyed. It only transforms from one form to another.
Hindi: ऊर्जा को न तो बनाया जा सकता है और न ही नष्ट किया जा सकता है। यह केवल एक रूप से दूसरे रूप में परिवर्तित होती है।"""

prompt_hi = f"English:\n{english_text}\nHindi:"

print("=== Testing Hindi Few-Shot ===")
res_hi = test_ollama(prompt_hi, sys_hi)
print("Result Hindi:\n", res_hi)

sys_ta = """You are an educational translator. Translate English into clear, natural Tamil (தமிழ்).
Rules:
- Translate meaning accurately into standard spoken Tamil script.
- Keep formulas and equations as-is (e.g., F = m * a, F = ma).
- Do not repeat sentences.
- Do not use Chinese or Hindi characters. Use only Tamil script and English math symbols.
- Do not add preamble or explanations.
- Output ONLY pure Tamil text.

Example:
English: Energy cannot be created or destroyed. It only transforms from one form to another.
Tamil: ஆற்றலை உருவாக்கவோ அழிக்கவோ முடியாது. அது ஒரு வடிவத்திலிருந்து மற்றொரு வடிவத்திற்கு மாறுகிறது."""

prompt_ta = f"English:\n{english_text}\nTamil:"

print("\n=== Testing Tamil Few-Shot ===")
res_ta = test_ollama(prompt_ta, sys_ta)
print("Result Tamil:\n", res_ta)
