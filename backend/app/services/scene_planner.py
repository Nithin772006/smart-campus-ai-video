"""
Academic Scene Planner.
Converts arbitrary user academic questions into structured educational scene plans.
Designed with an abstract interface (AcademicPlanner) so it can easily be swapped
with an LLMAcademicPlanner in the future without changing the Manim rendering engine.
"""
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

from app.schemas.scene import (
    SceneType,
    AcademicDomain,
    ScenePlanItem,
    EducationalVideoPlan,
)


class AcademicPlanner(ABC):
    """
    Abstract interface for educational video planning.
    Decouples prompt understanding from visual rendering.
    """
    @abstractmethod
    def plan(self, question: str) -> EducationalVideoPlan:
        """Analyze question/topic and produce an EducationalVideoPlan."""
        pass


class RuleBasedAcademicPlanner(AcademicPlanner):
    """
    Heuristic and knowledge-driven academic planner.
    Parses natural language question variants across multiple domains
    and maps them to pedagogical scene sequences.
    """

    def __init__(self):
        self._knowledge_base = self._build_knowledge_base()

    def plan(self, question: str) -> EducationalVideoPlan:
        cleaned_topic = self._extract_core_topic(question)
        normalized_key = self._normalize_key(cleaned_topic)

        # Lookup in curated knowledge base
        for key, entry in self._knowledge_base.items():
            if key in normalized_key or normalized_key in key:
                return self._build_plan_from_entry(cleaned_topic, entry)

        # Fallback to general academic template if topic is novel
        return self._build_fallback_plan(cleaned_topic, question)

    def _extract_core_topic(self, text: str) -> str:
        """Strip conversational question prefixes/suffixes to extract topic."""
        s = text.strip()
        s = re.sub(r"[?!.,]+$", "", s).strip()

        prefixes = [
            r"^can you explain to me",
            r"^can you explain",
            r"^please explain",
            r"^teach me about",
            r"^teach me",
            r"^tell me about",
            r"^how does",
            r"^how do",
            r"^what is the structure of an",
            r"^what is the structure of a",
            r"^what is the structure of",
            r"^what is an",
            r"^what is a",
            r"^what is the",
            r"^what is",
            r"^what are",
            r"^explain the structure of an",
            r"^explain the structure of a",
            r"^explain the structure of",
            r"^explain the",
            r"^explain",
            r"^describe the",
            r"^describe",
            r"^define",
            r"^introduction to",
            r"^overview of",
        ]
        for p in prefixes:
            s = re.sub(p, "", s, flags=re.IGNORECASE).strip()

        suffixes = [
            r"works?$",
            r"work$",
            r"for beginners?$",
            r"for a beginner$",
            r"in plants?$",
            r"in simple terms$",
            r"step by step$",
        ]
        for suf in suffixes:
            s = re.sub(suf, "", s, flags=re.IGNORECASE).strip()

        # Capitalize nicely
        words = s.split()
        if words:
            return " ".join([w.capitalize() if len(w) > 3 or i == 0 else w for i, w in enumerate(words)])
        return text.strip()

    def _normalize_key(self, text: str) -> str:
        return re.sub(r"[^a-z0-9]", "", text.lower())

    def _build_plan_from_entry(self, user_topic: str, entry: Dict[str, Any]) -> EducationalVideoPlan:
        scenes: List[ScenePlanItem] = []
        for i, sc in enumerate(entry["scenes"], start=1):
            scenes.append(ScenePlanItem(id=i, **sc))

        total_dur = sum(s.duration for s in scenes)
        return EducationalVideoPlan(
            topic=entry.get("canonical_name", user_topic),
            title=entry.get("title", f"Understanding {user_topic}"),
            level=entry.get("level", "beginner"),
            domain=entry.get("domain", AcademicDomain.GENERAL),
            summary=entry.get("summary", ""),
            target_duration=total_dur,
            scenes=scenes,
        )

    def _build_fallback_plan(self, topic: str, original_question: str) -> EducationalVideoPlan:
        """
        Graceful fallback for arbitrary concepts:
        Title -> Core Definition -> Key Principles -> Practical Process -> Conclusion
        Ensures the system never crashes on novel topics.
        """
        domain = self._guess_domain(topic)
        title = f"Understanding {topic}"

        scenes = [
            ScenePlanItem(
                id=1,
                type=SceneType.TITLE,
                duration=4.0,
                title=topic,
                subtitle=f"An Introduction to {domain.value.replace('_', ' ').title()}",
            ),
            ScenePlanItem(
                id=2,
                type=SceneType.EXPLANATION,
                duration=6.0,
                title=f"What is {topic}?",
                content=f"{topic} is a fundamental concept in {domain.value.replace('_', ' ')} governing core systems and behavior.",
            ),
            ScenePlanItem(
                id=3,
                type=SceneType.BULLET_POINTS,
                duration=7.0,
                title="Key Principles",
                bullets=[
                    f"Core property and defining mechanism of {topic}",
                    "Systematic interaction with surrounding components",
                    "Practical importance and modern real-world application",
                ],
            ),
            ScenePlanItem(
                id=4,
                type=SceneType.PROCESS,
                duration=8.0,
                title="Operational Process",
                steps=[
                    "Phase 1: Initial state & input conditions",
                    f"Phase 2: Active operation of {topic}",
                    "Phase 3: Measurable outcome & equilibrium",
                ],
            ),
            ScenePlanItem(
                id=5,
                type=SceneType.CONCLUSION,
                duration=5.0,
                title="Key Takeaway",
                content=f"Mastering {topic} unlocks deeper insight into {domain.value.replace('_', ' ')} systems.",
            ),
        ]

        return EducationalVideoPlan(
            topic=topic,
            title=title,
            level="beginner",
            domain=domain,
            summary=f"Conceptual overview of {topic}.",
            target_duration=sum(s.duration for s in scenes),
            scenes=scenes,
        )

    def _guess_domain(self, text: str) -> AcademicDomain:
        t = text.lower()
        if any(k in t for k in ["algorithm", "sort", "search", "network", "tcp", "osi", "code", "tree", "graph", "neural", "cnn"]):
            return AcademicDomain.COMPUTER_SCIENCE
        if any(k in t for k in ["newton", "force", "gravity", "motion", "energy", "velocity", "wave", "quantum"]):
            return AcademicDomain.PHYSICS
        if any(k in t for k in ["bio", "cell", "plant", "photosynthesis", "dna", "gene", "mitosis", "organism"]):
            return AcademicDomain.BIOLOGY
        if any(k in t for k in ["chem", "atom", "molecule", "reaction", "acid", "element", "periodic"]):
            return AcademicDomain.CHEMISTRY
        if any(k in t for k in ["theorem", "equation", "bayes", "integral", "matrix", "vector", "probability"]):
            return AcademicDomain.MATHEMATICS
        if any(k in t for k in ["circuit", "signal", "motor", "engine", "gear", "robot"]):
            return AcademicDomain.ENGINEERING
        return AcademicDomain.GENERAL

    def _build_knowledge_base(self) -> Dict[str, Dict[str, Any]]:
        """Pre-structured pedagogical visual outlines for standard academic subjects."""
        return {
            # 1. PHYSICS: Newton's Second Law
            "newtonsecondlaw": {
                "canonical_name": "Newton's Second Law",
                "title": "Newton's Second Law of Motion",
                "level": "beginner",
                "domain": AcademicDomain.PHYSICS,
                "summary": "Force equals mass multiplied by acceleration.",
                "scenes": [
                    {
                        "type": SceneType.TITLE,
                        "duration": 4.0,
                        "title": "Newton's Second Law",
                        "subtitle": "Classical Mechanics & Dynamics",
                    },
                    {
                        "type": SceneType.EXPLANATION,
                        "duration": 6.0,
                        "title": "The Core Law",
                        "content": "Net force applied to an object causes it to accelerate proportionally in the direction of the force.",
                    },
                    {
                        "type": SceneType.FORMULA,
                        "duration": 7.0,
                        "title": "Mathematical Formula",
                        "formula": "F = m · a",
                        "formula_breakdown": [
                            "F : Net Force (Newtons, N)",
                            "m : Mass of the body (kg)",
                            "a : Acceleration produced (m/s²)",
                        ],
                    },
                    {
                        "type": SceneType.CONCEPT,
                        "duration": 6.0,
                        "title": "Key Relationship",
                        "content": "More force produces more acceleration; greater mass requires more force to accelerate.",
                    },
                    {
                        "type": SceneType.CONCLUSION,
                        "duration": 4.0,
                        "title": "Summary",
                        "content": "F = ma forms the foundation of modern mechanical engineering and spaceflight.",
                    },
                ],
            },

            # 2. BIOLOGY: Photosynthesis
            "photosynthesis": {
                "canonical_name": "Photosynthesis",
                "title": "How Photosynthesis Works",
                "level": "beginner",
                "domain": AcademicDomain.BIOLOGY,
                "summary": "Plants convert solar energy and carbon dioxide into glucose and oxygen.",
                "scenes": [
                    {
                        "type": SceneType.TITLE,
                        "duration": 4.0,
                        "title": "Photosynthesis",
                        "subtitle": "Biological Solar Energy Conversion",
                    },
                    {
                        "type": SceneType.EXPLANATION,
                        "duration": 6.0,
                        "title": "What is Photosynthesis?",
                        "content": "The biochemical process where chloroplasts capture solar radiation to synthesize food molecules.",
                    },
                    {
                        "type": SceneType.PROCESS,
                        "duration": 8.0,
                        "title": "Reaction Process",
                        "steps": [
                            "1. Sunlight absorption by chlorophyll in leaves",
                            "2. Water (H2O) uptake via plant root network",
                            "3. Carbon dioxide (CO2) absorption from atmosphere",
                            "4. Glucose synthesis & Oxygen (O2) release",
                        ],
                    },
                    {
                        "type": SceneType.FORMULA,
                        "duration": 7.0,
                        "title": "Chemical Equation",
                        "formula": "6CO₂ + 6H₂O + Light  →  C₆H₁₂O₆ + 6O₂",
                        "formula_breakdown": [
                            "CO₂ : Carbon Dioxide",
                            "H₂O : Water",
                            "C₆H₁₂O₆ : Glucose (Energy)",
                            "O₂ : Oxygen byproduct",
                        ],
                    },
                    {
                        "type": SceneType.CONCLUSION,
                        "duration": 4.0,
                        "title": "Global Significance",
                        "content": "Photosynthesis supplies Earth with breathable oxygen and forms the base of all terrestrial food chains.",
                    },
                ],
            },

            # 3. COMPUTER SCIENCE: Binary Search
            "binarysearch": {
                "canonical_name": "Binary Search",
                "title": "Binary Search Algorithm",
                "level": "intermediate",
                "domain": AcademicDomain.COMPUTER_SCIENCE,
                "summary": "Logarithmic search algorithm over sorted collections.",
                "scenes": [
                    {
                        "type": SceneType.TITLE,
                        "duration": 4.0,
                        "title": "Binary Search",
                        "subtitle": "Divide & Conquer Algorithm",
                    },
                    {
                        "type": SceneType.EXPLANATION,
                        "duration": 6.0,
                        "title": "Core Mechanism",
                        "content": "Searches a sorted array by repeatedly dividing the search interval in half instead of inspecting every item.",
                    },
                    {
                        "type": SceneType.PROCESS,
                        "duration": 8.0,
                        "title": "Algorithm Steps",
                        "steps": [
                            "1. Inspect middle element of current interval",
                            "2. If target matches middle, search completes",
                            "3. If target is smaller, eliminate right half",
                            "4. If target is larger, eliminate left half",
                        ],
                    },
                    {
                        "type": SceneType.FORMULA,
                        "duration": 6.0,
                        "title": "Complexity Analysis",
                        "formula": "Time Complexity: O(log n)",
                        "formula_breakdown": [
                            "Worst case : O(log₂ n) comparisons",
                            "Best case : O(1) when target is middle",
                            "Requirement : Array must be sorted",
                        ],
                    },
                    {
                        "type": SceneType.CONCLUSION,
                        "duration": 4.0,
                        "title": "Algorithm Efficiency",
                        "content": "Searches 1,000,000 items in roughly 20 comparisons vs 1,000,000 in linear search.",
                    },
                ],
            },

            # 4. COMPUTER SCIENCE / NETWORKING: OSI Model
            "osimodel": {
                "canonical_name": "OSI Model",
                "title": "The 7 Layers of the OSI Model",
                "level": "intermediate",
                "domain": AcademicDomain.COMPUTER_SCIENCE,
                "summary": "Conceptual framework standardizing computer networking protocols.",
                "scenes": [
                    {
                        "type": SceneType.TITLE,
                        "duration": 4.0,
                        "title": "The OSI Model",
                        "subtitle": "Open Systems Interconnection",
                    },
                    {
                        "type": SceneType.EXPLANATION,
                        "duration": 6.0,
                        "title": "Architectural Purpose",
                        "content": "A 7-tier reference model standardizing network communication protocols across global computing hardware.",
                    },
                    {
                        "type": SceneType.HIERARCHY,
                        "duration": 9.0,
                        "title": "The 7 Network Layers",
                        "layers": [
                            "7. Application Layer (HTTP, DNS, SSH)",
                            "6. Presentation Layer (Encryption, SSL)",
                            "5. Session Layer (Connections & Sync)",
                            "4. Transport Layer (TCP, UDP segments)",
                            "3. Network Layer (IP routing & packets)",
                            "2. Data Link Layer (Ethernet frames & MAC)",
                            "1. Physical Layer (Bits, Cables, Radio)",
                        ],
                    },
                    {
                        "type": SceneType.CONCLUSION,
                        "duration": 4.0,
                        "title": "Interoperability",
                        "content": "Allows completely different vendors and architectures to communicate seamlessly across the internet.",
                    },
                ],
            },

            # 5. CHEMISTRY / EARTH SCIENCE: Water Cycle
            "watercycle": {
                "canonical_name": "The Water Cycle",
                "title": "The Hydrologic Cycle",
                "level": "beginner",
                "domain": AcademicDomain.CHEMISTRY,
                "summary": "The continuous movement of water on, above, and below Earth.",
                "scenes": [
                    {
                        "type": SceneType.TITLE,
                        "duration": 4.0,
                        "title": "The Water Cycle",
                        "subtitle": "Global Hydrologic Circulation",
                    },
                    {
                        "type": SceneType.EXPLANATION,
                        "duration": 6.0,
                        "title": "Continuous Circulation",
                        "content": "Solar radiation drives the endless circulation of water between oceans, atmosphere, and terrestrial landforms.",
                    },
                    {
                        "type": SceneType.CYCLE,
                        "duration": 8.0,
                        "title": "Continuous Cycle",
                        "steps": [
                            "1. Evaporation (Liquid water turns to atmospheric vapor)",
                            "2. Condensation (Vapor cools forming dense clouds)",
                            "3. Precipitation (Water returns as rain, snow, or hail)",
                            "4. Collection (Runoff flows into rivers, lakes & oceans)",
                        ],
                    },
                    {
                        "type": SceneType.CONCLUSION,
                        "duration": 4.0,
                        "title": "Ecological Balance",
                        "content": "Replenishes global freshwater reserves and stabilizes continental climate zones.",
                    },
                ],
            },

            # 6. MATHEMATICS: Bayes Theorem
            "bayestheorem": {
                "canonical_name": "Bayes' Theorem",
                "title": "Bayes' Theorem in Probability",
                "level": "intermediate",
                "domain": AcademicDomain.MATHEMATICS,
                "summary": "Calculates conditional probability based on prior beliefs and new evidence.",
                "scenes": [
                    {
                        "type": SceneType.TITLE,
                        "duration": 4.0,
                        "title": "Bayes' Theorem",
                        "subtitle": "Conditional Probability & Inference",
                    },
                    {
                        "type": SceneType.EXPLANATION,
                        "duration": 6.0,
                        "title": "What is Bayes' Theorem?",
                        "content": "A rigorous mathematical method to update the probability of a hypothesis as new observations emerge.",
                    },
                    {
                        "type": SceneType.FORMULA,
                        "duration": 8.0,
                        "title": "Bayes' Formula",
                        "formula": "P(A|B) = [P(B|A) · P(A)] / P(B)",
                        "formula_breakdown": [
                            "P(A|B) : Posterior probability after evidence",
                            "P(B|A) : Likelihood of evidence given hypothesis",
                            "P(A)   : Prior belief before observing evidence",
                            "P(B)   : Marginal probability of the evidence",
                        ],
                    },
                    {
                        "type": SceneType.CONCLUSION,
                        "duration": 4.0,
                        "title": "Modern Applications",
                        "content": "Drives Bayesian neural networks, medical diagnostics, spam filtering, and statistical decision theory.",
                    },
                ],
            },

            # 7. COMPUTER SCIENCE: Recursion
            "recursion": {
                "canonical_name": "Recursion",
                "title": "Recursion in Computer Science",
                "level": "intermediate",
                "domain": AcademicDomain.COMPUTER_SCIENCE,
                "summary": "Method where a function solves a problem by calling copies of itself.",
                "scenes": [
                    {
                        "type": SceneType.TITLE,
                        "duration": 4.0,
                        "title": "Recursion",
                        "subtitle": "Self-Referential Problem Solving",
                    },
                    {
                        "type": SceneType.EXPLANATION,
                        "duration": 6.0,
                        "title": "Core Concept",
                        "content": "Decomposing a complex computational problem into smaller identical instances until reaching a trivial base case.",
                    },
                    {
                        "type": SceneType.BULLET_POINTS,
                        "duration": 7.0,
                        "title": "The Two Essential Parts",
                        "bullets": [
                            "Base Case : Halts recursion without making further self-calls",
                            "Recursive Case : Shrinks problem size and invokes itself",
                            "Call Stack : Tracks pending execution frames until base case returns",
                        ],
                    },
                    {
                        "type": SceneType.CONCLUSION,
                        "duration": 4.0,
                        "title": "Practical Uses",
                        "content": "Essential for graph algorithms, tree traversal (DOM, ASTs), and divide-and-conquer paradigms.",
                    },
                ],
            },

            # 8. COMPUTER SCIENCE: Backpropagation
            "backpropagation": {
                "canonical_name": "Backpropagation",
                "title": "Backpropagation in Neural Networks",
                "level": "advanced",
                "domain": AcademicDomain.COMPUTER_SCIENCE,
                "summary": "Gradient descent optimization via the calculus chain rule.",
                "scenes": [
                    {
                        "type": SceneType.TITLE,
                        "duration": 4.0,
                        "title": "Backpropagation",
                        "subtitle": "Training Artificial Neural Networks",
                    },
                    {
                        "type": SceneType.EXPLANATION,
                        "duration": 6.0,
                        "title": "Algorithm Role",
                        "content": "Calculates the gradient of the loss function with respect to every weight in a deep neural network.",
                    },
                    {
                        "type": SceneType.PROCESS,
                        "duration": 8.0,
                        "title": "Training Cycle",
                        "steps": [
                            "1. Forward Pass : Compute network predictions and loss error",
                            "2. Backward Pass : Apply calculus chain rule across hidden layers",
                            "3. Weight Update : Adjust weights in direction opposing gradients",
                        ],
                    },
                    {
                        "type": SceneType.FORMULA,
                        "duration": 6.0,
                        "title": "Weight Update Rule",
                        "formula": "W = W - η · (∂Loss / ∂W)",
                        "formula_breakdown": [
                            "W : Weight parameter tensor",
                            "η : Learning rate step hyperparameter",
                            "∂Loss/∂W : Partial derivative computed via Chain Rule",
                        ],
                    },
                    {
                        "type": SceneType.CONCLUSION,
                        "duration": 4.0,
                        "title": "Deep Learning Engine",
                        "content": "Backpropagation powers modern LLMs, autonomous vehicles, and computer vision models.",
                    },
                ],
            },

            # 9. CHEMISTRY / PHYSICS: Structure of an Atom
            "structureofanatom": {
                "canonical_name": "Structure of an Atom",
                "title": "The Structure of an Atom",
                "level": "beginner",
                "domain": AcademicDomain.CHEMISTRY,
                "summary": "Subatomic constituents: Protons, Neutrons, and Electrons.",
                "scenes": [
                    {
                        "type": SceneType.TITLE,
                        "duration": 4.0,
                        "title": "Structure of an Atom",
                        "subtitle": "Basic Building Blocks of Matter",
                    },
                    {
                        "type": SceneType.EXPLANATION,
                        "duration": 6.0,
                        "title": "What is an Atom?",
                        "content": "The fundamental unit of ordinary matter consisting of a dense central nucleus encircled by electron orbitals.",
                    },
                    {
                        "type": SceneType.BULLET_POINTS,
                        "duration": 7.0,
                        "title": "Subatomic Particles",
                        "bullets": [
                            "Protons (+) : Positively charged particles in nucleus",
                            "Neutrons (0) : Neutral particles providing nuclear stability",
                            "Electrons (-) : Negatively charged particles in quantized orbitals",
                        ],
                    },
                    {
                        "type": SceneType.CONCLUSION,
                        "duration": 4.0,
                        "title": "Atomic Identity",
                        "content": "The number of protons (atomic number) uniquely defines the chemical element and its periodic properties.",
                    },
                ],
            },

            # 10. NETWORKING: TCP/IP
            "tcpip": {
                "canonical_name": "TCP/IP Protocol Suite",
                "title": "The TCP/IP Network Model",
                "level": "intermediate",
                "domain": AcademicDomain.COMPUTER_SCIENCE,
                "summary": "The standard communication architecture powering the internet.",
                "scenes": [
                    {
                        "type": SceneType.TITLE,
                        "duration": 4.0,
                        "title": "TCP/IP Architecture",
                        "subtitle": "Internet Protocol Suite",
                    },
                    {
                        "type": SceneType.EXPLANATION,
                        "duration": 6.0,
                        "title": "What is TCP/IP?",
                        "content": "A four-layer protocol stack standardizing packet routing, delivery, and verification across the global web.",
                    },
                    {
                        "type": SceneType.HIERARCHY,
                        "duration": 8.0,
                        "title": "The 4 Architecture Tiers",
                        "layers": [
                            "4. Application Tier (HTTP, DNS, SMTP, SSH)",
                            "3. Transport Tier (TCP reliable stream / UDP datagrams)",
                            "2. Internet Tier (IP routing & packet addressing)",
                            "1. Network Interface (Ethernet, Wi-Fi hardware)",
                        ],
                    },
                    {
                        "type": SceneType.CONCLUSION,
                        "duration": 4.0,
                        "title": "Global Impact",
                        "content": "Enables billions of diverse computing devices to interoperate globally.",
                    },
                ],
            },

            # 11. NETWORKING: OSI Model (Task 9F Visual Progression)
            "osimodel": {
                "canonical_name": "OSI Model",
                "title": "The 7 Layers of the OSI Model",
                "level": "intermediate",
                "domain": AcademicDomain.COMPUTER_SCIENCE,
                "summary": "Seven-layer reference model for open systems interconnection.",
                "scenes": [
                    {
                        "type": SceneType.TITLE,
                        "duration": 4.0,
                        "title": "The OSI Model",
                        "subtitle": "7-Layer Network Architecture",
                    },
                    {
                        "type": SceneType.HIERARCHY,
                        "duration": 7.0,
                        "title": "The 7 Network Layers",
                        "layers": [
                            "Layer 7: Application",
                            "Layer 6: Presentation",
                            "Layer 5: Session",
                            "Layer 4: Transport",
                            "Layer 3: Network",
                            "Layer 2: Data Link",
                            "Layer 1: Physical",
                        ],
                    },
                    {
                        "type": SceneType.PROCESS,
                        "duration": 6.5,
                        "title": "Physical & Data Link",
                        "steps": [
                            "Physical (L1): Raw electrical bits over cable & radio",
                            "Data Link (L2): MAC frames & switches on local LAN",
                        ],
                    },
                    {
                        "type": SceneType.PROCESS,
                        "duration": 7.0,
                        "title": "Network & Transport",
                        "steps": [
                            "Network (L3): IP packets routed across internet",
                            "Transport (L4): TCP port segments & error-free delivery",
                        ],
                    },
                    {
                        "type": SceneType.BULLET_POINTS,
                        "duration": 6.5,
                        "title": "Upper Session & Application",
                        "bullets": [
                            "Session (L5): Dialog checkpoints and connection state",
                            "Presentation (L6): Data encryption (TLS) and formatting",
                            "Application (L7): User protocols (HTTP, DNS, SSH)",
                        ],
                    },
                    {
                        "type": SceneType.CONCLUSION,
                        "duration": 4.5,
                        "title": "Encapsulation Complete",
                        "content": "From raw physical signals to web applications, modular layers power the global internet.",
                    },
                ],
            },
        }
