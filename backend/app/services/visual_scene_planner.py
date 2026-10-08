"""
Visual Scene Planner Service (Task 9B).
Produces visual-first educational video production plans using local Qwen2.5:3b via Ollama,
with graceful fallback to domain-tailored rule-based plans.
Determines narration, visual descriptions, engine requests, visual elements, animations,
and teacher presence for every scene.
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

from app.schemas.visual_scene import (
    VisualEngine,
    SceneType,
    TeacherPosition,
    VisualElement,
    AnimationInstruction,
    VisualScene,
    VisualVideoPlan,
)
from app.services.ollama_service import (
    OllamaService,
    OllamaError,
    ollama_service as default_ollama_service,
)

logger = logging.getLogger(__name__)

VISUAL_PLANNER_SYSTEM_PROMPT = """You are an expert educational video production director and instructional designer.
Your task is to convert an academic topic into a VISUAL-FIRST VIDEO PRODUCTION PLAN.

This is NOT merely a narration script. It is an engineering blueprint for rendering educational video scenes.

For EVERY scene, you MUST determine:
1. "narration": What the student hears (clear, concise spoken script for voice synthesis).
2. "visual_description": What the student sees on screen (spatial layout, graphics, equations, motion).
3. "visual_engine": The rendering engine:
   - "manim" : Equations, formulas, graphs, geometry, algorithmic diagrams, coordinate planes.
   - "cloud_video" : Photorealistic demonstrations, real-world physics metaphors, natural phenomena, cinematic visuals.
   - "avatar" : AI teacher direct address, lesson introduction, conceptual summary.
   - "mixed" : Composite scenes (Manim graphics with AI teacher presenting on the side).
4. "scene_type": One of:
   - "teacher_intro", "title", "explanation", "equation", "diagram", "graph", "process",
   - "timeline", "comparison", "algorithm", "physics_simulation", "chemistry_visual",
   - "biology_visual", "cinematic", "teacher_explanation", "teacher_summary", "transition".
5. "visual_elements": Array of key objects ({ "type": str, "label": str, "description": str, "properties": dict }).
6. "animations": Array of kinetic actions ({ "action": str, "target": str, "duration": float, "description": str }).
7. "teacher_enabled": true if the AI teacher avatar appears; false otherwise.
8. "teacher_position": "none", "left", "center", or "right".
9. "visual_prompt": For "cloud_video" scenes, provide a high-quality descriptive prompt for text-to-video generation.
10. "duration_seconds": 4.0 to 8.0 seconds per scene.

Guidelines:
- Produce 4 to 7 scenes (total duration ~25 to 45 seconds).
- Scene 1 should introduce the topic (e.g. teacher_intro with teacher at center or right, or title).
- Use "manim" for all equations, graphs, math notations, and computer science algorithms.
- Use "cloud_video" selectively for real-world conceptual metaphors and impressive cinematic shots.
- The final scene should summarize key takeaways (e.g. teacher_summary).
- Output MUST be valid JSON matching the exact schema below. Do not use Markdown code fences.

