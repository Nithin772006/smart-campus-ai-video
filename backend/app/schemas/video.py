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

class SubtitleSegmentItem(BaseModel):
    id: int = Field(..., description="Segment sequential index")
    start: float = Field(..., description="Segment start timestamp in seconds")
    end: float = Field(..., description="Segment end timestamp in seconds")
    text: str = Field(..., description="Transcribed text content")

class SubtitleResponse(BaseModel):
    success: bool = Field(True, description="Transcription status flag")
    audio_path: str = Field(..., description="Path to source audio file", example="generated/audio/newtons_second_law/narration.wav")
    subtitle_srt_path: str = Field(..., description="Relative path to generated SRT subtitle file", example="generated/subtitles/newtons_second_law/subtitles.srt")
    subtitle_vtt_path: str = Field(..., description="Relative path to generated WebVTT subtitle file", example="generated/subtitles/newtons_second_law/subtitles.vtt")
    transcription_path: str = Field(..., description="Relative path to transcription JSON file", example="generated/subtitles/newtons_second_law/transcription.json")
    text: str = Field(..., description="Full transcribed text")
    duration_seconds: float = Field(..., description="Measured audio duration in seconds")
    segment_count: int = Field(..., description="Total number of timestamped segments")
    language: str = Field("en", description="Detected or requested language code")
    generation_time_seconds: float = Field(..., description="Elapsed transcription time in seconds")
    device: str = Field(..., description="Inference device used (cuda or cpu)")
    segments: Optional[List[Dict[str, Any]]] = Field(None, description="Detailed timestamped segments")

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
    target_duration_seconds: Optional[float] = Field(None, description="Target narration duration in seconds", example=30.0)


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
    target_duration_seconds: Optional[float] = Field(None, description="Target duration in seconds")
    speech_rate_wpm: Optional[float] = Field(None, description="Actual speaking rate in words per minute")
    actual_wpm: Optional[float] = Field(None, description="Actual speaking rate in words per minute")
    estimated_wpm: Optional[float] = Field(None, description="Estimated speaking rate before synthesis")
    estimated_duration_seconds: Optional[float] = Field(None, description="Estimated duration in seconds")
    word_count: Optional[int] = Field(None, description="Narration word count")


class VideoCompositionRequest(BaseModel):
    video_path: str = Field(..., description="Path to input Manim/scene MP4 video")
    audio_path: str = Field(..., description="Path to input narration WAV/audio file")
    subtitle_path: Optional[str] = Field(None, description="Optional path to SRT subtitles to burn")
    output_path: Optional[str] = Field(None, description="Optional destination path for final MP4")
    output_name: Optional[str] = Field(None, description="Optional output file name")
    burn_subtitles: Optional[bool] = Field(None, description="Override whether to burn subtitles into video")


class VideoCompositionResponse(BaseModel):
    success: bool = Field(True, description="Composition status flag")
    video_path: str = Field(..., description="Relative web path to final composed MP4")
    video_url: Optional[str] = Field(None, description="Direct URL or web path to composed MP4")
    duration_seconds: float = Field(..., description="Final composed video duration in seconds")
    video_duration_seconds: float = Field(..., description="Original input visual video duration")
    audio_duration_seconds: float = Field(..., description="Original input narration audio duration")
    sync_difference: Optional[float] = Field(0.0, description="Duration difference between video and audio in seconds")
    audio_speed: Optional[str] = Field("1.00x", description="Audio playback speed factor")
    is_synchronized: Optional[bool] = Field(True, description="Sync validation status")
    file_size_mb: Optional[float] = Field(None, description="Final MP4 file size in megabytes")
    output_size_mb: Optional[float] = Field(None, description="Final MP4 file size in megabytes")
    has_video: bool = Field(True, description="Whether final video contains video track")
    has_audio: bool = Field(True, description="Whether final video contains audio track")
    has_subtitles: bool = Field(True, description="Whether subtitles were burned into video")
    subtitles_burned: Optional[bool] = Field(True, description="Whether subtitles were burned into video")
    generation_time_seconds: float = Field(..., description="Time taken for FFmpeg composition in seconds")
    width: Optional[int] = Field(None, description="Output video width")
    height: Optional[int] = Field(None, description="Output video height")
    fps: Optional[float] = Field(None, description="Output video frame rate")
    video_codec: Optional[str] = Field(None, description="Video codec name")
    audio_codec: Optional[str] = Field(None, description="Audio codec name")
    pixel_format: Optional[str] = Field(None, description="Pixel format")


