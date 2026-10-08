"""
Composition schemas for SmartCampus AI Video (Task 9D).
Pydantic validation for final multi-scene video composition and timeline synchronization.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class SceneTimelineItem(BaseModel):
    """Timing details for a single scene on the master timeline."""
    scene_id: str
    engine: str
    start: float = Field(..., ge=0.0, description="Start timestamp in seconds")
    end: float = Field(..., ge=0.0, description="End timestamp in seconds")
    duration: float = Field(..., ge=0.0, description="Scene duration in seconds")
    video_path: Optional[str] = None
    fallback_used: bool = False


class VideoTimeline(BaseModel):
    """Deterministic timeline representation for multi-scene video playback."""
    topic: str
    audio_duration: float = Field(..., ge=0.0)
    final_duration: float = Field(..., ge=0.0)
    sync_delta: float = Field(..., ge=0.0)
    scenes: List[SceneTimelineItem] = Field(default_factory=list)


class CompositionRequest(BaseModel):
    """Request payload for final video composition."""
    topic: str = Field(..., min_length=1, description="Educational topic name")
    quality: str = Field("medium_quality", description="Manim render quality (low_quality, medium_quality, high_quality)")
    subtitle_enabled: bool = Field(True, description="Whether to include subtitles (SRT/burned)")
    burn_subtitles: bool = Field(True, description="Whether to hardcode subtitles onto the MP4")
    transition_enabled: bool = Field(True, description="Whether to apply subtle scene transitions")
    transition_duration_seconds: float = Field(0.3, ge=0.1, le=1.0, description="Duration of transition in seconds")
    output_format: str = Field("mp4", description="Container output format")
    audio_path: Optional[str] = Field(None, description="Optional custom narration WAV path")
    subtitle_path: Optional[str] = Field(None, description="Optional custom subtitles SRT path")
    visual_style: Optional[str] = Field("auto", description="Visual style preset (educational, cinematic_educational, 3blue1brown, auto)")


class ComposedVideoResult(BaseModel):
    """Structured result returned by FinalCompositor and POST /api/video/compose."""
    success: bool
    topic: str
    video_path: str = ""
    duration_seconds: float = 0.0
    audio_duration_seconds: float = 0.0
    sync_delta_seconds: float = 0.0
    scene_count: int = 0
    output_size_mb: float = 0.0
    video_codec: str = "h264"
    audio_codec: str = "aac"
    pixel_format: str = "yuv420p"
    resolution: str = "1280x720"
    fps: float = 30.0
    subtitle_burned: bool = False
    subtitle_path: Optional[str] = None
    timeline_path: Optional[str] = None
    metadata_path: Optional[str] = None
    cloud_fallback_used: bool = False
    scenes: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None
    execution_time_seconds: float = 0.0
