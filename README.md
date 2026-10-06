# SmartCampus AI Video Generation Pipeline

An AI-driven video synthesis pipeline designed for campus educational content, combining generative video (LTX-Video), programmatic animations (Manim), Indic voice synthesis (IndicF5 TTS), speech transcription (Whisper), and media assembly (FFmpeg).

## Architecture Overview

```
smartcampus-ai-video/
├── backend/                         ← FastAPI Backend & AI Services
│   ├── app/
│   │   ├── main.py                  ← FastAPI entry point
│   │   ├── api/                     ← REST API endpoints (health, video, audio, subtitle)
│   │   ├── services/                ← Service layer (LTX, Manim, IndicF5, Whisper, FFmpeg)
│   │   ├── pipelines/               ← High-level video generation pipelines
│   │   ├── schemas/                 ← Pydantic request & response models
│   │   ├── utils/                   ← Utilities for IO, timing, and benchmarking
│   │   └── config.py                ← Application configuration & environment settings
│   ├── models/                      ← Model checkpoints (LTX-Video, IndicF5)
│   ├── generated/                   ← Output directory for media artifacts
│   ├── tests/                       ← Backend tests
│   ├── requirements.txt             ← Python dependencies
│   └── .env                         ← Backend environment configuration
├── frontend/                        ← Testing Web UI
├── benchmarks/                      ← Pipeline performance metrics & results.csv
└── scripts/                         ← Helper automation & model download scripts
```

## Quick Start

### 1. Backend Setup
```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 3. Download Models
```bash
python scripts/download_models.py
```
