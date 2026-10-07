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
)
from app.services.manim_service import (
    generate_manim_video,
    generate_dynamic_topic_video,
    render_educational_plan_to_video,
)
from app.services.llm_planner import llm_academic_planner


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

