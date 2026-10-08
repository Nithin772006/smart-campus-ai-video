"""
Tests for Real-Time Pipeline Progress Tracker and SSE Streaming (Task 9F UI Enhancement).
Validates per-stage progress metrics, overall progress computation, event dispatching,
and API stream integration.
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.services.pipeline_progress import PipelineProgressTracker, PIPELINE_STAGES_SPEC


def test_progress_tracker_initialization():
    """Verify that tracker initializes with 7 stages in pending state at 0%."""
    tracker = PipelineProgressTracker(topic="Binary Search", character_enabled=False)
    assert len(tracker.stages) == 7
    assert tracker.overall_progress == 0
    assert tracker.topic == "Binary Search"

    for stage in tracker.stages:
        assert stage["progress"] == 0
        assert stage["status"] == "pending"
        assert stage["error"] is None


def test_progress_tracker_update_and_overall_calculation():
    """Verify stage updates, percentage clamping, and overall progress averaging."""
    tracker = PipelineProgressTracker(topic="OSI Model")
    events = []
    tracker.add_listener(lambda e: events.append(e))

    # Update stage 1 to 100%
    snap1 = tracker.update_stage("understanding_topic", 100, "completed", "Topic analyzed")
    assert tracker.stages[0]["progress"] == 100
    assert tracker.stages[0]["status"] == "completed"
    # Overall: 100 / 7 = 14%
    assert tracker.overall_progress == 14
    assert snap1["overall_progress"] == 14

    # Update stage 2 to 50%
    tracker.update_stage("creating_lesson", 50, "running", "Planning scenes")
    assert tracker.stages[1]["progress"] == 50
    # Overall: (100 + 50) / 7 = 150 / 7 = 21%
    assert tracker.overall_progress == 21

    # Verify event structure
    assert len(events) == 2
    last_event = events[-1]
    assert last_event["type"] == "progress"
    assert last_event["stage"] == "creating_lesson"
    assert last_event["stage_index"] == 2
    assert last_event["total_stages"] == 7
    assert last_event["stage_progress"] == 50
    assert last_event["status"] == "running"
    assert last_event["overall_progress"] == 21


def test_progress_tracker_mark_completed():
    """Verify mark_completed sets all stages to 100% and overall progress to 100%."""
    tracker = PipelineProgressTracker(topic="Newton's Second Law")
    events = []
    tracker.add_listener(lambda e: events.append(e))

    dummy_result = {"video_path": "scenes/output.mp4", "duration_seconds": 25.0}
    tracker.mark_completed(dummy_result)

    assert tracker.overall_progress == 100
    for stage in tracker.stages:
        assert stage["progress"] == 100
        assert stage["status"] == "completed"

    assert len(events) == 1
    complete_event = events[0]
    assert complete_event["type"] == "complete"
    assert complete_event["overall_progress"] == 100
    assert complete_event["result"] == dummy_result


def test_progress_tracker_mark_error():
    """Verify mark_error records failure and preserves previous progress."""
    tracker = PipelineProgressTracker(topic="Test Error")
    events = []
    tracker.add_listener(lambda e: events.append(e))

    tracker.update_stage("rendering_visuals", 45, "running", "Rendering scene 2...")
    tracker.mark_error("rendering_visuals", "Manim subprocess timeout")

    visual_stage = next(s for s in tracker.stages if s["id"] == "rendering_visuals")
    assert visual_stage["status"] == "error"
    assert visual_stage["progress"] == 45
    assert visual_stage["error"] == "Manim subprocess timeout"

    assert len(events) == 2
    err_event = events[1]
    assert err_event["type"] == "error"
    assert err_event["stage"] == "rendering_visuals"
    assert err_event["status"] == "error"
    assert err_event["message"] == "Manim subprocess timeout"


def test_pipeline_composition_generate_accepts_progress_tracker():
    """Verify FullEducationalVideoPipeline.generate signature accepts progress_tracker."""
    from app.pipelines.video_composition import full_educational_video_pipeline

    tracker = PipelineProgressTracker(topic="Fast Test")
    
    # Mock services so pipeline doesn't invoke GPU/FFmpeg in this unit test
    with patch("app.pipelines.video_composition.llm_academic_planner.plan_with_fallback") as mock_plan, \
         patch("app.pipelines.video_composition.render_educational_plan_to_video") as mock_manim, \
         patch("app.pipelines.video_composition.indicf5_service.generate_plan_narration") as mock_tts, \
         patch("app.pipelines.video_composition.subtitle_service.process_audio") as mock_sub, \
         patch.object(full_educational_video_pipeline.composition_pipeline, "compose") as mock_compose:

        # Setup mock returns
        mock_plan_obj = MagicMock()
        mock_plan_obj.topic = "Fast Test"
        mock_plan_obj.scenes = [MagicMock()]
        mock_plan_obj.model_dump.return_value = {"scenes": []}
        mock_plan.return_value = (mock_plan_obj, False, "TestPlanner")

        mock_manim.return_value = {"video_path": "test.mp4", "duration_seconds": 10.0}
        mock_tts.return_value = {
            "audio_path": "test.wav",
            "duration_seconds": 10.0,
            "word_count": 25,
            "actual_wpm": 150.0,
        }
        mock_sub.return_value = {
            "subtitle_srt_path": "test.srt",
            "segment_count": 4,
            "segments": [{"end": 9.8}],
        }
        mock_compose.return_value = {
            "video_path": "final.mp4",
            "video_url": "http://127.0.0.1:8000/final.mp4",
            "duration_seconds": 10.0,
            "file_size_mb": 1.5,
            "audio_duration_seconds": 10.0,
        }

        res = full_educational_video_pipeline.generate(
            topic="Fast Test",
            quality="low_quality",
            progress_tracker=tracker,
        )

        assert res["success"] is True
        assert tracker.overall_progress == 100
        for s in tracker.stages:
            assert s["status"] == "completed"
            assert s["progress"] == 100


def test_generate_stream_endpoint_initial_event():
    """Verify that GET /api/video/generate-stream immediately returns SSE text/event-stream."""
    client = TestClient(app)

    # Validate that empty topic returns 400
    res_empty = client.get("/api/video/generate-stream?topic=")
    assert res_empty.status_code == 400

    # Validate that stream endpoint connects with text/event-stream content type
    with patch("app.api.video.full_educational_video_pipeline.generate") as mock_gen:
        def fake_generate(**kwargs):
            tracker = kwargs.get("progress_tracker")
            if tracker:
                tracker.update_stage("understanding_topic", 100, "completed", "Done")
                tracker.mark_completed({"success": True})
            return {"success": True}

        mock_gen.side_effect = fake_generate

        with client.stream("GET", "/api/video/generate-stream?topic=Binary+Search") as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

            lines = []
            for line in response.iter_lines():
                if line.startswith("data: "):
                    lines.append(json.loads(line.replace("data: ", "")))
                if len(lines) >= 1:
                    break

            assert len(lines) >= 1
            data = lines[0]
            assert data["type"] == "progress"
            assert data["total_stages"] == 7
            assert len(data["stages"]) == 7

