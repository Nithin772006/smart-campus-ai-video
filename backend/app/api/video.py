from fastapi import APIRouter, HTTPException
from app.schemas.video import VideoGenerationRequest, VideoGenerationResponse
from app.pipelines.script_to_video import ScriptToVideoPipeline

router = APIRouter()
pipeline = ScriptToVideoPipeline()

@router.post("/generate", response_model=VideoGenerationResponse)
async def generate_video(request: VideoGenerationRequest):
    try:
        result = await pipeline.generate(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
