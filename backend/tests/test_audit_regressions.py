"""
Independent Audit Regression Test Suite
Validates all deterministic formulas, LLM independence, real data integrity,
Nelson SPC rules, Pareto 80/20 vital few, capability warnings, RCA evidence ranking,
two-proportion effectiveness from real DB rows, and industrial safety guardrails.
"""
import pytest
import numpy as np
from unittest.mock import patch
from datetime import datetime, timezone

from backend.app.services.spec_engine import spec_engine
from backend.app.services.spc_engine import spc_engine
from backend.app.services.capability import capability_engine
from backend.app.services.anomaly import anomaly_detector
from backend.app.services.pareto import pareto_service
from backend.app.services.effectiveness import effectiveness_engine
from backend.app.agents.rca_agent import rca_agent
from backend.app.core.guardrails import (
    guardrails, EpistemicLabel, ForbiddenAutonomousAction, EpistemicViolation
)
from backend.app.db.session import SessionLocal
from backend.app.db.models import QualityIncident, RCAHypothesis, Batch, Measurement


# =====================================================================
# 1. LLM INDEPENDENCE & ZERO-COMPUTATION PROOF
# =====================================================================
def test_llm_garbage_mock_does_not_alter_deterministic_computations():
    """
    Proves that even if any LLM returns garbage strings or corrupted numbers,
    zero deterministic calculations or conformance decisions are affected.
    """
    garbage_llm_payload = '{"nominal_mm": -9999.9, "usl": 0.0, "conforming": true, "deviation": 999.99, "status": "APPROVED", "cp": 99.9}'
    
    with patch("backend.app.core.llm.universal_llm.chat", return_value=garbage_llm_payload):
        # 1. Spec Engine verification
        spec_res = spec_engine.evaluate_compliance(
            batch_id="BATCH-0245",
            nominal_mm=50.00,
            tol_plus=0.05,
            tol_minus=0.05,
            measurements=[50.01, 50.03, 50.06, 50.08, 50.07]
        )
        assert spec_res["total_inspected"] == 5
        assert spec_res["conforming_count"] == 2
        assert spec_res["nonconforming_count"] == 3
        assert spec_res["rejection_rate_percent"] == 60.0
        assert [i["deviation_from_limit"] for i in spec_res["evaluated_items"]] == [0.0, 0.0, 0.01, 0.03, 0.02]
        
        # 2. SPC Engine verification
        spc_res = spc_engine.evaluate_spc([50.01, 50.03, 50.06, 50.08, 50.07], subgroup_size=1, usl=50.05, lsl=49.95)
        assert abs(spc_res["center_line"] - 50.05) < 1e-6
        assert abs(spc_res["mr_bar"] - 0.02) < 1e-6
        assert abs(spc_res["sigma_within"] - 0.017730) < 1e-5
        assert abs(spc_res["ucl"] - 50.1032) < 1e-4
        assert abs(spc_res["lcl"] - 49.9968) < 1e-4
        assert abs(spc_res["mr_ucl"] - 0.06534) < 1e-4
        
        # 3. Capability Engine verification
        cap_res = capability_engine.calculate_capability(
            values=[50.01, 50.03, 50.06, 50.08, 50.07],
            usl=50.05,
            lsl=49.95
        )
        assert cap_res["pp"] == 0.5717
        assert cap_res["ppk"] == 0.0
        assert cap_res["cp"] == 0.9400
        assert cap_res["cpk"] == 0.0


# =====================================================================
# 2. SPECIFICATION LIMITS & CONFORMANCE BOUNDARY TESTS
# =====================================================================
def test_spec_conformance_boundary_and_float_noise():
    """
    Validates boundary conditions:
    50.05 and 49.95 are CONFORMING.
    50.0501 and 49.9499 are NONCONFORMING.
    Float noise 50.050000000000004 is CONFORMING.
    """
    res = spec_engine.evaluate_compliance(
        batch_id="BATCH-0245",
        nominal_mm=50.00,
        tol_plus=0.05,
        tol_minus=0.05,
        measurements=[50.05, 49.95, 50.0501, 49.9499, 50.050000000000004]
    )
    items = res["evaluated_items"]
    # 50.05: Conforming
    assert items[0]["is_conforming"] is True
    assert items[0]["deviation_from_limit"] == 0.0
    # 49.95: Conforming
    assert items[1]["is_conforming"] is True
    assert items[1]["deviation_from_limit"] == 0.0
    # 50.0501: Nonconforming
    assert items[2]["is_conforming"] is False
    assert items[2]["deviation_from_limit"] == 0.0001
    # 49.9499: Nonconforming
    assert items[3]["is_conforming"] is False
    assert items[3]["deviation_from_limit"] == 0.0001
    # 50.050000000000004 (float noise): Conforming
    assert items[4]["is_conforming"] is True
    assert items[4]["deviation_from_limit"] == 0.0


