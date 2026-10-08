"""
Pydantic Schemas for Visual Scene Renderer Layer (Task 9C).
Defines standard render outputs, per-scene render requests, and topic render payloads.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from app.schemas.visual_scene import RoutedScene


class RenderedScene(BaseModel):
    """Result of independently rendering a single visual educational scene."""
    scene_id: str = Field(..., description="Unique scene identifier", json_schema_extra={"example": "scene_1"})
    video_path: str = Field(..., description="Web-friendly relative path to rendered MP4 video", json_schema_extra={"example": "generated/rendered_scenes/newtons_second_law/scene_1/scene.mp4"})
    duration_seconds: float = Field(..., description="Duration of rendered scene video in seconds", json_schema_extra={"example": 5.5})
    engine: str = Field(..., description="Visual engine used to render the scene (manim, cloud_video, avatar, mixed)", json_schema_extra={"example": "manim"})
    success: bool = Field(..., description="Whether the scene rendered successfully", json_schema_extra={"example": True})
    error: Optional[str] = Field(None, description="Error message if rendering failed", json_schema_extra={"example": None})
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Technical and provider metadata (resolution, codec, fps, provider name)")


class RenderRequest(BaseModel):
    """Request payload to render an individual routed scene."""
    routed_scene: RoutedScene = Field(..., description="The routed educational scene to render")
    output_dir: Optional[str] = Field(None, description="Optional target directory path for rendered MP4")
    quality: Optional[str] = Field("medium_quality", description="Render quality flag (low_quality, medium_quality, high_quality)")
    device: Optional[str] = Field(None, description="Compute device override (auto, cuda, cpu)")
    settings: Optional[Dict[str, Any]] = Field(None, description="Optional engine-specific configuration parameters")


class TopicRenderRequest(BaseModel):
    """Request payload for POST /api/video/render to render all scenes of a topic."""
    topic: str = Field(..., min_length=2, max_length=300, description="Educational topic to plan, route, and render", json_schema_extra={"example": "Newton's Second Law"})
    quality: Optional[str] = Field("medium_quality", description="Manim render quality (low_quality, medium_quality, high_quality)", json_schema_extra={"example": "medium_quality"})
    planner: Optional[str] = Field("auto", description="Planner selection strategy: 'auto', 'qwen', or 'rule_based'", json_schema_extra={"example": "auto"})


class TopicRenderResponse(BaseModel):
    """Response payload for POST /api/video/render containing all independently rendered scenes."""
    success: bool = Field(..., description="Whether the overall topic render batch completed")
    topic: str = Field(..., description="Educational topic rendered")
    scene_count: int = Field(..., description="Total count of scenes in the plan")
    successful_scenes: int = Field(..., description="Number of scenes successfully rendered to MP4")
    failed_scenes: int = Field(..., description="Number of scenes that encountered rendering errors")
    scenes: List[RenderedScene] = Field(..., description="Ordered list of rendered scene results")
    total_duration_seconds: float = Field(..., description="Combined duration of successfully rendered scenes")
    execution_time_seconds: float = Field(..., description="Total time taken to render all scenes in seconds")
