"""
Topic to Video Pipeline: High-level prompt/topic -> Script generation -> Video assembly
"""
from app.pipelines.script_to_video import ScriptToVideoPipeline

class TopicToVideoPipeline:
    def __init__(self):
        self.script_to_video = ScriptToVideoPipeline()

    async def generate_from_topic(self, topic: str, target_duration_sec: float = 30.0):
        # 1. Generate educational script from topic
        # 2. Decompose into visual prompts / scene specs
        # 3. Call script_to_video pipeline
        pass
