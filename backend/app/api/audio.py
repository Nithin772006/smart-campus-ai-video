"""
Audio API endpoints for SmartCampus AI Video.
Provides endpoints for IndicF5 speech synthesis and plan voiceover generation.
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, Union
from pydantic import ValidationError

from app.schemas.scene import EducationalVideoPlan
from app.schemas.video import (
    TTSTestRequest,
    TTSPlanRequest,
    TTSAudioResponse,
    AudioRequest,
    PipelineStatusResponse,
)
from app.services.indicf5_service import indicf5_service

router = APIRouter()


@router.post("/test", response_model=TTSAudioResponse, summary="Direct Text-to-Speech Test")
async def test_tts(request: TTSTestRequest):
    """
    Lightweight endpoint for testing local IndicF5 TTS with an arbitrary text string.
    """
    try:
        result = indicf5_service.generate_speech(
            text=request.text,
            topic="test_speech",
        )
        return TTSAudioResponse(
            success=result["success"],
            audio_path=result["audio_path"],
            duration_seconds=result["duration_seconds"],
            sample_rate=result["sample_rate"],
            text_length=result["text_length"],
            generation_time_seconds=result["generation_time_seconds"],
            narration_text=result["narration_text"],
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")


@router.post("/tts", response_model=TTSAudioResponse, summary="Synthesize Audio from Educational Plan")
async def generate_plan_tts(payload: Dict[str, Any]):
    """
    Generates educational spoken voiceover for an EducationalVideoPlan using IndicF5.
    Accepts either `{"plan": {...}}` or direct `EducationalVideoPlan` JSON structure.
    """
    try:
        # Extract EducationalVideoPlan
        if "plan" in payload and isinstance(payload["plan"], dict):
            plan_data = payload["plan"]
        else:
            plan_data = payload

        # Validate with EducationalVideoPlan schema
        plan = EducationalVideoPlan(**plan_data)

        # Synthesize narration
        result = indicf5_service.generate_plan_narration(plan)

        return TTSAudioResponse(
            success=result["success"],
            audio_path=result["audio_path"],
            duration_seconds=result["duration_seconds"],
            sample_rate=result["sample_rate"],
            text_length=result["text_length"],
            generation_time_seconds=result["generation_time_seconds"],
            narration_text=result["narration_text"],
            topic=result.get("topic"),
            scene_scripts=result.get("scene_scripts"),
        )
    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=f"Invalid educational plan schema: {ve}")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS voiceover synthesis failed: {str(e)}")


@router.post("/generate", response_model=TTSAudioResponse, summary="Synthesize Audio from Narration Text")
async def generate_audio_legacy(request: AudioRequest):
    """
    Legacy audio synthesis endpoint using raw narration text.
    """
    try:
        result = indicf5_service.generate_speech(
            text=request.text,
            topic="narration",
        )
        return TTSAudioResponse(
            success=result["success"],
            audio_path=result["audio_path"],
            duration_seconds=result["duration_seconds"],
            sample_rate=result["sample_rate"],
            text_length=result["text_length"],
            generation_time_seconds=result["generation_time_seconds"],
            narration_text=result["narration_text"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio generation failed: {str(e)}")
