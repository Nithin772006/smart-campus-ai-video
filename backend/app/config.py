from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "SmartCampus AI Video"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    MODELS_DIR: Path = BASE_DIR / "models"
    GENERATED_DIR: Path = BASE_DIR / "generated"
    
    DEVICE: str = "cuda"
    TORCH_DTYPE: str = "float16"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
