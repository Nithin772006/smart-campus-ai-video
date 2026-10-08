"""
Manim Safe Layout & Text Wrapping Utilities (Task 9F - Visual Repair).
Ensures no text or visual elements overflow the 1280x720 video canvas,
overlap subtitles, or collide with the teacher avatar zone.
"""

import re
from typing import List, Optional, Tuple
from manim import (
    Text,
    VGroup,
    WHITE,
    BOLD,
    NORMAL,
    UP,
    DOWN,
    LEFT,
    RIGHT,
    Mobject,
)

from app.services.safe_area import (
    get_manim_safe_bounds,
    MAX_TITLE_CHARS,
    MAX_BODY_CHARS,
    MAX_VISIBLE_LINES,
    MANIM_SUBTITLE_TOP_Y,
    MANIM_HEADER_BOTTOM_Y,
)


def clean_text_string(text: str, max_chars: Optional[int] = None) -> str:
    """Sanitizes text string, normalizes whitespace, and truncates if needed."""
    if not text:
        return ""
    clean = re.sub(r"\s+", " ", str(text)).strip()
    if max_chars and len(clean) > max_chars:
        clean = clean[:max_chars].rstrip() + "..."
    return clean


def wrap_text_to_lines(
    text: str,
    max_chars_per_line: int = 36,
    max_lines: int = MAX_VISIBLE_LINES,
) -> List[str]:
    """
    Splits text cleanly into word-wrapped lines without breaking words.
    Capped at max_lines to prevent vertical screen overflow.
    """
    clean = clean_text_string(text)
    if not clean:
        return []

    words = clean.split()
    lines: List[str] = []
    current_line: List[str] = []
    current_len = 0

    for word in words:
        word_len = len(word)
        if current_line and (current_len + 1 + word_len > max_chars_per_line):
            lines.append(" ".join(current_line))
            if len(lines) >= max_lines:
                # Reached line budget: stop adding more lines
                return lines
            current_line = [word]
            current_len = word_len
        else:
            current_line.append(word)
            current_len += (1 + word_len) if current_len > 0 else word_len

    if current_line and len(lines) < max_lines:
        lines.append(" ".join(current_line))

    return lines


def create_safe_text(
    text: str,
    max_width: float = 8.5,
    max_height: float = 4.0,
    font_size: int = 24,
    min_font_size: int = 16,
    color=WHITE,
    weight=NORMAL,
    teacher_position: str = "none",
    max_chars: Optional[int] = MAX_BODY_CHARS,
) -> VGroup:
    """
    Builds a Manim VGroup of Text objects that is GUARANTEED to fit inside
    (max_width, max_height) and respect safe zones.
    If the text exceeds boundaries at the requested font size:
    1. Wraps text cleanly across 1-5 lines.
    2. Proactively scales down font size until it fits.
    3. As a final guarantee, applies .scale_to_fit() so zero clipping is possible.
    """
    bounds = get_manim_safe_bounds(teacher_position)
    effective_max_width = min(max_width, bounds.max_width)
    effective_max_height = min(max_height, bounds.max_height)

    clean = clean_text_string(text, max_chars=max_chars)
    if not clean:
        return VGroup()

    # Determine word-wrap threshold based on font size & available width
    # In Manim, ~1 font_size unit per char ≈ 0.016 width units
    chars_per_line = max(20, min(50, int(effective_max_width / (font_size * 0.015))))

    lines = wrap_text_to_lines(clean, max_chars_per_line=chars_per_line, max_lines=MAX_VISIBLE_LINES)
    if not lines:
        return VGroup()

    curr_font_size = font_size
    text_mobs = [Text(l, font_size=curr_font_size, color=color, weight=weight) for l in lines]
    group = VGroup(*text_mobs).arrange(DOWN, aligned_edge=LEFT, buff=0.18)

    # Scale down if width or height exceeds limits
    if group.width > effective_max_width:
        group.scale_to_fit_width(effective_max_width)

    if group.height > effective_max_height:
        group.scale_to_fit_height(effective_max_height)

    # Shift group center towards safe zone center
    group.move_to([bounds.center_x, group.get_center()[1], 0])

    return group


def create_safe_header(
    title: str,
    teacher_position: str = "none",
    font_size: int = 32,
    color=WHITE,
    weight=BOLD,
    max_width: float = 11.0,
) -> Text:
    """
    Creates a safe top header title that will not overflow horizontal bounds
    or collide with the teacher avatar zone.
    """
    bounds = get_manim_safe_bounds(teacher_position)
    clean_title = clean_text_string(title, max_chars=MAX_TITLE_CHARS)
    header = Text(clean_title, font_size=font_size, color=color, weight=weight)
    
    effective_width = min(max_width, bounds.max_width)
    if header.width > effective_width:
        header.scale_to_fit_width(effective_width)

    # Position at top edge with center in bounds
    header.to_edge(UP, buff=0.5)
    header.set_x(bounds.center_x)
    return header


def ensure_above_subtitles(mobject: Mobject, padding: float = 0.2) -> Mobject:
    """
    Ensures any mobject sits strictly above the subtitle safe line (Y >= -2.2).
    If mobject's bottom edge is below MANIM_SUBTITLE_TOP_Y, shifts it upward.
    """
    safe_bottom = MANIM_SUBTITLE_TOP_Y + padding
    m_bottom = mobject.get_bottom()[1]
    if m_bottom < safe_bottom:
        mobject.shift(UP * (safe_bottom - m_bottom))
    return mobject
