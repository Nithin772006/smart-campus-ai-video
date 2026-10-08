"""Pydantic schemas for Hugging Face Inference Providers video generation proof of concept."""

from typing import Optional
from pydantic import BaseModel, Field


class CloudVideoRequest(BaseModel):
    """Request payload for Hugging Face cloud text-to-video generation."""
    prompt: str = Field(
        ...,
        min_length=3,
        max_length=1500,
        description="Text prompt describing the educational visual animation",
        json_schema_extra={"example": "A cinematic educational visualization of a ball falling toward the ground due to gravity, clean classroom-style visual, smooth motion, realistic lighting, no text, no subtitles, no watermark"}
    )
    model: Optional[str] = Field(
        None,
        description="Hugging Face model repository ID (e.g. Wan-AI/Wan2.2-TI2V-5B)",
        json_schema_extra={"example": "Wan-AI/Wan2.2-TI2V-5B"}
    )
    provider: Optional[str] = Field(
        None,
        description="Inference provider (e.g. fal-ai, together, replicate)",
        json_schema_extra={"example": "fal-ai"}
    )
    num_frames: Optional[int] = Field(
        None,
        ge=1,
        le=160,
        description="Number of frames to generate",
        json_schema_extra={"example": 49}
    )
    num_inference_steps: Optional[int] = Field(
        None,
        ge=1,
        le=100,
        description="Number of denoising inference steps",
        json_schema_extra={"example": 30}
    )
    guidance_scale: Optional[float] = Field(
        None,
        ge=1.0,
        le=20.0,
        description="Classifier-free guidance scale",
        json_schema_extra={"example": 5.0}
    )
    negative_prompt: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional negative prompt to discourage unwanted elements",
        json_schema_extra={"example": "text, watermark, low quality, distortion, blurry"}
    )
    seed: Optional[int] = Field(
        None,
        description="Deterministic random seed",
        json_schema_extra={"example": 42}
    )


class CloudVideoResponse(BaseModel):
    """Response payload for generated cloud video artifact."""
    success: bool = Field(..., description="Whether cloud video generation succeeded")
    provider: str = Field(..., description="Inference provider used")
    model: str = Field(..., description="Model repository ID used")
    prompt: str = Field(..., description="Prompt sent to the model")
    video_path: str = Field(..., description="Web-accessible path to saved MP4 file")
    generation_time_seconds: float = Field(..., description="Generation elapsed time in seconds")
    output_size_mb: float = Field(..., description="Saved video file size in megabytes")
    duration_seconds: Optional[float] = Field(None, description="Video duration in seconds")
    resolution: Optional[str] = Field(None, description="Video resolution formatted as WxH")
    codec: Optional[str] = Field(None, description="Detected video codec")


class CloudVideoStatusResponse(BaseModel):
    """Status information for Hugging Face Cloud Video Provider."""
    enabled: bool = Field(..., description="Whether HF Cloud Video feature is globally enabled")
    provider: str = Field(..., description="Configured default cloud inference provider")
    model: str = Field(..., description="Configured default cloud video model")
    token_configured: bool = Field(..., description="Whether a non-empty HF_TOKEN is present in environment")
