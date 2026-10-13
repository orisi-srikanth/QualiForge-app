"""
Single-Command Launcher for Enterprise Quality Inspection System
Runs FastAPI on port 8000 (serving both API and compiled React White-Theme Frontend).
"""
import os
import sys
import uvicorn

if __name__ == "__main__":
    os.environ["PYTHONPATH"] = os.path.abspath(os.path.dirname(__file__))
    print("=" * 70)
    print("  QUALIFORGE INDUSTRIAL QUALITY INTELLIGENCE PLATFORM")
    print("  IATF 16949 / ISO 9001 Compliant Decision-Support System")
    print("  8 Specialized Agents: Intake | Vision | Spec | Telemetry | SPC | RCA | CAPA | Critic")
    print("=" * 70)
    print("  Serving Application at: http://localhost:8000")
    print("  Swagger API Docs at:     http://localhost:8000/docs")
    print("  Evaluation Suite:        http://localhost:8000/api/scenarios/all")
    print("=" * 70)
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=False)
