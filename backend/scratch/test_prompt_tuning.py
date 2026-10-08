"""
Test prompt tuning with strict script constraints for Qwen2.5 3B.
"""
import sys
import httpx
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

text = (
    "Today we will learn Newton's Second Law of Motion. "
    "The acceleration of an object is directly proportional to the net force acting on it. "
    "And inversely proportional to its mass. "
    "Mathematically, force equals mass times acceleration, written as F = m * a."
)

def test_chat(messages, options=None):
    payload = {
        "model": "qwen2.5:3b",
        "messages": messages,
        "stream": False,
        "options": options or {"temperature": 0.2, "repeat_penalty": 1.25}
    }
    with httpx.Client(timeout=40.0) as client:
        res = client.post("http://127.0.0.1:11434/api/chat", json=payload)
        return res.json().get("message", {}).get("content", "")

# Hindi with strict Devanagari constraint
sys_hi = (
    "You are an educational translator. Translate the text into Hindi.\n"
    "CRITICAL RULES:\n"
    "1. Write strictly in Hindi using Devanagari script (हिन्दी).\n"
    "2. Do NOT output Chinese characters or English words (except formulas like F = m * a).\n"
    "3. Do NOT repeat phrases or sentences.\n"
    "4. Output only the Hindi translation without explanation."
)
msgs_hi = [
    {"role": "system", "content": sys_hi},
    {"role": "user", "content": f"Translate this text into Hindi:\n{text}"}
]
print("=== Hindi Strict ===")
print(test_chat(msgs_hi))

# Tamil with strict Tamil constraint
sys_ta = (
    "You are an educational translator. Translate the text into Tamil.\n"
    "CRITICAL RULES:\n"
    "1. Write strictly in Tamil using Tamil script (தமிழ்).\n"
    "2. Do NOT output Chinese, Hindi, or foreign characters.\n"
    "3. Do NOT repeat phrases or sentences.\n"
    "4. Keep equations like F = m * a as English math notation.\n"
    "5. Output only the Tamil translation without explanation."
)
msgs_ta = [
    {"role": "system", "content": sys_ta},
    {"role": "user", "content": f"Translate this text into Tamil:\n{text}"}
]
print("\n=== Tamil Strict ===")
print(test_chat(msgs_ta))
