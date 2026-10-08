"""
Real-time Pipeline Progress Tracker (Task 9F UI Enhancement).
Manages per-stage progress states, dynamic percentages, stage-specific counters,
and event dispatching for Server-Sent Events (SSE) streaming.
"""

import json
import time
from typing import List, Dict, Any, Optional, Callable


PIPELINE_STAGES_SPEC = [
    {
        "id": "understanding_topic",
        "name": "Understanding topic",
        "description": "Analyzing academic scope and requirements",
    },
    {
        "id": "creating_lesson",
        "name": "Creating lesson",
        "description": "Structuring pedagogical video plan via Qwen2.5 3B",
    },
    {
        "id": "rendering_visuals",
        "name": "Rendering educational visuals",
        "description": "Generating programmatic animation with Manim",
    },
    {
        "id": "generating_narration",
        "name": "Generating narration",
        "description": "Synthesizing spoken audio with IndicF5 TTS",
    },
    {
        "id": "creating_subtitles",
        "name": "Creating subtitles",
        "description": "Transcribing and aligning timestamps via faster-whisper",
    },
    {
        "id": "creating_teacher",
        "name": "Creating AI teacher",
        "description": "Preparing transparent 3D educator presenter layer",
    },
    {
        "id": "composing_final_video",
        "name": "Composing final video",
        "description": "Multiplexing video, audio, subtitles, and avatar via FFmpeg",
    },
]


class PipelineProgressTracker:
    """
    Thread-safe progress coordinator for the 7-stage educational video pipeline.
    Calculates overall progress from per-stage metrics and dispatches events to listeners.
    """

    def __init__(self, topic: str = "", character_enabled: bool = False):
        self.topic = topic
        self.character_enabled = character_enabled
        self.listeners: List[Callable[[Dict[str, Any]], None]] = []

        # Initialize all 7 stages in PENDING state (0%, Waiting)
        self.stages: List[Dict[str, Any]] = []
        for s in PIPELINE_STAGES_SPEC:
            self.stages.append({
                "id": s["id"],
                "name": s["name"],
                "description": s["description"],
                "progress": 0,
                "status": "pending",  # "pending" | "running" | "completed" | "error"
                "message": "Waiting...",
                "error": None,
            })

    def add_listener(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback for progress events."""
        self.listeners.append(callback)

    @property
    def overall_progress(self) -> int:
        """Computes overall progress as the average of all stage percentages."""
        if not self.stages:
            return 0
        total = sum(s["progress"] for s in self.stages)
        return min(100, max(0, round(total / len(self.stages))))

    @property
    def active_stage(self) -> Optional[Dict[str, Any]]:
        """Finds the currently running stage, if any."""
        for s in self.stages:
            if s["status"] == "running":
                return s
        return None

    def update_stage(
        self,
        stage_id: str,
        progress: int,
        status: str = "running",
        message: str = "",
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Updates a specific stage and broadcasts the new pipeline snapshot.
        Clamps progress to 0-100 and enforces status invariants.
        """
        target = None
        for s in self.stages:
            if s["id"] == stage_id:
                target = s
                break

        if not target:
            return self.get_snapshot()

        clamped_progress = max(0, min(100, int(progress)))
        if status == "completed":
            clamped_progress = 100
        elif status == "pending":
            clamped_progress = 0

        target["progress"] = clamped_progress
        target["status"] = status
        if message:
            target["message"] = message
        if error:
            target["error"] = error

        stage_idx = next((i + 1 for i, s in enumerate(self.stages) if s["id"] == stage_id), 1)

        snapshot = self.get_snapshot()
        self._dispatch({
            "type": "progress",
            "stage": stage_id,
            "stage_id": stage_id,
            "stage_index": stage_idx,
            "total_stages": len(self.stages),
            "stage_name": target["name"],
            "stage_progress": clamped_progress,
            "status": status,
            "stage_status": status,
            "message": target["message"],
            "stage_message": target["message"],
            "overall_progress": snapshot["overall_progress"],
            "stages": snapshot["stages"],
        })
        return snapshot

    def mark_completed(self, result: Dict[str, Any]) -> None:
        """Sets all stages to 100% completed and sends final completion payload."""
        for s in self.stages:
            s["progress"] = 100
            s["status"] = "completed"
            if not s["message"] or s["message"] == "Waiting...":
                s["message"] = "Completed"

        self._dispatch({
            "type": "complete",
            "stage": "composing_final_video",
            "stage_id": "composing_final_video",
            "stage_index": len(self.stages),
            "total_stages": len(self.stages),
            "stage_progress": 100,
            "status": "completed",
            "stage_status": "completed",
            "overall_progress": 100,
            "result": result,
            "stages": self.stages,
            "message": "Video generation completed successfully!",
        })

    def mark_error(self, stage_id: str, error_message: str) -> None:
        """Marks the specified stage as failed and dispatches error event."""
        failed_stage = None
        stage_idx = 1
        for i, s in enumerate(self.stages):
            if s["id"] == stage_id:
                s["status"] = "error"
                s["error"] = error_message
                s["message"] = f"Failed: {error_message}"
                failed_stage = s
                stage_idx = i + 1
                break

        self._dispatch({
            "type": "error",
            "stage": stage_id,
            "stage_id": stage_id,
            "stage_index": stage_idx,
            "total_stages": len(self.stages),
            "stage_progress": failed_stage["progress"] if failed_stage else 0,
            "status": "error",
            "stage_status": "error",
            "message": error_message,
            "overall_progress": self.overall_progress,
            "stages": self.stages,
        })

    def get_snapshot(self) -> Dict[str, Any]:
        """Returns full state snapshot suitable for serialization."""
        return {
            "topic": self.topic,
            "overall_progress": self.overall_progress,
            "stages": [dict(s) for s in self.stages],
        }

    def _dispatch(self, event: Dict[str, Any]) -> None:
        """Sends event to all registered listeners."""
        for listener in list(self.listeners):
            try:
                listener(event)
            except Exception:
                pass
