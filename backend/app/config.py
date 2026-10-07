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
    
    # Compute
    DEVICE: str = "cuda"
    TORCH_DTYPE: str = "float16"

    # TTS Configuration
    TTS_DEVICE: str = "auto"
    TTS_MODEL_TYPE: str = "F5TTS_v1_Base"
    TTS_REF_TEXT: str = "Some call me nature, others call me mother nature."
    TTS_SPEED: float = 1.0

    # Ollama LLM Configuration
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    OLLAMA_TIMEOUT: float = 60.0

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
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
settings.ensure_directories()
