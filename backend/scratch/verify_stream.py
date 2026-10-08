"""
Verification script for Server-Sent Events (SSE) generate-stream endpoint.
Connects to live backend and reads real-time per-stage progress snapshots.
"""

import sys
import json
import urllib.request

def verify_live_stream():
    url = "http://127.0.0.1:8000/api/video/generate-stream?topic=Binary+Search&quality=low_quality"
    print(f"Connecting to {url} ...")

    req = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
    
    with urllib.request.urlopen(req, timeout=45) as response:
        print(f"Connected! HTTP Status: {response.status}")
        print(f"Content-Type: {response.headers.get('Content-Type')}\n")
        
        event_count = 0
        for line in response:
            line_str = line.decode("utf-8").strip()
            if not line_str or line_str.startswith(":"):
                continue
            if line_str.startswith("data: "):
                event_count += 1
                payload = json.loads(line_str[6:])
                stage = payload.get("stage_name") or payload.get("stage")
                progress = payload.get("stage_progress", 0)
                overall = payload.get("overall_progress", 0)
                status = payload.get("status")
                msg = payload.get("message")
                
                print(f"[Event #{event_count}] Overall: {overall}% | Stage: '{stage}' ({progress}%, {status}) | Msg: {msg}")
                
                # Check 7 stages array presence
                stages = payload.get("stages", [])
                assert len(stages) == 7, f"Expected 7 stages, got {len(stages)}"
                
                # Stop after seeing stage 1 and stage 2 progress to keep verification fast
                if payload.get("type") == "complete" or event_count >= 5:
                    print("\nSuccessfully received and validated 5 real-time stage progress snapshots!")
                    break

if __name__ == "__main__":
    verify_live_stream()
