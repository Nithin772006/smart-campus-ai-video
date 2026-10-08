"""
Test Ollama /api/chat with Qwen2.5 3B for Hindi and Tamil.
"""
import sys
import httpx
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

text = "Newton's Second Law of Motion states that force equals mass times acceleration."

def test_chat(messages, options=None):
    payload = {
        "model": "qwen2.5:3b",
        "messages": messages,
        "stream": False,
        "options": options or {"temperature": 0.2}
    }
    with httpx.Client(timeout=30.0) as client:
        res = client.post("http://127.0.0.1:11434/api/chat", json=payload)
        return res.json().get("message", {}).get("content", "")

# Test Hindi
msgs_hi = [
    {"role": "system", "content": "You are a professional translator. Translate into Hindi. Keep equations as F = m * a. Output only the Hindi translation."},
    {"role": "user", "content": f"Translate to Hindi:\n{text}"}
]
print("Chat Hindi:\n", test_chat(msgs_hi))

# Test Tamil
msgs_ta = [
    {"role": "system", "content": "You are a professional translator. Translate into Tamil. Keep equations as F = m * a. Output only the Tamil translation."},
    {"role": "user", "content": f"Translate to Tamil:\n{text}"}
]
print("\nChat Tamil:\n", test_chat(msgs_ta))
