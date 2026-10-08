"""
API endpoints for Hugging Face Cloud Video Generation (Task 9A Proof of Concept).
Provides endpoints to check status and generate standalone cloud AI video scenes.
"""

import logging
from fastapi import APIRouter, HTTPException, status

from app.schemas.cloud_video import (
    CloudVideoRequest,
    CloudVideoResponse,
    CloudVideoStatusResponse,
)
from app.services.huggingface_video_service import (
    hf_video_service,
    HuggingFaceVideoConfigError,
    HuggingFaceVideoDisabledError,
    HuggingFaceTimeoutError,
    HuggingFaceAPIError,
    HuggingFaceVideoError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/status",
    response_model=CloudVideoStatusResponse,
    summary="Get Hugging Face Cloud Video configuration status",
    description="Check whether cloud video generation is enabled and if HF_TOKEN is configured without making generation calls."
)
async def get_cloud_video_status() -> CloudVideoStatusResponse:
    """Return cloud video provider availability and configuration status."""
    status_info = hf_video_service.get_status()
    return CloudVideoStatusResponse(
        enabled=status_info["enabled"],
        provider=status_info["provider"],
        model=status_info["model"],
        token_configured=status_info["token_configured"],
    )


@router.post(
    "/generate",
    response_model=CloudVideoResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate cloud educational video scene via Hugging Face Inference Providers",
    description="Generates an isolated educational video scene using Hugging Face text_to_video inference client and returns the saved MP4 metadata."
)
async def generate_cloud_video(request: CloudVideoRequest) -> CloudVideoResponse:
    """
    Generate an isolated video clip using Hugging Face Inference Providers.
    """
    try:
        result = hf_video_service.generate_video(
            prompt=request.prompt,
            model=request.model,
            provider=request.provider,
            num_frames=request.num_frames,
            num_inference_steps=request.num_inference_steps,
            guidance_scale=request.guidance_scale,
            negative_prompt=request.negative_prompt,
            seed=request.seed,
            check_enabled=True,
        )

        return CloudVideoResponse(
            success=result["success"],
            provider=result["provider"],
            model=result["model"],
            prompt=result["prompt"],
            video_path=result["video_path"],
            generation_time_seconds=result["generation_time_seconds"],
            output_size_mb=result["output_size_mb"],
            duration_seconds=result.get("duration_seconds"),
            resolution=result.get("resolution"),
            codec=result.get("codec"),
        )

    except HuggingFaceVideoDisabledError as e:
        logger.warning("Cloud video generation requested while feature disabled: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HuggingFaceVideoConfigError as e:
        logger.warning("Cloud video generation requested with missing token: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HuggingFaceTimeoutError as e:
        logger.error("Cloud video generation timed out: %s", e)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e),
        )
    except HuggingFaceAPIError as e:
        logger.error("Cloud video generation API error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )
    except HuggingFaceVideoError as e:
        logger.error("Cloud video generation internal error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Unexpected error in cloud video endpoint: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during cloud video generation: {str(e)}",
        )
