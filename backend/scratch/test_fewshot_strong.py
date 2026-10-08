"""
Test few-shot prompting with sentence-by-sentence pairs.
"""
import sys
import httpx
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

text = "Newton's Second Law of Motion states that force equals mass times acceleration, written as F = m * a."

sys_hi = (
    "You are a professional Hindi science translator. "
    "Translate the English science narration into standard Hindi (हिन्दी) in Devanagari script.\n"
    "Guidelines:\n"
    "- Keep equations unchanged (e.g. F = m * a).\n"
    "- Do not use Chinese characters, Latin characters, or slang.\n"
    "- Output ONLY the Hindi translation.\n\n"
    "Example 1:\n"
    "English: Newton's First Law states that an object remains at rest unless acted on by a force.\n"
    "Hindi: न्यूटन का पहला नियम कहता है कि कोई वस्तु तब तक विरामावस्था में रहती है जब तक कि उस पर कोई बल न लगाया जाए।\n\n"
    "Example 2:\n"
    "English: Acceleration is the rate of change of velocity with respect to time.\n"
    "Hindi: त्वरण समय के साथ वेग में परिवर्तन की दर है।"
)

user_hi = f"English: {text}\nHindi:"

payload_hi = {
    "model": "qwen2.5:3b",
    "prompt": user_hi,
    "system": sys_hi,
    "stream": False,
    "options": {"temperature": 0.1, "repeat_penalty": 1.25}
}

with httpx.Client(timeout=30.0) as client:
    res = client.post("http://127.0.0.1:11434/api/generate", json=payload_hi)
    print("Hindi FewShot:")
    print(res.json().get("response", ""))

sys_ta = (
    "You are a professional Tamil science translator. "
    "Translate the English science narration into standard Tamil (தமிழ்) in Tamil script.\n"
    "Guidelines:\n"
    "- Keep equations unchanged (e.g. F = m * a).\n"
    "- Do not use Chinese characters, Latin characters, or slang.\n"
    "- Output ONLY the Tamil translation.\n\n"
    "Example 1:\n"
    "English: Newton's First Law states that an object remains at rest unless acted on by a force.\n"
    "Tamil: ஒரு பொருளின் மீது விசை செயல்படாத வரை அது தன் ஓய்வு நிலையிலேயே இருக்கும் என்று நியூட்டனின் முதல் விதி கூறுகிறது.\n\n"
    "Example 2:\n"
    "English: Acceleration is the rate of change of velocity with respect to time.\n"
    "Tamil: முடுக்கம் என்பது காலத்தைப் பொறுத்து திசைவேகத்தில் ஏற்படும் மாற்ற விகிதமாகும்."
)

user_ta = f"English: {text}\nTamil:"

payload_ta = {
    "model": "qwen2.5:3b",
    "prompt": user_ta,
    "system": sys_ta,
    "stream": False,
    "options": {"temperature": 0.1, "repeat_penalty": 1.25}
}

with httpx.Client(timeout=30.0) as client:
    res = client.post("http://127.0.0.1:11434/api/generate", json=payload_ta)
    print("\nTamil FewShot:")
    print(res.json().get("response", ""))
