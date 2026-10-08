"""
Service for rendering Manim educational animations and scenes.
Manages scene discovery, Manim CLI execution, media output, dynamic multi-scene compilation,
FFmpeg clip stitching, and benchmarking.
"""
import os
import sys
import time
import shutil
import subprocess
import tempfile
import csv
import logging
import re
from pathlib import Path
from typing import Optional, Union, Dict, Any, List

from app.config import settings
from app.services.ffmpeg_service import (
    is_ffmpeg_available,
    get_video_duration,
    concatenate_scene_clips,
)
from app.services.scene_planner import RuleBasedAcademicPlanner
from app.schemas.scene import EducationalVideoPlan, SceneType

logger = logging.getLogger(__name__)

# Topic to Scene mapping for modular scene discovery
TOPIC_SCENE_MAP = {
    "newton's second law": {
        "canonical_name": "Newton's Second Law",
        "scene_name": "NewtonSecondLawScene",
        "scene_module": "manim_scenes.py",
        "output_subfolder": "newton_second_law",
        "output_filename": "newton_second_law.mp4",
    }
}

QUALITY_MAP = {
    "low": ("-ql", "480p15", "low"),
    "low_quality": ("-ql", "480p15", "low"),
    "480p": ("-ql", "480p15", "low"),
    "medium": ("-qm", "720p30", "medium"),
    "medium_quality": ("-qm", "720p30", "medium"),
    "720p": ("-qm", "720p30", "medium"),
    "high": ("-qh", "1080p60", "high"),
    "high_quality": ("-qh", "1080p60", "high"),
    "1080p": ("-qh", "1080p60", "high"),
    "fourk": ("-qk", "2160p60", "fourk"),
    "fourk_quality": ("-qk", "2160p60", "fourk"),
    "2160p": ("-qk", "2160p60", "fourk"),
}


def record_benchmark(
    engine: str,
    topic: str,
    resolution: str,
    video_duration_seconds: float,
    generation_time_seconds: float,
    output_size_mb: float,
) -> None:
    """
    Log actual measured benchmark results to CSV.
    Updates root benchmarks/results.csv and backend/benchmarks/results.csv.
    """
    csv_headers = [
        "engine",
        "topic",
        "resolution",
        "video_duration_seconds",
        "generation_time_seconds",
        "output_size_mb",
    ]
    row = [
        engine,
        topic,
        resolution,
        video_duration_seconds,
        generation_time_seconds,
        output_size_mb,
    ]

    target_paths = [
        settings.BASE_DIR.parent / "benchmarks" / "results.csv",
        settings.BASE_DIR / "benchmarks" / "results.csv",
    ]

    for csv_path in target_paths:
        try:
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            write_header = not csv_path.exists() or csv_path.stat().st_size == 0
            if not write_header:
                with open(csv_path, "r", encoding="utf-8") as rf:
                    first_line = rf.readline()
                    if "engine" not in first_line:
                        write_header = True

            mode = "w" if write_header else "a"
            with open(csv_path, mode, newline="", encoding="utf-8") as wf:
                writer = csv.writer(wf)
                if write_header:
                    writer.writerow(csv_headers)
                writer.writerow(row)
        except Exception as e:
            logger.warning(f"Could not write benchmark to {csv_path}: {e}")


