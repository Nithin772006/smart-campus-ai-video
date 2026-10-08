"""
Manim Scene Renderer (Task 9C).
Renders educational visual scenes using Manim vector animation primitives.
Supports equations, physics simulations, graphs, diagrams, processes, and algorithms.
Produces verified MP4 output without crashing on unsupported types.
"""

import os
import sys
import time
import shutil
import logging
import subprocess
import tempfile
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

from app.config import settings
from app.schemas.visual_scene import (
    VisualEngine,
    SceneType,
    RoutedScene,
    VisualScene,
)
from app.schemas.render import RenderedScene
from app.services.renderers.base import SceneRenderer
from app.services.ffmpeg_service import ffmpeg_service

logger = logging.getLogger(__name__)

# Quality flag mapping
QUALITY_FLAGS = {
    "low": "-ql",
    "low_quality": "-ql",
    "medium": "-qm",
    "medium_quality": "-qm",
    "high": "-qh",
    "high_quality": "-qh",
}


class ManimRenderer(SceneRenderer):
    """
    Renders RoutedScenes into MP4 videos using Manim vector animations.
    Reuses existing dynamic scene templates and vector components.
    """

    SUPPORTED_TYPES = {
        SceneType.TITLE,
        SceneType.EXPLANATION,
        SceneType.EQUATION,
        SceneType.DIAGRAM,
        SceneType.GRAPH,
        SceneType.PROCESS,
        SceneType.ALGORITHM,
        SceneType.PHYSICS_SIMULATION,
        SceneType.CHEMISTRY_VISUAL,
        SceneType.BIOLOGY_VISUAL,
        SceneType.TIMELINE,
        SceneType.COMPARISON,
        SceneType.TRANSITION,
        SceneType.CINEMATIC,
    }

    @property
    def engine_name(self) -> str:
        return "manim"

    def can_render(self, scene: RoutedScene) -> bool:
        """Checks if the scene is targeted for Manim or fallback to Manim, and has a supported scene type."""
        engine_matches = (
            scene.selected_engine in (VisualEngine.MANIM, VisualEngine.MIXED)
            or scene.fallback_engine == VisualEngine.MANIM
        )
        type_matches = scene.scene.scene_type in self.SUPPORTED_TYPES
        return engine_matches and type_matches

    def render(
        self,
        scene: RoutedScene,
        output_dir: Path,
        **kwargs: Any
    ) -> RenderedScene:
        """
        Execute Manim to render the scene and produce a real MP4.
        Saves to output_dir / "scene.mp4".
        """
        visual_scene = scene.scene
        scene_id = visual_scene.scene_id
        scene_type = visual_scene.scene_type

        output_dir.mkdir(parents=True, exist_ok=True)
        target_path = output_dir / "scene.mp4"

        quality = kwargs.get("quality", "medium_quality")
        quality_flag = QUALITY_FLAGS.get(quality, "-qm")

        # 1. Check supported types
        if visual_scene.scene_type not in self.SUPPORTED_TYPES:
            logger.warning("[ManimRenderer] Scene type '%s' is not supported by ManimRenderer.", scene_type)
            return RenderedScene(
                scene_id=scene_id,
                video_path="",
                duration_seconds=0.0,
                engine=self.engine_name,
                success=False,
                error=f"Scene type '{scene_type}' is not supported by ManimRenderer",
                metadata={"quality": quality, "requested_type": str(scene_type)},
            )

        # 2. Build Python Manim script
        script_code, scene_class_name = self._generate_script(visual_scene)

        # 3. Create isolated temp directory outside repo root to prevent uvicorn reloads
        temp_dir = Path(tempfile.mkdtemp(prefix="manim_scene_render_"))
        script_file = temp_dir / "scene_script.py"

        try:
            script_file.write_text(script_code, encoding="utf-8")
            start_time = time.perf_counter()

            cmd = [
                sys.executable,
                "-m",
                "manim",
                "render",
                quality_flag,
                "--media_dir",
                str(temp_dir),
                str(script_file),
                scene_class_name,
            ]

            env = os.environ.copy()
            if "PYTHONHASHSEED" in env:
                seed_val = env.get("PYTHONHASHSEED", "")
                if seed_val != "random" and not (seed_val.isdigit() and 0 <= int(seed_val) <= 4294967295):
                    del env["PYTHONHASHSEED"]

            logger.info("[ManimRenderer] Executing Manim for scene %s (%s)", scene_id, scene_type)
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                cwd=str(settings.BASE_DIR),
            )

            if res.returncode != 0:
                logger.error("[ManimRenderer] Manim CLI failed for %s:\n%s", scene_id, res.stderr[-500:])
                return RenderedScene(
                    scene_id=scene_id,
                    video_path="",
                    duration_seconds=0.0,
                    engine=self.engine_name,
                    success=False,
                    error=f"Manim execution error: {res.stderr[-300:].strip()}",
                    metadata={"returncode": res.returncode},
                )

            # 4. Locate the generated MP4 file
            found_mp4s = list(temp_dir.glob("**/*.mp4"))
            if not found_mp4s:
                return RenderedScene(
                    scene_id=scene_id,
                    video_path="",
                    duration_seconds=0.0,
                    engine=self.engine_name,
                    success=False,
                    error="Manim executed successfully but no MP4 output was discovered",
                )

            # Sort by file size descending to pick the rendered output over temp clips
            found_mp4s.sort(key=lambda p: p.stat().st_size, reverse=True)
            rendered_source = found_mp4s[0]

            shutil.copy2(str(rendered_source), str(target_path))
            render_elapsed = round(time.perf_counter() - start_time, 2)

            # 5. Probe media properties
            duration_seconds = visual_scene.duration_seconds
            width, height, codec = None, None, "h264"
            if ffmpeg_service.is_available():
                try:
                    probe = ffmpeg_service.probe_media(target_path)
                    duration_seconds = probe.get("duration", duration_seconds)
                    width = probe.get("width")
                    height = probe.get("height")
                    codec = probe.get("video_codec", "h264")
                except Exception as pe:
                    logger.warning("Optional probe failed: %s", pe)

            # Compute relative path
            try:
                rel_path = str(target_path.relative_to(settings.BASE_DIR)).replace("\\", "/")
            except ValueError:
                rel_path = f"generated/rendered_scenes/{target_path.parent.name}/{target_path.name}"

            logger.info(
                "[ManimRenderer] Scene %s rendered successfully: %s (%.2fs duration, %.2fs render time)",
                scene_id, target_path.name, duration_seconds, render_elapsed
            )

            return RenderedScene(
                scene_id=scene_id,
                video_path=rel_path,
                duration_seconds=duration_seconds,
                engine=self.engine_name,
                success=True,
                error=None,
                metadata={
                    "quality": quality,
                    "resolution": f"{width}x{height}" if width and height else "720p",
                    "codec": codec,
                    "render_elapsed_seconds": render_elapsed,
                    "scene_type": str(scene_type),
                },
            )

        except Exception as e:
            logger.error("[ManimRenderer] Exception during rendering scene %s: %s", scene_id, e, exc_info=True)
            return RenderedScene(
                scene_id=scene_id,
                video_path="",
                duration_seconds=0.0,
                engine=self.engine_name,
                success=False,
                error=f"ManimRenderer exception: {str(e)}",
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _generate_script(self, visual_scene: VisualScene) -> tuple[str, str]:
        """
        Generate Manim python script code for the given scene.
        Returns (script_code, scene_class_name).
        """
        stype = visual_scene.scene_type
        class_name = f"Generated{stype.value.title().replace('_', '')}Scene"
        desc_lower = ((visual_scene.visual_description or "") + " " + (visual_scene.narration or "")).lower()

        # 1. Newton's 2nd Law physics simulation
        if stype in (SceneType.PHYSICS_SIMULATION, SceneType.EQUATION) and any(
            k in desc_lower for k in ("newton", "force", "f = ma", "mass m", "accelerat")
        ):
            return self._script_newton_physics(visual_scene, class_name), class_name

        # 2. Photosynthesis / Chloroplast biology
        if (stype in (SceneType.BIOLOGY_VISUAL, SceneType.EQUATION, SceneType.PROCESS, SceneType.COMPARISON) or "photosynthesis" in desc_lower) and any(
            k in desc_lower for k in ("photosynthesis", "chloroplast", "thylakoid", "glucose", "co2", "stomata")
        ):
            return self._script_photosynthesis(visual_scene, class_name), class_name

        # 3. Binary Search algorithm / array
        if (stype in (SceneType.ALGORITHM, SceneType.PROCESS) or "binary search" in desc_lower) and any(
            k in desc_lower for k in ("binary search", "sorted array", "divide and conquer", "pointer", "log n")
        ):
            return self._script_binary_search(visual_scene, class_name), class_name

        # 4. OSI Reference Model / Stack
        if any(k in desc_lower for k in ("osi model", "7 layers", "seven layers", "layer 7", "physical layer", "data link", "layer hierarchy", "network layers")):
            return self._script_osi_stack(visual_scene, class_name), class_name

        # 5. Network packet flow / transmission
        if any(k in desc_lower for k in ("packet", "router", "switch", "host a", "server b", "transmission", "signal", "routing")):
            return self._script_network_flow(visual_scene, class_name), class_name

        # 6. Vector Diagram
        if stype == SceneType.DIAGRAM and any(k in desc_lower for k in ("vector", "free body", "force", "normal force")):
            return self._script_vector_diagram(visual_scene, class_name), class_name

        # 7. Cinematic Fallback
        if stype == SceneType.CINEMATIC:
            return self._script_cinematic_fallback(visual_scene, class_name), class_name

        # Standard scene primitives with strict safe-area constraints
        if stype == SceneType.TITLE:
            return self._script_title(visual_scene, class_name), class_name
        elif stype == SceneType.EQUATION:
            return self._script_formula(visual_scene, class_name), class_name
        elif stype in (SceneType.PROCESS, SceneType.ALGORITHM):
            return self._script_process(visual_scene, class_name), class_name
        elif stype == SceneType.GRAPH:
            return self._script_graph(visual_scene, class_name), class_name
        else:
            return self._script_explanation(visual_scene, class_name), class_name

    def _script_osi_stack(self, scene: VisualScene, class_name: str) -> str:
        """High-clarity 7-layer stacked model for OSI Reference Architecture."""
        return f"""from manim import *

class {class_name}(Scene):
    def construct(self):
        head = Text("OSI Reference Model: 7 Layers", font_size=28, weight=BOLD, color=GOLD).to_edge(UP, buff=0.45)
        if head.width > 9.0:
            head.scale_to_fit_width(9.0)

        layers = [
            ("7. Application", "#38bdf8", "HTTP, DNS, SSH (User Interface)"),
            ("6. Presentation", "#60a5fa", "Data formatting & TLS encryption"),
            ("5. Session", "#818cf8", "Connection management & dialogs"),
            ("4. Transport", "#a78bfa", "TCP segments & reliable delivery"),
            ("3. Network", "#34d399", "IP packets & routing across internet"),
            ("2. Data Link", "#2dd4bf", "MAC frames & switches on local LAN"),
            ("1. Physical", "#f59e0b", "Raw electrical/optical bit signals"),
        ]

        boxes = []
        for name, col, desc in layers:
            rect = Rectangle(width=7.8, height=0.42, fill_color=col, fill_opacity=0.75, stroke_color=WHITE, stroke_width=1.2)
            lbl = Text(name, font_size=15, weight=BOLD, color=WHITE).move_to(rect.get_left() + RIGHT * 1.5)
            detail = Text(desc, font_size=12, color=WHITE).move_to(rect.get_right() + LEFT * 2.3)
            if detail.width > 3.8:
                detail.scale_to_fit_width(3.8)
            boxes.append(VGroup(rect, lbl, detail))

        stack = VGroup(*boxes).arrange(DOWN, buff=0.08).next_to(head, DOWN, buff=0.25)
        if stack.get_bottom()[1] < -2.2:
            stack.shift(UP * (-2.2 - stack.get_bottom()[1] + 0.15))

        self.play(Write(head), run_time=0.6)
        self.play(LaggedStart(*[FadeIn(b, shift=DOWN * 0.1) for b in boxes], lag_ratio=0.15), run_time=1.4)
        self.wait(2.0)
        self.play(FadeOut(VGroup(head, stack)), run_time=0.5)
"""

    def _script_network_flow(self, scene: VisualScene, class_name: str) -> str:
        """Visual packet movement between nodes (Computer -> Router -> Server)."""
        title = repr(scene.educational_goal[:40] if scene.educational_goal else "Packet Transmission")
        return f"""from manim import *

class {class_name}(Scene):
    def construct(self):
        head = Text({title}, font_size=28, weight=BOLD, color=TEAL_A).to_edge(UP, buff=0.5)
        if head.width > 9.0:
            head.scale_to_fit_width(9.0)

        # 3 Nodes: Host A, Router, Server B
        node_a = RoundedRectangle(corner_radius=0.15, width=2.0, height=1.1, color=BLUE, fill_color=DARK_BLUE, fill_opacity=0.8).shift(LEFT * 3.8 + DOWN * 0.1)
        lbl_a = Text("Host A", font_size=17, weight=BOLD, color=WHITE).move_to(node_a.get_center())
        group_a = VGroup(node_a, lbl_a)

        router = Circle(radius=0.65, color=GREEN, fill_color="#064e3b", fill_opacity=0.8).shift(DOWN * 0.1)
        lbl_r = Text("Router", font_size=15, weight=BOLD, color=WHITE).move_to(router.get_center())
        group_r = VGroup(router, lbl_r)

        node_b = RoundedRectangle(corner_radius=0.15, width=2.0, height=1.1, color=BLUE, fill_color=DARK_BLUE, fill_opacity=0.8).shift(RIGHT * 3.8 + DOWN * 0.1)
        lbl_b = Text("Server B", font_size=17, weight=BOLD, color=WHITE).move_to(node_b.get_center())
        group_b = VGroup(node_b, lbl_b)

        link_1 = Line(node_a.get_right(), router.get_left(), color=GRAY_A, stroke_width=3)
        link_2 = Line(router.get_right(), node_b.get_left(), color=GRAY_A, stroke_width=3)

        self.play(Write(head), run_time=0.5)
        self.play(FadeIn(group_a), FadeIn(group_r), FadeIn(group_b), Create(link_1), Create(link_2), run_time=0.8)

        # Animated Packet
        packet = RoundedRectangle(corner_radius=0.08, width=0.8, height=0.4, color=YELLOW, fill_color=GOLD, fill_opacity=0.9).move_to(node_a.get_center())
        pkt_lbl = Text("Packet", font_size=12, color=BLACK, weight=BOLD).move_to(packet.get_center())
        pkt_group = VGroup(packet, pkt_lbl)

        self.play(FadeIn(pkt_group), run_time=0.3)
        self.play(pkt_group.animate.move_to(router.get_center()), run_time=0.9)
        self.play(pkt_group.animate.move_to(node_b.get_center()), run_time=0.9)
        self.wait(1.2)
        self.play(FadeOut(VGroup(head, group_a, group_r, group_b, link_1, link_2, pkt_group)), run_time=0.5)
"""

    def _script_title(self, scene: VisualScene, class_name: str) -> str:
        title_text = repr(scene.visual_description[:50] if scene.visual_description else "Educational Lesson")
        subtitle_text = repr(scene.narration[:70] if scene.narration else "Instructional Overview")
        return f"""from manim import *

class {class_name}(Scene):
    def construct(self):
        title = Text({title_text}, font_size=36, weight=BOLD, color=BLUE_B).to_edge(UP, buff=1.0)
        if title.width > 9.5:
            title.scale_to_fit_width(9.5)
        line_w = min(title.width + 0.6, 9.0)
        underline = Line(LEFT * (line_w/2), RIGHT * (line_w/2), color=GOLD, stroke_width=3).next_to(title, DOWN, buff=0.18)
        sub = Text({subtitle_text}, font_size=22, color=GRAY_A).next_to(underline, DOWN, buff=0.35)
        if sub.width > 8.5:
            sub.scale_to_fit_width(8.5)
        group = VGroup(title, underline, sub)
        if group.get_bottom()[1] < -2.2:
            group.shift(UP * (-2.2 - group.get_bottom()[1] + 0.2))
        self.play(Write(title), Create(underline), run_time=0.8)
        self.play(FadeIn(sub, shift=UP * 0.2), run_time=0.6)
        self.wait(1.5)
        self.play(FadeOut(group), run_time=0.5)
"""

    def _script_formula(self, scene: VisualScene, class_name: str) -> str:
        header = repr(scene.educational_goal[:45] if scene.educational_goal else "Mathematical Formulation")
        formula = repr(scene.visual_description[:45] if scene.visual_description else "F = m · a")
        return f"""from manim import *

class {class_name}(Scene):
    def construct(self):
        head = Text({header}, font_size=30, weight=BOLD, color=BLUE_B).to_edge(UP, buff=0.6)
        if head.width > 9.5:
            head.scale_to_fit_width(9.5)
        form = Text({formula}, font_size=38, weight=BOLD, color=YELLOW).next_to(head, DOWN, buff=0.5)
        if form.width > 8.0:
            form.scale_to_fit_width(8.0)
        frame = SurroundingRectangle(form, color=GOLD, buff=0.25, corner_radius=0.15, stroke_width=2.5)
        group = VGroup(head, frame, form)
        if group.get_bottom()[1] < -2.2:
            group.shift(UP * (-2.2 - group.get_bottom()[1] + 0.2))
        self.play(Write(head), run_time=0.6)
        self.play(Create(frame), Write(form), run_time=0.9)
        self.wait(2.0)
        self.play(FadeOut(group), run_time=0.5)
"""

    def _script_graph(self, scene: VisualScene, class_name: str) -> str:
        header = repr("Relationship & Proportion Graph")
        return f"""from manim import *

class {class_name}(Scene):
    def construct(self):
        head = Text({header}, font_size=30, weight=BOLD, color=TEAL_A).to_edge(UP, buff=0.5)
        if head.width > 9.5:
            head.scale_to_fit_width(9.5)
        axes = Axes(
            x_range=[0, 10, 2],
            y_range=[0, 10, 2],
            x_length=5.5,
            y_length=3.5,
            axis_config={{"color": BLUE}},
        ).move_to(DOWN * 0.2)
        curve = axes.plot(lambda x: 0.8 * x, color=GREEN)
        group = VGroup(head, axes, curve)
        if group.get_bottom()[1] < -2.2:
            group.shift(UP * (-2.2 - group.get_bottom()[1] + 0.2))
        self.play(Write(head), Create(axes), run_time=0.7)
        self.play(Create(curve), run_time=1.0)
        self.wait(1.5)
        self.play(FadeOut(group), run_time=0.5)
"""

    def _script_process(self, scene: VisualScene, class_name: str) -> str:
        header = repr(scene.educational_goal[:45] if scene.educational_goal else "Process Progression")
        return f"""from manim import *

class {class_name}(Scene):
    def construct(self):
        head = Text({header}, font_size=30, weight=BOLD, color=TEAL_A).to_edge(UP, buff=0.6)
        if head.width > 9.5:
            head.scale_to_fit_width(9.5)
        divider = Line(LEFT * 4.5, RIGHT * 4.5, color=TEAL_E, stroke_width=2).next_to(head, DOWN, buff=0.2)
        
        step1 = Text("1. Initialize Search Boundary", font_size=20, color=WHITE)
        step2 = Text("2. Examine Midpoint Element", font_size=20, color=YELLOW)
        step3 = Text("3. Discard Subarray Halves Logarithmically", font_size=20, color=WHITE)
        for s in (step1, step2, step3):
            if s.width > 8.0:
                s.scale_to_fit_width(8.0)
        steps = VGroup(step1, step2, step3).arrange(DOWN, aligned_edge=LEFT, buff=0.3).next_to(divider, DOWN, buff=0.3)
        group = VGroup(head, divider, steps)
        if group.get_bottom()[1] < -2.2:
            group.shift(UP * (-2.2 - group.get_bottom()[1] + 0.2))
        self.play(Write(head), Create(divider), run_time=0.6)
        self.play(LaggedStart(FadeIn(step1), FadeIn(step2), FadeIn(step3), lag_ratio=0.25), run_time=1.3)
        self.wait(1.5)
        self.play(FadeOut(group), run_time=0.5)
"""

    def _script_explanation(self, scene: VisualScene, class_name: str) -> str:
        header = repr(scene.educational_goal[:40] if scene.educational_goal else "Key Concept Overview")
        body_raw = scene.visual_description if scene.visual_description else scene.narration
        body_words = " ".join((body_raw or "").split())[:140]
        return f"""from manim import *

class {class_name}(Scene):
    def construct(self):
        head = Text({header}, font_size=28, weight=BOLD, color=TEAL_A).to_edge(UP, buff=0.55)
        if head.width > 9.0:
            head.scale_to_fit_width(9.0)
        divider = Line(LEFT * 4.5, RIGHT * 4.5, color=TEAL_E, stroke_width=2).next_to(head, DOWN, buff=0.2)
        
        words = {repr(body_words)}.split()
        lines = []
        cur = []
        for w in words:
            if cur and sum(len(x)+1 for x in cur) + len(w) > 42:
                lines.append(" ".join(cur))
                if len(lines) >= 4:
                    break
                cur = [w]
            else:
                cur.append(w)
        if cur and len(lines) < 4:
            lines.append(" ".join(cur))
        
        mobs = [Text(l, font_size=20, color=WHITE) for l in lines]
        txt_group = VGroup(*mobs).arrange(DOWN, aligned_edge=LEFT, buff=0.16)
        if txt_group.width > 8.0:
            txt_group.scale_to_fit_width(8.0)
        if txt_group.height > 3.0:
            txt_group.scale_to_fit_height(3.0)
            
        card = RoundedRectangle(
            corner_radius=0.15,
            width=min(txt_group.width + 1.0, 9.0),
            height=min(txt_group.height + 0.6, 3.5),
            fill_color=DARK_BLUE,
            fill_opacity=0.4,
            stroke_color=BLUE_D,
            stroke_width=2,
        ).move_to(txt_group.get_center())
        
        content = VGroup(card, txt_group).next_to(divider, DOWN, buff=0.35)
        if content.get_bottom()[1] < -2.2:
            content.shift(UP * (-2.2 - content.get_bottom()[1] + 0.2))
            
        self.play(Write(head), Create(divider), run_time=0.6)
        self.play(Create(card), FadeIn(txt_group), run_time=0.9)
        self.wait(1.8)
        self.play(FadeOut(VGroup(head, divider, content)), run_time=0.5)
"""

    def _script_newton_physics(self, scene: VisualScene, class_name: str) -> str:
        """Specialized high-quality educational animation for Newton's 2nd law box + arrow."""
        return f"""from manim import *

class {class_name}(Scene):
    def construct(self):
        # 1. Header
        header = Text("Newton's Second Law: F = m · a", font_size=34, weight=BOLD, color=BLUE_B).to_edge(UP, buff=0.5)
        self.play(Write(header), run_time=0.6)

        # 2. Object block (Mass m)
        box = Square(side_length=1.4, color=TEAL, fill_color=TEAL_E, fill_opacity=0.85)
        box.shift(LEFT * 2.8 + DOWN * 0.4)
        mass_label = Text("m = 5 kg", font_size=24, weight=BOLD, color=WHITE).move_to(box.get_center())
        block_group = VGroup(box, mass_label)
        self.play(Create(box), Write(mass_label), run_time=0.6)

        # 3. Applied Force Arrow
        force_arrow = Arrow(
            start=box.get_left() + LEFT * 1.8,
            end=box.get_left(),
            color=YELLOW,
            buff=0.1,
            stroke_width=6,
            max_tip_length_to_length_ratio=0.25
        )
        force_label = Text("F = 20 N", font_size=24, weight=BOLD, color=YELLOW).next_to(force_arrow, UP, buff=0.1)
        self.play(GrowArrow(force_arrow), FadeIn(force_label), run_time=0.6)

        # 4. Acceleration animation
        self.play(
            block_group.animate.shift(RIGHT * 3.8),
            force_arrow.animate.shift(RIGHT * 3.8),
            force_label.animate.shift(RIGHT * 3.8),
            run_time=1.4,
            rate_func=rate_functions.ease_in_quad
        )

        # 5. Resulting Equation Callout
        eq = Text("a = F / m = 4 m/s²", font_size=32, weight=BOLD, color=GOLD).to_edge(DOWN, buff=0.8)
        box_frame = SurroundingRectangle(eq, color=YELLOW, buff=0.2, corner_radius=0.1)
        self.play(Write(eq), Create(box_frame), run_time=0.8)
        self.wait(1.0)
"""

    def _script_title(self, scene: VisualScene, class_name: str) -> str:
        title_text = repr(scene.visual_description[:60] if scene.visual_description else "Educational Lesson")
        subtitle_text = repr(scene.narration[:80] if scene.narration else "Instructional Overview")
        return f"""from manim import *

class {class_name}(Scene):
    def construct(self):
        title = Text({title_text}, font_size=40, weight=BOLD, color=BLUE_B).to_edge(UP, buff=1.2)
        underline = Line(LEFT * 4, RIGHT * 4, color=GOLD, stroke_width=3).next_to(title, DOWN, buff=0.2)
        sub = Text({subtitle_text}, font_size=24, color=GRAY_A).next_to(underline, DOWN, buff=0.4)
        self.play(Write(title), Create(underline), run_time=0.9)
        self.play(FadeIn(sub, shift=UP * 0.2), run_time=0.8)
        self.wait(1.5)
        self.play(FadeOut(VGroup(title, underline, sub)), run_time=0.5)
"""

    def _script_formula(self, scene: VisualScene, class_name: str) -> str:
        header = repr(scene.educational_goal or "Mathematical Formulation")
        formula = repr(scene.visual_description[:50] if scene.visual_description else "F = m · a")
        return f"""from manim import *

class {class_name}(Scene):
    def construct(self):
        head = Text({header}, font_size=32, weight=BOLD, color=BLUE_B).to_edge(UP, buff=0.7)
        form = Text({formula}, font_size=42, weight=BOLD, color=YELLOW).next_to(head, DOWN, buff=0.6)
        frame = SurroundingRectangle(form, color=GOLD, buff=0.3, corner_radius=0.15, stroke_width=3)
        self.play(Write(head), run_time=0.6)
        self.play(Create(frame), Write(form), run_time=1.0)
        self.wait(2.0)
        self.play(FadeOut(VGroup(head, frame, form)), run_time=0.5)
"""

    def _script_graph(self, scene: VisualScene, class_name: str) -> str:
        header = repr("Relationship & Proportion Graph")
        return f"""from manim import *

class {class_name}(Scene):
    def construct(self):
        head = Text({header}, font_size=32, weight=BOLD, color=TEAL_A).to_edge(UP, buff=0.5)
        axes = Axes(
            x_range=[0, 10, 2],
            y_range=[0, 10, 2],
            x_length=6,
            y_length=4,
            axis_config={{"color": BLUE}},
        ).move_to(DOWN * 0.3)
        curve = axes.plot(lambda x: 0.8 * x, color=GREEN)
        self.play(Write(head), Create(axes), run_time=0.8)
        self.play(Create(curve), run_time=1.2)
        self.wait(1.5)
        self.play(FadeOut(VGroup(head, axes, curve)), run_time=0.5)
"""

    def _script_process(self, scene: VisualScene, class_name: str) -> str:
        header = repr(scene.educational_goal or "Algorithm / Process Progression")
        return f"""from manim import *

class {class_name}(Scene):
    def construct(self):
        head = Text({header}, font_size=32, weight=BOLD, color=TEAL_A).to_edge(UP, buff=0.6)
        divider = Line(LEFT * 5, RIGHT * 5, color=TEAL_E, stroke_width=2).next_to(head, DOWN, buff=0.2)
        
        step1 = Text("1. Initialize Search Boundary", font_size=22, color=WHITE)
        step2 = Text("2. Examine Midpoint Element", font_size=22, color=YELLOW)
        step3 = Text("3. Discard Subarray Halves Logarithmically", font_size=22, color=WHITE)
        steps = VGroup(step1, step2, step3).arrange(DOWN, aligned_edge=LEFT, buff=0.35).move_to(DOWN * 0.2)
        
        self.play(Write(head), Create(divider), run_time=0.6)
        self.play(LaggedStart(FadeIn(step1), FadeIn(step2), FadeIn(step3), lag_ratio=0.3), run_time=1.5)
        self.wait(1.5)
        self.play(FadeOut(VGroup(head, divider, steps)), run_time=0.5)
"""

    def _script_explanation(self, scene: VisualScene, class_name: str) -> str:
        header = repr("Key Concept Overview")
        body = repr(scene.visual_description[:100] if scene.visual_description else scene.narration[:100])
        return f"""from manim import *

class {class_name}(Scene):
    def construct(self):
        head = Text({header}, font_size=34, weight=BOLD, color=TEAL_A).to_edge(UP, buff=0.7)
        divider = Line(LEFT * 5, RIGHT * 5, color=TEAL_E, stroke_width=2).next_to(head, DOWN, buff=0.25)
        txt = Text({body}, font_size=24, color=WHITE).next_to(divider, DOWN, buff=0.6)
        self.play(Write(head), Create(divider), run_time=0.7)
        self.play(FadeIn(txt), run_time=1.0)
        self.wait(1.8)
        self.play(FadeOut(VGroup(head, divider, txt)), run_time=0.5)
"""

    def _script_photosynthesis(self, scene: VisualScene, class_name: str) -> str:
        """High-impact biology visualization for Photosynthesis."""
        header_text = repr("Photosynthesis: Solar Conversion in Chloroplast")
        eq_text = repr("6CO2 + 6H2O + Light -> C6H12O6 + 6O2")
        return f"""from manim import *

class {class_name}(Scene):
    def construct(self):
        # 1. Header (Subtitle safe: top 15%)
        header = Text({header_text}, font_size=30, weight=BOLD, color=GREEN_B).to_edge(UP, buff=0.5)
        self.play(Write(header), run_time=0.6)

        # 2. Chloroplast outer double membrane
        outer_membrane = Ellipse(width=6.0, height=3.2, color=GREEN_D, stroke_width=4, fill_color="#064e3b", fill_opacity=0.6).shift(UP * 0.2)
        inner_label = Text("Chloroplast (Stroma)", font_size=20, color=GREEN_A).next_to(outer_membrane.get_top(), DOWN, buff=0.2)
        self.play(Create(outer_membrane), FadeIn(inner_label), run_time=0.7)

        # 3. Thylakoid Stacks (Granum)
        stack1 = VGroup(*[RoundedRectangle(corner_radius=0.1, width=1.1, height=0.25, color=TEAL_C, fill_color=TEAL_D, fill_opacity=0.9).shift(UP * 0.2 + LEFT * 1.6 + UP * (i * 0.3 - 0.3)) for i in range(3)])
        stack2 = VGroup(*[RoundedRectangle(corner_radius=0.1, width=1.1, height=0.25, color=TEAL_C, fill_color=TEAL_D, fill_opacity=0.9).shift(UP * 0.2 + RIGHT * 1.6 + UP * (i * 0.3 - 0.3)) for i in range(3)])
        thylakoid_label = Text("Thylakoid Grana", font_size=18, color=TEAL_A).next_to(stack1, DOWN, buff=0.15)
        self.play(LaggedStart(Create(stack1), Create(stack2), run_time=0.8, lag_ratio=0.2), Write(thylakoid_label))

        # 4. Sunlight photons incoming
        sun_rays = Arrow(start=UP * 2.8 + LEFT * 3.5, end=stack1.get_top() + LEFT * 0.2, color=YELLOW, stroke_width=5)
        sun_label = Text("Photons (hv)", font_size=20, weight=BOLD, color=YELLOW).next_to(sun_rays.get_start(), DOWN, buff=0.1)
        self.play(GrowArrow(sun_rays), FadeIn(sun_label), run_time=0.6)

        # 5. Chemical Equation Callout (Safe above subtitles)
        eq = Text({eq_text}, font_size=24, weight=BOLD, color=GOLD).move_to(DOWN * 1.6)
        eq_box = SurroundingRectangle(eq, color=YELLOW_C, buff=0.15, corner_radius=0.1)
        self.play(Write(eq), Create(eq_box), run_time=0.8)
        self.wait(1.5)
"""

    def _script_binary_search(self, scene: VisualScene, class_name: str) -> str:
        """High-impact algorithmic visualization for Binary Search."""
        header_text = repr("Binary Search: Divide & Conquer O(log N)")
        return f"""from manim import *

class {class_name}(Scene):
    def construct(self):
        # 1. Header
        header = Text({header_text}, font_size=32, weight=BOLD, color=BLUE_B).to_edge(UP, buff=0.5)
        self.play(Write(header), run_time=0.6)

        # 2. Sorted Array Boxes
        values = [2, 5, 8, 12, 16, 23, 38, 56, 72]
        boxes = VGroup()
        for i, val in enumerate(values):
            sq = Square(side_length=0.8, color=BLUE_D, fill_color="#0f172a", fill_opacity=0.85)
            num = Text(str(val), font_size=20, color=WHITE).move_to(sq.get_center())
            idx = Text(str(i), font_size=14, color=GRAY_B).next_to(sq, UP, buff=0.1)
            boxes.add(VGroup(sq, num, idx))
        boxes.arrange(RIGHT, buff=0.1).shift(UP * 0.6)
        self.play(LaggedStart(*[FadeIn(b) for b in boxes], lag_ratio=0.1), run_time=0.8)

        # 3. Pointers: Low, Mid, High
        low_p = Arrow(start=DOWN * 0.6, end=UP * 0.1, color=GREEN, max_tip_length_to_length_ratio=0.3).next_to(boxes[0], DOWN, buff=0.1)
        low_txt = Text("Low", font_size=16, color=GREEN).next_to(low_p, DOWN, buff=0.05)
        high_p = Arrow(start=DOWN * 0.6, end=UP * 0.1, color=RED, max_tip_length_to_length_ratio=0.3).next_to(boxes[-1], DOWN, buff=0.1)
        high_txt = Text("High", font_size=16, color=RED).next_to(high_p, DOWN, buff=0.05)
        mid_p = Arrow(start=DOWN * 0.6, end=UP * 0.1, color=YELLOW, max_tip_length_to_length_ratio=0.3).next_to(boxes[4], DOWN, buff=0.1)
        mid_txt = Text("Mid=16", font_size=16, color=YELLOW).next_to(mid_p, DOWN, buff=0.05)

        self.play(
            GrowArrow(low_p), FadeIn(low_txt),
            GrowArrow(high_p), FadeIn(high_txt),
            GrowArrow(mid_p), FadeIn(mid_txt),
            run_time=0.8
        )

        # 4. Highlight target & halving space
        target_info = Text("Target = 38 > Mid (16) -> Discard Left Half", font_size=22, weight=BOLD, color=GOLD).move_to(DOWN * 1.5)
        discard_group = VGroup(*boxes[:5])
        self.play(Write(target_info), discard_group.animate.set_opacity(0.25), run_time=0.8)
        self.wait(1.5)
"""

    def _script_vector_diagram(self, scene: VisualScene, class_name: str) -> str:
        """Free-body vector breakdown diagram."""
        header_text = repr("Free-Body Force Vector Decomposition")
        return f"""from manim import *

class {class_name}(Scene):
    def construct(self):
        header = Text({header_text}, font_size=32, weight=BOLD, color=BLUE_B).to_edge(UP, buff=0.5)
        self.play(Write(header), run_time=0.6)

        # Center Mass
        box = Square(side_length=1.4, color=TEAL, fill_color="#134e4a", fill_opacity=0.85).shift(UP * 0.2)
        mass_txt = Text("m", font_size=28, weight=BOLD, color=WHITE).move_to(box.get_center())
        self.play(Create(box), Write(mass_txt), run_time=0.5)

        # Normal force UP
        fn = Arrow(start=box.get_top(), end=box.get_top() + UP * 1.4, color=CYAN, buff=0)
        fn_lbl = Text("F_N (Normal)", font_size=18, color=CYAN).next_to(fn, UP, buff=0.1)
        # Gravity DOWN
        fg = Arrow(start=box.get_bottom(), end=box.get_bottom() + DOWN * 1.4, color=RED_C, buff=0)
        fg_lbl = Text("F_g = m*g", font_size=18, color=RED_C).next_to(fg, DOWN, buff=0.1)
        # Applied force RIGHT
        fapp = Arrow(start=box.get_right(), end=box.get_right() + RIGHT * 2.0, color=YELLOW, buff=0)
        fapp_lbl = Text("F_net = m*a", font_size=20, weight=BOLD, color=YELLOW).next_to(fapp, RIGHT, buff=0.1)

        self.play(GrowArrow(fn), FadeIn(fn_lbl), GrowArrow(fg), FadeIn(fg_lbl), run_time=0.7)
        self.play(GrowArrow(fapp), FadeIn(fapp_lbl), run_time=0.7)

        equilibrium_txt = Text("Vertical: F_N = F_g | Horizontal: F_net = m * a", font_size=22, color=GOLD).move_to(DOWN * 1.6)
        self.play(Write(equilibrium_txt), run_time=0.7)
        self.wait(1.5)
"""

    def _script_cinematic_fallback(self, scene: VisualScene, class_name: str) -> str:
        """High-fidelity cinematic-style Manim fallback for cloud generative video scenes."""
        prompt_txt = repr(scene.visual_description[:65] if scene.visual_description else scene.narration[:65])
        goal_txt = repr(scene.educational_goal[:75] if scene.educational_goal else "Cinematic Educational Concept")
        return f"""from manim import *

class {class_name}(Scene):
    def construct(self):
        # 1. Subtle glowing backdrop circles
        bg_glow = Annulus(inner_radius=2.0, outer_radius=4.5, color=TEAL_E, fill_opacity=0.15).move_to(ORIGIN)
        bg_circle = Circle(radius=1.8, color=BLUE_E, fill_opacity=0.25).move_to(ORIGIN)
        self.play(FadeIn(bg_glow), FadeIn(bg_circle), run_time=0.6)

        # 2. Main Title & Concept
        badge = Text("CINEMATIC VISUALIZATION", font_size=18, weight=BOLD, color=TEAL_A).to_edge(UP, buff=0.8)
        concept = Text({goal_txt}, font_size=28, weight=BOLD, color=GOLD).next_to(badge, DOWN, buff=0.3)
        self.play(FadeIn(badge, shift=DOWN*0.1), Write(concept), run_time=0.7)

        # 3. Dynamic Animated Physical Representation
        desc_box = RoundedRectangle(corner_radius=0.2, width=8.5, height=1.8, color=BLUE_B, fill_color="#0f172a", fill_opacity=0.85).move_to(DOWN * 0.2)
        desc_text = Text({prompt_txt}, font_size=18, color=WHITE).move_to(desc_box.get_center())
        
        # Kinetic particle markers
        p1 = Dot(point=LEFT * 2.2 + UP * 0.2, radius=0.12, color=YELLOW)
        p2 = Dot(point=RIGHT * 2.2 + UP * 0.2, radius=0.12, color=CYAN)
        
        self.play(Create(desc_box), Write(desc_text), FadeIn(p1), FadeIn(p2), run_time=0.8)
        self.play(
            p1.animate.shift(RIGHT * 4.4),
            p2.animate.shift(LEFT * 4.4),
            run_time=1.6,
            rate_func=rate_functions.smooth
        )
        self.wait(1.2)
"""
