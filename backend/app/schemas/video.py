from pydantic import BaseModel, Field
from typing import List, Optional
from app.schemas.scene import SceneSpec

class VideoGenerationRequest(BaseModel):
    title: str = Field(..., example="Introduction to Neural Networks")
    script: str = Field(..., example="Neural networks are computational models inspired by the human brain.")
    language: str = Field("en", example="en")
    scenes: List[SceneSpec] = Field(default_factory=list)
    duration_sec: float = Field(15.0, example=15.0)

class VideoGenerationResponse(BaseModel):
    video_url: str
    duration: float
    status: str
