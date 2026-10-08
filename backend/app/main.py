from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.api import health, video, audio, subtitle, avatar, cloud_video



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure generated and model storage directories exist on startup
    settings.ensure_directories()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Backend microservice for SmartCampus AI Video synthesis pipeline",
    version="0.1.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global error handling
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error occurred.",
            "detail": str(exc) if settings.DEBUG else None,
        },
    )

# Root endpoint
@app.get("/", tags=["General"])
async def root():
    return {
        "message": "SmartCampus AI Video API",
        "status": "running"
    }

# Top-level health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "service": "smartcampus-ai-video"
    }

# Mount static files for generated videos and media artifacts
app.mount("/generated", StaticFiles(directory=str(settings.GENERATED_DIR)), name="generated")
if settings.ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(settings.ASSETS_DIR)), name="assets")

# API Routers
app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(video.router, prefix="/api/video", tags=["Video"])
app.include_router(audio.router, prefix="/api/audio", tags=["Audio"])
app.include_router(subtitle.router, prefix="/api/subtitle", tags=["Subtitle"])
app.include_router(avatar.router, prefix="/api/avatar", tags=["Avatar"])
app.include_router(cloud_video.router, prefix="/api/video/cloud", tags=["Cloud Video"])