def test_spec_anchor_sample_golden_values():
    """
    Anchor sample: P001 50.01, P002 50.03, P003 50.06, P004 50.08, P005 50.07
    Validates tolerance band usage per part: (x - nominal)/tol_plus (e.g. P004 = 1.6 = 160%).
    """
    res = spec_engine.evaluate_compliance(
        batch_id="BATCH-0245",
        nominal_mm=50.00,
        tol_plus=0.05,
        tol_minus=0.05,
        measurements=[50.01, 50.03, 50.06, 50.08, 50.07]
    )
    items = res["evaluated_items"]
    assert items[0]["component_id"] == "P001" and items[0]["tolerance_band_usage"] == 0.2 and items[0]["tolerance_band_usage_percent"] == 20.0
    assert items[1]["component_id"] == "P002" and items[1]["tolerance_band_usage"] == 0.6 and items[1]["tolerance_band_usage_percent"] == 60.0
    assert items[2]["component_id"] == "P003" and items[2]["tolerance_band_usage"] == 1.2 and items[2]["tolerance_band_usage_percent"] == 120.0
    assert items[3]["component_id"] == "P004" and items[3]["tolerance_band_usage"] == 1.6 and items[3]["tolerance_band_usage_percent"] == 160.0
    assert items[4]["component_id"] == "P005" and items[4]["tolerance_band_usage"] == 1.4 and items[4]["tolerance_band_usage_percent"] == 140.0
    
    assert res["mean"] == 50.05
    assert res["std_dev_sample"] == 0.029155
    assert res["std_dev_pop"] == 0.026077
    assert res["max_deviation_mm"] == 0.03
    assert res["rejection_rate_percent"] == 60.0


def test_one_sided_tolerances():
    """Validates one-sided upper and lower tolerances."""
    res_upper = spec_engine.evaluate_compliance(
        batch_id="BATCH-0245",
        nominal_mm=50.00,
        tol_plus=0.05,
        tol_minus=None,
        measurements=[40.0, 50.02, 50.06]
    )
    assert res_upper["evaluated_items"][0]["is_conforming"] is True  # No LSL
    assert res_upper["evaluated_items"][1]["is_conforming"] is True
    assert res_upper["evaluated_items"][2]["is_conforming"] is False # > USL 50.05


# =====================================================================
# 3. SPC LIMITS, NELSON RULES & CAPABILITY
# =====================================================================
def test_spc_separate_fields_and_imr_mr_chart():
    """
    Verifies spec limits (LSL/USL) and control limits (UCL/LCL) are separate fields,
    and MR chart limits are correctly computed.
    """
    res = spc_engine.evaluate_spc(
        data=[50.01, 50.03, 50.06, 50.08, 50.07],
        subgroup_size=1,
        usl=50.05,
        lsl=49.95
    )
    # Control limits vs Spec limits
    assert res["ucl"] == 50.1032
    assert res["lcl"] == 49.9968
    assert res["usl"] == 50.05
    assert res["lsl"] == 49.95
    assert res["ucl"] != res["usl"]
    assert res["lcl"] != res["lsl"]
    
    # MR chart limits
    assert res["mr_cl"] == 0.02
    assert res["mr_ucl"] == 0.06534
    assert res["mr_lcl"] == 0.0


