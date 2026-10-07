"""
Reusable dynamic visual scene components for educational videos.
Engineered using Manim vector primitives and typography (without LaTeX dependency)
to ensure 100% reliable rendering on any host system.
"""
from typing import List, Optional, Dict
from manim import *


class DynamicTitleScene(Scene):
    """
    Opening Title Card with domain badge, topic header, and subtitle.
    """
    title_text: str = "Academic Topic"
    subtitle_text: str = "Concept Overview"
    domain_text: str = "GENERAL"

    def construct(self):
        # Domain badge pill
        domain_badge = Text(
            f" [ {self.domain_text.upper()} ] ",
            font_size=18,
            weight=BOLD,
            color=TEAL_A,
        ).to_edge(UP, buff=0.8)

        # Title
        title = Text(
            self.title_text,
            font_size=42,
            weight=BOLD,
            color=BLUE_B,
        ).next_to(domain_badge, DOWN, buff=0.4)

        # Underline accent
        underline = Line(
            start=title.get_left() + LEFT * 0.2,
            end=title.get_right() + RIGHT * 0.2,
            color=GOLD,
            stroke_width=3,
        ).next_to(title, DOWN, buff=0.15)

        # Subtitle
        subtitle = Text(
            self.subtitle_text,
            font_size=24,
            color=GRAY_A,
        ).next_to(underline, DOWN, buff=0.4)

        self.play(FadeIn(domain_badge, shift=DOWN * 0.2), run_time=0.6)
        self.play(Write(title), Create(underline), run_time=1.0)
        self.play(FadeIn(subtitle, shift=UP * 0.2), run_time=0.8)
        self.wait(1.4)
        self.play(FadeOut(VGroup(domain_badge, title, underline, subtitle)), run_time=0.6)


class DynamicExplanationScene(Scene):
    """
    Concept explanation scene with card frame, header, and clean wrapped text.
    """
    header_text: str = "Core Concept"
    body_text: str = "Primary explanation text goes here."

    def construct(self):
        header = Text(self.header_text, font_size=34, weight=BOLD, color=TEAL_A).to_edge(UP, buff=0.7)
        divider = Line(LEFT * 5, RIGHT * 5, color=TEAL_E, stroke_width=2).next_to(header, DOWN, buff=0.25)

        # Format body text wrapped
        # Split body text into multiple lines for clean layout if lengthy
        words = self.body_text.split()
        lines = []
        cur_line = []
        cur_len = 0
        for w in words:
            if cur_len + len(w) > 42:
                lines.append(" ".join(cur_line))
                cur_line = [w]
                cur_len = len(w)
            else:
                cur_line.append(w)
                cur_len += len(w) + 1
        if cur_line:
            lines.append(" ".join(cur_line))

        body_mobjects = [Text(l, font_size=24, color=WHITE) for l in lines]
        text_group = VGroup(*body_mobjects).arrange(DOWN, aligned_edge=LEFT, buff=0.25)

        card = RoundedRectangle(
            corner_radius=0.2,
            width=text_group.width + 1.2,
            height=text_group.height + 0.8,
            fill_color=DARK_BLUE,
            fill_opacity=0.3,
            stroke_color=BLUE_D,
            stroke_width=2,
        ).move_to(text_group.get_center())

        content_group = VGroup(card, text_group).move_to(DOWN * 0.2)

        self.play(Write(header), Create(divider), run_time=0.8)
        self.play(Create(card), FadeIn(text_group), run_time=1.2)
        self.wait(2.2)
        self.play(FadeOut(VGroup(header, divider, content_group)), run_time=0.6)


