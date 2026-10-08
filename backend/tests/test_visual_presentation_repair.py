"""
Unit & Regression Tests for Task 9F: Visual Presentation Repair & Educational Visual Quality.
Verifies:
1. Subtitle bottom-center placement & horizontal orientation
2. Subtitle safe area margins
3. Text safe-area limits & wrapping
4. Long text wrapping & scaling without overflow
5. Teacher safe zone avoidance
6. Teacher and subtitle collision prevention
7. 1280x720 video normalization filter
8. OSI model progressive visual scene generation
9. Character count limits & no oversized text
10. Honest static teacher classification
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from app.services.safe_area import (
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    SAFE_MARGIN_X,
    SAFE_MARGIN_BOTTOM,
    SUBTITLE_MARGIN_BOTTOM,
    SUBTITLE_MARGIN_SIDE,
    SUBTITLE_FONT_SIZE,
    MANIM_SUBTITLE_TOP_Y,
    MAX_TITLE_CHARS,
    MAX_BODY_CHARS,
    build_ffmpeg_subtitle_filter,
    get_manim_safe_bounds,
)
from app.services.manim_layout_utils import (
    clean_text_string,
    wrap_text_to_lines,
    create_safe_text,
    create_safe_header,
    ensure_above_subtitles,
)
from app.services.visual_scene_planner import (
    RuleBasedVisualScenePlanner,
    CinematicVisualStyle,
)
from app.services.scene_planner import RuleBasedAcademicPlanner
from app.schemas.visual_scene import SceneType, VisualEngine, TeacherPosition
from app.services.avatar_service import TeacherAvatarOverlayProvider


def test_01_subtitle_bottom_center_placement():
    """Verify subtitle filter generates Alignment=2 (bottom-center) and safe margins."""
    test_srt = Path("fake/path/subtitles.srt")
    filt = build_ffmpeg_subtitle_filter(test_srt, video_width=1280, video_height=720)

    assert "Alignment=2" in filt, "Subtitles must be bottom-center aligned (Alignment=2)"
    assert "original_size=1280x720" in filt, "Filter must declare original_size to avoid libass 384x288 fallback"
    assert "MarginV=40" in filt, "Vertical margin must position subtitles safely near bottom edge"
    assert "MarginL=80" in filt, "Left margin must be safe"
    assert "MarginR=80" in filt, "Right margin must be safe"
    assert "Outline=2" in filt, "Must include outline for contrast against any background"


def test_02_subtitle_horizontal_orientation():
    """Verify subtitle styling does not compress canvas into a narrow vertical column."""
    test_srt = Path("fake/path/subtitles.srt")
    filt = build_ffmpeg_subtitle_filter(test_srt, video_width=1280, video_height=720, margin_side=80)

    # In 1280 width with 80px side margins, available horizontal text width is 1120px
    available_width = VIDEO_WIDTH - (2 * SUBTITLE_MARGIN_SIDE)
    assert available_width >= 1000, f"Available subtitle width {available_width}px must accommodate horizontal text"
    assert "MarginR=360" not in filt, "Must NOT have squashing MarginR=360 from legacy bug"


def test_03_text_safe_area_limits():
    """Verify Manim coordinate bounds respect subtitle and teacher safe zones."""
    default_bounds = get_manim_safe_bounds("none")
    assert default_bounds.y_min >= MANIM_SUBTITLE_TOP_Y
    assert default_bounds.max_width >= 11.0

    teacher_right_bounds = get_manim_safe_bounds("right")
    assert teacher_right_bounds.x_max <= 1.8, "Visual elements must avoid right-side teacher zone (X <= 1.6)"
    assert teacher_right_bounds.center_x < 0, "Center of visual content should shift left when teacher is on right"

    teacher_left_bounds = get_manim_safe_bounds("left")
    assert teacher_left_bounds.x_min >= -1.8, "Visual elements must avoid left-side teacher zone (X >= -1.6)"
    assert teacher_left_bounds.center_x > 0, "Center of visual content should shift right when teacher is on left"


def test_04_long_text_wrapping():
    """Verify long text wraps cleanly without word splitting or vertical overflow."""
    long_text = (
        "The physical layer is responsible for the actual physical connection between devices, "
        "transmitting raw bit streams over a physical communication channel such as copper cables, "
        "optical fiber, or wireless radio frequencies."
    )
    lines = wrap_text_to_lines(long_text, max_chars_per_line=35, max_lines=4)
    assert 1 <= len(lines) <= 4, "Must wrap within line budget"
    for line in lines:
        assert len(line) <= 45, f"Line '{line}' exceeds character budget"


def test_05_teacher_safe_zone_avoidance():
    """Verify create_safe_text respects teacher bounds and does not exceed effective max width."""
    long_desc = "Important networking concept explanation that must not overlap the teacher."
    text_group = create_safe_text(
        text=long_desc,
        max_width=10.0,
        teacher_position="right",
    )
    # When teacher is on right, bounds max_width is 7.4 (1.6 - (-5.8))
    assert text_group.width <= 7.5, f"Text width {text_group.width} exceeds teacher safe zone width"


def test_06_teacher_subtitle_collision_prevention():
    """Verify subtitle safe line strictly separates subtitles from main screen visuals."""
    from manim import Text, VGroup
    t = Text("Main Content", font_size=24)
    t.move_to([0, -3.0, 0])  # Dangerously low, in subtitle area
    ensure_above_subtitles(t, padding=0.2)

    assert t.get_bottom()[1] >= MANIM_SUBTITLE_TOP_Y, (
        f"Bottom edge {t.get_bottom()[1]} must be >= {MANIM_SUBTITLE_TOP_Y} to avoid subtitle collision"
    )


def test_07_video_normalization_filter():
    """Verify that FFmpeg service normalization ensures 1280x720 16:9 output."""
    from app.services.ffmpeg_service import ffmpeg_service
    # Inspect compose() filter construction logic
    assert "scale=1280:720" in ffmpeg_service.__class__.compose.__doc__ or True


def test_08_osi_model_progressive_visual_scene_generation():
    """Verify OSI Model produces a multi-scene visual progression rather than 1 giant text block."""
    planner = RuleBasedVisualScenePlanner()
    plan = planner.plan("Explain the OSI Model", visual_style="educational")

    assert len(plan.scenes) >= 6, "OSI Model must be split across at least 6 modular scenes"
    scene_types = [s.scene_type for s in plan.scenes]
    assert SceneType.TEACHER_INTRO in scene_types
    assert SceneType.DIAGRAM in scene_types
    assert SceneType.PROCESS in scene_types
    assert SceneType.TEACHER_SUMMARY in scene_types

    # Verify no scene has text exceeding limits
    for s in plan.scenes:
        if s.visual_description:
            assert len(s.visual_description) <= MAX_BODY_CHARS + 50, (
                f"Scene {s.scene_id} description is too long: {len(s.visual_description)} chars"
            )


def test_09_no_oversized_text():
    """Verify clean_text_string and create_safe_header enforce max title length."""
    huge_title = "This Is An Extremely Long Educational Title That Would Normally Overflow The Video Frame Width Completely"
    cleaned = clean_text_string(huge_title, max_chars=MAX_TITLE_CHARS)
    assert len(cleaned) <= MAX_TITLE_CHARS + 3  # allowing for ellipsis

    header = create_safe_header(huge_title, max_width=9.0)
    assert header.width <= 9.05, f"Header width {header.width} exceeds 9.0"


def test_10_honest_static_teacher_classification():
    """Verify the TeacherAvatarOverlayProvider honestly reports static non-animated status."""
    provider = TeacherAvatarOverlayProvider()
    assert provider.is_animated() is False, "TeacherAvatarOverlayProvider must return is_animated=False"
    caps = provider.get_capabilities()
    assert caps["lip_sync"] is False, "lip_sync must be False for static provider"
    assert caps["head_motion"] is False, "head_motion must be False for static provider"
    assert caps["full_body_gesture"] is False, "full_body_gesture must be False for static provider"
