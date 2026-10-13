import urllib.request
import json

req = urllib.request.Request("http://localhost:8000/api/workflows/WF-C038A990/trace")
with urllib.request.urlopen(req) as resp:
    trace = json.loads(resp.read().decode())

print(f"Total steps: {len(trace)}")
for i, step in enumerate(trace):
    print(f"\n--- STEP {i+1}: {step.get('agent_name')} ---")
    print(f"Status: {step.get('status')}")
    print(f"Timestamp: {step.get('timestamp')}")
    print(f"Input summary: {step.get('input_summary')}")
    print(f"Tool calls: {step.get('tool_calls')}")
    print(f"Output summary: {step.get('output_summary')}")
    print(f"Certainty level: {step.get('certainty_level')}")
    print(f"Execution time: {step.get('duration_ms')} ms")

