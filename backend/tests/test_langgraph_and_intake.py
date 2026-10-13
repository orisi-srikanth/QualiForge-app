"""
Unit and Integration Tests for Agent 1 Data Intake Schema and LangGraph Orchestration
"""
import pytest
from backend.app.agents.data_intake_agent import data_intake_agent
from backend.app.models.schemas import DataIntakeOutput
from backend.app.orchestrator.langgraph_orchestration import qualitymind_langgraph
from backend.app.orchestrator.engine import orchestrator

def test_data_intake_deterministic_unit_normalization():
    """Verify fast deterministic processing normalizes inches and microns to millimeters."""
    raw_samples = [
        {"sample_id": "P001", "measured_value": 1.9685, "unit": "in"},      # ~50.00 mm
        {"sample_id": "P002", "measured_value": 50030.0, "unit": "um"},     # 50.03 mm
        {"sample_id": "P003", "measured_value": 5.006, "unit": "cm"},       # 50.06 mm
        {"sample_id": "P004", "measured_value": 50.08, "unit": "mm"},       # 50.08 mm
    ]
    batch_meta = {
        "batch_id": "BATCH-UNIT-TEST",
        "part_number": "PS-2026-101",
        "machine": "CNC-04",
        "quantity": 500,
        "nominal_mm": 50.00,
        "tolerance_mm": 0.05
    }
    
    res = data_intake_agent.process_batch_and_measurements(batch_meta=batch_meta, raw_measurements=raw_samples)
    schema: DataIntakeOutput = res["intake_schema"]
    
    assert schema.batch_id == "BATCH-UNIT-TEST"
    assert len(schema.unit_conversions) == 3
    assert len(schema.measurements) == 4
    
    # Check converted values in mm
    p1 = next(m for m in schema.measurements if m["sample_id"] == "P001")
    assert abs(p1["measured_value"] - 50.00) < 0.01
    
    p2 = next(m for m in schema.measurements if m["sample_id"] == "P002")
    assert abs(p2["measured_value"] - 50.03) < 0.01

    p3 = next(m for m in schema.measurements if m["sample_id"] == "P003")
    assert abs(p3["measured_value"] - 50.06) < 0.01

def test_data_intake_missing_fields_gating():
    """Missing critical fields sets needs_info=True with explicit warnings."""
    incomplete_meta = {
        "batch_id": "BATCH-INCOMPLETE",
        # missing part_number, machine, quantity, tolerance_mm
        "nominal_mm": 50.00
    }
    res = data_intake_agent.process_batch_and_measurements(batch_meta=incomplete_meta)
    schema: DataIntakeOutput = res["intake_schema"]
    assert schema.needs_info is True
    assert len(schema.missing_fields) > 0
    assert any("CRITICAL INTAKE ERROR" in w for w in schema.warnings)

def test_langgraph_orchestration_state_graph_execution():
    """Verify LangGraph executes across nodes, records checkpointed trace, and reaches gate."""
    init_state = {
        "workflow_id": "WF-LG-TEST",
        "batch_id": "BATCH-0245",
        "batch_metadata": {
            "batch_id": "BATCH-0245",
            "part_number": "PS-2026-101",
            "machine": "CNC-04",
            "quantity": 500,
            "nominal_mm": 50.00,
            "tolerance_mm": 0.05
        }
    }
    
    result = qualitymind_langgraph.invoke(
        init_state,
        config={"configurable": {"thread_id": "WF-LG-TEST"}}
    )
    
    assert result["status"] == "DISPOSITION_READY"
    assert len(result["execution_trace"]) >= 5
    assert "batch_metadata" in result
    assert "dimensional_report" in result
    assert "spc_report" in result
    assert "rca_report" in result
    assert "capa_report" in result
    assert "critic_review" in result

def test_orchestrator_engine_langgraph_method():
    """Verify orchestrator.run_langgraph_pipeline executes cleanly."""
    res = orchestrator.run_langgraph_pipeline(
        batch_meta={
            "batch_id": "BATCH-0245",
            "part_number": "PS-2026-101",
            "machine": "CNC-04",
            "quantity": 500,
            "nominal_mm": 50.00,
            "tolerance_mm": 0.05
        }
    )
    assert res is not None
    assert res.get("status") in ["DISPOSITION_READY", "PAUSED_AWAITING_HUMAN_APPROVAL"]
