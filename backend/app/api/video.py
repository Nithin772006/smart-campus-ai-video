import asyncio
import json
import logging
from typing import Union, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.services.pipeline_progress import PipelineProgressTracker
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
from app.schemas.composition import (
    CompositionRequest,
    ComposedVideoResult,
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
from app.services.final_compositor import final_compositor
from app.pipelines.video_composition import (
    video_composition_pipeline,
    full_educational_video_pipeline,
)
from typing import Union


router = APIRouter()
logger = logging.getLogger(__name__)

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


@router.post(
    "/compose",
    response_model=Union[ComposedVideoResult, VideoCompositionResponse],
    summary="Compose Video, Narration Audio and Subtitles (Tasks 7 & 9D)",
)
async def compose_video_endpoint(
    request: Union[CompositionRequest, VideoCompositionRequest]
):
    """
    Dual-mode video composition endpoint:
    1. Multi-Scene Composition (Task 9D): Accepts topic, quality, subtitle settings, and transitions.
       Orchestrates planning, routing, independent rendering, narration, and timeline-synchronized final video.
    2. Legacy Single-Clip Composition (Task 7): Accepts video_path, audio_path, subtitle_path.
    """
    try:
        # Check if Task 9D topic-based multi-scene request
        if hasattr(request, "topic") and getattr(request, "topic", None):
            result = await run_in_threadpool(
                final_compositor.compose_topic,
                topic=request.topic,
                quality=getattr(request, "quality", "medium_quality"),
                burn_subtitles=getattr(request, "burn_subtitles", True),
                subtitle_enabled=getattr(request, "subtitle_enabled", True),
                transition_enabled=getattr(request, "transition_enabled", True),
                transition_duration_seconds=getattr(request, "transition_duration_seconds", 0.3),
                audio_path=getattr(request, "audio_path", None),
                subtitle_path=getattr(request, "subtitle_path", None),
                visual_style=getattr(request, "visual_style", "auto"),
            )
            return result
        else:
            # Legacy Task 7 composition
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
            voice_provider=request.get_voice_provider(),
            voice_id=request.voice_id,
        )

        return FullVideoResponse(**result)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=500, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Full educational video generation failed: {str(e)}")


@router.get("/generate-stream", summary="Stream Real-Time Progress for Video Generation via SSE (GET)")
async def generate_video_stream_get(
    topic: str,
    quality: str = "medium_quality",
    burn_subtitles: bool = True,
    language: str = "en",
    target_duration_seconds: float = 30.0,
    character: bool = False,
    character_position: str = "auto",
    visual_style: str = "academic",
    voice_provider: str = "indicf5",
    voice_id: Optional[str] = None,
):
    """
    Server-Sent Events (SSE) streaming endpoint for real-time per-stage progress updates.
    Broadcasts stage status, percentages (0-100%), messages, and final video metadata.
    """
    clean_topic = topic.strip()
    if not clean_topic:
        raise HTTPException(status_code=400, detail="Topic parameter cannot be empty.")

    tracker = PipelineProgressTracker(topic=clean_topic, character_enabled=character)
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def on_progress(event: dict):
        loop.call_soon_threadsafe(queue.put_nowait, event)

    tracker.add_listener(on_progress)

    def background_worker():
        try:
            full_educational_video_pipeline.generate(
                topic=clean_topic,
                quality=quality,
                burn_subtitles=burn_subtitles,
                language=language,
                target_duration_seconds=target_duration_seconds,
                character=character,
                character_position=character_position,
                visual_style=visual_style,
                voice_provider=voice_provider,
                voice_id=voice_id,
                progress_tracker=tracker,
            )
        except Exception as e:
            logger.error("[SSE Stream] Pipeline generation error: %s", e)

    # Run heavy pipeline asynchronously in worker thread
    asyncio.create_task(asyncio.to_thread(background_worker))

    async def event_generator():
        # 1. Send immediate initial state
        initial_snap = tracker.get_snapshot()
        initial_event = {
            "type": "progress",
            "stage": "understanding_topic",
            "stage_id": "understanding_topic",
            "stage_index": 1,
            "total_stages": len(tracker.stages),
            "stage_name": "Understanding topic",
            "stage_progress": 0,
            "status": "pending",
            "stage_status": "pending",
            "message": f"Initializing educational pipeline for '{clean_topic}'...",
            "stage_message": "Initializing...",
            "overall_progress": 0,
            "stages": initial_snap["stages"],
        }
        yield f"data: {json.dumps(initial_event)}\n\n"

        # 2. Consume events until complete or error
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=25.0)
            except asyncio.TimeoutError:
                # Keepalive comment for proxies/browsers
                yield ": keepalive\n\n"
                continue

            yield f"data: {json.dumps(event)}\n\n"

            if event.get("type") in ("complete", "error"):
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/generate-stream", summary="Stream Real-Time Progress for Video Generation via SSE (POST)")
async def generate_video_stream_post(request: FullVideoRequest):
    """
    POST variant of SSE streaming for clients sending payload bodies.
    """
    try:
        topic = request.get_prompt()
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    return await generate_video_stream_get(
        topic=topic,
        quality=request.quality or "medium_quality",
        burn_subtitles=request.burn_subtitles if request.burn_subtitles is not None else True,
        language=request.language or "en",
        target_duration_seconds=request.target_duration_seconds or 30.0,
        character=bool(request.character),
        character_position=request.character_position or "auto",
        visual_style=request.visual_style or "academic",
        voice_provider=request.get_voice_provider(),
        voice_id=request.voice_id,
    )


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
    visual_style_str = request.visual_style.value if hasattr(request.visual_style, "value") else str(request.visual_style or "auto")

    try:
        if planner_mode == "rule_based":
            planner_instance = RuleBasedVisualScenePlanner()
            raw_plan = await run_in_threadpool(
                planner_instance.plan,
                topic=clean_topic,
                target_duration=target_duration,
                level=level,
                visual_style=visual_style_str,
            )
            planner_used = "rule_based"
        else:
            raw_plan = await run_in_threadpool(
                visual_scene_planner.plan,
                topic=clean_topic,
                target_duration=target_duration,
                level=level,
                visual_style=visual_style_str,
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
    visual_style_str = str(getattr(request, "visual_style", "auto") or "auto")

    try:
        # 1. Plan scenes
        if planner_mode == "rule_based":
            planner_instance = RuleBasedVisualScenePlanner()
            raw_plan = await run_in_threadpool(planner_instance.plan, topic=clean_topic, visual_style=visual_style_str)
        else:
            raw_plan = await run_in_threadpool(visual_scene_planner.plan, topic=clean_topic, visual_style=visual_style_str)

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