class DynamicFormulaScene(Scene):
    """
    Mathematical / Chemical formula scene with golden highlight frame and variable breakdown.
    """
    header_text: str = "Mathematical Formula"
    formula_text: str = "F = m · a"
    breakdown_items: List[str] = None

    def construct(self):
        if self.breakdown_items is None:
            self.breakdown_items = ["F = Force", "m = Mass", "a = Acceleration"]

        header = Text(self.header_text, font_size=32, weight=BOLD, color=BLUE_B).to_edge(UP, buff=0.6)

        # Formula text in prominent gold
        formula = Text(self.formula_text, font_size=42, weight=BOLD, color=YELLOW).next_to(header, DOWN, buff=0.5)
        box = SurroundingRectangle(formula, color=GOLD, buff=0.25, corner_radius=0.15, stroke_width=3)

        # Breakdown items
        legend_texts = [Text(item, font_size=20, color=GRAY_A) for item in self.breakdown_items]
        legend_group = VGroup(*legend_texts).arrange(DOWN, aligned_edge=LEFT, buff=0.2).next_to(box, DOWN, buff=0.5)

        self.play(Write(header), run_time=0.6)
        self.play(Create(box), Write(formula), run_time=1.0)
        self.play(
            LaggedStart(*[FadeIn(t, shift=RIGHT * 0.2) for t in legend_texts], lag_ratio=0.25),
            run_time=1.2
        )
        self.wait(2.0)
        self.play(FadeOut(VGroup(header, box, formula, legend_group)), run_time=0.6)


class DynamicBulletPointScene(Scene):
    """
    Bulleted key concepts scene with staggered row entrances.
    """
    header_text: str = "Key Principles"
    bullet_items: List[str] = None

    def construct(self):
        if self.bullet_items is None:
            self.bullet_items = ["Principle 1", "Principle 2", "Principle 3"]

        header = Text(self.header_text, font_size=32, weight=BOLD, color=TEAL_A).to_edge(UP, buff=0.7)
        divider = Line(LEFT * 5, RIGHT * 5, color=TEAL_E, stroke_width=2).next_to(header, DOWN, buff=0.2)

        rows = []
        for item in self.bullet_items:
            dot = Dot(color=YELLOW, radius=0.08)
            txt = Text(item, font_size=20, color=WHITE)
            row = VGroup(dot, txt).arrange(RIGHT, buff=0.25)
            rows.append(row)

        row_group = VGroup(*rows).arrange(DOWN, aligned_edge=LEFT, buff=0.35).move_to(DOWN * 0.2)

        self.play(Write(header), Create(divider), run_time=0.7)
        self.play(
            LaggedStart(*[FadeIn(r, shift=RIGHT * 0.3) for r in rows], lag_ratio=0.3),
            run_time=1.4
        )
        self.wait(2.2)
        self.play(FadeOut(VGroup(header, divider, row_group)), run_time=0.6)


class DynamicProcessScene(Scene):
    """
    Step-by-step or algorithm progression scene with numbered stages.
    """
    header_text: str = "Process Workflow"
    step_items: List[str] = None

    def construct(self):
        if self.step_items is None:
            self.step_items = ["Step 1", "Step 2", "Step 3"]

        header = Text(self.header_text, font_size=32, weight=BOLD, color=BLUE_B).to_edge(UP, buff=0.6)

        cards = []
        for i, step_str in enumerate(self.step_items):
            box = RoundedRectangle(
                corner_radius=0.15,
                width=10.0,
                height=0.75,
                fill_color=DARK_BLUE,
                fill_opacity=0.4,
                stroke_color=BLUE_C,
                stroke_width=2,
            )
            txt = Text(step_str, font_size=20, color=WHITE).move_to(box.get_center())
            cards.append(VGroup(box, txt))

        cards_group = VGroup(*cards).arrange(DOWN, buff=0.25).next_to(header, DOWN, buff=0.4)

        self.play(Write(header), run_time=0.6)
        self.play(
            LaggedStart(*[FadeIn(c, shift=UP * 0.2) for c in cards], lag_ratio=0.25),
            run_time=1.5
        )
        self.wait(2.2)
        self.play(FadeOut(VGroup(header, cards_group)), run_time=0.6)