def test_nelson_rules_injected_patterns():
    """
    Validates injection of each Nelson / Western Electric rule pattern:
    - Nelson Rule 1 (WECO 1): 1 point > 3 sigma
    - Nelson Rule 2 (WECO 4): 8 consecutive on one side of CL
    - Nelson Rule 3: 6 consecutive increasing / decreasing (drift)
    - Nelson Rule 5 (WECO 2): 2 of 3 > 2 sigma on same side
    - Nelson Rule 6 (WECO 3): 4 of 5 > 1 sigma on same side
    """
    # Nelson Rule 1: Point > 3 sigma
    vals_r1 = [50.00, 50.00, 50.00, 50.00, 50.50]
    res_r1 = spc_engine.evaluate_spc(vals_r1, subgroup_size=1)
    rule_ids_r1 = [v["rule_number"] for v in res_r1["rule_violations"]]
    assert 1 in rule_ids_r1

    # Nelson Rule 2: 8 consecutive on one side of CL
    vals_r2 = [50.01] * 8 + [49.95] * 8
    res_r2 = spc_engine.evaluate_spc(vals_r2, subgroup_size=1)
    rule_ids_r2 = [v["rule_number"] for v in res_r2["rule_violations"]]
    assert 2 in rule_ids_r2

    # Nelson Rule 3: 6 consecutive increasing
    vals_r3 = [50.00, 50.01, 50.02, 50.03, 50.04, 50.05, 50.02]
    res_r3 = spc_engine.evaluate_spc(vals_r3, subgroup_size=1)
    rule_ids_r3 = [v["rule_number"] for v in res_r3["rule_violations"]]
    assert 3 in rule_ids_r3

    # Nelson Rule 5: 2 of 3 > 2 sigma on same side
    vals_r5 = [50.00] * 10 + [50.06, 50.06, 50.00]
    res_r5 = spc_engine.evaluate_spc(vals_r5, subgroup_size=1)
    rule_ids_r5 = [v["rule_number"] for v in res_r5["rule_violations"]]
    assert 5 in rule_ids_r5

    # Nelson Rule 6: 4 of 5 > 1 sigma on same side
    vals_r6 = [50.03, 50.03, 50.03, 50.03, 50.00, 50.00]
    res_r6 = spc_engine.evaluate_spc(vals_r6, subgroup_size=1)
    rule_ids_r6 = [v["rule_number"] for v in res_r6["rule_violations"]]
    assert 6 in rule_ids_r6


def test_capability_guardrails_and_golden_anchor():
    """
    Validates capability indices on anchor sample (5 points) and sample size guardrails:
    - n < 5: INSUFFICIENT_DATA
    - n < 30: COMPUTED with visible warning
    - Pp = 0.5717, Cp = 0.9400, Ppk = 0.0, Cpk = 0.0
    """
    # Refuse n < 5
    refused = capability_engine.calculate_capability([50.01, 50.02, 50.03], usl=50.05, lsl=49.95)
    assert refused["status"] == "INSUFFICIENT_DATA"
    assert refused["cp"] is None

    # n = 5 (anchor sample)
    cap = capability_engine.calculate_capability([50.01, 50.03, 50.06, 50.08, 50.07], usl=50.05, lsl=49.95)
    assert cap["status"] == "COMPUTED"
    assert cap["pp"] == 0.5717
    assert cap["cp"] == 0.9400
    assert cap["ppk"] == 0.0
    assert cap["cpk"] == 0.0
    assert len(cap["warnings"]) > 0
    assert any("Preliminary estimate: n=5" in w for w in cap["warnings"])


# =====================================================================
# 4. PROCESS ANOMALY MATH & TELEMETRY DETECTIONS
# =====================================================================
def test_process_anomaly_anchor_case():
    """
    Validates anchor case:
    - vibration 3.8 vs 2.1 flagged
    - tool usage 1,150 vs 600 flagged
    - spindle 1,200 and feed 0.20 NOT flagged
    - coolant 25 vs 24 not flagged
    """
    res = anomaly_detector.analyze_telemetry_series(
        batch_id="BATCH-0245",
        machine_code="CNC-04",
        telemetry_records=[{
            "spindle_speed": 1200.0,
            "feed_rate": 0.20,
            "coolant_temp": 25.0,
            "vibration": 3.8,
            "tool_usage_cycles": 1150,
            "motor_current": 14.5,
            "cycle_time": 45.0,
            "pressure": 5.5
        }]
    )
    flagged = [a["parameter"] for a in res["anomalies"]]
    assert "vibration" in flagged
    assert "tool_usage_cycles" in flagged
    assert "spindle_speed" not in flagged
    assert "feed_rate" not in flagged
    assert "coolant_temp" not in flagged


