"""
End-to-End Pipeline: Script / Structured Scenes -> Complete Video
"""
from app.schemas.video import VideoGenerationRequest, VideoGenerationResponse
from app.services.ltx_service import LTXService
from app.services.indicf5_service import IndicF5Service
from app.services.whisper_service import WhisperService
from app.services.ffmpeg_service import FFmpegService

class ScriptToVideoPipeline:
    def __init__(self):
        self.ltx = LTXService()
        self.tts = IndicF5Service()
        self.whisper = WhisperService()
        self.ffmpeg = FFmpegService()

    async def generate(self, request: VideoGenerationRequest) -> VideoGenerationResponse:
        # Orchestration logic
        audio_path = await self.tts.generate_tts(text=request.script, language=request.language)
        subtitles = await self.whisper.transcribe_audio(audio_path=audio_path)
        
        scene_videos = []
        for i, scene in enumerate(request.scenes):
            scene_video = await self.ltx.generate_scene_video(prompt=scene.description)
            scene_videos.append(scene_video)
            
        final_video = await self.ffmpeg.concatenate_scenes(scene_paths=scene_videos, audio_path=audio_path)
        
        return VideoGenerationResponse(
            video_url=final_video,
            duration=request.duration_sec,
            status="completed"
        )
