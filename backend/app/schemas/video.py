from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.schemas.scene import Scene, EducationalVideoPlan

class VideoRequest(BaseModel):
    script: str = Field(..., description="Full narration or instructional script", example="Isaac Newton formulated the laws of motion in 1687.")
    language: str = Field("en", description="Target language code", example="en")
    title: Optional[str] = Field(None, description="Optional title for the video project", example="Newton's Laws of Motion")
    output_format: Optional[str] = Field("mp4", description="Output container format", example="mp4")
    scenes: Optional[List[Scene]] = Field(default=None, description="Optional pre-structured scene breakdown")

class TopicVideoRequest(BaseModel):
    topic: str = Field(..., description="High-level topic or lesson subject", example="Photosynthesis in plants")
    language: str = Field("en", description="Target language code", example="en")
    title: Optional[str] = Field(None, description="Optional video title", example="How Photosynthesis Works")
    target_duration: Optional[float] = Field(30.0, description="Target video duration in seconds", example=30.0)
    output_format: Optional[str] = Field("mp4", description="Output container format", example="mp4")

class AudioRequest(BaseModel):
    text: str = Field(..., description="Text content to be spoken", example="Welcome to SmartCampus AI.")
    language: str = Field("en", description="Language code for voice synthesis", example="en")
    voice: Optional[str] = Field("default", description="Voice identifier or speaker style", example="default")

class SubtitleRequest(BaseModel):
    audio_path: str = Field(..., description="Path to generated or source audio file", example="generated/audio/narration.wav")
    language: Optional[str] = Field("auto", description="Transcription language code or 'auto'", example="auto")

class PipelineStatusResponse(BaseModel):
    status: str = Field("not_implemented", example="not_implemented")
    message: str = Field(..., example="Pipeline will be implemented in the next milestone.")
    pipeline: Optional[str] = None

class ManimVideoRequest(BaseModel):
    topic: str = Field(..., description="Educational topic to animate", example="Newton's Second Law")
    quality: Optional[str] = Field("medium_quality", description="Render quality: low_quality, medium_quality, high_quality", example="medium_quality")

class ManimVideoResponse(BaseModel):
    success: bool = Field(True, description="Render status flag", example=True)
    topic: str = Field(..., description="Topic of generated scene", example="Newton's Second Law")
    video_path: str = Field(..., description="Path to generated MP4 video", example="generated/scenes/newton_second_law/newton_second_law.mp4")
    duration_seconds: float = Field(..., description="Video duration in seconds", example=13.6)
    generation_time_seconds: float = Field(..., description="Total time taken to render video in seconds", example=8.5)
    output_size_mb: float = Field(..., description="Output video file size in megabytes", example=0.65)

class DynamicTopicRequest(BaseModel):
    question: str = Field(..., description="Academic question or lesson subject to explain", example="Explain photosynthesis")
    quality: Optional[str] = Field("medium_quality", description="Manim render quality: low_quality, medium_quality, high_quality", example="medium_quality")

class DynamicTopicResponse(BaseModel):
    success: bool = Field(True, description="Generation status flag", example=True)
    question: str = Field(..., description="Original user prompt or question", example="Explain photosynthesis")
    topic: str = Field(..., description="Resolved academic topic", example="Photosynthesis")
    video_path: str = Field(..., description="Path to generated combined MP4 video", example="generated/scenes/photosynthesis/photosynthesis.mp4")
    duration_seconds: float = Field(..., description="Final combined video duration in seconds", example=24.5)
    generation_time_seconds: float = Field(..., description="Total time taken to generate video in seconds", example=18.2)
    scene_count: int = Field(..., description="Number of visual scenes concatenated", example=4)
    output_size_mb: Optional[float] = Field(None, description="Output video file size in MB", example=1.2)


class LLMTopicRequest(BaseModel):
    topic: Optional[str] = Field(None, description="Academic topic or prompt to plan and animate", example="Explain Newton's Second Law")
    question: Optional[str] = Field(None, description="Alternative field for academic question", example="Explain Newton's Second Law")
    quality: Optional[str] = Field("medium_quality", description="Manim render quality: low_quality, medium_quality, high_quality", example="medium_quality")

    def get_prompt(self) -> str:
        prompt = (self.topic or self.question or "").strip()
        if not prompt:
            raise ValueError("Either 'topic' or 'question' must be provided.")
        return prompt


class LLMTopicResponse(BaseModel):
    success: bool = Field(True, description="Generation status flag", example=True)
    topic: str = Field(..., description="Resolved educational topic", example="Newton's Second Law")
    video_path: str = Field(..., description="Path to generated MP4 video", example="generated/scenes/newtons_second_law/newtons_second_law.mp4")
    duration_seconds: float = Field(..., description="Final combined video duration in seconds", example=20.0)
    generation_time_seconds: float = Field(..., description="Total time taken to generate video in seconds", example=14.5)
    scene_count: int = Field(..., description="Number of visual scenes concatenated", example=4)
    output_size_mb: Optional[float] = Field(None, description="Output video file size in MB", example=0.85)
    plan: Optional[dict] = Field(None, description="Structured EducationalVideoPlan generated by LLM")
    used_fallback: bool = Field(False, description="Flag indicating if rule-based fallback planner was used", example=False)
    planner: str = Field("ollama/qwen2.5:3b", description="Identifier of the planner used", example="ollama/qwen2.5:3b")


class TTSTestRequest(BaseModel):
    text: str = Field(..., description="Text content to synthesize to audio", example="Newton's Second Law states that force equals mass multiplied by acceleration.")
    language: Optional[str] = Field("en", description="Spoken language code", example="en")


class TTSPlanRequest(BaseModel):
    plan: Optional[EducationalVideoPlan] = Field(None, description="Structured EducationalVideoPlan object")
    topic: Optional[str] = Field(None, description="Direct topic if plan is passed at root level")
    title: Optional[str] = Field(None, description="Direct title if plan is passed at root level")
    scenes: Optional[List[dict]] = Field(None, description="Direct scenes if plan is passed at root level")


class TTSAudioResponse(BaseModel):
    success: bool = Field(True, description="TTS generation status flag")
    audio_path: str = Field(..., description="Relative web path to generated WAV audio file", example="generated/audio/newtons_second_law/narration.wav")
    duration_seconds: float = Field(..., description="Exact duration of generated audio in seconds", example=7.14)
    sample_rate: int = Field(24000, description="Audio sample rate in Hertz", example=24000)
    text_length: int = Field(..., description="Character count of synthesized narration", example=81)
    generation_time_seconds: float = Field(..., description="Elapsed synthesis time in seconds", example=7.32)
    narration_text: Optional[str] = Field(None, description="Spoken narration text that was synthesized")
    topic: Optional[str] = Field(None, description="Educational topic name")
    scene_scripts: Optional[List[dict]] = Field(None, description="Per-scene narration breakdowns")




