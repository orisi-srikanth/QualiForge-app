"""
Unit Tests for Phase 3: Deterministic Analytical Engines
Tests Specification Engine, SPC Engine, Capability Guardrails, Pareto, and Effectiveness.
"""
import pytest
from backend.app.services.spec_engine import spec_engine
from backend.app.services.spc_engine import spc_engine
from backend.app.services.capability import capability_engine
from backend.app.services.effectiveness import effectiveness_engine
from backend.app.core.guardrails import EpistemicLabel

def test_spec_engine_boundary_safety():
    # Boundary test: nominal 50.00, tolerance +/- 0.05 -> USL=50.05, LSL=49.95
    measurements = [
        {"sample_id": "T01", "measured_value": 50.05},    # Exactly at USL -> MUST be conforming
        {"sample_id": "T02", "measured_value": 49.95},    # Exactly at LSL -> MUST be conforming
        {"sample_id": "T03", "measured_value": 50.0501},  # Just over USL -> Nonconforming
        {"sample_id": "T04", "measured_value": 49.9499},  # Just under LSL -> Nonconforming
        {"sample_id": "T05", "measured_value": 50.00},    # At nominal -> Conforming
    ]
    res = spec_engine.evaluate_compliance(
        batch_id="TEST-BOUNDARY",
        nominal_mm=50.00,
        tol_plus=0.05,
        tol_minus=0.05,
        measurements=measurements
    )
    assert res["usl"] == 50.05
    assert res["lsl"] == 49.95
    assert res["accepted"] == 3, "T01, T02, and T05 must be conforming"
    assert res["nonconforming"] == 2, "T03 and T04 must be nonconforming"
    assert res["label"] == EpistemicLabel.OBSERVED_FACT.value

def test_spec_engine_anchor_sample():
    # Anchor sample from BATCH-0245
    anchor_measurements = [
        {"sample_id": "P001", "measured_value": 50.01},
        {"sample_id": "P002", "measured_value": 50.03},
        {"sample_id": "P003", "measured_value": 50.06},
        {"sample_id": "P004", "measured_value": 50.08},
        {"sample_id": "P005", "measured_value": 50.07},
    ]
    res = spec_engine.evaluate_compliance(
        batch_id="BATCH-0245",
        nominal_mm=50.00,
        tol_plus=0.05,
        tol_minus=0.05,
        measurements=anchor_measurements
    )
    assert res["accepted"] == 2
    assert res["nonconforming"] == 3
    assert res["rejection_rate_percent"] == 60.0
    assert abs(res["max_deviation_from_limit"] - 0.03) < 1e-4

def test_spc_engine_limit_separation():
    """HARD REQUIREMENT: Control limits (UCL/LCL) and Spec limits (USL/LSL) must never be conflated."""
    data = [50.01, 50.02, 50.01, 50.03, 50.02, 50.01, 50.02, 50.03, 50.02, 50.01]
    res = spc_engine.evaluate_spc(data, usl=50.05, lsl=49.95)

    ucl = res["ucl"]
    lcl = res["lcl"]
    cl = res["center_line"]
    usl = res["limit_separation_info"]["specification_limits"]["usl"]
    lsl = res["limit_separation_info"]["specification_limits"]["lsl"]

    # Statistical limits are data-derived; Spec limits are engineering blueprint constraints
    assert ucl != usl, "UCL and USL must not be conflated"
    assert lcl != lsl, "LCL and LSL must not be conflated"
    assert "CRITICAL INDUSTRIAL DISTINCTION" in res["limit_separation_info"]["legend_notice"]

def test_spc_engine_nelson_rules():
    # Drift test: 6 consecutive increasing readings
    drift_data = [50.00, 50.01, 50.02, 50.03, 50.04, 50.05, 50.06]
    res = spc_engine.evaluate_spc(drift_data)
    rule_numbers = [v["rule_number"] for v in res["nelson_violations"]]
    assert 3 in rule_numbers, "Nelson Rule 3 (Process drift) must be detected"

def test_capability_guardrails_sample_size():
    # Subgroup n < 5 MUST be refused with INSUFFICIENT_DATA
    tiny_sample = [50.01, 50.02, 50.03]
    res_tiny = capability_engine.calculate_capability(tiny_sample, usl=50.05, lsl=49.95)
    assert res_tiny["status"] == "INSUFFICIENT_DATA"
    assert res_tiny["cpk"] is None
    assert any("too small" in w.lower() for w in res_tiny["warnings"])

    # Anchor 5-point sample (5 <= n < 30) must issue warning banner
    anchor_sample = [50.01, 50.03, 50.06, 50.08, 50.07]
    res_anchor = capability_engine.calculate_capability(anchor_sample, usl=50.05, lsl=49.95)
    assert res_anchor["status"] == "COMPUTED"
    assert any("less than the recommended" in w for w in res_anchor["warnings"])

def test_effectiveness_engine_statistical_test():
    # Pre-action 41/500 (8.2%) vs Post-action 6/500 (1.2%)
    res = effectiveness_engine.evaluate_capa_effectiveness(
        capa_id="CAPA-2026-001",
        n_before=500,
        defects_before=41,
        n_after=500,
        defects_after=6
    )
    assert res["rejection_rate_before_percent"] == 8.2
    assert res["rejection_rate_after_percent"] == 1.2
    assert res["is_statistically_significant"] is True
    assert res["p_value"] < 0.01
    assert "Observed association" in res["conclusion_label"]
    assert "causation not established" in res["conclusion_label"]
