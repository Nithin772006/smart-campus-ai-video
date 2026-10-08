from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SceneType(str, Enum):
    TITLE = "title"
    EXPLANATION = "explanation"
    FORMULA = "formula"
    CONCEPT = "concept"
    BULLET_POINTS = "bullet_points"
    PROCESS = "process"
    COMPARISON = "comparison"
    DIAGRAM = "diagram"
    FLOWCHART = "flowchart"
    HIERARCHY = "hierarchy"
    CYCLE = "cycle"
    CONCLUSION = "conclusion"


class AcademicDomain(str, Enum):
    MATHEMATICS = "mathematics"
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    BIOLOGY = "biology"
    COMPUTER_SCIENCE = "computer_science"
    ENGINEERING = "engineering"
    GENERAL = "general"


class ScenePlanItem(BaseModel):
    id: Optional[int] = Field(None, description="Sequential scene index")
    type: SceneType = Field(..., description="Classification of the visual scene")
    duration: float = Field(5.0, description="Target duration of this scene in seconds")
    title: Optional[str] = Field(None, description="Scene title or header")
    subtitle: Optional[str] = Field(None, description="Subtitle or category")
    content: Optional[str] = Field(None, description="Primary explanation text or concept body")
    formula: Optional[str] = Field(None, description="Mathematical formula or equation string")
    formula_breakdown: Optional[List[str]] = Field(None, description="Legend items explaining formula variables")
    bullets: Optional[List[str]] = Field(None, description="Key points or bullet items")
    steps: Optional[List[str]] = Field(None, description="Procedural stages or algorithm steps")
    layers: Optional[List[str]] = Field(None, description="Stacked architectural layers (e.g. OSI model)")
    comparison: Optional[Dict[str, List[str]]] = Field(None, description="Left vs right comparison points")
    visual_engine: str = Field("manim", description="Rendering engine")
    character_expression: Optional[str] = Field("neutral", description="Teacher expression: neutral, friendly, happy, thinking, surprised, serious")
    character_gesture: Optional[str] = Field("explain", description="Teacher gesture: idle, explain, point_left, point_right, point_up, point_down, celebrate, thinking")
    character_visible: Optional[bool] = Field(True, description="Whether character is visible in this scene")


class EducationalVideoPlan(BaseModel):
    topic: str = Field(..., description="Canonical academic topic", example="Photosynthesis")
    title: str = Field(..., description="Video title", example="How Photosynthesis Works")
    level: str = Field("beginner", description="Difficulty level", example="beginner")
    domain: AcademicDomain = Field(AcademicDomain.GENERAL, description="Academic subject domain")
    summary: Optional[str] = Field(None, description="Brief educational summary")
    target_duration: float = Field(25.0, description="Estimated total video duration in seconds")
    scenes: List[ScenePlanItem] = Field(..., description="Structured sequence of visual scenes")


# Legacy schema preserved for backward compatibility
class Scene(BaseModel):
    id: int = Field(..., description="Unique sequential identifier for the scene")
    type: str = Field(..., description="Scene classification (e.g., 'formula', 'concept', 'animation')")
    text: str = Field(..., description="Script narration or voiceover text for the scene")
    visual_engine: str = Field(..., description="Engine used for rendering (e.g., 'manim', 'ltx')")
    duration: float = Field(..., description="Duration of the scene in seconds")
    language: str = Field("en", description="Audio language code (e.g., 'en', 'hi', 'te')")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "type": "formula",
                "text": "F equals m times a",
                "visual_engine": "manim",
                "duration": 6,
                "language": "en"
            }
        }
