from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.indicf5_service import IndicF5Service

router = APIRouter()
indic_service = IndicF5Service()

class AudioSynthesisRequest(BaseModel):
    text: str
    language: str = "en"
    speaker_voice: str = "default"

@router.post("/synthesize")
async def synthesize_audio(request: AudioSynthesisRequest):
    try:
        output_path = await indic_service.generate_tts(
            text=request.text,
            language=request.language,
            voice=request.speaker_voice
        )
        return {"audio_url": output_path, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
