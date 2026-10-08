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

        # Extract optional target_duration_seconds
        target_dur = payload.get("target_duration_seconds")
        if target_dur is None and "plan" in payload and isinstance(payload["plan"], dict):
            target_dur = payload["plan"].get("target_duration")

        # Synthesize narration
        result = indicf5_service.generate_plan_narration(
            plan=plan,
            target_duration_seconds=float(target_dur) if target_dur else None,
        )

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
            target_duration_seconds=result.get("target_duration_seconds"),
            speech_rate_wpm=result.get("actual_wpm"),
            actual_wpm=result.get("actual_wpm"),
            estimated_wpm=result.get("estimated_wpm"),
            estimated_duration_seconds=result.get("estimated_duration_seconds"),
            word_count=result.get("word_count"),
        )
    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=f"Invalid educational plan schema: {ve}")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS voiceover synthesis failed: {str(e)}")


@router.post("/generate", response_model=PipelineStatusResponse, summary="Legacy audio generation pipeline status")
async def generate_audio_legacy(request: AudioRequest = None):
    return PipelineStatusResponse(
        status="not_implemented",
        message="Audio generation pipeline will be implemented in the next milestone.",
        pipeline="audio_generation"
    )

