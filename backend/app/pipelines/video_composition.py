"""
Video composition pipelines for SmartCampus AI Video.
Orchestrates media validation, subtitle burning, and full end-to-end educational video synthesis.
"""

import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from app.config import settings
from app.services.ffmpeg_service import ffmpeg_service
from app.services.llm_planner import llm_academic_planner
from app.services.manim_service import render_educational_plan_to_video
from app.services.narration_service import narration_service
from app.services.indicf5_service import indicf5_service
from app.services.subtitle_service import subtitle_service

logger = logging.getLogger(__name__)


class VideoCompositionPipeline:
    """
    Pipeline for merging an existing Manim video, IndicF5 narration WAV, and Whisper SRT subtitles.
    """

    def __init__(self):
        self.ffmpeg = ffmpeg_service

    def compose(
        self,
        video_path: str,
        audio_path: str,
        subtitle_path: Optional[str] = None,
        output_path: Optional[str] = None,
        output_name: Optional[str] = None,
        burn_subtitles: Optional[bool] = None,
        character_enabled: bool = False,
        character_position: str = "auto",
        character_image_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validate input media and compose with FFmpeg, with optional AI Teacher avatar layer.
        """
        logger.info(
            "[Pipeline] Composing video: %s with audio: %s (character: %s, pos: %s)",
            video_path,
            audio_path,
            character_enabled,
            character_position,
        )

        result = self.ffmpeg.compose(
            video_path=video_path,
            audio_path=audio_path,
            subtitle_path=subtitle_path,
            output_path=output_path,
            output_name=output_name,
            burn_subtitles=burn_subtitles,
            character_enabled=character_enabled,
            character_position=character_position,
            character_image_path=character_image_path,
        )


        logger.info(
            "[Pipeline] Video composed successfully: %s (duration: %.2fs, size: %.2fMB)",
            result["video_path"],
            result["duration_seconds"],
            result["file_size_mb"],
        )
        return result


class FullEducationalVideoPipeline:
    """
    Complete end-to-end educational video synthesis pipeline:
    Qwen2.5 3B (Plan) -> Manim (Visual MP4) + IndicF5 (Narration WAV) + faster-whisper (SRT) -> FFmpeg (Final MP4)
    Reuses existing singleton services without duplication.
    """

    def __init__(self):
        self.composition_pipeline = VideoCompositionPipeline()

    def generate(
        self,
        topic: str,
        quality: str = "medium_quality",
        burn_subtitles: bool = True,
        language: str = "en",
        target_duration_seconds: Optional[float] = None,
        character: bool = False,
        character_position: str = "auto",
        visual_style: str = "academic",
    ) -> Dict[str, Any]:
        """
        Execute full educational pipeline from academic topic to final burned MP4 video,
        with optional AI Teacher avatar layer.
        """
        total_start = time.time()
        eff_target_duration = target_duration_seconds or settings.DEFAULT_TARGET_DURATION_SECONDS
        logger.info(
            "[FullPipeline] Starting end-to-end generation for topic: '%s' (target duration: %.1fs, character: %s, pos: %s)",
            topic,
            eff_target_duration,
            character,
            character_position,
        )

        # -------------------------------------------------------------
        # Stage 1: LLM Planning with Qwen2.5 3B (with rule-based fallback)
        # -------------------------------------------------------------
        logger.info("[FullPipeline] Stage 1/6: Generating educational video plan...")
        plan, used_fallback, planner_name = llm_academic_planner.plan_with_fallback(topic)

        resolved_topic = plan.topic or topic
        logger.info("[FullPipeline] Plan generated: %d scenes using %s", len(plan.scenes), planner_name)

        # -------------------------------------------------------------
        # Stage 2: Visual Video Rendering with Dynamic Manim
        # -------------------------------------------------------------
        logger.info("[FullPipeline] Stage 2/6: Rendering visual animation scenes with Manim...")
        manim_result = render_educational_plan_to_video(
            plan=plan,
            question=resolved_topic,
            output_dir=None,
            quality=quality,
            allow_specialized_fast_path=False,
        )
        video_path = manim_result["video_path"]
        manim_dur = manim_result["duration_seconds"]
        logger.info("[FullPipeline] Manim video rendered: %s (%.2fs)", video_path, manim_dur)
        logger.info("[SYNC] Manim video duration: %.2fs", manim_dur)

        # -------------------------------------------------------------
        # Stage 3: Educator Voiceover Narration with IndicF5
        # -------------------------------------------------------------
        logger.info("[FullPipeline] Stage 3/6: Synthesizing spoken voiceover with IndicF5...")
        tts_result = indicf5_service.generate_plan_narration(
            plan=plan,
            target_duration_seconds=eff_target_duration,
        )
        audio_path = tts_result["audio_path"]
        audio_dur = tts_result["duration_seconds"]
        logger.info("[FullPipeline] Audio synthesized: %s (%.2fs)", audio_path, audio_dur)
        logger.info("[SYNC] IndicF5 audio duration: %.2fs", audio_dur)

        # -------------------------------------------------------------
        # Stage 4: Subtitle Generation & Alignment with faster-whisper
        # -------------------------------------------------------------
        logger.info("[FullPipeline] Stage 4/6: Aligning timestamps & subtitles with faster-whisper...")
        sub_result = subtitle_service.process_audio(
            audio_path=audio_path,
            language=language,
        )
        subtitle_path = sub_result["subtitle_srt_path"]
        sub_segments = sub_result.get("segments", [])
        sub_final_ts = sub_segments[-1]["end"] if sub_segments else None
        if sub_final_ts is not None:
            logger.info("[SYNC] Whisper final timestamp: %.2fs", sub_final_ts)
        logger.info(
            "[FullPipeline] Subtitles generated: %s (%d segments)",
            subtitle_path,
            sub_result["segment_count"],
        )

        # Master Audio Timeline Confirmation
        logger.info("[SYNC] Master duration: %.2fs", audio_dur)
        logger.info("[SYNC] Audio speed modification: NONE")

        # -------------------------------------------------------------
        # Stage 5: Optional AI Teacher Character Layer
        # -------------------------------------------------------------
        if character:
            logger.info("[FullPipeline] Stage 5/6: Preparing AI Teacher character overlay (%s)...", character_position)
        else:
            logger.info("[FullPipeline] Stage 5/6: Character mode disabled; proceeding directly to composition.")

        # -------------------------------------------------------------
        # Stage 6: Final FFmpeg Composition
        # -------------------------------------------------------------
        logger.info("[FullPipeline] Stage 6/6: Composing final video with FFmpeg...")
        comp_result = self.composition_pipeline.compose(
            video_path=video_path,
            audio_path=audio_path,
            subtitle_path=subtitle_path,
            burn_subtitles=burn_subtitles,
            character_enabled=character,
            character_position=character_position,
        )


        logger.info("[SYNC] Final MP4 duration: %.2fs", comp_result["duration_seconds"])
        logger.info("[SYNC] Sync difference: %.3fs", comp_result.get("sync_difference", 0.0))

        # -------------------------------------------------------------
        # Requirement 16: Synchronization Report Banner
        # -------------------------------------------------------------
        words_count = tts_result.get("word_count", 0)
        target_wpm = tts_result.get("target_wpm", settings.NARRATION_TARGET_WPM)
        est_narration_dur = tts_result.get("estimated_duration_seconds", 0.0)
        actual_indicf5_dur = audio_dur
        actual_wpm = tts_result.get("actual_wpm", 0.0)
        whisper_ts_str = f"{sub_final_ts:.2f}s" if sub_final_ts is not None else "N/A"
        final_mp4_dur = comp_result["duration_seconds"]
        final_sync_diff = comp_result.get("sync_difference", 0.0)

        sync_report = (
            "\n================ SYNC REPORT ================\n\n"
            f"Narration words: {words_count}\n"
            f"Target WPM: {target_wpm}\n"
            f"Estimated narration duration: {est_narration_dur:.2f}s\n"
            f"Actual IndicF5 duration: {actual_indicf5_dur:.2f}s\n"
            f"Actual WPM: {actual_wpm:.1f}\n\n"
            f"Manim duration: {manim_dur:.2f}s\n"
            f"Whisper final timestamp: {whisper_ts_str}\n"
            f"Final MP4 duration: {final_mp4_dur:.2f}s\n\n"
            f"Audio speed modification: NONE\n"
            f"Audio playback speed: 1.00x\n\n"
            f"Final sync difference: {final_sync_diff:.2f}s\n\n"
            "=============================================="
        )
        logger.info(sync_report)
        print(sync_report)

        total_elapsed = round(time.time() - total_start, 2)

        return {
            "success": True,
            "topic": resolved_topic,
            "video_path": comp_result["video_path"],
            "video_url": comp_result["video_url"],
            "duration_seconds": comp_result["duration_seconds"],
            "scene_count": len(plan.scenes),
            "video_duration_seconds": manim_dur,
            "audio_duration_seconds": comp_result["audio_duration_seconds"],
            "sync_difference": comp_result.get("sync_difference", 0.0),
            "audio_speed": comp_result.get("audio_speed", "1.00x"),
            "is_synchronized": comp_result.get("is_synchronized", True),
            "subtitle_segment_count": sub_result["segment_count"],
            "subtitles_burned": comp_result.get("subtitles_burned", True),
            "has_subtitles": comp_result.get("has_subtitles", True),
            "video_codec": comp_result.get("video_codec"),
            "audio_codec": comp_result.get("audio_codec"),
            "pixel_format": comp_result.get("pixel_format", settings.PIXEL_FORMAT),
            "speech_rate_wpm": actual_wpm,
            "actual_wpm": actual_wpm,
            "estimated_wpm": tts_result.get("estimated_wpm"),
            "target_duration_seconds": eff_target_duration,
            "estimated_duration_seconds": est_narration_dur,
            "narration_words": words_count,
            "generation_time_seconds": total_elapsed,
            "file_size_mb": comp_result["file_size_mb"],
            "output_size_mb": comp_result.get("output_size_mb", comp_result["file_size_mb"]),
            "plan": plan.model_dump(),
            "narration_path": audio_path,
            "subtitle_path": subtitle_path,
            "used_fallback": used_fallback,
            "planner": planner_name,
            "character_enabled": comp_result.get("character_enabled", False),
            "character_position": comp_result.get("character_position"),
            "character_video_path": comp_result.get("character_path"),
        }



# Singleton pipeline instances
video_composition_pipeline = VideoCompositionPipeline()
full_educational_video_pipeline = FullEducationalVideoPipeline()
