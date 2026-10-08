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
from app.services.audio_provider import get_audio_provider

logger = logging.getLogger(__name__)


class VideoCompositionPipeline:
    """
    Pipeline for merging an existing Manim video, narration WAV, and subtitles.
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
    Qwen2.5 3B (Plan) -> Manim (Visual MP4) + AudioProvider (Narration WAV/MP3) + SubtitleService (SRT) -> FFmpeg (Final MP4)
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
        voice_provider: str = "indicf5",
        audio_provider: Optional[str] = None,
        voice_id: Optional[str] = None,
        progress_tracker: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Execute full educational pipeline from academic topic to final burned MP4 video,
        with optional AI Teacher avatar layer, configurable TTS provider (IndicF5 / ElevenLabs),
        and real-time per-stage progress tracking.
        """
        total_start = time.time()
        eff_target_duration = target_duration_seconds or settings.DEFAULT_TARGET_DURATION_SECONDS
        selected_provider_name = (audio_provider or voice_provider or "indicf5").strip().lower()

        logger.info(
            "[FullPipeline] Starting end-to-end generation for topic: '%s' "
            "(target duration: %.1fs, provider: %s, lang: %s, character: %s, pos: %s)",
            topic,
            eff_target_duration,
            selected_provider_name,
            language,
            character,
            character_position,
        )

        def _update(stage_id: str, pct: int, status: str = "running", msg: str = ""):
            if progress_tracker:
                progress_tracker.update_stage(stage_id, pct, status=status, message=msg)

        # -------------------------------------------------------------
        # Stage 1: Understanding Topic
        # -------------------------------------------------------------
        logger.info("[FullPipeline] Stage 1/7: Understanding topic...")
        _update("understanding_topic", 25, "running", f"Analyzing topic '{topic}' and pedagogical objectives...")
        clean_topic = topic.strip()
        if not clean_topic:
            if progress_tracker:
                progress_tracker.mark_error("understanding_topic", "Topic cannot be empty.")
            raise ValueError("Topic cannot be empty.")

        _update("understanding_topic", 75, "running", f"Target duration: {eff_target_duration:.0f}s, Quality: {quality}")
        time.sleep(0.05)
        _update("understanding_topic", 100, "completed", f"Topic verified: '{clean_topic}'")

        # -------------------------------------------------------------
        # Stage 2: Creating Lesson (LLM Planning with Qwen2.5 3B)
        # -------------------------------------------------------------
        logger.info("[FullPipeline] Stage 2/7: Creating lesson plan with Qwen2.5 3B...")
        _update("creating_lesson", 20, "running", "Structuring pedagogical video plan via Qwen2.5 3B...")
        try:
            plan, used_fallback, planner_name = llm_academic_planner.plan_with_fallback(clean_topic)
            resolved_topic = plan.topic or clean_topic
            logger.info("[FullPipeline] Plan generated: %d scenes using %s", len(plan.scenes), planner_name)
            _update("creating_lesson", 85, "running", f"Organized {len(plan.scenes)} scenes via {planner_name}...")
            time.sleep(0.05)
            _update("creating_lesson", 100, "completed", f"Created {len(plan.scenes)} educational scenes ({planner_name})")
        except Exception as e:
            if progress_tracker:
                progress_tracker.mark_error("creating_lesson", str(e))
            raise

        # -------------------------------------------------------------
        # Stage 3: Rendering Educational Visuals (Dynamic Manim)
        # -------------------------------------------------------------
        logger.info("[FullPipeline] Stage 3/7: Rendering visual animation scenes with Manim...")
        scene_count = len(plan.scenes)
        _update("rendering_visuals", 15, "running", f"Compiling Manim scene graphs ({scene_count} scenes)...")
        try:
            _update("rendering_visuals", 35, "running", f"Rendering programmatic animation scenes ({quality})...")
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
            _update("rendering_visuals", 85, "running", "Stitching scene clips and applying safe bounds...")
            time.sleep(0.05)
            _update("rendering_visuals", 100, "completed", f"Rendered {scene_count} visual scenes ({manim_dur:.1f}s)")
        except Exception as e:
            if progress_tracker:
                progress_tracker.mark_error("rendering_visuals", str(e))
            raise

        # -------------------------------------------------------------
        # Stage 4: Generating Narration (AudioProvider: IndicF5 / ElevenLabs)
        # -------------------------------------------------------------
        provider_label = "ElevenLabs" if selected_provider_name == "elevenlabs" else "IndicF5"
        logger.info(f"[FullPipeline] Stage 4/7: Synthesizing spoken voiceover with {provider_label}...")
        _update("generating_narration", 15, "running", f"Synthesizing spoken voiceover via {provider_label} ({language})...")
        try:
            tts_provider = get_audio_provider(selected_provider_name)
            tts_result = tts_provider.generate_plan_narration(
                plan=plan,
                target_duration_seconds=eff_target_duration,
                language=language,
                voice_id=voice_id,
            )
            audio_path = tts_result["audio_path"]
            audio_dur = tts_result["duration_seconds"]
            actual_provider = tts_result.get("provider_used", selected_provider_name)
            fallback_used = tts_result.get("fallback_used", False)
            fallback_reason = tts_result.get("fallback_reason")
            actual_lang = tts_result.get("actual_language", language)
            loc_fallback = tts_result.get("localization_fallback", False)

            logger.info(
                f"[FullPipeline] Audio synthesized: {audio_path} ({audio_dur:.2f}s, "
                f"provider={actual_provider}, lang={actual_lang}, fallback={fallback_used})"
            )
            logger.info("[SYNC] Narration audio duration: %.2fs", audio_dur)
            actual_wpm = tts_result.get("actual_wpm", 0.0)

            msg = f"Synthesized narration ({audio_dur:.1f}s, {actual_wpm:.1f} WPM, {actual_provider}, {actual_lang})"
            if fallback_used:
                msg += f" (Fallback: {fallback_reason})"
            _update("generating_narration", 100, "completed", msg)
        except Exception as e:
            if progress_tracker:
                progress_tracker.mark_error("generating_narration", str(e))
            raise

        # -------------------------------------------------------------
        # Stage 5: Creating Subtitles (ElevenLabs Timestamps or faster-whisper)
        # -------------------------------------------------------------
        logger.info("[FullPipeline] Stage 5/7: Generating subtitles & aligning timestamps...")
        _update("creating_subtitles", 20, "running", "Aligning timestamps and formatting subtitles...")
        try:
            sub_result = subtitle_service.process_audio(
                audio_path=audio_path,
                language=actual_lang,
                alignment_data=tts_result.get("alignment"),
            )
            subtitle_path = sub_result["subtitle_srt_path"]
            sub_segments = sub_result.get("segments", [])
            sub_final_ts = sub_segments[-1]["end"] if sub_segments else None
            sub_source = sub_result.get("source", "whisper")

            if sub_final_ts is not None:
                logger.info("[SYNC] Subtitle final timestamp: %.2fs (source: %s)", sub_final_ts, sub_source)
            logger.info(
                "[FullPipeline] Subtitles generated: %s (%d segments, source: %s)",
                subtitle_path,
                sub_result["segment_count"],
                sub_source,
            )
            _update("creating_subtitles", 100, "completed", f"Aligned {sub_result['segment_count']} subtitle segments ({sub_source})")
        except Exception as e:
            if progress_tracker:
                progress_tracker.mark_error("creating_subtitles", str(e))
            raise

        # Master Audio Timeline Confirmation
        logger.info("[SYNC] Master duration: %.2fs", audio_dur)
        logger.info("[SYNC] Audio speed modification: NONE")

        # -------------------------------------------------------------
        # Stage 6: Creating AI Teacher Character Layer
        # -------------------------------------------------------------
        logger.info("[FullPipeline] Stage 6/7: AI Teacher configuration (character: %s)...", character)
        if character:
            _update("creating_teacher", 30, "running", f"Preparing transparent 3D educator presenter ({character_position})...")
            time.sleep(0.05)
            _update("creating_teacher", 100, "completed", f"AI Teacher presenter configured ({character_position})")
        else:
            _update("creating_teacher", 100, "completed", "Character overlay skipped (disabled)")

        # -------------------------------------------------------------
        # Stage 7: Composing Final Video (FFmpeg)
        # -------------------------------------------------------------
        logger.info("[FullPipeline] Stage 7/7: Composing final video with FFmpeg...")
        _update("composing_final_video", 20, "running", "Multiplexing video, audio, subtitles, and avatar via FFmpeg...")
        try:
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
            _update("composing_final_video", 100, "completed", f"Final video rendered ({comp_result['duration_seconds']:.1f}s, {comp_result['file_size_mb']:.1f}MB)")
        except Exception as e:
            if progress_tracker:
                progress_tracker.mark_error("composing_final_video", str(e))
            raise

        # -------------------------------------------------------------
        # Requirement 16: Synchronization Report Banner
        # -------------------------------------------------------------
        words_count = tts_result.get("word_count", 0)
        target_wpm = tts_result.get("target_wpm", settings.NARRATION_TARGET_WPM)
        est_narration_dur = tts_result.get("estimated_duration_seconds", 0.0)
        actual_indicf5_dur = audio_dur
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

        output_payload = {
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
            "voice_provider": actual_provider,
            "audio_provider": actual_provider,
            "voice_id": tts_result.get("voice_id"),
            "language": language,
            "actual_language": actual_lang,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "localization_fallback": loc_fallback,
            "script_ratio": tts_result.get("script_ratio"),
        }

        if progress_tracker:
            progress_tracker.mark_completed(output_payload)

        return output_payload



# Singleton pipeline instances
video_composition_pipeline = VideoCompositionPipeline()
full_educational_video_pipeline = FullEducationalVideoPipeline()
