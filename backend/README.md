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
| `POST` | `/api/audio/tts` | **Synthesize narration from EducationalVideoPlan via IndicF5** | **Active (Task 5)** |
| `POST` | `/api/audio/test` | Synthesize test voiceover from arbitrary text string | Active (Task 5) |
| `POST` | `/api/subtitle/transcribe` | **Transcribe audio to SRT, WebVTT & JSON via faster-whisper** | **Active (Task 6)** |
| `POST` | `/api/subtitle/test` | Direct test endpoint for audio transcription & subtitles | Active (Task 6) |
| `POST` | `/api/video/compose` | **Compose video + narration + burned subtitles via FFmpeg** | **Active (Task 7)** |
| `POST` | `/api/video/full` | **Full end-to-end Topic → MP4 educational video generation** | **Active (Task 7)** |
| `POST` | `/api/video/script-to-video` | Generate video from scene script | Planned (Milestone 2) |
| `POST` | `/api/video/topic-to-video` | Generate video from topic prompt | Planned (Milestone 2) |

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
python -m uvicorn app.main:app --reload --reload-dir app --host 127.0.0.1 --port 8000
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

# Run IndicF5 Text-to-Speech tests:
pytest tests/test_indicf5.py -v
```

---

## IndicF5 Local Text-to-Speech (Task 5)

Local educational voiceover speech synthesis using IndicF5 / F5-TTS architecture. 100% local execution—zero cloud APIs and zero external costs.

```
EducationalVideoPlan
        ↓
 NarrationService (Educator script synthesis, formula pronunciation)
        ↓
 IndicF5Service (F5-TTS local DiT model on CUDA with CPU fallback)
        ↓
 WAV Audio (24 kHz) + TXT Transcript
```

### Model Details
- **Architecture**: F5-TTS Flow Matching DiT (`F5TTS_v1_Base`)
- **Vocoder**: Vocos Mel-24kHz (`charactr/vocos-mel-24khz`)
- **Sample Rate**: 24,000 Hz (mono)
- **Reference Voice**: Built-in conversational reference (`basic_ref_en.wav`)

### Dependencies & Setup
```powershell
pip install f5-tts soundfile pytest
```

### Hardware & VRAM Optimization (RTX 2050 4 GB)
- **Preferred Device**: CUDA acceleration (~1.8s per sentence, ~7.8s per full 3-scene lecture plan).
- **Resilient Fallback**: If CUDA memory is insufficient or an OOM error is encountered, the service automatically clears GPU cache, logs `[TTS] Falling back to CPU`, and completes generation on CPU without crashing.
- **Config**: Configurable via `.env`:
  ```env
  TTS_DEVICE=auto   # Options: auto, cuda, cpu
  ```

### Storage Structure
Generated audio is saved in dedicated topic directories:
```
backend/generated/
└── audio/
    └── newtons_second_law/
        ├── narration.wav       # 24 kHz spoken audio
        └── narration.txt       # Full exact spoken transcript
```
Files are statically served by FastAPI:
`http://127.0.0.1:8000/generated/audio/<topic_slug>/narration.wav`

### API Endpoints

#### 1. Plan-to-Speech Endpoint: `POST /api/audio/tts`
Takes an `EducationalVideoPlan` (or `{ "plan": ... }`), builds natural educator narration, converts formulas into spoken words, and generates the WAV file.

**Example Request:**
```powershell
curl -X POST "http://127.0.0.1:8000/api/audio/tts" `
  -H "Content-Type: application/json" `
  -d '{
    "plan": {
      "topic": "Newton'\''s Second Law",
      "title": "Newton'\''s Second Law of Motion",
      "scenes": [
        {
          "id": 1,
          "type": "title",
          "title": "Newton'\''s Second Law",
          "subtitle": "Force, Mass, and Acceleration",
          "content": "The acceleration of an object depends on the net force acting on it."
        },
        {
          "id": 2,
          "type": "formula",
          "title": "Governing Equation",
          "content": "Net force equals mass times acceleration.",
          "formula": "F = ma",
          "formula_breakdown": ["F = Net Force (N)", "m = Mass (kg)", "a = Acceleration (m/s^2)"]
        },
        {
          "id": 3,
          "type": "conclusion",
          "title": "Summary",
          "content": "More force produces more acceleration, while more mass resists acceleration."
        }
      ]
    }
  }'
```

