from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app.schemas.video import (
    VideoRequest,
    TopicVideoRequest,
    PipelineStatusResponse,
    ManimVideoRequest,
    ManimVideoResponse,
    DynamicTopicRequest,
    DynamicTopicResponse,
    LLMTopicRequest,
    LLMTopicResponse,
    VideoCompositionRequest,
    VideoCompositionResponse,
    FullVideoRequest,
    FullVideoResponse,
)
from app.schemas.visual_scene import (
    VisualPlanRequest,
    VisualPlanResponse,
)
from app.schemas.render import (
    TopicRenderRequest,
    TopicRenderResponse,
)
from app.services.manim_service import (
    generate_manim_video,
    generate_dynamic_topic_video,
    render_educational_plan_to_video,
)
from app.services.llm_planner import llm_academic_planner
from app.services.visual_scene_planner import (
    visual_scene_planner,
    RuleBasedVisualScenePlanner,
)
from app.services.scene_router import scene_router
from app.services.scene_render_service import scene_render_service
from app.pipelines.video_composition import (
    video_composition_pipeline,
    full_educational_video_pipeline,
)


router = APIRouter()

@router.post("/script-to-video", response_model=PipelineStatusResponse)
async def script_to_video(request: VideoRequest = None):
    return PipelineStatusResponse(
        status="not_implemented",
        message="Script-to-video pipeline will be implemented in the next milestone.",
        pipeline="script_to_video"
    )

@router.post("/topic-to-video", response_model=PipelineStatusResponse)
async def topic_to_video(request: TopicVideoRequest = None):
    return PipelineStatusResponse(
        status="not_implemented",
        message="Topic-to-video pipeline will be implemented in the next milestone.",
        pipeline="topic_to_video"
    )

@router.post("/manim", response_model=ManimVideoResponse)
async def generate_manim_endpoint(request: ManimVideoRequest):
    """
    Generate an educational Manim animation video for a specified topic.
    Preserved for Task 2 backward compatibility.
    """
    if request.topic.strip().lower() != "newton's second law":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Topic '{request.topic}' is not supported. "
                "Currently only 'Newton\\'s Second Law' is implemented in this demo."
            ),
        )

    try:
        result = await run_in_threadpool(
            generate_manim_video,
            topic=request.topic,
            output_dir=None,
            quality=request.quality or "medium_quality",
        )
        return ManimVideoResponse(**result)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate Manim video: {str(e)}"
        )


@router.post("/manim/topic", response_model=DynamicTopicResponse)
async def generate_dynamic_topic_endpoint(request: DynamicTopicRequest):
    """
    Generate an educational video for any arbitrary academic question or topic.
    Extracts lesson structure through AcademicPlanner, synthesizes modular visual scenes,
    renders them in parallel with Manim CLI, and losslessly stitches them via FFmpeg.
    """
    if not request.question or not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="The 'question' field cannot be empty.",
        )

    try:
        result = await run_in_threadpool(
            generate_dynamic_topic_video,
            question=request.question.strip(),
            output_dir=None,
            quality=request.quality or "medium_quality",
        )
        return DynamicTopicResponse(**result)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate dynamic Manim video: {str(e)}"
        )


@router.post("/llm/topic", response_model=LLMTopicResponse)
async def generate_llm_topic_endpoint(request: LLMTopicRequest):
    """
    LLM-driven educational video synthesis pipeline:
    1. Parse topic prompt through local Qwen2.5 3B via Ollama.
    2. Fall back to RuleBasedAcademicPlanner if Ollama is unavailable or invalid.
    3. Validate structured EducationalVideoPlan with Pydantic.
    4. Compile sequenced Manim scenes and render clips via Manim CLI.
    5. Losslessly stitch clips into final MP4 using FFmpeg concat.
    """
    try:
        prompt = request.get_prompt()
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    try:
        # Step 1: Plan with Qwen2.5 3B / Ollama (with safe fallback)
        plan, used_fallback, planner_name = await run_in_threadpool(
            llm_academic_planner.plan_with_fallback,
            question=prompt,
        )

        # Step 2: Render EducationalVideoPlan into MP4 using Manim
        quality_str = request.quality or "medium_quality"
        result = await run_in_threadpool(
            render_educational_plan_to_video,
            plan=plan,
            question=prompt,
            output_dir=None,
            quality=quality_str,
            allow_specialized_fast_path=False,
        )

        return LLMTopicResponse(
            success=result["success"],
            topic=result["topic"],
            video_path=result["video_path"],
            duration_seconds=result["duration_seconds"],
            generation_time_seconds=result["generation_time_seconds"],
            scene_count=result["scene_count"],
            output_size_mb=result.get("output_size_mb"),
            plan=result.get("plan"),
            used_fallback=used_fallback,
            planner=planner_name,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate LLM-planned video: {str(e)}"
        )