def generate_manim_video(
    topic: str,
    output_dir: Optional[Union[str, Path]] = None,
    quality: str = "medium_quality",
) -> Dict[str, Any]:
    """
    Render a Manim animation for the specified educational topic (Task 2 endpoint).
    """
    if not is_ffmpeg_available():
        raise RuntimeError(
            "FFmpeg is not installed or not accessible in PATH. "
            "Please ensure FFmpeg is installed to generate videos."
        )

    normalized_key = topic.strip().lower()
    if normalized_key not in TOPIC_SCENE_MAP:
        raise ValueError(
            f"Topic '{topic}' is not supported. "
            "Currently only 'Newton\\'s Second Law' is supported."
        )

    topic_info = TOPIC_SCENE_MAP[normalized_key]
    canonical_topic = topic_info["canonical_name"]
    scene_name = topic_info["scene_name"]
    output_filename = topic_info["output_filename"]

    quality_key = quality.strip().lower()
    quality_flag, resolution_label, benchmark_res = QUALITY_MAP.get(
        quality_key, ("-qm", "720p30", "medium")
    )

    if output_dir is None:
        target_dir = settings.SCENES_DIR / topic_info["output_subfolder"]
    else:
        target_dir = Path(output_dir)

    target_dir.mkdir(parents=True, exist_ok=True)
    final_video_path = target_dir / output_filename

    temp_render_dir = Path(tempfile.mkdtemp(prefix="manim_spec_render_"))
    try:
        scene_script_path = Path(__file__).resolve().parent / topic_info["scene_module"]
        if not scene_script_path.exists():
            raise FileNotFoundError(f"Scene script file not found: {scene_script_path}")

        start_time = time.perf_counter()

        cmd = [
            sys.executable,
            "-m",
            "manim",
            "render",
            quality_flag,
            "--media_dir",
            str(temp_render_dir),
            str(scene_script_path),
            scene_name,
        ]

        env = os.environ.copy()
        if "PYTHONHASHSEED" in env:
            seed_val = env.get("PYTHONHASHSEED", "")
            if seed_val != "random" and not (seed_val.isdigit() and 0 <= int(seed_val) <= 4294967295):
                del env["PYTHONHASHSEED"]

        try:
            subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                env=env,
                cwd=str(settings.BASE_DIR),
            )
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or e.stdout
            logger.error(f"Manim render failed with exit code {e.returncode}: {error_msg}")
            raise RuntimeError(f"Manim rendering failed: {error_msg}") from e

        generation_time_seconds = round(time.perf_counter() - start_time, 2)

        rendered_candidates = list(temp_render_dir.glob(f"**/{scene_name}.mp4"))
        if not rendered_candidates:
            rendered_candidates = list(temp_render_dir.glob("**/*.mp4"))

        if not rendered_candidates:
            raise RuntimeError("Manim completed but no output MP4 file was found.")

        rendered_file = rendered_candidates[0]

        if final_video_path.exists():
            final_video_path.unlink()
        shutil.copy2(rendered_file, final_video_path)
    finally:
        try:
            shutil.rmtree(temp_render_dir, ignore_errors=True)
        except Exception:
            pass

    duration_seconds = get_video_duration(final_video_path)
    file_size_bytes = final_video_path.stat().st_size
    output_size_mb = round(file_size_bytes / (1024 * 1024), 2)

    try:
        rel_video_path = final_video_path.relative_to(settings.BASE_DIR).as_posix()
    except ValueError:
        rel_video_path = str(final_video_path.as_posix())

    record_benchmark(
        engine="manim",
        topic=canonical_topic,
        resolution=benchmark_res,
        video_duration_seconds=duration_seconds,
        generation_time_seconds=generation_time_seconds,
        output_size_mb=output_size_mb,
    )

    return {
        "success": True,
        "topic": canonical_topic,
        "video_path": rel_video_path,
        "duration_seconds": duration_seconds,
        "generation_time_seconds": generation_time_seconds,
        "output_size_mb": output_size_mb,
    }


def _build_dynamic_scene_script_content(plan: EducationalVideoPlan) -> str:
    """
    Generate Python script containing sequenced Manim Scene classes
    corresponding to each planned educational scene.
    """
    backend_dir_repr = repr(str(settings.BASE_DIR))
    lines = [
        "# Auto-generated dynamic educational scenes",
        "import sys",
        "from pathlib import Path",
        f"if {backend_dir_repr} not in sys.path:",
        f"    sys.path.insert(0, {backend_dir_repr})",
        "",
        "from manim import *",
        "from app.services.manim_components import (",
        "    DynamicTitleScene,",
        "    DynamicExplanationScene,",
        "    DynamicFormulaScene,",
        "    DynamicBulletPointScene,",
        "    DynamicProcessScene,",
        "    DynamicHierarchyScene,",
        "    DynamicCycleScene,",
        "    DynamicConclusionScene,",
        ")",
        "",
    ]

    for idx, sc in enumerate(plan.scenes, start=1):
        class_name = f"Scene_{idx:02d}_{sc.type.value.capitalize()}"

        if sc.type == SceneType.TITLE:
            lines.extend([
                f"class {class_name}(DynamicTitleScene):",
                f"    title_text = {repr(sc.title or plan.title)}",
                f"    subtitle_text = {repr(sc.subtitle or f'An Exploration of {plan.topic}')}",
                f"    domain_text = {repr(plan.domain.value.upper())}",
                "",
            ])
        elif sc.type == SceneType.EXPLANATION:
            lines.extend([
                f"class {class_name}(DynamicExplanationScene):",
                f"    header_text = {repr(sc.title or f'Understanding {plan.topic}')}",
                f"    body_text = {repr(sc.content or '')}",
                "",
            ])
        elif sc.type == SceneType.FORMULA:
            lines.extend([
                f"class {class_name}(DynamicFormulaScene):",
                f"    header_text = {repr(sc.title or 'Mathematical Formulation')}",
                f"    formula_text = {repr(sc.formula or '')}",
                f"    breakdown_items = {repr(sc.formula_breakdown or ['Formula variable definition'])}",
                "",
            ])
        elif sc.type in (SceneType.CONCEPT, SceneType.BULLET_POINTS):
            bullets = sc.bullets if sc.bullets else ([sc.content] if sc.content else ["Key Principle"])
            lines.extend([
                f"class {class_name}(DynamicBulletPointScene):",
                f"    header_text = {repr(sc.title or 'Key Principles')}",
                f"    bullet_items = {repr(bullets)}",
                "",
            ])
        elif sc.type in (SceneType.PROCESS, SceneType.FLOWCHART):
            steps = sc.steps if sc.steps else (sc.bullets if sc.bullets else ["Step 1", "Step 2", "Step 3"])
            lines.extend([
                f"class {class_name}(DynamicProcessScene):",
                f"    header_text = {repr(sc.title or 'Procedural Steps')}",
                f"    step_items = {repr(steps)}",
                "",
            ])
        elif sc.type == SceneType.HIERARCHY:
            layers = sc.layers if sc.layers else (sc.steps if sc.steps else ["Tier 1", "Tier 2", "Tier 3"])
            lines.extend([
                f"class {class_name}(DynamicHierarchyScene):",
                f"    header_text = {repr(sc.title or 'System Layers')}",
                f"    layer_items = {repr(layers)}",
                "",
            ])
        elif sc.type == SceneType.CYCLE:
            stages = sc.steps if sc.steps else (sc.bullets if sc.bullets else ["Stage 1", "Stage 2", "Stage 3", "Stage 4"])
            lines.extend([
                f"class {class_name}(DynamicCycleScene):",
                f"    header_text = {repr(sc.title or 'Continuous Cycle')}",
                f"    stage_items = {repr(stages)}",
                "",
            ])
        elif sc.type == SceneType.CONCLUSION:
            lines.extend([
                f"class {class_name}(DynamicConclusionScene):",
                f"    title_text = {repr(sc.title or 'Key Takeaway')}",
                f"    takeaway_text = {repr(sc.content or f'Mastering {plan.topic} is fundamental to {plan.domain.value.title()}.')}",
                "",
            ])
        else:
            # Fallback for any other scene type
            lines.extend([
                f"class {class_name}(DynamicExplanationScene):",
                f"    header_text = {repr(sc.title or 'Overview')}",
                f"    body_text = {repr(sc.content or f'Overview of {plan.topic}')}",
                "",
            ])

    return "\n".join(lines)