**Example Response:**
```json
{
  "success": true,
  "audio_path": "generated/audio/newtons_second_law/narration.wav",
  "duration_seconds": 14.88,
  "sample_rate": 24000,
  "text_length": 587,
  "generation_time_seconds": 7.86,
  "narration_text": "Welcome to this lesson on Newton's Second Law...",
  "topic": "Newton's Second Law"
}
```

#### 2. Direct Text Test Endpoint: `POST /api/audio/test`
Quick test endpoint for arbitrary text strings.

**Example Request:**
```powershell
curl -X POST "http://127.0.0.1:8000/api/audio/test" `
  -H "Content-Type: application/json" `
  -d '{"text": "Newton'\''s Second Law states that force equals mass multiplied by acceleration."}'
```

**Example Response:**
```json
{
  "success": true,
  "audio_path": "generated/audio/test_speech/narration.wav",
  "duration_seconds": 1.54,
  "sample_rate": 24000,
  "text_length": 77,
  "generation_time_seconds": 1.87,
  "narration_text": "Newton's Second Law states that force equals mass multiplied by acceleration."
}
```

---

## faster-whisper Timestamped Transcription & Subtitles (Task 6)

Speech transcription, word/phrase timestamp alignment, and subtitle generation using `faster-whisper` (CTranslate2-backed Whisper). 100% local, high performance, and memory-conscious for 4 GB GPUs.

```
WAV Narration (from IndicF5)
        ↓
 faster-whisper (CTranslate2 on CUDA / float16)
        ↓
 Timestamped Transcription Segments
        ↓
 SubtitleService (SRT + WebVTT + transcription.json)
        ↓
 Future Video Composition & Lip-Sync (Task 7)
```

### Model & Compute Configuration
- **Default Model**: `base` (`Systran/faster-whisper-base`, ~140 MB weights).
- **Alternative Lightweight Option**: `tiny` (~75 MB). Avoid `medium` or `large` models to respect 4 GB VRAM limits.
- **Compute Type**: `auto` (resolves to `float16` on CUDA, `int8` on CPU).
- **VAD Filtering**: Enabled (`vad_filter=True`) to suppress hallucinations and trailing synthetic speech silence.
- **Timestamp Integrity**: Clamped to exact audio duration, monotonically increasing start/end times.

### 4 GB VRAM Considerations (NVIDIA RTX 2050)
- The `base` model in `float16` utilizes only ~250–350 MB of VRAM.
- Coexists smoothly alongside Ollama and IndicF5.
- If GPU memory is exhausted or CUDA is absent, `WhisperService` transparently falls back to CPU (`int8`).

### Environment Variables
Configure in `.env`:
```env
WHISPER_MODEL=base          # tiny, base, small
WHISPER_DEVICE=auto         # auto, cuda, cpu
WHISPER_COMPUTE_TYPE=auto   # auto, float16, int8, float32
```

### Storage Structure
Subtitles and alignment metadata are saved per topic:
```
backend/generated/
└── subtitles/
    └── newtons_second_law/
        ├── subtitles.srt       # Standard SubRip format with HH:MM:SS,mmm
        ├── subtitles.vtt       # WebVTT format for browser video player
        └── transcription.json  # Structured timestamps and segment metadata
```
Files are statically served by FastAPI:
- `http://127.0.0.1:8000/generated/subtitles/<topic_slug>/subtitles.srt`
- `http://127.0.0.1:8000/generated/subtitles/<topic_slug>/subtitles.vtt`
- `http://127.0.0.1:8000/generated/subtitles/<topic_slug>/transcription.json`

### API Endpoints

#### 1. Transcribe Narration: `POST /api/subtitle/transcribe`
Transcribes a generated WAV file into timestamped SRT, WebVTT, and structured JSON.

**Example Request:**
```powershell
curl -X POST "http://127.0.0.1:8000/api/subtitle/transcribe" `
  -H "Content-Type: application/json" `
  -d '{"audio_path": "generated/audio/newtons_second_law/narration.wav"}'
```

