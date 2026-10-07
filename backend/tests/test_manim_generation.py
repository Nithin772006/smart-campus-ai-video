import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.manim_service import generate_manim_video
from app.config import settings


def test_manim_scene_generation():
    """
    Verify that Manim generates the Newton's Second Law educational scene,
    produces a valid non-empty MP4, measures valid duration and generation time.
    """
    topic = "Newton's Second Law"
    result = generate_manim_video(topic=topic, quality="medium_quality")

    # 1. Manim can generate the scene
    assert result["success"] is True
    assert result["topic"] == topic

    # 2. The MP4 file exists
    video_path_str = result["video_path"]
    video_path = settings.BASE_DIR / video_path_str if not Path(video_path_str).is_absolute() else Path(video_path_str)
    assert video_path.exists(), f"Generated video file does not exist at {video_path}"
    assert video_path.suffix == ".mp4", "Output file is not an MP4"

    # 3. The generated file is not empty
    file_size = video_path.stat().st_size
    assert file_size > 0, "Generated video file is empty (0 bytes)"
    assert result["output_size_mb"] > 0, "Output size MB must be greater than 0"

    # 4. The video has a valid duration
    duration = result["duration_seconds"]
    assert duration > 0, "Video duration must be greater than 0"
    assert 8.0 <= duration <= 20.0, f"Video duration {duration}s outside expected range"

    # 5. Generation time is recorded
    gen_time = result["generation_time_seconds"]
    assert gen_time > 0, "Generation time must be recorded and > 0"

    print("\n[PASS] Manim scene generation verified:")
    print(f"  - Video path: {video_path}")
    print(f"  - File size: {result['output_size_mb']} MB ({file_size} bytes)")
    print(f"  - Duration: {duration}s")
    print(f"  - Generation time: {gen_time}s")


if __name__ == "__main__":
    test_manim_scene_generation()
    print("ALL MANIM GENERATION TESTS PASSED SUCCESSFULLY!")
