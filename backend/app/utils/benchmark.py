import time
from typing import Dict, Any

class BenchmarkTracker:
    def __init__(self):
        self.metrics: Dict[str, Any] = {}
        self._start_times: Dict[str, float] = {}

    def start_stage(self, stage_name: str):
        self._start_times[stage_name] = time.perf_counter()

    def end_stage(self, stage_name: str):
        if stage_name in self._start_times:
            elapsed = time.perf_counter() - self._start_times[stage_name]
            self.metrics[f"{stage_name}_time_sec"] = round(elapsed, 3)

    def get_results(self) -> Dict[str, Any]:
        return self.metrics
