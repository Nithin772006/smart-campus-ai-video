from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class CharacterPosition(str, Enum):
    AUTO = "auto"
    LEFT = "left"
    RIGHT = "right"


class CharacterExpression(str, Enum):
    NEUTRAL = "neutral"
    FRIENDLY = "friendly"
    HAPPY = "happy"
    THINKING = "thinking"
    SURPRISED = "surprised"
    SERIOUS = "serious"


class CharacterGesture(str, Enum):
    IDLE = "idle"
    EXPLAIN = "explain"
    POINT_LEFT = "point_left"
    POINT_RIGHT = "point_right"
    POINT_UP = "point_up"
    POINT_DOWN = "point_down"
    CELEBRATE = "celebrate"
    THINKING = "thinking"


class VisualStyle(str, Enum):
    ACADEMIC = "academic"
    EXPLAINER = "explainer"
    CLASSROOM = "classroom"


class CharacterState(BaseModel):
    """Future-compatible character state metadata per scene."""
    expression: CharacterExpression = CharacterExpression.NEUTRAL
    gesture: CharacterGesture = CharacterGesture.EXPLAIN
    visible: bool = True
    position: CharacterPosition = CharacterPosition.AUTO


class CharacterSpec(BaseModel):
    """Specification metadata for canonical SmartCampus teacher character."""
    name: str = "SmartCampus Teacher"
    version: str = "1.0"
    style: str = "modern_educational_3d"
    view: str = "front_three_quarter"
    framing: str = "upper_body"
    background: str = "transparent"
    canonical_image: str = "teacher.png"
    intended_use: str = "talking_avatar"


class AvatarCapabilities(BaseModel):
    """Granular feature capabilities of an avatar provider."""
    lip_sync: bool = False
    head_motion: bool = False
    full_body_gesture: bool = False


class AvatarStatusResponse(BaseModel):
    """Response schema for GET /api/avatar/status."""
    enabled: bool = True
    selected_provider: str = "auto"
    active_provider: str = "teacher_overlay"
    available: bool = True
    device: str = "cuda"
    animated: bool = False
    reason: Optional[str] = None
    fallback_provider: str = "teacher_overlay"
    capabilities: AvatarCapabilities = Field(default_factory=AvatarCapabilities)


class AvatarPreviewRequest(BaseModel):
    """Request schema for POST /api/avatar/preview."""
    audio_path: Optional[str] = Field(None, description="Optional path to existing narration audio WAV")
    character: Optional[str] = Field("teacher", description="Character identifier (defaults to teacher)")
    provider: Optional[str] = Field("auto", description="Avatar provider: auto, musetalk, cloud, or overlay")
    duration: Optional[float] = Field(10.0, ge=1.0, le=60.0, description="Preview duration in seconds")
    position: Optional[CharacterPosition] = Field(CharacterPosition.AUTO, description="Avatar screen position")


class AvatarPreviewResponse(BaseModel):
    """Response schema for POST /api/avatar/preview."""
    success: bool = Field(True, description="Generation status flag")
    provider: str = Field(..., description="Avatar provider used (e.g. musetalk, cloud, or teacher_overlay)")
    video_path: str = Field(..., description="Path to generated avatar preview video")
    video_url: Optional[str] = Field(None, description="Direct URL to stream or view the preview video")
    duration_seconds: float = Field(..., description="Measured duration of the preview video in seconds")
    generation_time_seconds: float = Field(..., description="Elapsed generation time in seconds")
    character_name: str = Field("SmartCampus Teacher", description="Character identifier")
    resolution: Optional[str] = Field(None, description="Output video resolution (e.g., 1280x720)")
    fps: Optional[float] = Field(None, description="Frame rate of generated preview")
    is_animated: bool = Field(False, description="Genuinely animated flag (false for static overlay)")
    fallback_used: bool = Field(False, description="Whether fallback overlay was applied")
    fallback_reason: Optional[str] = Field(None, description="Reason if fallback was used")
    capabilities: Optional[Dict[str, bool]] = Field(None, description="Capabilities supported by the rendering provider")

