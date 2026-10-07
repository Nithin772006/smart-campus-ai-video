import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "SmartCampus AI Video API"
    assert data["status"] == "running"

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "smartcampus-ai-video"

def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "smartcampus-ai-video"

def test_video_script_to_video():
    payload = {
        "script": "Linear regression models the relationship between dependent and independent variables.",
        "language": "en",
        "title": "Linear Regression Basics"
    }
    response = client.post("/api/video/script-to-video", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_implemented"
    assert "Script-to-video" in data["message"]

def test_video_topic_to_video():
    payload = {
        "topic": "Newton's First Law of Motion",
        "language": "en",
        "target_duration": 30.0
    }
    response = client.post("/api/video/topic-to-video", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_implemented"
    assert "Topic-to-video" in data["message"]

def test_audio_generate():
    payload = {
        "text": "Welcome to class.",
        "language": "en",
        "voice": "default"
    }
    response = client.post("/api/audio/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_implemented"
    assert "Audio generation" in data["message"]

def test_subtitle_generate():
    payload = {
        "audio_path": "generated/audio/sample.wav",
        "language": "en"
    }
    response = client.post("/api/subtitle/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_implemented"
    assert "Subtitle generation" in data["message"]

def test_video_manim_unsupported_topic():
    payload = {
        "topic": "Quantum Mechanics"
    }
    response = client.post("/api/video/manim", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "not supported" in data["detail"].lower()

def test_video_manim_success():
    payload = {
        "topic": "Newton's Second Law"
    }
    response = client.post("/api/video/manim", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["topic"] == "Newton's Second Law"
    assert "newton_second_law.mp4" in data["video_path"]
    assert data["duration_seconds"] > 0
    assert data["generation_time_seconds"] > 0
    assert data["output_size_mb"] > 0

def test_video_llm_topic_empty_prompt():
    response = client.post("/api/video/llm/topic", json={})
    assert response.status_code == 400

def test_video_llm_topic_success():
    payload = {
        "topic": "Explain Newton's Second Law",
        "quality": "low_quality"
    }
    response = client.post("/api/video/llm/topic", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Newton" in data["topic"]
    assert data["video_path"]
    assert data["duration_seconds"] > 0
    assert data["generation_time_seconds"] > 0
    assert "planner" in data
    assert "plan" in data

def test_docs_accessible():
    response = client.get("/docs")
    assert response.status_code == 200

if __name__ == "__main__":
    test_root()
    test_health()
    test_api_health()
    test_video_script_to_video()
    test_video_topic_to_video()
    test_audio_generate()
    test_subtitle_generate()
    test_video_manim_unsupported_topic()
    test_video_manim_success()
    test_video_llm_topic_empty_prompt()
    test_video_llm_topic_success()
    test_docs_accessible()
    print("ALL API TESTS PASSED SUCCESSFULLY!")