def render_educational_plan_to_video(
    plan: EducationalVideoPlan,
    question: Optional[str] = None,
    output_dir: Optional[Union[str, Path]] = None,
    quality: str = "medium_quality",
    allow_specialized_fast_path: bool = False,
) -> Dict[str, Any]:
    """
    Render an EducationalVideoPlan into an MP4 video using dynamic Manim scenes.
    Coordinates script generation, Manim rendering, FFmpeg stitching, and benchmarking.
    """
    if not is_ffmpeg_available():
        raise RuntimeError("FFmpeg is not available. Please ensure FFmpeg is installed.")

    logger.info(f"[MANIM] Rendering plan for topic: '{plan.topic}' ({len(plan.scenes)} scenes)")

    # Specialized fast-path check (e.g. for rule-based Newton's Second Law backward compatibility)
    if allow_specialized_fast_path and plan.topic.strip().lower() == "newton's second law":
        specialized_res = generate_manim_video(
            topic="Newton's Second Law",
            output_dir=output_dir,
            quality=quality,
        )
        specialized_res["question"] = question or plan.topic
        specialized_res["scene_count"] = 1
        specialized_res["plan"] = plan.model_dump()
        logger.info(f"[MANIM] Render complete (specialized scene): {specialized_res['video_path']}")
        return specialized_res

    # 2. Output and temporary directories
    topic_slug = re.sub(r"[^a-z0-9_]", "", plan.topic.lower().replace(" ", "_").replace("-", "_"))
    if not topic_slug:
        topic_slug = "academic_topic"

    if output_dir is None:
        target_dir = settings.SCENES_DIR / topic_slug
    else:
        target_dir = Path(output_dir)

    target_dir.mkdir(parents=True, exist_ok=True)
    final_video_path = target_dir / f"{topic_slug}.mp4"

    # Use a system temporary directory outside the workspace so uvicorn's file watcher
    # (--reload) does not detect runner_scenes.py and trigger an immediate server restart/SIGINT
    temp_render_dir = Path(tempfile.mkdtemp(prefix="manim_dynamic_render_"))

    # 3. Quality flag resolution
    quality_key = quality.strip().lower()
    quality_flag, resolution_label, benchmark_res = QUALITY_MAP.get(
        quality_key, ("-qm", "720p30", "medium")
    )

    try:
        # 4. Generate runner script
        script_content = _build_dynamic_scene_script_content(plan)
        script_path = temp_render_dir / "runner_scenes.py"
        script_path.write_text(script_content, encoding="utf-8")

        # 5. Render all scenes using Manim CLI (-a flag renders all scenes in runner script)
        start_time = time.perf_counter()

        cmd = [
            sys.executable,
            "-m",
            "manim",
            "render",
            quality_flag,
            "-a",
            "--media_dir",
            str(temp_render_dir),
            str(script_path),
        ]

        env = os.environ.copy()
        if "PYTHONHASHSEED" in env:
            seed_val = env.get("PYTHONHASHSEED", "")
            if seed_val != "random" and not (seed_val.isdigit() and 0 <= int(seed_val) <= 4294967295):
                del env["PYTHONHASHSEED"]

        try:
            subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                env=env,
                cwd=str(settings.BASE_DIR),
            )
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or e.stdout
            logger.error(f"Dynamic scene render failed: {error_msg}")
            raise RuntimeError(f"Manim dynamic rendering failed: {error_msg}") from e

        # 6. Gather all rendered scene MP4 clips in sequential order
        raw_clips = [
            p for p in temp_render_dir.glob("**/*.mp4")
            if "partial_movie_files" not in str(p) and p.name != f"{topic_slug}.mp4"
        ]

        # Sort clips by scene prefix Scene_01_, Scene_02_, etc.
        sorted_clips = sorted(raw_clips, key=lambda p: p.name)

        if not sorted_clips:
            raise RuntimeError("Manim completed but no scene MP4 clips were found.")

        # 7. Concatenate clips using FFmpeg
        concatenate_scene_clips(sorted_clips, final_video_path)

        generation_time_seconds = round(time.perf_counter() - start_time, 2)
    finally:
        # Cleanup temporary files
        try:
            shutil.rmtree(temp_render_dir, ignore_errors=True)
        except Exception:
            pass

    # 8. Probe final video metrics
    duration_seconds = get_video_duration(final_video_path)
    file_size_bytes = final_video_path.stat().st_size
    output_size_mb = round(file_size_bytes / (1024 * 1024), 2)

    try:
        rel_video_path = final_video_path.relative_to(settings.BASE_DIR).as_posix()
    except ValueError:
        rel_video_path = str(final_video_path.as_posix())

    # 9. Record benchmark
    record_benchmark(
        engine="manim_dynamic",
        topic=plan.topic,
        resolution=benchmark_res,
        video_duration_seconds=duration_seconds,
        generation_time_seconds=generation_time_seconds,
        output_size_mb=output_size_mb,
    )

    logger.info(f"[MANIM] Render complete: {rel_video_path} ({duration_seconds}s, {generation_time_seconds}s gen time)")

    return {
        "success": True,
        "question": question or plan.topic,
        "topic": plan.topic,
        "video_path": rel_video_path,
        "duration_seconds": duration_seconds,
        "generation_time_seconds": generation_time_seconds,
        "scene_count": len(plan.scenes),
        "output_size_mb": output_size_mb,
        "plan": plan.model_dump(),
    }