**Example Response:**
```json
{
  "success": true,
  "audio_path": "generated/audio/newtons_second_law/narration.wav",
  "subtitle_srt_path": "generated/subtitles/newtons_second_law/subtitles.srt",
  "subtitle_vtt_path": "generated/subtitles/newtons_second_law/subtitles.vtt",
  "transcription_path": "generated/subtitles/newtons_second_law/transcription.json",
  "text": "Welcome to this lesson on Newton's Second Law of Motion...",
  "duration_seconds": 19.86,
  "segment_count": 10,
  "language": "en",
  "generation_time_seconds": 3.26,
  "device": "cuda",
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 3.2,
      "text": "Welcome to this lesson on Newton's Second Law of Motion."
    },
    {
      "id": 1,
      "start": 3.2,
      "end": 5.92,
      "text": "In this lesson, we will explore force, mass, and acceleration."
    }
  ]
}
```

#### 2. Direct Test Endpoint: `POST /api/subtitle/test`
Convenience testing endpoint that runs transcription and subtitle export on any audio path.

**Example Request:**
```powershell
curl -X POST "http://127.0.0.1:8000/api/subtitle/test" `
  -H "Content-Type: application/json" `
  -d '{"audio_path": "generated/audio/newtons_second_law/narration.wav"}'
```

### Running Subtitle Tests
```powershell
cd backend
.venv\Scripts\activate
pytest tests/test_whisper.py -v
```

### Downstream Synchronization
The generated timestamps (`transcription.json` and SRT cues) provide the synchronization reference for:
1. Scene transitions matching narration phrasing.
2. Character/avatar lip-sync and gesture cues.
3. Subtitle overlay rendering in final FFmpeg video muxing.

---

## FFmpeg Final Video Composition (Task 7)

Combines visual animations, spoken narration, and burned subtitles into a unified, browser-compatible MP4 container. Completes the first 100% local end-to-end pipeline: **Topic Prompt → LLM Plan → Dynamic Manim → IndicF5 Voiceover → faster-whisper Subtitles → FFmpeg Final MP4**.

```
Manim Scene Video (.mp4)  ────────┐
                                  │
IndicF5 Voiceover (.wav)  ────────┼──► [FFmpegService] ──► Final Browser MP4
                                  │    (Duration Alignment +
faster-whisper Subtitles (.srt) ──┘     Burned Subtitles)
```

### Architecture & Key Responsibilities
1. **Intelligent Duration Synchronization**:
   - **Visuals > Narration ($D_v > D_a$)**: The audio stream is padded with silence using `-af apad=whole_dur=Dv` so all planned educational visuals, formulas, and conclusions play completely without truncation.
   - **Narration > Visuals ($D_a > D_v$)**: The visual stream is extended by holding/cloning the final frame using `-vf tpad=stop_mode=clone:stop_duration=(Da-Dv)` so voiceover is never cut off.
2. **Subtitle Burning (libass)**:
   - Burns SRT subtitles directly into the video frame with high-legibility styling: white font, crisp black outline border, safe bottom margins (`MarginV=25`), and bottom-center alignment (`Alignment=2`).
   - Configurable via `BURN_SUBTITLES=true`.
3. **Browser Compatibility**:
   - Encodes video to H.264 (`libx264`, `yuv420p`, CRF 23).
   - Encodes audio to AAC (`aac`, 44.1 kHz, 128 kbps).
   - Enables faststart (`-movflags +faststart`) for instant HTML5 web playback.

### Configuration (`.env`)
```env
FFMPEG_PATH=ffmpeg
FFPROBE_PATH=ffprobe
BURN_SUBTITLES=true
VIDEO_CODEC=libx264
AUDIO_CODEC=aac
VIDEO_CRF=23
AUDIO_BITRATE=128k
```

### Storage Structure
```
backend/generated/
└── videos/
    └── newtons_second_law/
        └── final.mp4       # Final browser-compatible MP4 with audio and burned subtitles
```
Statically served by FastAPI:
`http://127.0.0.1:8000/generated/videos/<topic_slug>/final.mp4`

### API Endpoints

#### 1. Compose Existing Media: `POST /api/video/compose`
Combines existing video, audio, and subtitle files into a final MP4.

**Request:**
```bash
curl -X POST "http://127.0.0.1:8000/api/video/compose" \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "generated/scenes/newtons_second_law/newtons_second_law.mp4",
    "audio_path": "generated/audio/newtons_second_law/narration.wav",
    "subtitle_path": "generated/subtitles/newtons_second_law/subtitles.srt",
    "burn_subtitles": true
  }'
```

