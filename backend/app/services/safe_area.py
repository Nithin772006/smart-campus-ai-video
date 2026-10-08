"""
Safe Area and Visual Layout Specifications (Task 9F - Visual Repair).
Defines standard coordinate systems and constraints for 1280x720 educational videos.
Used across Manim scene generators, avatar overlays, subtitles, and FFmpeg composition.
"""

from pathlib import Path
from typing import Dict, Any, Tuple
from dataclasses import dataclass

# Pixel dimensions for standard output
VIDEO_WIDTH: int = 1280
VIDEO_HEIGHT: int = 720
FPS: int = 30

# Safe Margins (pixels)
SAFE_MARGIN_X: int = 70       # Left/Right margin (approx 5.5% of width)
SAFE_MARGIN_TOP: int = 50     # Top header margin
SAFE_MARGIN_BOTTOM: int = 110 # Bottom margin reserved for subtitles + safety

# Subtitle Safe Area (pixels)
SUBTITLE_MARGIN_BOTTOM: int = 40  # Distance from bottom of screen to subtitle baseline
SUBTITLE_MARGIN_SIDE: int = 80    # Left and right subtitle padding
SUBTITLE_FONT_SIZE: int = 24      # Proportional readable font size for 720p
SUBTITLE_SAFE_HEIGHT: int = 80    # Reserved height band for subtitles (Y: 600 - 680)

# Teacher Avatar Safe Area (pixels)
TEACHER_FRAME_WIDTH: int = 340    # Teacher width (~26.5% of 1280)
TEACHER_SAFE_MARGIN: int = 20     # Margin from screen edge

# Manim Coordinate System Constants (Camera frame is 14.222 x 8.0 units)
MANIM_FRAME_WIDTH: float = 14.2222
MANIM_FRAME_HEIGHT: float = 8.0

# Subtitle boundary in Manim coordinates:
# Y = -4.0 is screen bottom, Y = +4.0 is screen top.
# Bottom 110px of 720px is: 110/720 * 8.0 = 1.22 units from bottom.
# So Y < -2.4 is strictly reserved for subtitles. All visuals must stay Y >= -2.2.
MANIM_SUBTITLE_TOP_Y: float = -2.2
MANIM_HEADER_BOTTOM_Y: float = 3.2

# Text density limits
MAX_TITLE_CHARS: int = 40
MAX_BODY_CHARS: int = 160
MAX_VISIBLE_LINES: int = 5


@dataclass
class ManimBounds:
    """Safe coordinate boundaries for Manim visual elements."""
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    center_x: float

    @property
    def max_width(self) -> float:
        return self.x_max - self.x_min

    @property
    def max_height(self) -> float:
        return self.y_max - self.y_min


def get_manim_safe_bounds(teacher_position: str = "none") -> ManimBounds:
    """
    Computes safe Manim layout bounds based on teacher avatar placement.
    - 'none' or 'center': Full width available (X: -5.8 to +5.8)
    - 'right': Teacher on right; visuals constrained to left/center (X: -5.8 to +1.6)
    - 'left': Teacher on left; visuals constrained to center/right (X: -1.6 to +5.8)
    """
    pos = (teacher_position or "none").lower().strip()
    y_min = MANIM_SUBTITLE_TOP_Y  # -2.2 (strictly above subtitles)
    y_max = MANIM_HEADER_BOTTOM_Y # 3.2

    if pos == "right":
        x_min = -5.8
        x_max = 1.6
        center_x = (x_min + x_max) / 2.0  # -2.1
    elif pos == "left":
        x_min = -1.6
        x_max = 5.8
        center_x = (x_min + x_max) / 2.0  # +2.1
    else:
        x_min = -5.8
        x_max = 5.8
        center_x = 0.0

    return ManimBounds(
        x_min=x_min,
        x_max=x_max,
        y_min=y_min,
        y_max=y_max,
        center_x=center_x,
    )


def build_ffmpeg_subtitle_filter(
    srt_path: Path,
    video_width: int = VIDEO_WIDTH,
    video_height: int = VIDEO_HEIGHT,
    font_size: int = SUBTITLE_FONT_SIZE,
    margin_v: int = SUBTITLE_MARGIN_BOTTOM,
    margin_side: int = SUBTITLE_MARGIN_SIDE,
) -> str:
    """
    Generates a production-grade FFmpeg subtitles filter string.
    Crucial fix:
    1. Sets original_size so libass knows true script resolution and never falls back to 384x288.
    2. Alignment=2 ensures bottom-center horizontal alignment.
    3. Balanced side margins ensure text wraps naturally and never collapses into vertical text.
    4. Black outline (Outline=2) and shadow (Shadow=1) guarantee legibility on any background.
    """
    escaped_path = srt_path.resolve().as_posix().replace(":", r"\:")
    
    # ASS force_style parameters
    style_parts = [
        "Alignment=2",                          # Bottom-Center alignment
        f"FontSize={font_size}",                # Proportional readable font
        "PrimaryColour=&H00FFFFFF",             # Pure white text
        "OutlineColour=&H00000000",             # Pure black outline
        "BackColour=&H80000000",                # 50% opacity shadow box
        "BorderStyle=1",                        # Outline with drop shadow
        "Outline=2",                            # 2px crisp outline
        "Shadow=1",                             # 1px subtle shadow
        f"MarginV={margin_v}",                  # Vertical distance from bottom edge
        f"MarginL={margin_side}",               # Left safe margin
        f"MarginR={margin_side}",               # Right safe margin
    ]
    style_str = ",".join(style_parts)

    return f"subtitles='{escaped_path}':original_size={video_width}x{video_height}:force_style='{style_str}'"
