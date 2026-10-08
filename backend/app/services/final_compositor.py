"""
Final Video Compositor and Synchronization Service (Task 9D).
Combines multi-engine rendered scene MP4s, master narration WAV, and Whisper subtitles
into a single, high-quality, fully-synchronized educational video MP4.

Core Principle: Audio is the Master Clock.
Speech duration is authoritative. Visual scenes naturally adapt through frame-holding (tpad)
or trimming. Audio speed is never altered.
"""

import os
import sys
import json
import time
import shutil
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union

from app.config import settings
from app.schemas.composition import (
    SceneTimelineItem,
    VideoTimeline,
    CompositionRequest,
    ComposedVideoResult,
)
from app.schemas.render import RenderedScene
from app.services.ffmpeg_service import (
    ffmpeg_service,
    find_ffmpeg_binary,
    validate_audio_video_sync,
    AudioVideoSyncError,
    MediaProbeError,
    MediaNotFoundError,
)

logger = logging.getLogger("smartcampus.compositor")


class FinalCompositorError(Exception):
    """Base exception for final compositor failures."""
    pass


class FinalCompositor:
    """
    Production-grade multi-scene video compositor and timeline synchronizer.
    Orchestrates format normalization, crossfade transitions, audio multiplexing,
    subtitle burn-in, timeline export, and rigorous ffprobe quality validation.
    """

    def __init__(self, output_base_dir: Optional[Path] = None):
        self.output_base_dir = output_base_dir or settings.VIDEOS_DIR
        self.output_base_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_bin = find_ffmpeg_binary("ffmpeg")
        self.ffprobe_bin = find_ffmpeg_binary("ffprobe")

    def _ensure_binaries(self):
        """Verify ffmpeg and ffprobe are available."""
        if not self.ffmpeg_bin:
            self.ffmpeg_bin = find_ffmpeg_binary("ffmpeg")
        if not self.ffprobe_bin:
            self.ffprobe_bin = find_ffmpeg_binary("ffprobe")
        if not self.ffmpeg_bin or not self.ffprobe_bin:
            raise FinalCompositorError("FFmpeg or FFprobe binary is not available on this system.")

    def _sanitize_slug(self, topic: str) -> str:
        """Create filesystem-safe directory slug from topic."""
        import re
        s = topic.strip().lower()
        s = re.sub(r"['\"]", "", s)
        s = re.sub(r"[^a-z0-9]+", "_", s)
        return s.strip("_") or "educational_video"

    def _build_fallback_scene_video(
        self,
        scene_id: str,
        duration: float,
        description: str,
        output_path: Path,
    ) -> Path:
        """
        Creates a clean 1280x720 fallback video clip for a failed cloud scene
        using FFmpeg synthetic video generation.
        """
        self._ensure_binaries()
        dur = max(2.0, round(duration, 2))
        clean_text = description.replace("'", "").replace(":", "-")[:80] or "Educational Visual Demonstration"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        vf = (
            f"color=c=0x0f172a:s=1280x720:d={dur}:r=30,"
            f"drawtext=text='SmartCampus AI Educational Concept':fontsize=32:fontcolor=0x38bdf8:x=(w-text_w)/2:y=240,"
            f"drawtext=text='{clean_text}':fontsize=24:fontcolor=0xe2e8f0:x=(w-text_w)/2:y=340"
        )
        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-f", "lavfi",
            "-i", f"color=c=0x0f172a:s=1280x720:d={dur}:r=30",
            "-vf", vf,
            "-c:v", settings.VIDEO_CODEC,
            "-pix_fmt", "yuv420p",
            "-r", "30",
            "-an",
            str(output_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            # Fallback without drawtext if fonts are missing
            cmd_simple = [
                self.ffmpeg_bin,
                "-y",
                "-f", "lavfi",
                "-i", f"color=c=0x0f172a:s=1280x720:d={dur}:r=30",
                "-c:v", settings.VIDEO_CODEC,
                "-pix_fmt", "yuv420p",
                "-r", "30",
                "-an",
                str(output_path),
            ]
            subprocess.run(cmd_simple, capture_output=True, text=True, check=True)

        return output_path

    def _normalize_scene(
        self,
        input_path: Path,
        output_path: Path,
        target_width: int = 1280,
        target_height: int = 720,
        target_fps: int = 30,
    ) -> float:
        """
        Normalizes any input scene video into uniform H.264 / 1280x720 / 30fps / yuv420p / video-only.
        Uses aspect-preserving scale + pad (black letterboxing/pillarboxing) so portrait
        avatar clips and 16:9 manim clips combine seamlessly.
        Returns measured duration of normalized clip.
        """
        self._ensure_binaries()
        vf = (
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
            f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black,"
            f"setsar=1,fps={target_fps}"
        )
        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-i", str(input_path),
            "-vf", vf,
            "-c:v", settings.VIDEO_CODEC,
            "-preset", "fast",
            "-crf", str(settings.VIDEO_CRF),
            "-pix_fmt", "yuv420p",
            "-r", str(target_fps),
            "-an",  # strip internal audio; master narration will be added
            str(output_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise FinalCompositorError(f"Failed to normalize scene {input_path.name}: {res.stderr}")

        probe = ffmpeg_service.probe_media(output_path)
        return float(probe["duration"])

    def _build_xfade_filter(
        self,
        clip_paths: List[Path],
        durations: List[float],
        transition_duration: float = 0.3,
    ) -> Tuple[List[str], str, float]:
        """
        Builds an FFmpeg complex filter chain for seamless crossfade transitions between clips.
        Returns (input_args, filter_complex, final_expected_duration).
        """
        n = len(clip_paths)
        inputs: List[str] = []
        for p in clip_paths:
            inputs.extend(["-i", str(p)])

        if n == 1:
            return inputs, "[0:v]null[vout]", durations[0]

        filter_parts: List[str] = []
        last_out = "[0:v]"
        current_offset = durations[0] - transition_duration
        effective_duration = durations[0]

        for i in range(1, n):
            trans_dur = min(transition_duration, durations[i] / 2.0, durations[i-1] / 2.0)
            current_offset = max(0.1, round(effective_duration - trans_dur, 3))
            next_out = f"[v{i}]" if i < n - 1 else "[vout]"
            part = f"{last_out}[{i}:v]xfade=transition=fade:duration={trans_dur:.2f}:offset={current_offset:.3f}{next_out}"
            filter_parts.append(part)
            last_out = next_out
            effective_duration = round(current_offset + durations[i], 3)

        return inputs, ";".join(filter_parts), effective_duration

    def compose(
        self,
        topic: str,
        scenes: List[Union[RenderedScene, Dict[str, Any]]],
        audio_path: Union[str, Path],
        subtitle_path: Optional[Union[str, Path]] = None,
        output_dir: Optional[Union[str, Path]] = None,
        output_name: str = "final.mp4",
        burn_subtitles: bool = True,
        transition_enabled: bool = True,
        transition_duration_seconds: float = 0.3,
        tolerance_seconds: float = 0.15,
    ) -> ComposedVideoResult:
        """
        Executes full multi-scene composition with audio synchronization.
        """
        start_time = time.perf_counter()
        self._ensure_binaries()

        topic_slug = self._sanitize_slug(topic)
        target_dir = Path(output_dir) if output_dir else self.output_base_dir / topic_slug
        target_dir.mkdir(parents=True, exist_ok=True)
        final_video_path = target_dir / output_name

        resolved_audio = Path(audio_path).resolve()
        if not resolved_audio.exists():
            raise MediaNotFoundError(f"Master narration audio not found at: {resolved_audio}")

        # Probe master audio (The Master Clock)
        audio_probe = ffmpeg_service.probe_media(resolved_audio)
        audio_duration = float(audio_probe["duration"])
        if audio_duration <= 0.0:
            raise MediaProbeError(f"Master audio has invalid duration ({audio_duration}s)")

        logger.info(
            "[FinalCompositor] Starting composition for '%s': audio_dur=%.2fs, scenes=%d",
            topic,
            audio_duration,
            len(scenes),
        )

        temp_dir = Path(tempfile.mkdtemp(prefix=f"compositor_{topic_slug}_"))
        cloud_fallback_used = False
        normalized_scenes: List[Path] = []
        normalized_durations: List[float] = []
        timeline_items: List[SceneTimelineItem] = []
        scene_metadata_list: List[Dict[str, Any]] = []

        try:
            # 1. Process and normalize each scene
            current_time = 0.0
            for idx, raw_sc in enumerate(scenes):
                sc_dict = raw_sc.model_dump() if isinstance(raw_sc, RenderedScene) else dict(raw_sc)
                sc_id = sc_dict.get("scene_id", f"scene_{idx+1}")
                engine = sc_dict.get("engine", "manim")
                success = bool(sc_dict.get("success", True))
                video_str = sc_dict.get("video_path", "")
                planned_dur = float(sc_dict.get("duration_seconds", 4.0))

                video_file: Optional[Path] = None
                if video_str:
                    cand = Path(video_str)
                    if not cand.is_absolute():
                        cand = settings.BASE_DIR / cand
                    if cand.exists() and cand.stat().st_size > 0:
                        video_file = cand

                # Handle scene failure / missing cloud video
                fallback_active = False
                if not success or not video_file:
                    fallback_active = True
                    desc = sc_dict.get("metadata", {}).get("visual_description") or f"Educational Demonstration: {sc_id}"
                    if engine == "cloud_video":
                        cloud_fallback_used = True
                        logger.warning(
                            "[FinalCompositor] Cloud scene %s unavailable (%s). Attempting Manim cinematic fallback visual.",
                            sc_id,
                            sc_dict.get("error", "No credit / disabled"),
                        )
                        # Try ManimRenderer cinematic fallback
                        try:
                            from app.services.renderers.manim_renderer import ManimRenderer
                            from app.schemas.visual_scene import RoutedScene, VisualScene, SceneType, VisualEngine
                            manim_rend = ManimRenderer()
                            fb_scene = VisualScene(
                                scene_id=sc_id,
                                scene_type=SceneType.CINEMATIC,
                                visual_engine=VisualEngine.MANIM,
                                narration=sc_dict.get("metadata", {}).get("narration") or f"Educational scene: {sc_id}",
                                visual_description=desc,
                                educational_goal=sc_dict.get("metadata", {}).get("educational_goal") or desc,
                                duration_seconds=planned_dur,
                            )
                            fb_routed = RoutedScene(scene=fb_scene, selected_engine=VisualEngine.MANIM, routing_reason="Fallback to Manim")
                            manim_res = manim_rend.render(fb_routed, output_dir=temp_dir / f"manim_fb_{sc_id}", quality="low_quality")
                            if manim_res.success and manim_res.video_path:
                                cand_fb = Path(manim_res.video_path)
                                if not cand_fb.is_absolute():
                                    cand_fb = settings.BASE_DIR / cand_fb
                                if cand_fb.exists() and cand_fb.stat().st_size > 0:
                                    video_file = cand_fb
                                    logger.info("[FinalCompositor] Manim cinematic fallback SUCCEEDED for %s", sc_id)
                        except Exception as m_fb_err:
                            logger.warning("[FinalCompositor] Manim fallback failed: %s. Using synthetic clip.", m_fb_err)
                    else:
                        logger.warning("[FinalCompositor] Scene %s failed. Generating fallback visual.", sc_id)

                    if not video_file:
                        fb_path = temp_dir / f"fallback_{sc_id}.mp4"
                        video_file = self._build_fallback_scene_video(
                            scene_id=sc_id,
                            duration=planned_dur,
                            description=desc,
                            output_path=fb_path,
                        )

                # Normalize scene to 1280x720 30fps yuv420p video-only
                norm_path = temp_dir / f"norm_{idx:02d}_{sc_id}.mp4"
                measured_dur = self._normalize_scene(video_file, norm_path)
                normalized_scenes.append(norm_path)
                normalized_durations.append(measured_dur)

                # Record timeline
                timeline_items.append(SceneTimelineItem(
                    scene_id=sc_id,
                    engine=engine,
                    start=round(current_time, 2),
                    end=round(current_time + measured_dur, 2),
                    duration=round(measured_dur, 2),
                    video_path=video_str if not fallback_active else str(norm_path),
                    fallback_used=fallback_active,
                ))
                current_time += measured_dur

                sc_dict["fallback_used"] = fallback_active
                sc_dict["measured_duration"] = measured_dur
                scene_metadata_list.append(sc_dict)

            if not normalized_scenes:
                raise FinalCompositorError(f"No valid scenes available to compose for topic '{topic}'.")

            # 2. Stage A: Join scenes (with or without transitions)
            raw_video_joined = temp_dir / "joined_video.mp4"
            if transition_enabled and len(normalized_scenes) >= 2:
                try:
                    inputs, filter_comp, expected_dur = self._build_xfade_filter(
                        normalized_scenes,
                        normalized_durations,
                        transition_duration=transition_duration_seconds,
                    )
                    cmd_xfade = [
                        self.ffmpeg_bin,
                        "-y",
                        *inputs,
                        "-filter_complex", filter_comp,
                        "-map", "[vout]",
                        "-c:v", settings.VIDEO_CODEC,
                        "-preset", "fast",
                        "-crf", str(settings.VIDEO_CRF),
                        "-pix_fmt", "yuv420p",
                        str(raw_video_joined),
                    ]
                    res_xf = subprocess.run(cmd_xfade, capture_output=True, text=True)
                    if res_xf.returncode != 0:
                        logger.warning("[FinalCompositor] xfade filter failed: %s. Falling back to concat.", res_xf.stderr)
                        self._concat_scenes_demuxer(normalized_scenes, raw_video_joined)
                except Exception as xerr:
                    logger.warning("[FinalCompositor] Crossfade transition error: %s. Falling back to concat.", xerr)
                    self._concat_scenes_demuxer(normalized_scenes, raw_video_joined)
            else:
                self._concat_scenes_demuxer(normalized_scenes, raw_video_joined)

            # Probe joined video duration
            joined_probe = ffmpeg_service.probe_media(raw_video_joined)
            joined_duration = float(joined_probe["duration"])
            logger.info(
                "[FinalCompositor] Joined visual duration: %.2fs (Master audio: %.2fs)",
                joined_duration,
                audio_duration,
            )

            # 3. Stage B: Synchronize Video Timeline to Master Narration
            # (Audio is the Master Clock: visual extends by freezing last frame if shorter, or trims if longer)
            video_filters: List[str] = []
            if audio_duration > joined_duration:
                diff = round(audio_duration - joined_duration, 3)
                video_filters.append(f"tpad=stop_mode=clone:stop_duration={diff}")
                logger.info("[FinalCompositor] Audio longer than visuals. Extending final frame by %.2fs", diff)
                # Adjust last scene on timeline
                if timeline_items:
                    timeline_items[-1].end = round(audio_duration, 2)
                    timeline_items[-1].duration = round(timeline_items[-1].end - timeline_items[-1].start, 2)
            elif joined_duration > audio_duration:
                diff = round(joined_duration - audio_duration, 3)
                if diff > tolerance_seconds:
                    video_filters.append(f"trim=duration={audio_duration},setpts=PTS-STARTPTS")
                    logger.info("[FinalCompositor] Visuals longer than audio. Trimming by %.2fs", diff)
                    # Adjust last scene on timeline
                    if timeline_items:
                        timeline_items[-1].end = round(audio_duration, 2)
                        timeline_items[-1].duration = round(timeline_items[-1].end - timeline_items[-1].start, 2)

            # 4. Stage C: Subtitle integration
            resolved_subtitle: Optional[Path] = None
            if subtitle_path:
                cand_sub = Path(subtitle_path).resolve()
                if cand_sub.exists() and cand_sub.stat().st_size > 0:
                    resolved_subtitle = cand_sub
                    # Copy to final directory as final.srt
                    dest_srt = target_dir / f"{final_video_path.stem}.srt"
                    try:
                        shutil.copy2(cand_sub, dest_srt)
                    except Exception as e:
                        logger.warning("Could not copy subtitle to destination: %e", e)

            if burn_subtitles and resolved_subtitle:
                from app.services.safe_area import build_ffmpeg_subtitle_filter
                sub_filter_str = build_ffmpeg_subtitle_filter(
                    resolved_subtitle,
                    video_width=1280,
                    video_height=720,
                    font_size=24,
                    margin_v=40,
                    margin_side=80,
                )
                video_filters.append(sub_filter_str)
                logger.info("[FinalCompositor] Subtitles will be burned into video: %s", resolved_subtitle.name)

            # 5. Stage D: Final Multiplexing (H.264 + AAC 128kbps + faststart)
            cmd_final = [
                self.ffmpeg_bin,
                "-y",
                "-i", str(raw_video_joined),
                "-i", str(resolved_audio),
            ]

            if video_filters:
                cmd_final.extend(["-vf", ",".join(video_filters)])

            cmd_final.extend([
                "-c:v", settings.VIDEO_CODEC,
                "-preset", "medium",
                "-crf", str(settings.VIDEO_CRF),
                "-pix_fmt", "yuv420p",
                "-c:a", settings.AUDIO_CODEC,
                "-b:a", settings.AUDIO_BITRATE,
                "-ar", "44100",
                "-ac", "2",
                "-movflags", "+faststart",
                str(final_video_path),
            ])

            logger.info("[FinalCompositor] Executing final multiplexing command")
            res_fin = subprocess.run(cmd_final, capture_output=True, text=True)
            if res_fin.returncode != 0:
                raise FinalCompositorError(f"Final composition multiplexing failed: {res_fin.stderr}")

            # 6. Stage E: Deep Verification with ffprobe
            final_probe = ffmpeg_service.probe_media(final_video_path)
            final_dur = float(final_probe.get("video_duration") or final_probe["duration"])
            final_audio_dur = float(final_probe.get("audio_duration") or final_probe["duration"])
            sync_delta = round(abs(final_dur - audio_duration), 3)

            logger.info(
                "[FinalCompositor] Success! Final MP4: %.2fs, Narration: %.2fs, Sync delta: %.3fs",
                final_dur,
                audio_duration,
                sync_delta,
            )

            if sync_delta > tolerance_seconds:
                logger.warning(
                    "[FinalCompositor] Warning: Sync delta %.3fs exceeds tolerance %.2fs",
                    sync_delta,
                    tolerance_seconds,
                )

            # 7. Stage F: Write timeline.json & metadata.json
            timeline_obj = VideoTimeline(
                topic=topic,
                audio_duration=round(audio_duration, 2),
                final_duration=round(final_dur, 2),
                sync_delta=sync_delta,
                scenes=timeline_items,
            )
            timeline_path = target_dir / "timeline.json"
            timeline_path.write_text(json.dumps(timeline_obj.model_dump(), indent=2), encoding="utf-8")

            metadata_payload = {
                "topic": topic,
                "video_path": str(final_video_path.relative_to(settings.BASE_DIR)).replace("\\", "/") if final_video_path.is_relative_to(settings.BASE_DIR) else str(final_video_path),
                "duration_seconds": round(final_dur, 2),
                "audio_duration_seconds": round(audio_duration, 2),
                "sync_delta_seconds": sync_delta,
                "scene_count": len(timeline_items),
                "output_size_mb": final_probe.get("size_mb", 0.0),
                "video_codec": final_probe.get("video_codec", "h264"),
                "audio_codec": final_probe.get("audio_codec", "aac"),
                "pixel_format": final_probe.get("pixel_format", "yuv420p"),
                "resolution": f"{final_probe.get('width', 1280)}x{final_probe.get('height', 720)}",
                "fps": final_probe.get("fps", 30.0),
                "subtitle_burned": burn_subtitles and resolved_subtitle is not None,
                "subtitle_path": str(resolved_subtitle) if resolved_subtitle else None,
                "cloud_fallback_used": cloud_fallback_used,
                "scenes": scene_metadata_list,
                "timeline": timeline_obj.model_dump(),
            }
            metadata_path = target_dir / "metadata.json"
            metadata_path.write_text(json.dumps(metadata_payload, indent=2), encoding="utf-8")

            execution_time = round(time.perf_counter() - start_time, 2)
            rel_video_path = str(final_video_path.relative_to(settings.BASE_DIR)).replace("\\", "/") if final_video_path.is_relative_to(settings.BASE_DIR) else str(final_video_path)

            return ComposedVideoResult(
                success=True,
                topic=topic,
                video_path=rel_video_path,
                duration_seconds=round(final_dur, 2),
                audio_duration_seconds=round(audio_duration, 2),
                sync_delta_seconds=sync_delta,
                scene_count=len(timeline_items),
                output_size_mb=final_probe.get("size_mb", 0.0),
                video_codec=final_probe.get("video_codec", "h264"),
                audio_codec=final_probe.get("audio_codec", "aac"),
                pixel_format=final_probe.get("pixel_format", "yuv420p"),
                resolution=f"{final_probe.get('width', 1280)}x{final_probe.get('height', 720)}",
                fps=final_probe.get("fps", 30.0),
                subtitle_burned=burn_subtitles and resolved_subtitle is not None,
                subtitle_path=str(resolved_subtitle) if resolved_subtitle else None,
                timeline_path=str(timeline_path.relative_to(settings.BASE_DIR)).replace("\\", "/") if timeline_path.is_relative_to(settings.BASE_DIR) else str(timeline_path),
                metadata_path=str(metadata_path.relative_to(settings.BASE_DIR)).replace("\\", "/") if metadata_path.is_relative_to(settings.BASE_DIR) else str(metadata_path),
                cloud_fallback_used=cloud_fallback_used,
                scenes=scene_metadata_list,
                execution_time_seconds=execution_time,
            )

        finally:
            # Clean up temporary processing directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _concat_scenes_demuxer(self, clip_paths: List[Path], output_path: Path):
        """Concatenate clips using FFmpeg concat demuxer."""
        concat_file = output_path.parent / f"demuxer_{output_path.stem}.txt"
        with open(concat_file, "w", encoding="utf-8") as f:
            for p in clip_paths:
                f.write(f"file '{p.as_posix()}'\n")

        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c:v", settings.VIDEO_CODEC,
            "-pix_fmt", "yuv420p",
            "-r", "30",
            str(output_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if concat_file.exists():
            concat_file.unlink(missing_ok=True)
        if res.returncode != 0:
            raise FinalCompositorError(f"Concat demuxer failed: {res.stderr}")

    def compose_topic(
        self,
        topic: str,
        quality: str = "medium_quality",
        burn_subtitles: bool = True,
        subtitle_enabled: bool = True,
        transition_enabled: bool = True,
        transition_duration_seconds: float = 0.3,
        audio_path: Optional[Union[str, Path]] = None,
        subtitle_path: Optional[Union[str, Path]] = None,
        reuse_existing: bool = True,
        visual_style: Optional[str] = "auto",
    ) -> ComposedVideoResult:
        """
        End-to-end multi-scene video composition for a topic:
        1. Obtains visual plan and routes scenes (VisualScenePlanner & SceneRouter)
        2. Renders scenes independently across Manim, Avatar, and Cloud video (SceneRenderService)
        3. Obtains or synthesizes master narration audio (IndicF5)
        4. Obtains or generates subtitles (Whisper / SubtitleService)
        5. Composes scenes with audio timeline synchronization, transitions, and subtitle burning
        6. Emits timeline.json, metadata.json, and returns ComposedVideoResult
        """
        from app.services.visual_scene_planner import visual_scene_planner
        from app.services.scene_router import scene_router
        from app.services.scene_render_service import scene_render_service
        from app.services.indicf5_service import indicf5_service
        from app.services.subtitle_service import subtitle_service

        topic_slug = self._sanitize_slug(topic)

        # 1. Plan & Route
        logger.info("[FinalCompositor.compose_topic] Planning scenes for '%s' (visual_style=%s)", topic, visual_style)
        raw_plan = visual_scene_planner.plan(topic, visual_style=visual_style)
        routed_plan = scene_router.route_plan(raw_plan)

        # 2. Render individual scenes
        logger.info("[FinalCompositor.compose_topic] Rendering scenes for '%s'", topic)
        render_response = scene_render_service.render_plan(routed_plan, quality=quality)
        scenes = render_response.scenes

        # 3. Master narration audio
        resolved_audio: Optional[Path] = None
        if audio_path:
            cand_a = Path(audio_path).resolve()
            if cand_a.exists() and cand_a.stat().st_size > 0:
                resolved_audio = cand_a

        if not resolved_audio:
            # Check for existing audio in audio/<topic_slug>/narration.wav
            cand_existing = settings.AUDIO_DIR / topic_slug / "narration.wav"
            if reuse_existing and cand_existing.exists() and cand_existing.stat().st_size > 0:
                resolved_audio = cand_existing
                logger.info("[FinalCompositor.compose_topic] Reusing existing narration audio: %s", resolved_audio)
            else:
                # Synthesize narration text from plan
                script_parts = [sc.narration.strip() for sc in raw_plan.scenes if sc.narration and sc.narration.strip()]
                full_narration = " ".join(script_parts)
                if not full_narration:
                    full_narration = f"An overview of {topic}."
                logger.info("[FinalCompositor.compose_topic] Synthesizing narration for '%s' (%d chars)", topic, len(full_narration))
                tts_res = indicf5_service.generate_speech(
                    text=full_narration,
                    topic=topic,
                )
                resolved_audio = Path(tts_res["absolute_audio_path"])

        # 4. Subtitles
        resolved_sub: Optional[Path] = None
        if subtitle_enabled:
            if subtitle_path:
                cand_s = Path(subtitle_path).resolve()
                if cand_s.exists() and cand_s.stat().st_size > 0:
                    resolved_sub = cand_s

            if not resolved_sub:
                cand_existing_sub = settings.SUBTITLES_DIR / topic_slug / "subtitles.srt"
                if reuse_existing and cand_existing_sub.exists() and cand_existing_sub.stat().st_size > 0:
                    resolved_sub = cand_existing_sub
                    logger.info("[FinalCompositor.compose_topic] Reusing existing subtitles: %s", resolved_sub)
                else:
                    logger.info("[FinalCompositor.compose_topic] Transcribing audio with Whisper...")
                    sub_res = subtitle_service.process_audio(audio_path=resolved_audio, topic=topic)
                    resolved_sub = Path(sub_res["srt_path"])

        # 5. Execute composition
        return self.compose(
            topic=topic,
            scenes=scenes,
            audio_path=resolved_audio,
            subtitle_path=resolved_sub,
            burn_subtitles=burn_subtitles,
            transition_enabled=transition_enabled,
            transition_duration_seconds=transition_duration_seconds,
        )


# Global singleton instance
final_compositor = FinalCompositor()
