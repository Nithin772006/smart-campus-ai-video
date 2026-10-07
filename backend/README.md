# SmartCampus AI Video Generation Microservice

Backend microservice for the standalone SmartCampus AI Video Generation system. This service synthesizes educational, formula-rich, and instructional video lectures from text scripts, topic prompts, and curriculum documents.

---

## Architecture & Pipeline

### LLM-Powered Video Planning Pipeline (Task 3)

```
User Academic Question / Topic
              ↓
    LLMAcademicPlanner
              ↓
  Local Qwen2.5 3B via Ollama
              ↓
   JSON Schema Validation
              ↓
    EducationalVideoPlan
              ↓
 Dynamic Manim Scene Renderer
              ↓
     FFmpeg Concat
              ↓
         FINAL MP4
```

#### Fallback Mechanism
```
Qwen/Ollama Unavailable, Timeout, or Invalid Schema
                      ↓
        [LLM] Fallback Triggered
                      ↓
          RuleBasedAcademicPlanner
                      ↓
            EducationalVideoPlan
                      ↓
         Dynamic Manim Renderer
                      ↓
                  FINAL MP4
```

---

## Ollama & Qwen2.5 3B Setup

All LLM planning runs 100% locally using Ollama and Qwen2.5 3B. No external or cloud APIs are required.

