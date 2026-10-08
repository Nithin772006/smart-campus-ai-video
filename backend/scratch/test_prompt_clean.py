"""
Test clean educational translation prompt on Qwen2.5 3B.
"""
import sys
import httpx
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

text = (
    "Understanding Newton's Second Law of Motion. "
    "The acceleration of an object depends on the net force acting upon it and the mass of the object. "
    "Mathematically, this is expressed as F equals m times a. "
    "In summary, force causes acceleration, while mass resists change in motion."
)

def test_translate(text, lang_name, script_name):
    sys_prompt = (
        f"You are a university science educator translating video narration into {lang_name}.\n"
        f"Translate the text into natural spoken {lang_name} using {script_name} script.\n"
        f"Rules:\n"
        f"1. Use pure {script_name} script for words.\n"
        f"2. Keep math formulas unchanged (e.g., F = m * a).\n"
        f"3. Do NOT repeat phrases or sentences.\n"
        f"4. Output ONLY the {lang_name} translation. No greetings, no English explanations."
    )
    user_prompt = f"Translate the following educational narration into {lang_name}:\n\n{text}"
    payload = {
        "model": "qwen2.5:3b",
        "prompt": user_prompt,
        "system": sys_prompt,
        "stream": False,
        "options": {
            "temperature": 0.15,
            "repeat_penalty": 1.3,
            "top_p": 0.85
        }
    }
    with httpx.Client(timeout=40.0) as client:
        res = client.post("http://127.0.0.1:11434/api/generate", json=payload)
        return res.json().get("response", "").strip()

print("--- Hindi Result ---")
hi = test_translate(text, "Hindi", "Devanagari")
print(hi)

print("\n--- Tamil Result ---")
ta = test_translate(text, "Tamil", "Tamil")
print(ta)
