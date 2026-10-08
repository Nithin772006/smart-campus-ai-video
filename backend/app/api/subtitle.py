"""
Subtitle API endpoints for SmartCampus AI Video.
Provides endpoints for audio transcription, timestamp extraction, and SRT/VTT subtitle generation.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.schemas.video import (
    SubtitleRequest,
    SubtitleResponse,
    PipelineStatusResponse,
)
from app.services.subtitle_service import subtitle_service

router = APIRouter()


@router.post("/transcribe", response_model=SubtitleResponse, summary="Transcribe Audio and Generate Subtitles")
async def transcribe_audio_endpoint(request: SubtitleRequest):
    """
    Transcribes a WAV narration audio file using faster-whisper, generates
    standard SRT and WebVTT subtitles, and returns timing metadata.
    """
    try:
        result = subtitle_service.process_audio(
            audio_path=request.audio_path,
            language=request.language,
        )
        return SubtitleResponse(
            success=result["success"],
            audio_path=result["audio_path"],
            subtitle_srt_path=result["subtitle_srt_path"],
            subtitle_vtt_path=result["subtitle_vtt_path"],
            transcription_path=result["transcription_path"],
            text=result["text"],
            duration_seconds=result["duration_seconds"],
            segment_count=result["segment_count"],
            language=result["language"],
            generation_time_seconds=result["generation_time_seconds"],
            device=result["device"],
            segments=result.get("segments"),
        )
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Subtitle generation failed: {str(e)}")


@router.post("/test", response_model=SubtitleResponse, summary="Direct Subtitle Generation Test")
async def test_subtitles_endpoint(request: SubtitleRequest):
    """
    Lightweight endpoint for testing Whisper transcription and subtitle generation.
    """
    try:
        result = subtitle_service.process_audio(
            audio_path=request.audio_path,
            language=request.language,
        )
        return SubtitleResponse(
            success=result["success"],
            audio_path=result["audio_path"],
            subtitle_srt_path=result["subtitle_srt_path"],
            subtitle_vtt_path=result["subtitle_vtt_path"],
            transcription_path=result["transcription_path"],
            text=result["text"],
            duration_seconds=result["duration_seconds"],
            segment_count=result["segment_count"],
            language=result["language"],
            generation_time_seconds=result["generation_time_seconds"],
            device=result["device"],
            segments=result.get("segments"),
        )
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Subtitle test failed: {str(e)}")


@router.post("/generate", response_model=PipelineStatusResponse, summary="Legacy Subtitle Generation Status")
async def generate_subtitles_legacy(request: SubtitleRequest = None):
    """
    Legacy placeholder endpoint maintained for backward compatibility.
    """
    return PipelineStatusResponse(
        status="not_implemented",
        message="Subtitle generation pipeline will be implemented in the next milestone.",
        pipeline="subtitle_generation",
    )
