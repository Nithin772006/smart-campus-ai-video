import os
from pathlib import Path
from typing import List, Union
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "SmartCampus AI Video"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # CORS
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    MODELS_DIR: Path = BASE_DIR / "models"
    GENERATED_DIR: Path = BASE_DIR / "generated"
    
    VIDEOS_DIR: Path = GENERATED_DIR / "videos"
    AUDIO_DIR: Path = GENERATED_DIR / "audio"
    SUBTITLES_DIR: Path = GENERATED_DIR / "subtitles"
    SCENES_DIR: Path = GENERATED_DIR / "scenes"
    
    LTX_MODELS_DIR: Path = MODELS_DIR / "ltx"
    INDICF5_MODELS_DIR: Path = MODELS_DIR / "indicf5"

    ASSETS_DIR: Path = BASE_DIR / "assets"
    CHARACTER_DIR: Path = ASSETS_DIR / "character"
    CANONICAL_TEACHER_IMAGE: Path = CHARACTER_DIR / "teacher.png"
    AVATAR_OUTPUT_DIR: Path = GENERATED_DIR / "avatar"
    CLOUD_VIDEO_DIR: Path = GENERATED_DIR / "cloud_video"
    RENDERED_SCENES_DIR: Path = GENERATED_DIR / "rendered_scenes"
    
    # Compute
    DEVICE: str = "cuda"
    TORCH_DTYPE: str = "float16"

    # TTS Configuration
    TTS_DEVICE: str = "auto"
    TTS_MODEL_TYPE: str = "F5TTS_v1_Base"
    TTS_REF_TEXT: str = "Some call me nature, others call me mother nature."
    TTS_SPEED: float = float(os.getenv("TTS_SPEED", "1.5"))

    # Narration Rate & Duration Configuration
    NARRATION_TARGET_WPM: int = 160
    NARRATION_DURATION_TOLERANCE: float = 0.20
    MAX_NARRATION_RETRIES: int = 2
    DEFAULT_TARGET_DURATION_SECONDS: float = 30.0

    # Ollama LLM Configuration
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    OLLAMA_TIMEOUT: float = 60.0

    # Whisper Subtitle Configuration
    WHISPER_MODEL: str = "base"
    WHISPER_DEVICE: str = "auto"
    WHISPER_COMPUTE_TYPE: str = "auto"

    # FFmpeg Composition Configuration
    FFMPEG_PATH: str = "ffmpeg"
    FFPROBE_PATH: str = "ffprobe"
    BURN_SUBTITLES: bool = True
    VIDEO_CODEC: str = "libx264"
    AUDIO_CODEC: str = "aac"
    VIDEO_CRF: int = 23
    AUDIO_BITRATE: str = "128k"
    PIXEL_FORMAT: str = "yuv420p"
    MOVFLAGS: str = "+faststart"

    # Avatar Configuration
    AVATAR_ENABLED: bool = False
    AVATAR_PROVIDER: str = "musetalk"
    AVATAR_CHARACTER: str = "teacher"
    AVATAR_DEVICE: str = "auto"
    AVATAR_MAX_VRAM_GB: int = 4
    AVATAR_CLOUD_PROVIDER: str = "replicate"
    AVATAR_CLOUD_API_URL: str = ""
    AVATAR_CLOUD_API_KEY: str = ""

    # Hugging Face Video Configuration (Task 9A Proof of Concept)
    HF_TOKEN: str = ""
    HF_VIDEO_ENABLED: bool = False
    HF_VIDEO_PROVIDER: str = "fal-ai"
    HF_VIDEO_MODEL: str = "Wan-AI/Wan2.2-TI2V-5B"
    HF_VIDEO_TIMEOUT: float = 300.0

    # ElevenLabs Multilingual TTS Configuration (Task 9G-A)
    ELEVENLABS_ENABLED: bool = False
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_TTS_MODEL: str = "eleven_multilingual_v2"
    ELEVENLABS_VOICE_ID: str = ""
    ELEVENLABS_LANGUAGE: str = "en"
    ELEVENLABS_TIMEOUT: float = 120.0

    @property
    def cors_origins_list(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    def ensure_directories(self) -> None:
        """Automatically create generated and model directories if they do not exist."""
        directories = [
            self.GENERATED_DIR,
            self.VIDEOS_DIR,
            self.AUDIO_DIR,
            self.SUBTITLES_DIR,
            self.SCENES_DIR,
            self.MODELS_DIR,
            self.LTX_MODELS_DIR,
            self.INDICF5_MODELS_DIR,
            self.CHARACTER_DIR,
            self.AVATAR_OUTPUT_DIR,
            self.CLOUD_VIDEO_DIR,
            self.RENDERED_SCENES_DIR,
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    class Config:
        env_file = (
            str(Path(__file__).resolve().parent.parent / ".env"),
            ".env",
        )
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
settings.ensure_directories()