@router.post("/compose", response_model=VideoCompositionResponse, summary="Compose Video, Narration Audio and Subtitles")
async def compose_video_endpoint(request: VideoCompositionRequest):
    """
    Combines an educational visual video (Manim), spoken narration audio (IndicF5),
    and SRT subtitles (faster-whisper) into a browser-ready MP4 container using FFmpeg.
    Synchronizes durations (tpad last-frame freeze or apad silence) and burns subtitles.
    """
    try:
        result = await run_in_threadpool(
            video_composition_pipeline.compose,
            video_path=request.video_path,
            audio_path=request.audio_path,
            subtitle_path=request.subtitle_path,
            output_path=request.output_path,
            output_name=request.output_name,
            burn_subtitles=request.burn_subtitles,
        )
        return VideoCompositionResponse(**result)
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video composition failed: {str(e)}")


@router.post("/full", response_model=FullVideoResponse, summary="Generate Full End-to-End Educational Video")
async def generate_full_video_endpoint(request: FullVideoRequest):
    """
    Executes the complete five-stage educational video generation pipeline:
    1. Qwen2.5 3B local planning -> EducationalVideoPlan
    2. Dynamic Manim rendering -> Visual Scenes MP4
    3. IndicF5 local TTS -> Spoken Voiceover WAV
    4. faster-whisper local alignment -> Timestamps & Subtitles SRT
    5. FFmpeg composition -> Final Browser-Ready MP4
    """
    try:
        prompt = request.get_prompt()
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    try:
        result = await run_in_threadpool(
            full_educational_video_pipeline.generate,
            topic=prompt,
            quality=request.quality or "medium_quality",
            burn_subtitles=request.burn_subtitles if request.burn_subtitles is not None else True,
            language=request.language or "en",
            target_duration_seconds=request.target_duration_seconds or 30.0,
            character=bool(request.character),
            character_position=request.character_position or "auto",
            visual_style=request.visual_style or "academic",
        )

        return FullVideoResponse(**result)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Full educational video generation failed: {str(e)}")


@router.post(
    "/plan",
    response_model=VisualPlanResponse,
    summary="Plan and route visual educational scenes (Task 9B)",
    description="Generates a visual-first educational production plan and routes each scene to Manim, Cloud Video, or Avatar without rendering media."
)
async def generate_visual_plan_endpoint(request: VisualPlanRequest) -> VisualPlanResponse:
    """
    Visual Scene Planner & Router Endpoint (Task 9B).
    Creates structured educational scene plan and deterministically assigns visual engines.
    Does NOT invoke video rendering, TTS, or external cloud inference.
    """
    if not request.topic or not request.topic.strip():
        raise HTTPException(status_code=400, detail="Topic field cannot be empty.")

    clean_topic = request.topic.strip()
    target_duration = request.target_duration or 30.0
    level = request.level or "intermediate"
    planner_mode = (request.planner or "auto").strip().lower()

    try:
        if planner_mode == "rule_based":
            planner_instance = RuleBasedVisualScenePlanner()
            raw_plan = await run_in_threadpool(
                planner_instance.plan,
                topic=clean_topic,
                target_duration=target_duration,
                level=level,
            )
            planner_used = "rule_based"
        else:
            raw_plan = await run_in_threadpool(
                visual_scene_planner.plan,
                topic=clean_topic,
                target_duration=target_duration,
                level=level,
            )
            planner_used = "qwen2.5:3b (with fallback)"

        # Apply deterministic scene routing rules
        routed_plan = await run_in_threadpool(scene_router.route_plan, raw_plan)

        return VisualPlanResponse(
            success=True,
            topic=routed_plan.original_plan.topic,
            title=routed_plan.original_plan.title,
            total_duration_seconds=routed_plan.original_plan.total_duration_seconds,
            learning_objectives=routed_plan.original_plan.learning_objectives,
            scenes=routed_plan.routed_scenes,
            engine_summary=routed_plan.engine_summary,
            planner_used=planner_used,
        )

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Visual scene planning failed: {str(e)}")


@router.post(
    "/render",
    response_model=TopicRenderResponse,
    summary="Render routed visual scenes independently (Task 9C)",
    description="Plans, routes, and independently renders scenes across Manim, Cloud Video, and Avatar without stitching into a final video."
)
async def render_scenes_endpoint(request: TopicRenderRequest) -> TopicRenderResponse:
    """
    Renders each routed scene into its own standalone MP4 video.
    Does not concatenate scenes (reserved for Task 9D compositor).
    """
    if not request.topic or not request.topic.strip():
        raise HTTPException(status_code=400, detail="Topic field cannot be empty.")

    clean_topic = request.topic.strip()
    quality = request.quality or "medium_quality"
    planner_mode = (request.planner or "auto").strip().lower()

    try:
        # 1. Plan scenes
        if planner_mode == "rule_based":
            planner_instance = RuleBasedVisualScenePlanner()
            raw_plan = await run_in_threadpool(planner_instance.plan, topic=clean_topic)
        else:
            raw_plan = await run_in_threadpool(visual_scene_planner.plan, topic=clean_topic)

        # 2. Route scenes
        routed_plan = await run_in_threadpool(scene_router.route_plan, raw_plan)

        # 3. Render scenes independently
        result = await run_in_threadpool(
            scene_render_service.render_plan,
            plan=routed_plan,
            quality=quality,
        )
        return result

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Visual scene rendering failed: {str(e)}")