JSON Schema format:
{
  "topic": "Topic Name",
  "title": "Educational Title",
  "total_duration_seconds": 30.0,
  "learning_objectives": ["Objective 1", "Objective 2"],
  "scenes": [
    {
      "scene_id": "scene_1",
      "scene_type": "teacher_intro",
      "visual_engine": "avatar",
      "narration": "Welcome! Today we explore Newton's second law.",
      "visual_description": "Friendly teacher in navy blazer introducing the topic.",
      "visual_prompt": null,
      "duration_seconds": 5.0,
      "teacher_enabled": true,
      "teacher_position": "center",
      "visual_elements": [
        { "type": "avatar", "label": "Teacher", "description": "SmartCampus teacher avatar" }
      ],
      "animations": [
        { "action": "fade_in", "target": "Teacher", "duration": 1.0, "description": "Teacher appears center stage" }
      ],
      "educational_goal": "Engage learner and introduce concept"
    }
  ]
}
"""


class VisualScenePlanner(ABC):
    """Abstract base class for visual scene planners."""

    @abstractmethod
    def plan(
        self,
        topic: str,
        target_duration: float = 30.0,
        level: str = "intermediate",
    ) -> VisualVideoPlan:
        """Generate a visual-first educational video plan for the topic."""
        pass


class RuleBasedVisualScenePlanner(VisualScenePlanner):
    """
    Deterministic rule-based visual scene planner.
    Provides verified educational templates across physics, biology, CS, math, and networking,
    with automatic extrapolation for arbitrary subjects.
    """

    def plan(
        self,
        topic: str,
        target_duration: float = 30.0,
        level: str = "intermediate",
    ) -> VisualVideoPlan:
        clean_topic = topic.strip()
        lower_topic = clean_topic.lower()

        if "newton" in lower_topic:
            return self._plan_newton(clean_topic)
        elif "photosynthesis" in lower_topic:
            return self._plan_photosynthesis(clean_topic)
        elif "binary search" in lower_topic:
            return self._plan_binary_search(clean_topic)
        elif "gradient descent" in lower_topic:
            return self._plan_gradient_descent(clean_topic)
        elif "tcp" in lower_topic or "handshake" in lower_topic:
            return self._plan_tcp_handshake(clean_topic)
        else:
            return self._plan_generic(clean_topic, target_duration, level)

    def _plan_newton(self, topic: str) -> VisualVideoPlan:
        scenes = [
            VisualScene(
                scene_id="scene_1",
                scene_type=SceneType.TEACHER_INTRO,
                visual_engine=VisualEngine.AVATAR,
                narration="Welcome to Physics! Today we uncover Newton's Second Law of Motion, the foundation of classical mechanics.",
                visual_description="AI Teacher in navy blazer standing center stage welcoming the class.",
                duration_seconds=5.0,
                teacher_enabled=True,
                teacher_position=TeacherPosition.CENTER,
                visual_elements=[
                    VisualElement(type="avatar", label="Teacher", description="SmartCampus AI Teacher")
                ],
                animations=[
                    AnimationInstruction(action="fade_in", target="Teacher", duration=1.0, description="Teacher appears on screen")
                ],
                educational_goal="Hook interest and introduce the principle of force and motion."
            ),
            VisualScene(
                scene_id="scene_2",
                scene_type=SceneType.EQUATION,
                visual_engine=VisualEngine.MANIM,
                narration="At its heart is a simple yet powerful relationship: Net Force equals mass times acceleration, written as F equals m a.",
                visual_description="Prominent vector LaTeX equation F = ma written in brilliant cyan with labeled variable callouts.",
                duration_seconds=5.5,
                teacher_enabled=False,
                teacher_position=TeacherPosition.NONE,
                visual_elements=[
                    VisualElement(type="formula", label="FormulaFma", description="LaTeX F = m a", properties={"color": "CYAN"}),
                    VisualElement(type="text", label="Labels", description="Force (N), Mass (kg), Acceleration (m/s^2)")
                ],
                animations=[
                    AnimationInstruction(action="create", target="FormulaFma", duration=1.5, description="Formula writes onto screen"),
                    AnimationInstruction(action="indicate", target="FormulaFma", duration=1.0, description="Glow on acceleration symbol")
                ],
                educational_goal="Memorize and comprehend the algebraic formulation F = ma."
            ),
            VisualScene(
                scene_id="scene_3",
                scene_type=SceneType.PHYSICS_SIMULATION,
                visual_engine=VisualEngine.MANIM,
                narration="When a constant force pushes a block, it accelerates uniformly across the plane in the exact direction of the force vector.",
                visual_description="2D physics simulation of a mass block on a flat surface with dynamic force vector arrow accelerating rightward.",
                duration_seconds=5.5,
                teacher_enabled=False,
                teacher_position=TeacherPosition.NONE,
                visual_elements=[
                    VisualElement(type="shape", label="Block", description="Square mass m = 5 kg"),
                    VisualElement(type="arrow", label="ForceArrow", description="Vector arrow labeled F = 20 N", properties={"color": "YELLOW"})
                ],
                animations=[
                    AnimationInstruction(action="create", target="ForceArrow", duration=1.0, description="Arrow emerges from center of mass"),
                    AnimationInstruction(action="move", target="Block", duration=3.0, description="Block accelerates linearly across the frame")
                ],
                educational_goal="Visualize dynamic acceleration caused by unbalanced force."
            ),
            VisualScene(
                scene_id="scene_4",
                scene_type=SceneType.CINEMATIC,
                visual_engine=VisualEngine.CLOUD_VIDEO,
                narration="Imagine pushing a heavy cargo cart: the heavier the mass, the harder you must push to achieve the same speed.",
                visual_description="Cinematic real-world illustration of an industrial warehouse cart accelerating under heavy applied human force.",
                visual_prompt="A cinematic educational visualization of a heavy wheeled cart being pushed along a polished warehouse floor, realistic lighting, physical inertia, smooth camera tracking",
                duration_seconds=5.0,
                teacher_enabled=False,
                teacher_position=TeacherPosition.NONE,
                visual_elements=[
                    VisualElement(type="cinematic_scene", label="WarehouseCart", description="Real-world mass inertia demonstration")
                ],
                animations=[
                    AnimationInstruction(action="play", target="WarehouseCart", duration=5.0, description="Continuous realistic cinematic motion")
                ],
                educational_goal="Connect mathematical theory to real-world mass resistance."
            ),
            VisualScene(
                scene_id="scene_5",
                scene_type=SceneType.GRAPH,
                visual_engine=VisualEngine.MANIM,
                narration="Plotting acceleration versus force reveals a direct linear relationship: double the force, and you double the acceleration.",
                visual_description="Cartesian coordinate axes displaying linear plot a = F / m with slope 1/m and dynamic point tracking.",
                duration_seconds=5.0,
                teacher_enabled=False,
                teacher_position=TeacherPosition.NONE,
                visual_elements=[
                    VisualElement(type="axis", label="Axes", description="Y-axis acceleration (m/s^2), X-axis Force (N)"),
                    VisualElement(type="line", label="LinearPlot", description="Straight linear trajectory through origin", properties={"color": "GREEN"})
                ],
                animations=[
                    AnimationInstruction(action="create", target="Axes", duration=1.0, description="Axes draw onto grid"),
                    AnimationInstruction(action="create", target="LinearPlot", duration=2.5, description="Line sweeps upward linearly")
                ],
                educational_goal="Interpret the linear proportionality graph of force and acceleration."
            ),
            VisualScene(
                scene_id="scene_6",
                scene_type=SceneType.TEACHER_SUMMARY,
                visual_engine=VisualEngine.AVATAR,
                narration="To summarize: Force creates acceleration, mass resists it, and F equals m a explains it all. Great work today!",
                visual_description="AI Teacher positioned on the right reviewing the summary key takeaways with gesture.",
                duration_seconds=5.0,
                teacher_enabled=True,
                teacher_position=TeacherPosition.RIGHT,
                visual_elements=[
                    VisualElement(type="avatar", label="Teacher", description="SmartCampus AI Teacher")
                ],
                animations=[
                    AnimationInstruction(action="fade_in", target="Teacher", duration=1.0, description="Teacher re-enters on right")
                ],
                educational_goal="Consolidate core formula and law of motion."
            ),
        ]
        total_dur = sum(s.duration_seconds for s in scenes)
        return VisualVideoPlan(
            topic=topic,
            title="Newton's Second Law of Motion: Force, Mass, and Acceleration",
            total_duration_seconds=total_dur,
            scenes=scenes,
            learning_objectives=[
                "State and write Newton's Second Law: F = ma",
                "Understand that force is directly proportional to acceleration",
                "Recognize that mass inversely resists acceleration"
            ]
        )

    def _plan_photosynthesis(self, topic: str) -> VisualVideoPlan:
        scenes = [
            VisualScene(
                scene_id="scene_1",
                scene_type=SceneType.TEACHER_INTRO,
                visual_engine=VisualEngine.AVATAR,
                narration="Welcome to Plant Biology! Today we discover photosynthesis, the biochemical miracle that fuels life on Earth.",
                visual_description="AI Teacher introducing plant solar energy capture.",
                duration_seconds=5.0,
                teacher_enabled=True,
                teacher_position=TeacherPosition.CENTER,
                visual_elements=[VisualElement(type="avatar", label="Teacher", description="AI Teacher")],
                animations=[AnimationInstruction(action="fade_in", target="Teacher", duration=1.0)],
                educational_goal="Introduce the primary solar energy conversion process."
            ),
            VisualScene(
                scene_id="scene_2",
                scene_type=SceneType.EQUATION,
                visual_engine=VisualEngine.MANIM,
                narration="Plants transform six carbon dioxide molecules and six water molecules using light into glucose and life-giving oxygen.",
                visual_description="Chemical reaction equation 6CO2 + 6H2O + Light -> C6H12O6 + 6O2 in vibrant color-coded chemical symbols.",
                duration_seconds=6.0,
                teacher_enabled=False,
                teacher_position=TeacherPosition.NONE,
                visual_elements=[
                    VisualElement(type="formula", label="PhotosynthesisEq", description="6CO2 + 6H2O -> C6H12O6 + 6O2", properties={"color": "EMERALD"})
                ],
                animations=[
                    AnimationInstruction(action="create", target="PhotosynthesisEq", duration=2.0)
                ],
                educational_goal="Master the balanced chemical equation of photosynthesis."
            ),
            VisualScene(
                scene_id="scene_3",
                scene_type=SceneType.BIOLOGY_VISUAL,
                visual_engine=VisualEngine.MANIM,
                narration="Inside plant leaf cells, double-membraned chloroplasts house disc-shaped thylakoids where chlorophyll captures photons.",
                visual_description="Detailed cross-section diagram of a chloroplast displaying stroma, thylakoid stacks, and granum.",
                duration_seconds=6.0,
                teacher_enabled=False,
                teacher_position=TeacherPosition.NONE,
                visual_elements=[
                    VisualElement(type="diagram", label="ChloroplastDiagram", description="Organelle anatomy and thylakoid stacks")
                ],
                animations=[
                    AnimationInstruction(action="create", target="ChloroplastDiagram", duration=2.0)
                ],
                educational_goal="Identify chloroplast structure and the site of light reactions."
            ),
            VisualScene(
                scene_id="scene_4",
                scene_type=SceneType.CINEMATIC,
                visual_engine=VisualEngine.CLOUD_VIDEO,
                narration="Under bright sunlight, microscopic leaf stomata breathe in carbon dioxide while chlorophyll radiates lush emerald vitality.",
                visual_description="Photorealistic macro camera dive into a sunlit leaf surface showing shimmering sunlight and translucent cell walls.",
                visual_prompt="Cinematic macro shot of sunlit plant leaf, translucent cellular structure, radiant golden sunbeams, dew drops, photorealistic biology",
                duration_seconds=5.0,
                teacher_enabled=False,
                teacher_position=TeacherPosition.NONE,
                visual_elements=[
                    VisualElement(type="cinematic_scene", label="SunlitLeaf", description="Macro biological landscape")
                ],
                animations=[
                    AnimationInstruction(action="play", target="SunlitLeaf", duration=5.0)
                ],
                educational_goal="Connect microscopic chemical reactions to visible living foliage."
            ),
            VisualScene(
                scene_id="scene_5",
                scene_type=SceneType.TEACHER_SUMMARY,
                visual_engine=VisualEngine.AVATAR,
                narration="In summary: Sunlight, water, and air become sugar and oxygen. Without photosynthesis, complex ecosystems could not exist.",
                visual_description="AI Teacher presenting closing remarks on the right side of the screen.",
                duration_seconds=5.0,
                teacher_enabled=True,
                teacher_position=TeacherPosition.RIGHT,
                visual_elements=[VisualElement(type="avatar", label="Teacher", description="AI Teacher")],
                animations=[AnimationInstruction(action="fade_in", target="Teacher", duration=1.0)],
                educational_goal="Summarize inputs, outputs, and ecological significance."
            ),
        ]
        return VisualVideoPlan(
            topic=topic,
            title="Photosynthesis: How Plants Convert Sunlight into Chemical Energy",
            total_duration_seconds=sum(s.duration_seconds for s in scenes),
            scenes=scenes,
            learning_objectives=[
                "Write the chemical equation for photosynthesis",
                "Explain the role of chloroplasts and chlorophyll",
                "Distinguish inputs (CO2, H2O) from outputs (Glucose, O2)"
            ]
        )

    def _plan_binary_search(self, topic: str) -> VisualVideoPlan:
        scenes = [
            VisualScene(
                scene_id="scene_1",
                scene_type=SceneType.TEACHER_INTRO,
                visual_engine=VisualEngine.AVATAR,
                narration="Welcome to Algorithms! Today we explore Binary Search, the cornerstone of logarithmic divide-and-conquer efficiency.",
                visual_description="AI Teacher introducing algorithm complexity.",
                duration_seconds=5.0,
                teacher_enabled=True,
                teacher_position=TeacherPosition.CENTER,
                visual_elements=[VisualElement(type="avatar", label="Teacher", description="AI Teacher")],
                animations=[AnimationInstruction(action="fade_in", target="Teacher", duration=1.0)],
                educational_goal="Introduce binary search premise on sorted collections."
            ),
            VisualScene(
                scene_id="scene_2",
                scene_type=SceneType.ALGORITHM,
                visual_engine=VisualEngine.MANIM,
                narration="Binary search requires an already sorted array. We maintain three pointers: low, mid, and high to examine the middle element.",
                visual_description="Horizontal array of indexed boxes [2, 5, 8, 12, 16, 23, 38, 56, 72] with arrows pointing to low, mid, and high.",
                duration_seconds=6.0,
                teacher_enabled=False,
                teacher_position=TeacherPosition.NONE,
                visual_elements=[
                    VisualElement(type="shape", label="SortedArray", description="Array boxes with numbers"),
                    VisualElement(type="arrow", label="Pointers", description="Low, Mid, High pointer markers")
                ],
                animations=[
                    AnimationInstruction(action="create", target="SortedArray", duration=1.5),
                    AnimationInstruction(action="indicate", target="Pointers", duration=1.5)
                ],
                educational_goal="Identify initialization of low, high, and midpoint indices."
            ),
            VisualScene(
                scene_id="scene_3",
                scene_type=SceneType.PROCESS,
                visual_engine=VisualEngine.MANIM,
                narration="If the target is smaller than mid, we discard the right half entirely. With each comparison, the search space halves.",
                visual_description="Right half of array dims and fades out, and high pointer updates to mid minus one.",
                duration_seconds=6.0,
                teacher_enabled=False,
                teacher_position=TeacherPosition.NONE,
                visual_elements=[
                    VisualElement(type="shape", label="RemainingArray", description="Left half illuminated")
                ],
                animations=[
                    AnimationInstruction(action="transform", target="RemainingArray", duration=2.0)
                ],
                educational_goal="Understand elimination of sub-arrays via order comparison."
            ),
            VisualScene(
                scene_id="scene_4",
                scene_type=SceneType.DIAGRAM,
                visual_engine=VisualEngine.MANIM,
                narration="This logarithmic reduction achieves Big-O of log n time complexity: searching one million items takes only twenty checks!",
                visual_description="Decision tree bifurcation diagram illustrating O(log N) depth scaling against linear O(N) curve.",
                duration_seconds=5.5,
                teacher_enabled=False,
                teacher_position=TeacherPosition.NONE,
                visual_elements=[
                    VisualElement(type="diagram", label="ComplexityTree", description="Binary tree with O(log n) level labels")
                ],
                animations=[
                    AnimationInstruction(action="create", target="ComplexityTree", duration=2.0)
                ],
                educational_goal="Contrast logarithmic time complexity with linear search."
            ),
            VisualScene(
                scene_id="scene_5",
                scene_type=SceneType.TEACHER_SUMMARY,
                visual_engine=VisualEngine.AVATAR,
                narration="Remember: sorted data is required, divide by half each step, and achieve lightning-fast O of log n lookups.",
                visual_description="AI Teacher on right concluding binary search lecture.",
                duration_seconds=5.0,
                teacher_enabled=True,
                teacher_position=TeacherPosition.RIGHT,
                visual_elements=[VisualElement(type="avatar", label="Teacher", description="AI Teacher")],
                animations=[AnimationInstruction(action="fade_in", target="Teacher", duration=1.0)],
                educational_goal="Solidify prerequisites and algorithmic efficiency."
            ),
        ]
        return VisualVideoPlan(
            topic=topic,
            title="Binary Search Algorithm: Logarithmic Divide and Conquer",
            total_duration_seconds=sum(s.duration_seconds for s in scenes),
            scenes=scenes,
            learning_objectives=[
                "Understand the precondition: sorted array",
                "Track low, mid, and high pointer updates",
                "Explain why binary search runs in O(log n) time"
            ]
        )

    def _plan_gradient_descent(self, topic: str) -> VisualVideoPlan:
        scenes = [
            VisualScene(
                scene_id="scene_1",
                scene_type=SceneType.TEACHER_INTRO,
                visual_engine=VisualEngine.AVATAR,
                narration="Welcome to Machine Learning! Today we unravel Gradient Descent, the optimization engine driving modern artificial intelligence.",
                visual_description="AI Teacher welcoming viewers to mathematical optimization.",
                duration_seconds=5.0,
                teacher_enabled=True,
                teacher_position=TeacherPosition.CENTER,
                visual_elements=[VisualElement(type="avatar", label="Teacher", description="AI Teacher")],
                animations=[AnimationInstruction(action="fade_in", target="Teacher", duration=1.0)],
                educational_goal="Define the objective of loss minimization in machine learning."
            ),
            VisualScene(
                scene_id="scene_2",
                scene_type=SceneType.EQUATION,
                visual_engine=VisualEngine.MANIM,
                narration="Weights update by taking steps proportional to the negative gradient: w new equals w minus alpha times the derivative of loss.",
                visual_description="Vector update equation w := w - alpha * grad(L) with alpha marked as the learning rate.",
                duration_seconds=6.0,
                teacher_enabled=False,
                teacher_position=TeacherPosition.NONE,
                visual_elements=[
                    VisualElement(type="formula", label="UpdateRule", description="w := w - alpha * grad(L)", properties={"color": "GOLD"})
                ],
                animations=[
                    AnimationInstruction(action="create", target="UpdateRule", duration=1.5)
                ],
                educational_goal="Understand the mathematical weight update rule."
            ),
            VisualScene(
                scene_id="scene_3",
                scene_type=SceneType.GRAPH,
                visual_engine=VisualEngine.MANIM,
                narration="On a convex error bowl, the gradient points toward the steepest ascent. We step in the opposite direction toward the minimum.",
                visual_description="3D paraboloid loss surface with contour lines and sequential step vectors descending toward the global minimum.",
                duration_seconds=6.0,
                teacher_enabled=False,
                teacher_position=TeacherPosition.NONE,
                visual_elements=[
                    VisualElement(type="shape", label="LossSurface", description="Convex loss bowl with gradient arrows")
                ],
                animations=[
                    AnimationInstruction(action="create", target="LossSurface", duration=2.0)
                ],
                educational_goal="Visualize iterative descent down a loss manifold."
            ),
            VisualScene(
                scene_id="scene_4",
                scene_type=SceneType.CINEMATIC,
                visual_engine=VisualEngine.CLOUD_VIDEO,
                narration="Think of a fog-covered mountain valley: taking careful steps downward will reliably lead you to the lowest floor.",
                visual_description="Cinematic physical visual of a polished chrome sphere rolling smoothly along a curved valley toward the basin.",
                visual_prompt="Cinematic visualization of a chrome sphere rolling down a smooth contoured fog-covered mountain valley into the valley floor, photorealistic physics, soft morning light",
                duration_seconds=5.0,
                teacher_enabled=False,
                teacher_position=TeacherPosition.NONE,
                visual_elements=[
                    VisualElement(type="cinematic_scene", label="ValleyMetaphor", description="Ball rolling down mountain valley")
                ],
                animations=[
                    AnimationInstruction(action="play", target="ValleyMetaphor", duration=5.0)
                ],
                educational_goal="Anchor abstract gradient descent in physical gravitational intuition."
            ),
            VisualScene(
                scene_id="scene_5",
                scene_type=SceneType.TEACHER_SUMMARY,
                visual_engine=VisualEngine.AVATAR,
                narration="Calibrate your learning rate carefully: too large causes overshoot, too small causes sluggish learning. See you next time!",
                visual_description="AI Teacher summarizing hyperparameter tuning on right.",
                duration_seconds=5.0,
                teacher_enabled=True,
                teacher_position=TeacherPosition.RIGHT,
                visual_elements=[VisualElement(type="avatar", label="Teacher", description="AI Teacher")],
                animations=[AnimationInstruction(action="fade_in", target="Teacher", duration=1.0)],
                educational_goal="Highlight practical role of the learning rate parameter."
            ),
        ]
        return VisualVideoPlan(
            topic=topic,
            title="Gradient Descent Optimization: Navigating the Loss Landscape",
            total_duration_seconds=sum(s.duration_seconds for s in scenes),
            scenes=scenes,
            learning_objectives=[
                "Understand the weight update equation w := w - alpha * grad(L)",
                "Explain the role of gradient as steepest ascent",
                "Recognize impact of learning rate alpha on convergence"
            ]
        )

    def _plan_tcp_handshake(self, topic: str) -> VisualVideoPlan:
        scenes = [
            VisualScene(
                scene_id="scene_1",
                scene_type=SceneType.TEACHER_INTRO,
                visual_engine=VisualEngine.AVATAR,
                narration="Welcome to Computer Networking! Today we explore the TCP Three-Way Handshake, the bedrock of reliable internet connections.",
                visual_description="AI Teacher presenting network protocol basics.",
                duration_seconds=5.0,
                teacher_enabled=True,
                teacher_position=TeacherPosition.CENTER,
                visual_elements=[VisualElement(type="avatar", label="Teacher", description="AI Teacher")],
                animations=[AnimationInstruction(action="fade_in", target="Teacher", duration=1.0)],
                educational_goal="Introduce the necessity of connection establishment in TCP."
            ),
            VisualScene(
                scene_id="scene_2",
                scene_type=SceneType.PROCESS,
                visual_engine=VisualEngine.MANIM,
                narration="First, the client sends a SYN packet with a random sequence number to request a synchronized communication session.",
                visual_description="Two vertical timeline lifelines labeled Client and Server; a packet arrow moves right labeled SYN (seq = x).",
                duration_seconds=6.0,
                teacher_enabled=False,
                teacher_position=TeacherPosition.NONE,
                visual_elements=[
                    VisualElement(type="diagram", label="Lifelines", description="Client and Server timeline columns"),
                    VisualElement(type="arrow", label="SynPacket", description="Packet arrow SYN with seq=x", properties={"color": "CYAN"})
                ],
                animations=[
                    AnimationInstruction(action="create", target="Lifelines", duration=1.0),
                    AnimationInstruction(action="move", target="SynPacket", duration=2.5)
                ],
                educational_goal="Identify Step 1: Client SYN request."
            ),
            VisualScene(
                scene_id="scene_3",
                scene_type=SceneType.PROCESS,
                visual_engine=VisualEngine.MANIM,
                narration="Second, the server replies with SYN-ACK: it acknowledges the client's sequence number and sends its own sequence y.",
                visual_description="Reverse packet arrow moves from Server to Client labeled SYN-ACK (seq = y, ack = x + 1).",
                duration_seconds=6.0,
                teacher_enabled=False,
                teacher_position=TeacherPosition.NONE,
                visual_elements=[
                    VisualElement(type="arrow", label="SynAckPacket", description="Packet arrow SYN-ACK", properties={"color": "YELLOW"})
                ],
                animations=[
                    AnimationInstruction(action="move", target="SynAckPacket", duration=2.5)
                ],
                educational_goal="Identify Step 2: Server SYN-ACK confirmation."
            ),
            VisualScene(
                scene_id="scene_4",
                scene_type=SceneType.DIAGRAM,
                visual_engine=VisualEngine.MANIM,
                narration="Finally, the client returns an ACK packet. Both sides are now synchronized, and the TCP connection state is ESTABLISHED.",
                visual_description="Third packet arrow moves Client to Server labeled ACK (ack = y + 1); both status lights turn green: ESTABLISHED.",
                duration_seconds=5.5,
                teacher_enabled=False,
                teacher_position=TeacherPosition.NONE,
                visual_elements=[
                    VisualElement(type="arrow", label="AckPacket", description="Packet arrow ACK", properties={"color": "GREEN"}),
                    VisualElement(type="text", label="StateStatus", description="ESTABLISHED connection state")
                ],
                animations=[
                    AnimationInstruction(action="move", target="AckPacket", duration=2.0),
                    AnimationInstruction(action="indicate", target="StateStatus", duration=1.5)
                ],
                educational_goal="Identify Step 3: Client final ACK and state synchronization."
            ),
            VisualScene(
                scene_id="scene_5",
                scene_type=SceneType.TEACHER_SUMMARY,
                visual_engine=VisualEngine.AVATAR,
                narration="SYN, SYN-ACK, ACK. In just three quick packets, the internet ensures reliable, ordered data transmission for billions of users.",
                visual_description="AI Teacher on right delivering closing summary of handshake.",
                duration_seconds=5.0,
                teacher_enabled=True,
                teacher_position=TeacherPosition.RIGHT,
                visual_elements=[VisualElement(type="avatar", label="Teacher", description="AI Teacher")],
                animations=[AnimationInstruction(action="fade_in", target="Teacher", duration=1.0)],
                educational_goal="Recap the three-phase handshake sequence."
            ),
        ]
        return VisualVideoPlan(
            topic=topic,
            title="The TCP Three-Way Handshake: Reliable Connection Establishment",
            total_duration_seconds=sum(s.duration_seconds for s in scenes),
            scenes=scenes,
            learning_objectives=[
                "Define the purpose of the 3-way handshake in TCP",
                "Sequence SYN, SYN-ACK, and ACK transmissions",
                "Explain sequence and acknowledgment number increments"
            ]
        )

    def _plan_generic(self, topic: str, target_duration: float, level: str) -> VisualVideoPlan:
        scenes = [
            VisualScene(
                scene_id="scene_1",
                scene_type=SceneType.TEACHER_INTRO,
                visual_engine=VisualEngine.AVATAR,
                narration=f"Welcome! In this lesson we explore {topic}, examining core principles and practical mechanics.",
                visual_description=f"AI Teacher introducing the subject of {topic}.",
                duration_seconds=5.0,
                teacher_enabled=True,
                teacher_position=TeacherPosition.CENTER,
                visual_elements=[VisualElement(type="avatar", label="Teacher", description="AI Teacher")],
                animations=[AnimationInstruction(action="fade_in", target="Teacher", duration=1.0)],
                educational_goal=f"Engage students with {topic}."
            ),
            VisualScene(
                scene_id="scene_2",
                scene_type=SceneType.EXPLANATION,
                visual_engine=VisualEngine.MANIM,
                narration=f"Let us break down the fundamental conceptual definition and core components of {topic}.",
                visual_description=f"Structured visual diagram outlining foundational definitions of {topic}.",
                duration_seconds=6.0,
                teacher_enabled=False,
                teacher_position=TeacherPosition.NONE,
                visual_elements=[
                    VisualElement(type="diagram", label="ConceptMap", description=f"Foundational concepts of {topic}")
                ],
                animations=[AnimationInstruction(action="create", target="ConceptMap", duration=2.0)],
                educational_goal=f"Define the key terms of {topic}."
            ),
            VisualScene(
                scene_id="scene_3",
                scene_type=SceneType.DIAGRAM,
                visual_engine=VisualEngine.MANIM,
                narration=f"Analyzing the internal mechanics reveals how components interact sequentially to govern {topic}.",
                visual_description=f"Precise technical flowchart detailing the interactions within {topic}.",
                duration_seconds=6.0,
                teacher_enabled=False,
                teacher_position=TeacherPosition.NONE,
                visual_elements=[
                    VisualElement(type="shape", label="Flowchart", description=f"Mechanics of {topic}")
                ],
                animations=[AnimationInstruction(action="create", target="Flowchart", duration=2.0)],
                educational_goal=f"Understand the mechanism of {topic}."
            ),
            VisualScene(
                scene_id="scene_4",
                scene_type=SceneType.CINEMATIC,
                visual_engine=VisualEngine.CLOUD_VIDEO,
                narration=f"In the physical world, {topic} manifests through dynamic real-world phenomena and practical applications.",
                visual_description=f"Cinematic illustration showcasing real-world manifestation of {topic}.",
                visual_prompt=f"A cinematic educational visualization of {topic}, clean modern visual, smooth camera motion, realistic lighting, no text, no watermark",
                duration_seconds=5.0,
                teacher_enabled=False,
                teacher_position=TeacherPosition.NONE,
                visual_elements=[
                    VisualElement(type="cinematic_scene", label="RealWorld", description=f"Real world application of {topic}")
                ],
                animations=[AnimationInstruction(action="play", target="RealWorld", duration=5.0)],
                educational_goal=f"Relate {topic} to practical real-world instances."
            ),
            VisualScene(
                scene_id="scene_5",
                scene_type=SceneType.TEACHER_SUMMARY,
                visual_engine=VisualEngine.AVATAR,
                narration=f"To recap: {topic} combines clear structural principles with real-world impact. Great job following along today!",
                visual_description="AI Teacher delivering lecture wrap-up on the right side.",
                duration_seconds=5.0,
                teacher_enabled=True,
                teacher_position=TeacherPosition.RIGHT,
                visual_elements=[VisualElement(type="avatar", label="Teacher", description="AI Teacher")],
                animations=[AnimationInstruction(action="fade_in", target="Teacher", duration=1.0)],
                educational_goal=f"Review summary takeaways for {topic}."
            ),
        ]
        return VisualVideoPlan(
            topic=topic,
            title=f"Understanding {topic}",
            total_duration_seconds=sum(s.duration_seconds for s in scenes),
            scenes=scenes,
            learning_objectives=[
                f"Define the foundational principles of {topic}",
                f"Explain the internal mechanisms of {topic}",
                f"Identify practical applications of {topic}"
            ]
        )


class LLMVisualScenePlanner(VisualScenePlanner):
    """
    Visual Scene Planner powered by local Qwen2.5:3b via Ollama.
    Generates video production plans with automated fallback to RuleBasedVisualScenePlanner.
    """

    def __init__(self, ollama_service_instance: Optional[OllamaService] = None):
        self.ollama = ollama_service_instance or default_ollama_service
        self.fallback_planner = RuleBasedVisualScenePlanner()

    def plan(
        self,
        topic: str,
        target_duration: float = 30.0,
        level: str = "intermediate",
    ) -> VisualVideoPlan:
        """
        Generate a visual plan using Ollama / Qwen2.5 3B.
        Falls back to RuleBasedVisualScenePlanner if Ollama is unavailable or schema validation fails.
        """
        clean_topic = topic.strip()
        if not self.ollama.is_available(check_model=False):
            logger.warning("[VisualPlanner] Ollama service not reachable. Using RuleBasedVisualScenePlanner fallback.")
            return self.fallback_planner.plan(clean_topic, target_duration, level)

        prompt = (
            f"Topic: {clean_topic}\n"
            f"Target Duration: {target_duration} seconds\n"
            f"Difficulty Level: {level}\n\n"
            f"Generate a visual educational video production plan matching the requested JSON schema."
        )

        try:
            raw_response = self.ollama.generate(
                prompt=prompt,
                system_prompt=VISUAL_PLANNER_SYSTEM_PROMPT,
                format="json",
                temperature=0.2,
                timeout=45.0,
            )
            data = self._clean_and_parse_json(raw_response)
            plan = VisualVideoPlan.model_validate(data)
            logger.info("[VisualPlanner] Successfully generated visual plan for '%s' via Qwen.", clean_topic)
            return plan

        except Exception as e:
            logger.warning(
                "[VisualPlanner] LLM visual planning failed for topic '%s' (%s: %s). Falling back to rule-based planner.",
                clean_topic, type(e).__name__, e
            )
            return self.fallback_planner.plan(clean_topic, target_duration, level)

    def _clean_and_parse_json(self, raw_text: str) -> Dict[str, Any]:
        """Strip markdown fences and parse JSON payload."""
        text = raw_text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1:
            text = text[start_idx : end_idx + 1]
        return json.loads(text)


# Default singleton planner
visual_scene_planner = LLMVisualScenePlanner()
