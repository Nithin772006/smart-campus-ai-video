from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.whisper_service import WhisperService

router = APIRouter()
whisper_service = WhisperService()

class SubtitleRequest(BaseModel):
    audio_path: str
    language: str = "auto"

@router.post("/generate")
async def generate_subtitles(request: SubtitleRequest):
    try:
        subtitles = await whisper_service.transcribe_audio(
            audio_path=request.audio_path,
            language=request.language
        )
        return {"subtitles": subtitles, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
