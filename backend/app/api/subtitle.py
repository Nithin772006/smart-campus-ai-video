from fastapi import APIRouter
from app.schemas.video import SubtitleRequest, PipelineStatusResponse

router = APIRouter()

@router.post("/generate", response_model=PipelineStatusResponse)
async def generate_subtitles(request: SubtitleRequest = None):
    return PipelineStatusResponse(
        status="not_implemented",
        message="Subtitle generation pipeline will be implemented in the next milestone.",
        pipeline="subtitle_generation"
    )