**Response:**
```json
{
  "success": true,
  "video_path": "generated/videos/newtons_second_law/final.mp4",
  "video_url": "/generated/videos/newtons_second_law/final.mp4",
  "duration_seconds": 23.93,
  "video_duration_seconds": 23.93,
  "audio_duration_seconds": 12.36,
  "file_size_mb": 0.47,
  "has_video": true,
  "has_audio": true,
  "has_subtitles": true,
  "generation_time_seconds": 0.97,
  "width": 854,
  "height": 480,
  "fps": 15.0,
  "video_codec": "h264",
  "audio_codec": "aac"
}
```

#### 2. Full End-to-End Generation: `POST /api/video/full`
Orchestrates the entire 5-stage pipeline from topic prompt to final MP4 in a single request.

**Request:**
```bash
curl -X POST "http://127.0.0.1:8000/api/video/full" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Explain Newton'\''s Second Law",
    "quality": "medium_quality",
    "burn_subtitles": true
  }'
```

### Running Composition Tests
```powershell
cd backend
.venv\Scripts\activate
pytest tests/test_ffmpeg.py -v
```

---

## Hugging Face Inference Providers Cloud Video (Task 9A Proof of Concept)

A standalone proof-of-concept integrating Hugging Face Inference Providers for generating isolated educational video scene clips via cloud models (e.g., `Wan-AI/Wan2.2-TI2V-5B` via `fal-ai`).

> [!IMPORTANT]
> **Architecture Isolation:** This is currently a standalone proof-of-concept cloud video provider.
> It is **NOT** yet connected to:
> - Qwen scene planner
> - Manim renderer
> - IndicF5 TTS
> - faster-whisper subtitles
> - FFmpeg final composition
> - `/api/video/full`
> 
> Those pipelines will be integrated only in subsequent milestones after cloud provider validation. The existing Tasks 1–8 local pipeline remains completely intact and unaffected.

### Setup Instructions

1. **Create Hugging Face Token:**
   Obtain an API token with inference permissions from [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).

2. **Configure `.env`:**
   Add the following variables to `backend/.env`:
   ```env
   HF_TOKEN=hf_your_actual_token_here
   HF_VIDEO_ENABLED=true
   HF_VIDEO_PROVIDER=fal-ai
   HF_VIDEO_MODEL=Wan-AI/Wan2.2-TI2V-5B
   HF_VIDEO_TIMEOUT=300
   ```

3. **Install Dependency:**
   ```powershell
   cd backend
   .\.venv\Scripts\pip install huggingface_hub
   ```

4. **Start Backend Server:**
   ```powershell
   python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

5. **Check Provider Status:**
   ```bash
   curl -X GET "http://127.0.0.1:8000/api/video/cloud/status"
   ```

6. **Generate Cloud Video Scene:**
   ```bash
   curl -X POST "http://127.0.0.1:8000/api/video/cloud/generate" \
     -H "Content-Type: application/json" \
     -d '{
       "prompt": "A cinematic educational visualization of a red apple falling from a tree, clear gravity concept, realistic physics, smooth camera movement",
       "model": "Wan-AI/Wan2.2-TI2V-5B",
       "provider": "fal-ai"
     }'
   ```

7. **Access Generated Media:**
   Generated clips are saved under `backend/generated/cloud_video/` and served statically at:
   `http://127.0.0.1:8000/generated/cloud_video/<filename>.mp4`

8. **Run Unit Tests (Zero API credits consumed):**
   ```powershell
   pytest tests/test_huggingface_video.py -v
   ```

9. **Run Real Integration Test:**
   ```powershell
   python tests/manual_test_huggingface_video.py
   ```

---

## Visual Scene Planning & Scene Router (Task 9B)

A visual-first instructional planning and deterministic engine routing layer that produces comprehensive video production blueprints without triggering media rendering.

```
                   User Academic Topic
                            ↓
                LLMVisualScenePlanner
           (Local Qwen2.5 3B via Ollama)
                            ↓
                     VisualVideoPlan
                            ↓
                       SceneRouter
              (Deterministic Policy Engine)
                            ↓
                     RoutedVideoPlan
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
       Manim           Cloud Video           Avatar
  (Equations/Graphs)  (Cinematic/Real)    (Teacher Intro/
                                            Summary)
```

