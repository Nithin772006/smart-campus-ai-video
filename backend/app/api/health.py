from fastapi import APIRouter
from app.config import settings

router = APIRouter()

@router.get("")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.APP_ENV,
        "device": settings.DEVICE
    }