class ElevenLabsVoiceItem(BaseModel):
    voice_id: str = Field(..., description="Unique ElevenLabs voice ID")
    name: str = Field(..., description="Voice display name")
    category: Optional[str] = Field("premade", description="Voice category (premade, cloned, generated)")
    labels: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Voice descriptive labels")
    preview_url: Optional[str] = Field(None, description="Preview audio sample URL")
    description: Optional[str] = Field(None, description="Voice summary or style description")


class ElevenLabsVoicesResponse(BaseModel):
    success: bool = Field(True, description="Query status flag")
    voices: List[ElevenLabsVoiceItem] = Field(default_factory=list, description="List of available ElevenLabs voices")
    count: int = Field(0, description="Total voices returned")


class ElevenLabsTTSRequest(BaseModel):
    text: str = Field(..., description="Text content to synthesize to audio", example="Newton's Second Law states that force equals mass times acceleration.")
    voice_id: Optional[str] = Field(None, description="ElevenLabs voice identifier")
    language: Optional[str] = Field("en", description="Target language code: en, ta, hi")
    timestamps: Optional[bool] = Field(True, description="Whether to request character-level timestamps")
    topic: Optional[str] = Field(None, description="Educational topic name for directory slug")


class ElevenLabsTTSResponse(BaseModel):
    success: bool = Field(True, description="Synthesis status flag")
    provider: str = Field("elevenlabs", description="TTS provider name")
    audio_path: str = Field(..., description="Relative path to generated WAV/MP3 audio file")
    mp3_path: Optional[str] = Field(None, description="Relative path to generated MP3 file")
    duration_seconds: float = Field(..., description="Exact audio duration in seconds")
    language: str = Field("en", description="Spoken language code")
    voice_id: str = Field(..., description="ElevenLabs voice ID used")
    model: str = Field("eleven_multilingual_v2", description="ElevenLabs model used")
    timestamp_data_available: bool = Field(True, description="Whether character-level alignment data is present")
    alignment: Optional[Dict[str, Any]] = Field(None, description="Alignment character and timestamp data")
    sample_rate: Optional[int] = Field(None, description="Audio sample rate in Hz")
    text_length: Optional[int] = Field(None, description="Input text character count")
    generation_time_seconds: Optional[float] = Field(None, description="Time taken to generate audio")
    fallback_used: Optional[bool] = Field(False, description="Whether fallback TTS was used")
    fallback_reason: Optional[str] = Field(None, description="Reason for fallback if applicable")


class FullVideoRequest(BaseModel):
    topic: Optional[str] = Field(None, description="Educational topic to plan, render, narrate, subtitle, and compose")
    question: Optional[str] = Field(None, description="Alternative phrasing for educational topic")
    quality: Optional[str] = Field("medium_quality", description="Manim render quality: low_quality, medium_quality, high_quality")
    burn_subtitles: Optional[bool] = Field(True, description="Whether to burn subtitles into final MP4")
    language: Optional[str] = Field("en", description="Narration language code")
    target_duration_seconds: Optional[float] = Field(30.0, description="Target video duration in seconds (e.g. 30, 45, 60, 90, 120)")
    character: Optional[bool] = Field(False, description="Whether to include the AI Teacher avatar layer")
    character_position: Optional[str] = Field("auto", description="Position of AI Teacher avatar: auto, left, right")
    visual_style: Optional[str] = Field("academic", description="Visual style: academic, explainer, classroom")
    voice_provider: Optional[str] = Field("indicf5", description="TTS voice provider: 'indicf5' or 'elevenlabs'")
    audio_provider: Optional[str] = Field(None, description="Alias for voice_provider")
    voice_id: Optional[str] = Field(None, description="Voice ID if using ElevenLabs")

    def get_prompt(self) -> str:
        prompt = (self.topic or self.question or "").strip()
        if not prompt:
            raise ValueError("Either 'topic' or 'question' must be provided.")
        return prompt

    def get_voice_provider(self) -> str:
        return (self.audio_provider or self.voice_provider or "indicf5").strip().lower()