### 1. Install Ollama
Download and install Ollama from [https://ollama.com](https://ollama.com).

### 2. Pull the Qwen2.5 3B Model
```powershell
ollama pull qwen2.5:3b
```

### 3. Verify Ollama is Running
```powershell
ollama list
```
Ensure `qwen2.5:3b` is listed. Ollama runs on `http://127.0.0.1:11434` by default.

### 4. Configuration Environment Variables
Add to `.env` (optional, sensible defaults already built-in):
```env
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_TIMEOUT=60.0
```

---

## Target Hardware Specifications

- **OS**: Windows 11
- **Python**: 3.10.11
- **GPU**: NVIDIA GeForce RTX 2050 (4 GB VRAM)
- **CUDA Runtime**: 12.6
- **PyTorch**: 2.9.1+cu126 (CUDA enabled)

---

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entrypoint & routing
│   ├── config.py            # Pydantic settings & Ollama / directory config
│   ├── api/                 # Modular API routers
│   │   ├── health.py        # System health checks
│   │   ├── video.py         # LLM topic, dynamic Manim, and video endpoints
│   │   ├── audio.py         # IndicF5 audio synthesis endpoints
│   │   └── subtitle.py      # Whisper subtitle generation endpoints
│   ├── services/            # Engine service wrappers
│   │   ├── ollama_service.py# HTTP client for local Ollama API
│   │   ├── llm_planner.py   # LLMAcademicPlanner with Qwen & fallback
│   │   ├── scene_planner.py # AcademicPlanner base & RuleBasedAcademicPlanner
│   │   ├── manim_service.py # Dynamic Manim renderer & FFmpeg stitcher
│   │   ├── manim_components.py # Manim vector visual scenes
│   │   ├── ffmpeg_service.py# FFmpeg clip concatenation
│   │   ├── ltx_service.py   # LTX-Video generator (future)
│   │   ├── indicf5_service.py # IndicF5 TTS (future)
│   │   └── whisper_service.py # faster-whisper transcription (future)
│   ├── schemas/             # Pydantic request/response models
│   │   ├── scene.py         # EducationalVideoPlan, ScenePlanItem, SceneType
│   │   └── video.py         # LLMTopicRequest, LLMTopicResponse, etc.
│   └── utils/               # File management, timing, benchmark utilities
├── generated/               # Media output artifact storage
│   ├── videos/
│   ├── audio/
│   ├── subtitles/
│   └── scenes/
├── benchmarks/              # Measured render metrics (results.csv)
├── tests/                   # Test suites
│   ├── test_ollama_planner.py # Tests for Ollama, LLM planner, and fallback
│   ├── test_dynamic_manim.py  # Tests for dynamic Manim scene generation
│   ├── test_api.py            # FastAPI route tests
│   └── test_health.py         # Healthcheck tests
├── requirements.txt         # Production backend dependencies
└── .env.example             # Environment variable template
```

---

## API Endpoints

| Method | Endpoint | Description | Status |
|---|---|---|---|
| `GET` | `/` | API status information | Active |
| `GET` | `/health` | Top-level health check | Active |
| `GET` | `/api/health` | API router health check | Active |
| `POST` | `/api/video/llm/topic` | **Generate video via Qwen2.5 3B LLM plan + Manim** | **Active (Task 3)** |
| `POST` | `/api/video/manim/topic` | Dynamic rule-based topic video generation | Active (Task 2) |
| `POST` | `/api/video/manim` | Single-scene Manim animation (Newton's 2nd Law) | Active (Task 2) |
| `POST` | `/api/video/script-to-video` | Generate video from scene script | Planned (Milestone 2) |
| `POST` | `/api/video/topic-to-video` | Generate video from topic prompt | Planned (Milestone 2) |
| `POST` | `/api/audio/generate` | Synthesize speech from text | Planned (Milestone 3) |
| `POST` | `/api/subtitle/generate` | Transcribe audio into subtitles | Planned (Milestone 4) |

---

## Running Locally

### 1. Start Ollama (in a separate terminal if not already running as service)
```powershell
ollama serve
```

### 2. Activate Virtual Environment
```powershell
cd backend
.venv\Scripts\activate
```

### 3. Start FastAPI Server
```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 4. Interactive Documentation
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Example API Request

### LLM-Powered Topic Video Generation (`POST /api/video/llm/topic`)

```bash
curl -X POST "http://127.0.0.1:8000/api/video/llm/topic" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Explain Newton'\''s Second Law",
    "quality": "medium_quality"
  }'
```

### Response Example
```json
{
  "success": true,
  "topic": "Newton's Second Law of Motion",
  "video_path": "generated/scenes/newtons_second_law_of_motion/newtons_second_law_of_motion.mp4",
  "duration_seconds": 20.0,
  "generation_time_seconds": 15.3,
  "scene_count": 4,
  "output_size_mb": 0.82,
  "plan": {
    "topic": "Newton's Second Law of Motion",
    "title": "Understanding Newton's Second Law of Motion",
    "level": "beginner",
    "domain": "physics",
    "summary": "Explains how force, mass, and acceleration relate.",
    "target_duration": 20.0,
    "scenes": [
      {
        "id": 1,
        "type": "title",
        "duration": 4.0,
        "title": "Newton's Second Law of Motion",
        "subtitle": "Classical Mechanics",
        "visual_engine": "manim"
      },
      {
        "id": 2,
        "type": "explanation",
        "duration": 6.0,
        "title": "Core Law",
        "content": "Acceleration is proportional to net force and inversely proportional to mass.",
        "visual_engine": "manim"
      },
      {
        "id": 3,
        "type": "formula",
        "duration": 6.0,
        "title": "Mathematical Formula",
        "formula": "F = m · a",
        "formula_breakdown": ["F : Net Force (N)", "m : Mass (kg)", "a : Acceleration (m/s²)"],
        "visual_engine": "manim"
      },
      {
        "id": 4,
        "type": "conclusion",
        "duration": 4.0,
        "title": "Key Takeaway",
        "content": "F = ma is fundamental to engineering and physics.",
        "visual_engine": "manim"
      }
    ]
  },
  "used_fallback": false,
  "planner": "ollama/qwen2.5:3b"
}
```

---

## Tested Academic Topics

The following subjects have been verified through local Qwen2.5 3B planning and Manim rendering:

1. **Newton's Second Law** — Physics (Force, mass, acceleration equation & dynamics)
2. **Photosynthesis** — Biology (Chloroplast light reaction process)
3. **Binary Search** — Computer Science (Divide-and-conquer algorithm)
4. **Gradient Descent** — Computer Science / AI (Optimization and loss reduction)
5. **TCP Three-Way Handshake** — Computer Science / Networking (SYN, SYN-ACK, ACK connection establishment)

---

## Running the Test Suite

```powershell
cd backend
.venv\Scripts\activate

# Run Ollama LLM planner and integration tests (including real Qwen and Manim render):
python tests/test_ollama_planner.py

# Run API endpoint tests:
python tests/test_api.py

# Run Dynamic Manim rendering tests:
python tests/test_dynamic_manim.py

# Run Health tests:
python tests/test_health.py
```
