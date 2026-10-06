import time
from contextlib import contextmanager

@contextmanager
def timer(label: str = "Operation"):
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        print(f"[{label}] Elapsed: {elapsed:.3f}s")