class FullVideoResponse(BaseModel):
    success: bool = Field(True, description="Overall pipeline status flag")
    topic: str = Field(..., description="Resolved educational topic")
    video_path: str = Field(..., description="Relative path to final composed MP4")
    video_url: Optional[str] = Field(None, description="Direct URL or web path to video")
    duration_seconds: float = Field(..., description="Final composed video duration")
    scene_count: int = Field(..., description="Number of visual scenes")
    video_duration_seconds: Optional[float] = Field(None, description="Original input visual video duration")
    audio_duration_seconds: float = Field(..., description="Duration of synthesized narration audio")
    sync_difference: Optional[float] = Field(0.0, description="Difference between video and audio durations")
    audio_speed: Optional[str] = Field("1.00x", description="Audio playback speed factor")
    is_synchronized: Optional[bool] = Field(True, description="Whether sync validation passed")
    subtitle_segment_count: int = Field(..., description="Number of timestamped subtitle cues")
    subtitles_burned: Optional[bool] = Field(True, description="Whether subtitles were burned into video")
    has_subtitles: Optional[bool] = Field(True, description="Whether subtitles were burned into video")
    video_codec: Optional[str] = Field(None, description="Video codec")
    audio_codec: Optional[str] = Field(None, description="Audio codec")
    pixel_format: Optional[str] = Field(None, description="Pixel format")
    speech_rate_wpm: Optional[float] = Field(None, description="Actual speaking rate in words per minute")
    actual_wpm: Optional[float] = Field(None, description="Actual speaking rate in words per minute")
    estimated_wpm: Optional[float] = Field(None, description="Estimated speaking rate before synthesis")
    estimated_duration_seconds: Optional[float] = Field(None, description="Estimated narration duration in seconds")
    target_duration_seconds: Optional[float] = Field(30.0, description="Target duration in seconds")
    narration_words: Optional[int] = Field(None, description="Word count of spoken narration")
    generation_time_seconds: float = Field(..., description="Total pipeline execution time in seconds")
    file_size_mb: Optional[float] = Field(None, description="Output video file size in megabytes")
    output_size_mb: Optional[float] = Field(None, description="Output video file size in megabytes")
    plan: Optional[dict] = Field(None, description="Structured EducationalVideoPlan")
    narration_path: Optional[str] = Field(None, description="Path to generated narration WAV")
    subtitle_path: Optional[str] = Field(None, description="Path to generated SRT subtitles")
    character_enabled: Optional[bool] = Field(False, description="Whether AI teacher character was included")
    character_position: Optional[str] = Field(None, description="Position used for AI teacher character")
    character_video_path: Optional[str] = Field(None, description="Path to generated character video track")
    voice_provider: Optional[str] = Field("indicf5", description="Voice provider used")
    voice_id: Optional[str] = Field(None, description="Voice ID used")
    language: Optional[str] = Field("en", description="Requested narration language")
    actual_language: Optional[str] = Field("en", description="Actual language synthesized")
    fallback_used: Optional[bool] = Field(False, description="Whether fallback TTS was used")
    fallback_reason: Optional[str] = Field(None, description="Reason for fallback if used")
    localization_fallback: Optional[bool] = Field(False, description="Whether localization fell back to English")






