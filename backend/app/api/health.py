from fastapi import APIRouter

router = APIRouter()

@router.get("", response_model=dict)
@router.get("/", response_model=dict)
async def get_health():
    return {
        "status": "ok",
        "service": "smartcampus-ai-video"
    }