### Roles and Responsibilities

- **Qwen2.5:3b (Visual Scene Planner) Decides:**
  1. Spoken narration for each scene.
  2. Visual screen content (`visual_description`).
  3. Pedagogical scene classification (`scene_type`).
  4. Specific visual graphical objects (`visual_elements`).
  5. Kinetic transitions and directives (`animations`).
  6. Teacher avatar presence (`teacher_enabled`) and screen placement (`teacher_position`).
  7. Prompt text for potential generative cloud video models (`visual_prompt`).
  8. Approximate per-scene duration.

- **Scene Router Decides & Enforces:**
  1. **Manim**: Selected for equations, LaTeX formulas, coordinate graphs, geometry, algorithmic arrays, flowcharts, and technical process diagrams. Generative cloud video is strictly forbidden from equations to prevent hallucinations.
  2. **Cloud Video**: Selected for photorealistic environments, real-world demonstrations, natural phenomena, and cinematic visual metaphors.
  3. **Avatar**: Selected for direct teacher addresses, topic introductions, and summary takeaways.
  4. **Mixed**: Selected when combining primary Manim visuals with secondary AI teacher narration overlay.

> [!NOTE]
> **No Video Generation:** The Scene Router does **NOT** render video, call TTS, or invoke external Hugging Face cloud APIs. It is exclusively an architectural planning and routing system.

### API Endpoint: `POST /api/video/plan`

**Request:**
```bash
curl -X POST "http://127.0.0.1:8000/api/video/plan" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Explain Newton'\''s Second Law"
  }'
```

**Running Tests:**
```powershell
pytest tests/test_visual_scene_planner.py -v
```

---

## Task 9C — Visual Scene Renderer Layer

The Visual Scene Renderer layer allows every scene produced by the Visual Scene Planner and routed by the Scene Router to be rendered independently into standard MP4 clips prior to downstream composition.

### Architecture

```
User Topic
    ↓
Qwen2.5 3B / VisualScenePlanner
    ↓
VisualVideoPlan
    ↓
SceneRouter
    ↓
Renderer Registry (`get_renderer(engine)`)
 ├── ManimRenderer (Local vector math & educational visuals)
 ├── CloudVideoRenderer (Hugging Face Inference Providers video generation)
 └── AvatarRenderer (Canonical 3D teacher presenter overlay video)
    ↓
Standardized RenderedScene Results
    ↓
[Task 9D Compositor (Upcoming)]
```

### Supported Engines & Fallback Guarantees

