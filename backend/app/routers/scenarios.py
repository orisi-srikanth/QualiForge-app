"""
Platform Telemetry & Evaluation Scenarios Endpoints
Runs mandated test scenarios (TC-01..TC-08) and provides version diagnostics.
"""
from fastapi import APIRouter
from backend.app.scenarios.test_scenarios import run_test_scenario, run_all_scenarios

router = APIRouter()

@router.get("/version", tags=["System"], summary="Retrieve system version and model metadata", description="Returns platform version, computer vision model version, and governance guarantees.")
def get_system_version():
    return {
        "system": "QualityMind: Agentic Manufacturing Quality Decision-Support Platform",
        "version": "2.0.0",
        "cv_model_version": "mvtec-two-stage-v1.0 (PatchCore ResNet18 + MobileNetV3-Small)",
        "environment": "production-ready",
        "decision_support_guarantee": "ISO 9001 / IATF 16949 Compliant (No Autonomous Physical Actuation)"
    }

@router.get("/scenarios/all", tags=["System"], summary="Execute all 8 evaluation test scenarios (TC-01..TC-08)", description="Executes the complete evaluation suite across conforming batches, tolerance trips, defect images, vibration anomalies, Nelson drift, vector RAG, and CAPA effectiveness.")
def get_all_scenarios():
    return run_all_scenarios()

@router.get("/scenarios/{scenario_id}", tags=["System"], summary="Execute individual evaluation scenario", description="Executes single scenario (e.g. TC-01 to TC-08) and returns structured verification report.")
def get_single_scenario(scenario_id: str = "TC-02"):
    return run_test_scenario(scenario_id)
