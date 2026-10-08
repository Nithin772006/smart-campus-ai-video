"""
Visual Scene and Video Plan Schemas (Task 9B).
Defines visual-first scene planning models, animation instructions, engine routing representations,
and structured plans for Manim, Cloud Video (HF/Wan/LTX), and Talking Avatar synthesis.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator


class VisualEngine(str, Enum):
    """Rendering engine or provider designated for a scene."""
    MANIM = "manim"
    CLOUD_VIDEO = "cloud_video"
    AVATAR = "avatar"
    MIXED = "mixed"


class SceneType(str, Enum):
    """Pedagogical classification of the visual scene."""
    TITLE = "title"
    EXPLANATION = "explanation"
    EQUATION = "equation"
    DIAGRAM = "diagram"
    GRAPH = "graph"
    PROCESS = "process"
    TIMELINE = "timeline"
    COMPARISON = "comparison"
    ALGORITHM = "algorithm"
    PHYSICS_SIMULATION = "physics_simulation"
    CHEMISTRY_VISUAL = "chemistry_visual"
    BIOLOGY_VISUAL = "biology_visual"
    CINEMATIC = "cinematic"
    TEACHER_INTRO = "teacher_intro"
    TEACHER_EXPLANATION = "teacher_explanation"
    TEACHER_SUMMARY = "teacher_summary"
    TRANSITION = "transition"


class TeacherPosition(str, Enum):
    """Screen positioning for the talking AI teacher avatar."""
    NONE = "none"
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class CameraMotion(str, Enum):
    """Kinetic camera motions for enhanced visual presentation."""
    STATIC = "static"
    SLOW_ZOOM_IN = "slow_zoom_in"
    SLOW_ZOOM_OUT = "slow_zoom_out"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    FOCUS_CENTER = "focus_center"


class VisualEmphasis(str, Enum):
    """Dynamic focal emphasis applied to salient visual elements."""
    NONE = "none"
    HIGHLIGHT = "highlight"
    GLOW = "glow"
    PULSE = "pulse"
    ZOOM = "zoom"
    DRAW_ATTENTION = "draw_attention"


class SceneTransition(str, Enum):
    """Cinematic transitions between educational scenes."""
    CUT = "cut"
    FADE = "fade"
    CROSSFADE = "crossfade"
    SLIDE = "slide"
    ZOOM = "zoom"


class BackgroundStyle(str, Enum):
    """Aesthetic canvas style for educational scene presentation."""
    DARK_SLATE = "dark_slate"
    MIDNIGHT_BLUE = "midnight_blue"
    BLACK_CHALKBOARD = "black_chalkboard"
    DEEP_GRADIENT = "deep_gradient"


class CinematicVisualStyle(str, Enum):
    """Overarching aesthetic theme requested for the video."""
    EDUCATIONAL = "educational"
    CINEMATIC_EDUCATIONAL = "cinematic_educational"
    THREE_BLUE_ONE_BROWN = "3blue1brown"
    AUTO = "auto"



class VisualElement(BaseModel):
    """Specific graphical or spatial object presented in the scene."""
    type: str = Field(
        ...,
        description="Category of the element (e.g. formula, text, shape, axis, arrow, particle, character)",
        json_schema_extra={"example": "formula"}
    )
    label: Optional[str] = Field(
        None,
        description="Optional identifier or title for the visual element",
        json_schema_extra={"example": "SecondLawEquation"}
    )
    description: str = Field(
        ...,
        description="Detailed appearance and visual attributes of the object",
        json_schema_extra={"example": "LaTeX equation F = m * a in bold cyan"}
    )
    properties: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional geometric or rendering properties (e.g. color, scale, coordinates)",
        json_schema_extra={"example": {"color": "CYAN", "scale": 1.2}}
    )


class AnimationInstruction(BaseModel):
    """Explicit kinetic or transition directive for objects within the scene."""
    action: str = Field(
        ...,
        description="Animation action (e.g. create, transform, fade_in, fade_out, move, indicate, play)",
        json_schema_extra={"example": "create"}
    )
    target: str = Field(
        ...,
        description="Target visual element or group to apply the animation to",
        json_schema_extra={"example": "SecondLawEquation"}
    )
    duration: Optional[float] = Field(
        None,
        ge=0.1,
        le=30.0,
        description="Duration of this animation phase in seconds",
        json_schema_extra={"example": 2.0}
    )
    description: Optional[str] = Field(
        None,
        description="Human-readable summary of the animation movement",
        json_schema_extra={"example": "Equation writes onto the screen with glowing emphasis"}
    )


class VisualScene(BaseModel):
    """A distinct visual-first educational scene unit."""
    scene_id: str = Field(
        ...,
        description="Unique identifier for the scene (e.g. scene_1, scene_intro)",
        json_schema_extra={"example": "scene_1"}
    )
    scene_type: SceneType = Field(
        ...,
        description="Pedagogical type of this scene",
        json_schema_extra={"example": "equation"}
    )
    visual_engine: VisualEngine = Field(
        ...,
        description="Target rendering engine (manim, cloud_video, avatar, mixed)",
        json_schema_extra={"example": "manim"}
    )
    narration: str = Field(
        ...,
        min_length=1,
        description="Spoken voiceover script for this scene (synthesized via TTS)",
        json_schema_extra={"example": "Newton's second law quantifies how force relates to mass and acceleration."}
    )
    visual_description: str = Field(
        ...,
        min_length=1,
        description="Description of what the viewer sees on screen",
        json_schema_extra={"example": "Clear coordinate plane with force vector arrow applied to a moving mass block."}
    )
    visual_prompt: Optional[str] = Field(
        None,
        description="Prompt intended for future cloud video generators (Wan, LTX) if applicable",
        json_schema_extra={"example": "Cinematic close-up of a wooden block accelerating on a frictionless surface under an applied horizontal force."}
    )
    duration_seconds: float = Field(
        ...,
        ge=1.0,
        le=60.0,
        description="Target duration of this scene in seconds",
        json_schema_extra={"example": 5.5}
    )
    teacher_enabled: bool = Field(
        default=False,
        description="Whether the AI teacher avatar is present in this scene"
    )
    teacher_position: TeacherPosition = Field(
        default=TeacherPosition.NONE,
        description="Spatial placement of the teacher (none, left, center, right)"
    )
    visual_elements: List[VisualElement] = Field(
        default_factory=list,
        description="Key graphic elements displayed in this scene"
    )
    animations: List[AnimationInstruction] = Field(
        default_factory=list,
        description="Sequence of animations occurring in this scene"
    )
    educational_goal: Optional[str] = Field(
        None,
        description="Core learning takeaway for this scene",
        json_schema_extra={"example": "Understand that acceleration is directly proportional to applied force."}
    )
    camera_motion: CameraMotion = Field(
        default=CameraMotion.STATIC,
        description="Camera movement applied during the scene (static, slow_zoom_in, etc.)"
    )
    emphasis: VisualEmphasis = Field(
        default=VisualEmphasis.NONE,
        description="Focal emphasis applied to primary educational objects"
    )
    transition_in: SceneTransition = Field(
        default=SceneTransition.CUT,
        description="Transition effect when entering this scene"
    )
    transition_out: SceneTransition = Field(
        default=SceneTransition.CUT,
        description="Transition effect when leaving this scene"
    )
    background_style: BackgroundStyle = Field(
        default=BackgroundStyle.DARK_SLATE,
        description="Canvas styling of the scene background"
    )
    visual_style: Optional[str] = Field(
        default="educational",
        description="Visual design style identifier"
    )
    is_hook: bool = Field(
        default=False,
        description="Whether this scene acts as a visual hook to captivate attention"
    )

    @model_validator(mode="after")
    def validate_teacher_alignment(self) -> "VisualScene":
        """Ensure teacher position is none when teacher_enabled is False, and vice versa."""
        if not self.teacher_enabled and self.teacher_position != TeacherPosition.NONE:
            # Normalize to NONE if teacher is disabled
            self.teacher_position = TeacherPosition.NONE
        elif self.teacher_enabled and self.teacher_position == TeacherPosition.NONE:
            # Default to right if enabled but none given
            self.teacher_position = TeacherPosition.RIGHT
        return self


class VisualVideoPlan(BaseModel):
    """Complete multi-scene visual educational video plan."""
    topic: str = Field(
        ...,
        min_length=2,
        description="Educational topic or subject matter",
        json_schema_extra={"example": "Newton's Second Law"}
    )
    title: str = Field(
        ...,
        min_length=2,
        description="Compelling title of the educational video",
        json_schema_extra={"example": "Understanding Newton's Second Law of Motion"}
    )
    total_duration_seconds: float = Field(
        ...,
        ge=5.0,
        description="Cumulative planned duration across all scenes in seconds",
        json_schema_extra={"example": 30.0}
    )
    overall_visual_style: CinematicVisualStyle = Field(
        default=CinematicVisualStyle.EDUCATIONAL,
        description="Global aesthetic theme across all scenes in the plan"
    )
    scenes: List[VisualScene] = Field(
        ...,
        min_length=1,
        description="Ordered sequence of visual scenes composing the video lesson"
    )
    learning_objectives: List[str] = Field(
        default_factory=list,
        description="Pedagogical objectives achieved upon watching the video",
        json_schema_extra={"example": ["Define F = ma", "Interpret force-acceleration graphs", "Apply formula to physical mass"]}
    )


class RoutedScene(BaseModel):
    """A scene that has passed through the deterministic SceneRouter."""
    scene: VisualScene = Field(..., description="The underlying visual scene plan")
    selected_engine: VisualEngine = Field(..., description="Engine selected by the router after policy enforcement")
    routing_reason: str = Field(..., description="Deterministic reason why this engine was selected or overridden")
    fallback_engine: Optional[VisualEngine] = Field(None, description="Safe fallback engine if primary is unavailable")
    cloud_generation_required: bool = Field(default=False, description="Whether this scene requires external cloud video generation")


class RoutedVideoPlan(BaseModel):
    """Output of SceneRouter containing all routed scenes and summary metrics."""
    original_plan: VisualVideoPlan = Field(..., description="Original visual plan before routing")
    routed_scenes: List[RoutedScene] = Field(..., description="Ordered list of routed scene decisions")
    engine_summary: Dict[str, int] = Field(..., description="Count of scenes assigned to each visual engine")


class VisualPlanRequest(BaseModel):
    """Request payload for POST /api/video/plan."""
    topic: str = Field(
        ...,
        min_length=2,
        max_length=300,
        description="Educational topic to plan (e.g. 'Explain Newton's Second Law')",
        json_schema_extra={"example": "Explain Newton's Second Law"}
    )
    target_duration: Optional[float] = Field(
        30.0,
        ge=10.0,
        le=120.0,
        description="Target duration of the video lesson in seconds",
        json_schema_extra={"example": 30.0}
    )
    level: Optional[str] = Field(
        "intermediate",
        description="Difficulty level (beginner, intermediate, advanced)",
        json_schema_extra={"example": "intermediate"}
    )
    planner: Optional[str] = Field(
        "auto",
        description="Planner selection strategy: 'auto', 'qwen', or 'rule_based'",
        json_schema_extra={"example": "auto"}
    )
    visual_style: Optional[str] = Field(
        "auto",
        description="Visual style aesthetic: 'educational', 'cinematic_educational', '3blue1brown', or 'auto'",
        json_schema_extra={"example": "cinematic_educational"}
    )



class VisualPlanResponse(BaseModel):
    """Response payload for POST /api/video/plan."""
    success: bool = Field(True, description="Whether plan generation and routing succeeded")
    topic: str = Field(..., description="Canonical topic planned")
    title: str = Field(..., description="Educational title generated for the video")
    total_duration_seconds: float = Field(..., description="Total planned duration in seconds")
    learning_objectives: List[str] = Field(..., description="Core learning takeaways")
    scenes: List[RoutedScene] = Field(..., description="Routed educational scenes with engine decisions")
    engine_summary: Dict[str, int] = Field(..., description="Histogram of visual engines allocated")
    planner_used: str = Field(..., description="Identifier of the planner that generated the plan (e.g. 'qwen2.5:3b', 'rule_based')")
