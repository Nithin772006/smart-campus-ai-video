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
    ElevenLabsTTSRequest,
    ElevenLabsTTSResponse,
    ElevenLabsVoicesResponse,
    ElevenLabsVoiceItem,
)
from app.services.indicf5_service import indicf5_service
from app.services.elevenlabs_service import (
    elevenlabs_service,
    ElevenLabsAuthError,
    ElevenLabsConfigError,
    ElevenLabsRateLimitError,
    ElevenLabsTimeoutError,
    ElevenLabsServerError,
    ElevenLabsError,
)
from app.services.audio_provider import get_audio_provider

router = APIRouter()


@router.get("/elevenlabs/voices", response_model=ElevenLabsVoicesResponse, summary="List available ElevenLabs voices")
async def list_elevenlabs_voices():
    """
    Safely retrieves the catalog of available ElevenLabs voices.
    Returns voice metadata without exposing any secrets or API keys.
    """
    if not elevenlabs_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="ElevenLabs is not configured. Missing ELEVENLABS_API_KEY in environment.",
        )

    try:
        voices_data = elevenlabs_service.get_voices()
        voice_items = [ElevenLabsVoiceItem(**v) for v in voices_data]
        return ElevenLabsVoicesResponse(
            success=True,
            voices=voice_items,
            count=len(voice_items),
        )
    except ElevenLabsAuthError as ae:
        raise HTTPException(status_code=401, detail=str(ae))
    except ElevenLabsRateLimitError as rle:
        raise HTTPException(status_code=429, detail=str(rle))
    except ElevenLabsTimeoutError as te:
        raise HTTPException(status_code=504, detail=str(te))
    except ElevenLabsServerError as se:
        raise HTTPException(status_code=502, detail=str(se))
    except ElevenLabsError as ee:
        raise HTTPException(status_code=500, detail=str(ee))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error retrieving voices: {str(e)}")


@router.post("/elevenlabs", response_model=ElevenLabsTTSResponse, summary="Synthesize Speech with ElevenLabs (with Timestamps)")
async def generate_elevenlabs_audio(request: ElevenLabsTTSRequest):
    """
    Synthesizes multilingual spoken narration via ElevenLabs.
    Extracts character timestamps for synchronized subtitles, saves audio artifacts,
    and returns rich duration and alignment metadata without exposing credentials.
    """
    if not elevenlabs_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="ElevenLabs API key is not configured.",
        )

    try:
        result = elevenlabs_service.generate_speech(
            text=request.text,
            voice_id=request.voice_id,
            language=request.language or "en",
            topic=request.topic,
            timestamps=bool(request.timestamps),
        )

        return ElevenLabsTTSResponse(
            success=result["success"],
            provider=result.get("provider", "elevenlabs"),
            audio_path=result["audio_path"],
            mp3_path=result.get("mp3_path"),
            duration_seconds=result["duration_seconds"],
            language=result["language"],
            voice_id=result["voice_id"],
            model=result["model"],
            timestamp_data_available=result.get("timestamp_data_available", False),
            alignment=result.get("alignment"),
            sample_rate=result.get("sample_rate"),
            text_length=result.get("text_length"),
            generation_time_seconds=result.get("generation_time_seconds"),
            fallback_used=False,
            fallback_reason=None,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except ElevenLabsAuthError as ae:
        raise HTTPException(status_code=401, detail=str(ae))
    except ElevenLabsRateLimitError as rle:
        raise HTTPException(status_code=429, detail=str(rle))
    except ElevenLabsTimeoutError as te:
        raise HTTPException(status_code=504, detail=str(te))
    except ElevenLabsServerError as se:
        raise HTTPException(status_code=502, detail=str(se))
    except ElevenLabsError as ee:
        raise HTTPException(status_code=500, detail=str(ee))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ElevenLabs TTS generation failed: {str(e)}")


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
    Generates educational spoken voiceover for an EducationalVideoPlan.
    Supports either IndicF5 (default) or ElevenLabs via the AudioProvider abstraction.
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

        provider_name = payload.get("provider") or payload.get("voice_provider") or "indicf5"
        voice_id = payload.get("voice_id")
        language = payload.get("language") or "en"

        provider = get_audio_provider(provider_name)
        result = provider.generate_plan_narration(
            plan=plan,
            target_duration_seconds=float(target_dur) if target_dur else None,
            voice_id=voice_id,
            language=language,
        )

        return TTSAudioResponse(
            success=result["success"],
            audio_path=result["audio_path"],
            duration_seconds=result["duration_seconds"],
            sample_rate=result.get("sample_rate", 24000),
            text_length=result.get("text_length", len(result.get("narration_text", ""))),
            generation_time_seconds=result["generation_time_seconds"],
            narration_text=result.get("narration_text"),
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