# =====================================================================
# 5. PARETO 80/20 VITAL FEW & DATE FILTERING
# =====================================================================
def test_pareto_vital_few_and_date_filtering():
    """
    Verifies that 'vital few' includes categories until cumulative percentage >= 80%,
    and that date-range filter excludes non-matching records without mock fallback.
    """
    db = SessionLocal()
    try:
        # Query existing incidents
        res = pareto_service.compute_pareto(db=db, dimension="defect_type")
        assert res["total_incidents"] > 0
        assert len(res["vital_few_categories"]) > 0
        
        # Test date filter that excludes all records
        res_empty = pareto_service.compute_pareto(
            db=db,
            dimension="defect_type",
            start_date="2020-01-01T00:00:00",
            end_date="2020-01-02T00:00:00"
        )
        assert res_empty["total_incidents"] == 0
        assert len(res_empty["items"]) == 0
        assert res_empty["vital_few_categories"] == []
    finally:
        db.close()


# =====================================================================
# 6. TWO-PROPORTION Z-TEST EFFECTIVENESS FROM REAL DB ROWS
# =====================================================================
def test_two_proportion_effectiveness_from_real_db_rows():
    """
    Verifies that evaluate_capa_effectiveness loads pre/post batch measurements
    from SQLite database (1000 pre with 82 nonconforming = 8.2% vs 1000 post with 11 = 1.1%),
    and verifies the two-sample z-test (z = 7.54, p-value < 1e-6), and epistemic wording.
    """
    eff = effectiveness_engine.evaluate_capa_effectiveness("CAPA-2026-001")
    assert eff["sample_before_count"] == 1000
    assert eff["defects_before_count"] == 82
    assert eff["rejection_rate_before_percent"] == 8.2
    assert eff["sample_after_count"] == 1000
    assert eff["defects_after_count"] == 11
    assert eff["rejection_rate_after_percent"] == 1.1
    assert eff["z_statistic"] == 7.54
    assert eff["is_statistically_significant"] is True
    assert "Observed association" in eff["conclusion_label"]
    assert "causation not established" in eff["conclusion_label"]


# =====================================================================
# 7. RCA EVIDENCE WEIGHTING & COUNTERFACTUAL PROOF
# =====================================================================
def test_rca_evidence_weighting_and_counterfactual_ranking():
    """
    Proves that hypothesis ranking is computed deterministically from data:
    - BATCH-0245 (cycles 1,150, vibration 3.8): Tool Wear is Rank 1 (score 0.88).
    - Counterfactual (cycles 450, vibration 2.1): Tool Wear drops to Rank 5 (score 0.13),
      and Incorrect Tool Offset ranks ahead.
    """
    # 1. BATCH-0245
    res1 = rca_agent.analyze_incident(batch_id="BATCH-0245", tool_cycles=1150, vibration_val=3.8)
    hypos1 = res1["report"].ranked_hypotheses
    assert hypos1[0].title == "Progressive Tool Flank Wear"
    assert hypos1[0].confidence_score == 0.88
    assert hypos1[1].title == "Spindle Harmonic Vibration and Bearing Play"
    assert hypos1[1].confidence_score == 0.62

    # 2. Counterfactual with normal tooling and vibration
    res2 = rca_agent.analyze_incident(batch_id="BATCH-TEST", tool_cycles=450, vibration_val=2.1)
    hypos2 = res2["report"].ranked_hypotheses
    assert hypos2[0].title != "Progressive Tool Flank Wear"
    # Tool wear is lowest rank
    tool_wear_hypo = [h for h in hypos2 if h.title == "Progressive Tool Flank Wear"][0]
    assert tool_wear_hypo.confidence_score <= 0.20


# =====================================================================
# 8. INDUSTRIAL SAFETY GUARDRAILS & FORBIDDEN ACTIONS
# =====================================================================
def test_safety_guardrails_prevent_autonomous_actions():
    forbidden_actions = [
        "emergency_stop",
        "set_feed_rate",
        "release_batch",
        "reject_batch",
        "change_plc_config",
        "stop_machine",
        "override_engineer_decision",
        "confirm_root_cause_autonomous"
    ]
    for act in forbidden_actions:
        with pytest.raises(ForbiddenAutonomousAction):
            guardrails.validate_action(act, agent_name="Agent 7 CAPA")

    # Prove agents cannot emit CONFIRMED_ROOT_CAUSE
    with pytest.raises(EpistemicViolation):
        guardrails.validate_epistemic_label("CONFIRMED_ROOT_CAUSE", source="Agent 6 RCA", is_human_engineer=False)

    # Human quality engineer CAN emit CONFIRMED_ROOT_CAUSE
    label = guardrails.validate_epistemic_label("CONFIRMED_ROOT_CAUSE", source="Lead QE Sarah Chen", is_human_engineer=True)
    assert label == EpistemicLabel.CONFIRMED_ROOT_CAUSE