class DynamicHierarchyScene(Scene):
    """
    Layered hierarchy scene (e.g., OSI model, TCP/IP stack) with stacked color tiers.
    """
    header_text: str = "Layer Hierarchy"
    layer_items: List[str] = None

    def construct(self):
        if self.layer_items is None:
            self.layer_items = ["Layer 3", "Layer 2", "Layer 1"]

        header = Text(self.header_text, font_size=32, weight=BOLD, color=GOLD).to_edge(UP, buff=0.6)

        colors = [BLUE_D, BLUE_C, TEAL_D, TEAL_C, GREEN_D, GREEN_C, YELLOW_D]
        layer_boxes = []

        # Height per bar adjusts based on total layers
        h = min(0.65, 4.2 / max(len(self.layer_items), 1))
        f_size = 18 if len(self.layer_items) > 5 else 22

        for i, l_text in enumerate(self.layer_items):
            c = colors[i % len(colors)]
            box = Rectangle(
                width=9.5,
                height=h,
                fill_color=c,
                fill_opacity=0.65,
                stroke_color=WHITE,
                stroke_width=1.5,
            )
            txt = Text(l_text, font_size=f_size, weight=BOLD, color=WHITE).move_to(box.get_center())
            layer_boxes.append(VGroup(box, txt))

        stack = VGroup(*layer_boxes).arrange(DOWN, buff=0.1).next_to(header, DOWN, buff=0.3)

        self.play(Write(header), run_time=0.6)
        self.play(
            LaggedStart(*[FadeIn(lb, shift=DOWN * 0.15) for lb in layer_boxes], lag_ratio=0.18),
            run_time=1.8
        )
        self.wait(2.4)
        self.play(FadeOut(VGroup(header, stack)), run_time=0.6)


class DynamicCycleScene(Scene):
    """
    Continuous cycle scene with connected stages (e.g., Water Cycle).
    """
    header_text: str = "Continuous Cycle"
    stage_items: List[str] = None

    def construct(self):
        if self.stage_items is None:
            self.stage_items = ["Stage 1", "Stage 2", "Stage 3", "Stage 4"]

        header = Text(self.header_text, font_size=32, weight=BOLD, color=TEAL_A).to_edge(UP, buff=0.6)

        stage_blocks = []
        for stage in self.stage_items:
            card = RoundedRectangle(
                corner_radius=0.15,
                width=9.5,
                height=0.75,
                fill_color=DARK_BLUE,
                fill_opacity=0.35,
                stroke_color=TEAL_C,
                stroke_width=2,
            )
            txt = Text(stage, font_size=20, color=WHITE).move_to(card.get_center())
            stage_blocks.append(VGroup(card, txt))

        cycle_group = VGroup(*stage_blocks).arrange(DOWN, buff=0.25).next_to(header, DOWN, buff=0.4)

        self.play(Write(header), run_time=0.6)
        self.play(
            LaggedStart(*[FadeIn(b, shift=RIGHT * 0.2) for b in stage_blocks], lag_ratio=0.25),
            run_time=1.5
        )
        self.wait(2.2)
        self.play(FadeOut(VGroup(header, cycle_group)), run_time=0.6)


class DynamicConclusionScene(Scene):
    """
    Closing takeaway card summarizing the educational lesson.
    """
    title_text: str = "Key Takeaway"
    takeaway_text: str = "Summary of core principle."

    def construct(self):
        badge = Text("CONCLUSION", font_size=18, weight=BOLD, color=GOLD).to_edge(UP, buff=0.8)
        title = Text(self.title_text, font_size=36, weight=BOLD, color=WHITE).next_to(badge, DOWN, buff=0.3)

        words = self.takeaway_text.split()
        lines = []
        cur_line = []
        cur_len = 0
        for w in words:
            if cur_len + len(w) > 42:
                lines.append(" ".join(cur_line))
                cur_line = [w]
                cur_len = len(w)
            else:
                cur_line.append(w)
                cur_len += len(w) + 1
        if cur_line:
            lines.append(" ".join(cur_line))

        body_mobjects = [Text(l, font_size=24, color=GRAY_A) for l in lines]
        text_group = VGroup(*body_mobjects).arrange(DOWN, buff=0.2)

        card = RoundedRectangle(
            corner_radius=0.2,
            width=text_group.width + 1.2,
            height=text_group.height + 0.8,
            fill_color=DARK_BLUE,
            fill_opacity=0.4,
            stroke_color=GOLD,
            stroke_width=2.5,
        ).move_to(text_group.get_center())

        box_group = VGroup(card, text_group).next_to(title, DOWN, buff=0.5)

        self.play(FadeIn(badge), Write(title), run_time=0.8)
        self.play(Create(card), FadeIn(text_group), run_time=1.0)
        self.wait(2.0)
        self.play(FadeOut(VGroup(badge, title, box_group)), run_time=0.6)
