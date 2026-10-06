from pydantic import BaseModel, Field
from typing import Optional

class SceneSpec(BaseModel):
    scene_id: int
    scene_type: str = Field("ltx", description="Type of scene: 'ltx' or 'manim'")
    description: str = Field(..., description="Visual prompt or manim animation instruction")
    duration_sec: float = Field(3.0, description="Duration in seconds")
