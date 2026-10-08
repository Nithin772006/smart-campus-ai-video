"""
Test scene-by-scene translation vs full-paragraph translation with Qwen2.5 3B.
"""
import sys
import httpx
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

scenes = [
    "Understanding Newton's Second Law of Motion.",
    "The acceleration of an object depends on the net force acting upon it and the mass of the object.",
    "Mathematically, this is expressed as F equals m times a.",
    "A larger force produces greater acceleration, while a larger mass requires more force.",
    "In summary, Newton's second law explains how force, mass, and acceleration are related."
]

def translate_snippet(text, lang_name, lang_code, script_name):
    sys_prompt = (
        f"You are a professional educational translator.\n"
        f"Translate the English text into natural, accurate spoken {lang_name} ({script_name}).\n"
        f"Rules:\n"
        f"1. Output ONLY the {lang_name} translation in {script_name} script.\n"
        f"2. Keep mathematical expressions like 'F = m * a' unchanged.\n"
        f"3. Do not add intro, explanations, or commentary.\n"
        f"4. Do not repeat sentences."
    )
    prompt = f"English: {text}\n{lang_name}:"
    payload = {
        "model": "qwen2.5:3b",
        "prompt": prompt,
        "system": sys_prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "repeat_penalty": 1.25,
        }
    }
    with httpx.Client(timeout=30.0) as client:
        res = client.post("http://127.0.0.1:11434/api/generate", json=payload)
        return res.json().get("response", "").strip()

print("--- Testing Scene-by-Scene Hindi ---")
hindi_results = []
for i, s in enumerate(scenes):
    hi = translate_snippet(s, "Hindi", "hi", "Devanagari")
    print(f"Scene {i+1}: {hi}")
    hindi_results.append(hi)

print("\n--- Testing Scene-by-Scene Tamil ---")
tamil_results = []
for i, s in enumerate(scenes):
    ta = translate_snippet(s, "Tamil", "ta", "Tamil")
    print(f"Scene {i+1}: {ta}")
    tamil_results.append(ta)