1. **`ManimRenderer`**:
   - Converts routed scenes into real Manim educational vector animations.
   - Generates educational visuals for physics (e.g. Newton's Second Law mass box, force vector arrow, acceleration, and $F = ma$ equation), algorithms, graphs, formulas, and diagrams.
   - Returns standard `RenderedScene` with video path and verified duration.

2. **`CloudVideoRenderer`**:
   - Connects to `HuggingFaceVideoService`.
   - Safely detects missing tokens, disabled settings, timeouts, and credit exhaustion (HTTP 402 Payment Required).
   - Returns a structured failure (`success=False`, `engine="cloud_video"`, clear provider error) without crashing the batch or pretending an MP4 was generated.

3. **`AvatarRenderer`**:
   - Uses the canonical 3D AI Teacher (`backend/assets/character/teacher.png`) and `TeacherAvatarOverlayProvider`.
   - Generates standardized 1080p/480p educational presenter video clips with clean AAC audio.
   - Identified in metadata as `metadata.provider = "teacher_overlay"`.

### API Endpoint: `POST /api/video/render`

**Request:**
```bash
curl -X POST "http://127.0.0.1:8000/api/video/render" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Newton'\''s Second Law",
    "quality": "medium_quality"
  }'
```

**Response:**
```json
{
  "success": true,
  "topic": "Newton's Second Law",
  "scene_count": 4,
  "successful_scenes": 4,
  "failed_scenes": 0,
  "total_duration_seconds": 18.14,
  "execution_time_seconds": 28.5,
  "scenes": [
    {
      "scene_id": "scene_1",
      "video_path": "generated/rendered_scenes/newtons_second_law/scene_1/scene.mp4",
      "duration_seconds": 5.0,
      "engine": "avatar",
      "success": true,
      "error": null,
      "metadata": {"provider": "teacher_overlay"}
    },
    {
      "scene_id": "scene_2",
      "video_path": "generated/rendered_scenes/newtons_second_law/scene_2/scene.mp4",
      "duration_seconds": 4.07,
      "engine": "manim",
      "success": true,
      "error": null,
      "metadata": {"scene_type": "equation", "width": 854, "height": 480}
    }
  ]
}
```

### Output File Structure

Rendered scenes are stored per topic slug in:
```
backend/generated/rendered_scenes/
    └── <topic_slug>/
        ├── scene_1/
        │   └── scene.mp4
        ├── scene_2/
        │   └── scene.mp4
        └── scene_3/
            └── scene.mp4
```

### Running Renderer Tests

```powershell
pytest tests/test_scene_renderers.py -v
```

---

## Task 9D — Final Video Composition & Synchronization

The Final Video Composition layer integrates multi-engine rendered scene MP4s, master IndicF5 narration WAV, and Whisper SRT subtitles into a single, synchronized, educational MP4 video.

### Core Principle: Audio is the Master Clock

- **Master Timeline:** Narration audio duration is authoritative. Audio speed is **never** compressed, stretched, or modified.
- **Visual Adaptation:** If total scene video duration is shorter than narration audio, the final frame is held (`tpad=stop_mode=clone:stop_duration=...`) to match audio duration within 0.15s.
- **Format Normalization:** All scene videos (Manim 854x480, Avatar 1144x1374, etc.) are aspect-ratio-preserved and padded to uniform **1280x720 / 30fps / H.264 / yuv420p**.
- **Transitions:** Professional crossfade (`xfade`) transitions between scenes without timeline drift.
- **Subtitles:** Whisper subtitles burned into the video with safe area bottom margins.
- **Cloud Fallback:** If cloud video generation fails (e.g. 0 HF credits / HTTP 402), an educational fallback visual is rendered and `cloud_fallback_used=True` is recorded in metadata.

### Pipeline Architecture

```
                  USER TOPIC
                      ↓
                    QWEN
                      ↓
              VISUAL SCENE PLAN
                      ↓
                 SCENE ROUTER
                      ↓
               RENDERER REGISTRY
                      ↓
        ┌─────────────┼──────────────┐
        ↓             ↓              ↓
      MANIM        CLOUD VIDEO      AVATAR
        ↓             ↓              ↓
      MP4           MP4            MP4
        └─────────────┼──────────────┘
                      ↓
              RENDERED SCENES
                      ↓
              MASTER NARRATION
                      ↓
                  WHISPER
                      ↓
                 SUBTITLES
                      ↓
              FINAL COMPOSITOR
                      ↓
                 FINAL MP4
                      ↓
          ┌───────────┴───────────┐
          ↓                       ↓
       timeline.json          metadata.json
```

### API Endpoint: `POST /api/video/compose`

**Request:**
```bash
curl -X POST "http://127.0.0.1:8000/api/video/compose" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Newton'\''s Second Law",
    "quality": "low_quality",
    "subtitle_enabled": true,
    "burn_subtitles": true,
    "transition_enabled": true
  }'
```

**Response:**
```json
{
  "success": true,
  "topic": "Newton's Second Law",
  "video_path": "generated/videos/newtons_second_law/final.mp4",
  "duration_seconds": 26.9,
  "audio_duration_seconds": 26.9,
  "sync_delta_seconds": 0.0,
  "scene_count": 5,
  "output_size_mb": 1.03,
  "video_codec": "h264",
  "audio_codec": "aac",
  "pixel_format": "yuv420p",
  "resolution": "1280x720",
  "fps": 30.0,
  "subtitle_burned": true,
  "timeline_path": "generated/videos/newtons_second_law/timeline.json",
  "metadata_path": "generated/videos/newtons_second_law/metadata.json",
  "cloud_fallback_used": false
}
```

### Output File Structure

```
backend/generated/videos/
    └── <topic_slug>/
        ├── final.mp4         # Master composed 1280x720 MP4
        ├── final.srt         # Synchronized Whisper subtitles
        ├── timeline.json     # Deterministic scene start/end timeline
        └── metadata.json     # Complete technical and stream metadata
```

### Running Composition Tests

```powershell
pytest tests/test_final_compositor.py -v
```





