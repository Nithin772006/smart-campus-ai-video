import logging
from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app.schemas.character import (
    AvatarPreviewRequest,
    AvatarPreviewResponse,
    CharacterSpec,
)
from app.services.avatar_service import (
    avatar_service,
    AvatarError,
    AvatarProviderUnavailableError,
    CharacterAssetError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/character", summary="Get Canonical Character Metadata")
async def get_character_info():
    """
    Returns canonical teacher character metadata, dimensions, and transparency status.
    """
    try:
        info = await run_in_threadpool(avatar_service.validate_canonical_character)
        return {
            "success": True,
            "character": info,
        }
    except CharacterAssetError as cae:
        raise HTTPException(status_code=404, detail=str(cae))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to inspect character: {e}")


@router.post("/preview", response_model=AvatarPreviewResponse, summary="Generate AI Teacher Avatar Preview")
async def generate_avatar_preview(request: AvatarPreviewRequest):
    """
    Generate a talking avatar preview clip using the canonical teacher character
    and an existing local IndicF5 narration WAV.
    """
    try:
        position_str = request.position.value if request.position else "auto"
        response = await run_in_threadpool(
            avatar_service.generate_preview,
            duration=request.duration or 10.0,
            position=position_str,
        )
        return response
    except AvatarProviderUnavailableError as apue:
        raise HTTPException(status_code=503, detail=str(apue))
    except CharacterAssetError as cae:
        raise HTTPException(status_code=404, detail=str(cae))
    except AvatarError as ae:
        raise HTTPException(status_code=400, detail=str(ae))
    except Exception as e:
        logger.exception("Avatar preview generation failed")
        raise HTTPException(status_code=500, detail=f"Avatar preview generation failed: {str(e)}")
