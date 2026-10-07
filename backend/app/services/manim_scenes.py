from manim import *

class NewtonSecondLawScene(Scene):
    """
    Educational animation demonstrating Newton's Second Law of Motion: F = ma.
    Duration: ~12-14 seconds at 30fps.
    """
    def construct(self):
        # 1. Opening title
        title = Text("Newton's Second Law", font_size=42, weight=BOLD, color=BLUE_B)
        subtitle = Text("Force determines how an object's motion changes.", font_size=24, color=GRAY_A)
        header_group = VGroup(title, subtitle).arrange(DOWN, buff=0.3)

        self.play(Write(title), run_time=1.0)
        self.play(FadeIn(subtitle, shift=UP * 0.2), run_time=0.8)
        self.wait(0.5)

        # Shift title to header, fade out initial explanation
        self.play(
            title.animate.scale(0.8).to_edge(UP, buff=0.4),
            FadeOut(subtitle),
            run_time=0.8
        )

        # 2. Display a simple square representing an object (mass m)
        box = Square(side_length=1.5, color=TEAL, fill_color=TEAL_E, fill_opacity=0.7)
        box.shift(LEFT * 2.5 + DOWN * 0.8)
        mass_label = Text("m", font_size=32, weight=BOLD, color=WHITE).move_to(box.get_center())
        object_group = VGroup(box, mass_label)

        self.play(Create(box), Write(mass_label), run_time=0.8)

        # 3. Show a force arrow pointing toward the object
        force_arrow = Arrow(
            start=box.get_left() + LEFT * 2.0,
            end=box.get_left(),
            color=YELLOW,
            buff=0.1,
            stroke_width=6,
            max_tip_length_to_length_ratio=0.25
        )
        force_label = Text("F", font_size=32, weight=BOLD, color=YELLOW).next_to(force_arrow, UP, buff=0.15)

        self.play(GrowArrow(force_arrow), FadeIn(force_label), run_time=0.8)

        # Animate object accelerating forward under applied force
        self.play(
            object_group.animate.shift(RIGHT * 2.0),
            force_arrow.animate.shift(RIGHT * 2.0),
            force_label.animate.shift(RIGHT * 2.0),
            run_time=1.0,
            rate_func=rate_functions.ease_in_quad
        )
        self.wait(0.4)

        # Clean up motion demo before formula introduction
        self.play(
            FadeOut(object_group),
            FadeOut(force_arrow),
            FadeOut(force_label),
            run_time=0.6
        )

        # 4. Introduce F = ma
        f_sym = Text("F", font_size=52, weight=BOLD, color=YELLOW)
        eq_sym = Text(" = ", font_size=52, weight=BOLD, color=WHITE)
        m_sym = Text("m", font_size=52, weight=BOLD, color=TEAL_A)
        a_sym = Text("a", font_size=52, weight=BOLD, color=RED_B)
        formula = VGroup(f_sym, eq_sym, m_sym, a_sym).arrange(RIGHT, buff=0.15).shift(UP * 1.0)

        self.play(FadeIn(formula, shift=DOWN * 0.3), run_time=0.8)

        # 5. Explain visually:
        # F = Force
        # m = Mass
        # a = Acceleration
        f_item = Text("F = Force", font_size=24, color=YELLOW)
        m_item = Text("m = Mass", font_size=24, color=TEAL_A)
        a_item = Text("a = Acceleration", font_size=24, color=RED_B)
        legend = VGroup(f_item, m_item, a_item).arrange(DOWN, aligned_edge=LEFT, buff=0.25).next_to(formula, DOWN, buff=0.6)

        self.play(
            LaggedStart(
                Write(f_item),
                Write(m_item),
                Write(a_item),
                lag_ratio=0.25
            ),
            run_time=1.2
        )
        self.wait(0.5)

        # 6. Demonstrate relationship: More force -> more acceleration
        relationship_text = Text(
            "More force \u2192 more acceleration",
            font_size=24,
            weight=BOLD,
            color=GREEN_B
        ).next_to(legend, DOWN, buff=0.5)

        self.play(FadeIn(relationship_text, shift=UP * 0.2), run_time=0.8)
        self.wait(0.8)

        # 7. End with the formula clearly visible
        self.play(
            FadeOut(legend),
            FadeOut(relationship_text),
            formula.animate.scale(1.2).move_to(UP * 0.3),
            run_time=0.8
        )
        box_highlight = SurroundingRectangle(
            formula,
            color=GOLD,
            buff=0.3,
            corner_radius=0.2,
            stroke_width=4
        )
        law_summary = Text(
            "Acceleration is directly proportional to net force",
            font_size=22,
            color=GRAY_A
        ).next_to(box_highlight, DOWN, buff=0.5)

        self.play(Create(box_highlight), FadeIn(law_summary), run_time=0.8)
        self.wait(1.2)
