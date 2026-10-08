# SmartCampus AI Video Generation Pipeline

An AI-driven video synthesis pipeline designed for campus educational content, combining local LLM planning (Qwen2.5 3B via Ollama), programmatic educational animations (Manim), generative video (LTX-Video), Indic voice synthesis (IndicF5 TTS), speech transcription (Whisper), and media assembly (FFmpeg).

## Architecture Overview

```
smartcampus-ai-video/
├── backend/                         ← FastAPI Backend & AI Services
│   ├── app/
│   │   ├── main.py                  ← FastAPI entry point
│   │   ├── api/                     ← REST API endpoints (health, video, audio, subtitle)
│   │   ├── services/                ← Service layer (Ollama, LLM Planner, Manim, FFmpeg)
│   │   ├── pipelines/               ← High-level video generation pipelines
│   │   ├── schemas/                 ← Pydantic request & response models
│   │   ├── utils/                   ← Utilities for IO, timing, and benchmarking
│   │   └── config.py                ← Application configuration & environment settings
│   ├── models/                      ← Model checkpoints (LTX-Video, IndicF5)
│   ├── generated/                   ← Output directory for media artifacts
│   ├── tests/                       ← Backend tests (unit, integration, real Qwen & Manim)
│   ├── requirements.txt             ← Python dependencies
│   └── .env.example                 ← Backend environment configuration template
├── frontend/                        ← Testing Web UI
├── benchmarks/                      ← Pipeline performance metrics & results.csv
└── scripts/                         ← Helper automation & model download scripts
```

## Planning & Video Pipeline

```
User Academic Question
          ↓
  Local Qwen2.5 3B (Ollama)   ──[Fallback if offline/invalid]──>  RuleBasedAcademicPlanner
          ↓                                                                   ↓
EducationalVideoPlan JSON <───────────────────────────────────────────────────┘
          ↓
Dynamic Manim Scene Renderer
          ↓
       FFmpeg
          ↓
      Final MP4
```

## Quick Start

### 1. Local LLM Setup (Ollama + Qwen2.5 3B)
```bash
# 1. Install Ollama from https://ollama.com
# 2. Pull local model:
ollama pull qwen2.5:3b

# 3. Ensure Ollama service is running:
ollama list
```

### 2. Backend Setup
```bash
cd backend
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 4. Run Backend Tests
```bash
cd backend
.venv\Scripts\activate

# Run Ollama LLM and integration tests:
python tests/test_ollama_planner.py

# Run IndicF5 TTS tests:
pytest tests/test_indicf5.py -v

# Run faster-whisper Subtitle & Timestamp tests:
pytest tests/test_whisper.py -v

# Run FFmpeg Video Composition tests:
pytest tests/test_ffmpeg.py -v

# Run API endpoint tests:
python tests/test_api.py
```

### 5. IndicF5 Local TTS (Task 5)
- **POST `/api/audio/tts`**: Accepts an `EducationalVideoPlan` and synthesizes spoken WAV voiceover at `generated/audio/<topic_slug>/narration.wav`.
- **POST `/api/audio/test`**: Directly synthesizes arbitrary text to WAV.

### 6. faster-whisper Subtitles & Timestamps (Task 6)
- **POST `/api/subtitle/transcribe`**: Transcribes WAV voiceover using local faster-whisper on CUDA into `subtitles.srt`, `subtitles.vtt`, and `transcription.json` under `generated/subtitles/<topic_slug>/`.
- **POST `/api/subtitle/test`**: Directly test transcription on any audio file.
- **Hardware Optimization**: Configured with `base` model (~140MB) and `float16` precision on NVIDIA RTX 2050 (4 GB VRAM), using VAD filtering and CPU fallback.

### 7. FFmpeg Final Video Composition (Task 7)
- **POST `/api/video/compose`**: Composes Manim visual video, IndicF5 voiceover, and burned subtitles into a final browser-ready H.264/AAC MP4.
- **POST `/api/video/full`**: Complete single-endpoint orchestration: Qwen2.5 3B → EducationalVideoPlan → Manim → IndicF5 → faster-whisper → FFmpeg → Final MP4.
- **Duration Synchronization**: Automatically aligns durations via `tpad` frame-hold or `apad` silence padding.

### 8. AI Teacher / Talking Avatar Layer (Task 8)
- **POST `/api/avatar/preview`**: Generates a 10s preview clip using canonical `teacher.png` and existing IndicF5 narration.
- **GET `/api/avatar/character`**: Retrieves canonical teacher metadata and layout rules.
- **Provider Architecture**: `AvatarProvider` abstraction with fallback overlay generator and MuseTalk-ready interfaces.
- **Full Video Pipeline Extension**: Optional `character: true` and `character_position: "auto" | "left" | "right"` parameters on `POST /api/video/full`.

### 9. Hugging Face Inference Providers Cloud Video (Task 9A Proof of Concept)
- **GET `/api/video/cloud/status`**: Reports configuration and availability status of cloud video provider.
- **POST `/api/video/cloud/generate`**: Generates isolated educational AI video scenes via Hugging Face Inference Providers (e.g. `Wan-AI/Wan2.2-TI2V-5B` via `fal-ai`).
- **Isolation**: Standalone proof of concept. Not yet tied to Qwen/Manim/FFmpeg pipelines.

### 10. Visual Scene Planner & Scene Router (Task 9B)
- **POST `/api/video/plan`**: Visual-first scene planner and deterministic router. Produces complete video production plans mapping scenes to Manim, Cloud Video, Avatar, or Mixed without rendering media.
- **Pedagogical Engine Allocations**: Guarantees equations and coordinate graphs use Manim vector rendering; routes cinematic visual metaphors to Cloud Video and lecture milestones to the AI Teacher.

### 11. ElevenLabs Multilingual TTS (Task 9G-A)
- **POST `/api/audio/elevenlabs`**: Multilingual speech synthesis with character-level timestamps (`en`, `ta`, `hi`). Saves MP3 and transcode WAV to `generated/audio/<topic_slug>/elevenlabs/`.
- **GET `/api/audio/elevenlabs/voices`**: Safely retrieves available ElevenLabs voices with premade canonical fallbacks.
- **Timestamped Subtitle Generation**: Uses ElevenLabs character timestamps to construct SRT/VTT subtitles directly, bypassing Whisper when available. Whisper remains a resilient fallback.
- **Provider Abstraction & Fallback**: Full video generation supports `voice_provider: "elevenlabs" | "indicf5"`. If ElevenLabs is disabled (`ELEVENLABS_ENABLED=false`) or encounters an API error, it gracefully falls back to local IndicF5.
- **Audio Master Clock**: Synthesized audio acts as the master clock across Manim and FFmpeg; playback speed is never manipulated.
- **Configuration (`backend/.env`)**:
  ```env
  ELEVENLABS_ENABLED=true
  ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
  ELEVENLABS_TTS_MODEL=eleven_multilingual_v2
  ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
  ELEVENLABS_LANGUAGE=en
  ELEVENLABS_TIMEOUT=120
  ```



