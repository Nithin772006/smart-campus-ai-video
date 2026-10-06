from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import health, video, audio, subtitle

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for SmartCampus AI Video synthesis pipeline",
    version="1.0.0",
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(video.router, prefix="/api/video", tags=["Video"])
app.include_router(audio.router, prefix="/api/audio", tags=["Audio"])
app.include_router(subtitle.router, prefix="/api/subtitle", tags=["Subtitle"])

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "docs_url": "/docs",
        "health_check": "/api/health"
    }
