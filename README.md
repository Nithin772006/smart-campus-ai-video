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

# Run API endpoint tests:
python tests/test_api.py
```