def generate_dynamic_topic_video(
    question: str,
    output_dir: Optional[Union[str, Path]] = None,
    quality: str = "medium_quality",
) -> Dict[str, Any]:
    """
    Dynamic educational video pipeline:
    1. Parse natural question through AcademicPlanner.
    2. Synthesize multi-scene script using reusable Manim visual components.
    3. Render all scene clips in one pass with Manim CLI.
    4. Losslessly stitch clips into final MP4 using FFmpeg concat.
    5. Measure duration, generation time, file size, and log benchmarks.
    """
    planner = RuleBasedAcademicPlanner()
    plan = planner.plan(question)
    return render_educational_plan_to_video(
        plan=plan,
        question=question,
        output_dir=output_dir,
        quality=quality,
        allow_specialized_fast_path=True,
    )



class ManimService:
    """
    Modular wrapper for Manim animation synthesis.
    """
    def __init__(self, default_output_dir: Optional[Union[str, Path]] = None):
        self.default_output_dir = Path(default_output_dir) if default_output_dir else settings.SCENES_DIR

    def generate_video(
        self,
        topic: str,
        output_dir: Optional[Union[str, Path]] = None,
        quality: str = "medium_quality",
    ) -> Dict[str, Any]:
        target_dir = output_dir or self.default_output_dir
        return generate_manim_video(topic=topic, output_dir=target_dir, quality=quality)

    def generate_topic_video(
        self,
        question: str,
        output_dir: Optional[Union[str, Path]] = None,
        quality: str = "medium_quality",
    ) -> Dict[str, Any]:
        target_dir = output_dir or self.default_output_dir
        return generate_dynamic_topic_video(question=question, output_dir=target_dir, quality=quality)

    async def render_scene_script(self, scene_code: str, output_name: str = "manim_scene.mp4") -> str:
        """Placeholder for dynamic scene code execution."""
        output_file = str(self.default_output_dir / output_name)
        return output_file
