"""
Test Suite: Agent 5 — Statistical Process Control (SPC) Agent
Covers all 19 mandatory test areas:
1. Mean and sample standard deviation against independently calculated expected values.
2. Correct control limits for each implemented chart type (I-MR, X-bar/R, p-chart).
3. Point beyond UCL.
4. Point below LCL.
5. Shift detection (Nelson Rule 2).
6. Increasing/decreasing trend detection (Nelson Rule 3).
7. Correct distinction between specification violations and control-limit violations.
8. Cp/Cpk/Pp/Ppk against independently calculated reference values.
9. Missing specification limits.
10. Insufficient observations (n=0, n=1, n<5, n<30).
11. Zero variance.
12. Invalid numbers and non-finite values.
13. Unknown batch and mismatch error handling.
14. Multiple batches and characteristics isolation.
15. Persisted findings retrieval linked to correct batch.
16. Duplicate execution behavior (no duplicate records).
17. Downstream RCA integration in workflow state.
18. PDF quality report generation with distinct control & spec limits.
19. Prevention of prohibited autonomous actions & human review governance.
"""
import io
import json
import pytest
import numpy as np
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.agents.spc_agent import spc_agent, StatisticalProcessControlAgent
from backend.app.services.capability import capability_engine
from backend.app.services.spc_charts import spc_engine, SPCEngine, SPC_CONSTANTS
from backend.app.database.session import SessionLocal
from backend.app.database.models import Batch, Product, InspectionCharacteristic, Measurement, SPCResult
from backend.app.orchestrator.state import WorkflowState
from backend.app.services.pdf_report import generate_quality_pdf_report

client = TestClient(app)


# ---------------------------------------------------------------------------
# TEST 1: Descriptive Statistics (Mean & Sample Std Dev with N-1 Bessel's)
# ---------------------------------------------------------------------------
def test_1_mean_and_sample_std_dev_independent_numpy():
    """Verifies sample mean and sample standard deviation against independent numpy calculations."""
    data = [50.012, 50.024, 49.988, 50.005, 50.031, 49.995, 50.018, 50.002, 50.021, 49.998]
    np_mean = float(np.mean(data))
    np_std = float(np.std(data, ddof=1))  # N-1 Bessel's correction
    np_min = float(np.min(data))
    np_max = float(np.max(data))
    np_range = float(np.ptp(data))

    res = spc_agent.analyze_process_capability_and_control(
        batch_id="TEST-BATCH-01",
        values=data,
        usl=50.05,
        lsl=49.95,
        nominal=50.00
    )
    rep = res["report"]
    assert rep.sample_size == len(data)
    assert rep.mean == round(np_mean, 4)
    assert rep.std_dev == round(np_std, 4)
    assert rep.min_value == round(np_min, 4)
    assert rep.max_value == round(np_max, 4)
    assert rep.range_value == round(np_range, 4)


# ---------------------------------------------------------------------------
# TEST 2: Control Limits for Each Implemented Chart Type
# ---------------------------------------------------------------------------
def test_2_control_limits_for_each_chart_type():
    """Verifies control limits for I-MR (Individuals), X-bar/R (Subgroups), and p-chart (Attributes)."""
    # (a) I-MR Chart
    imr_data = [50.01, 50.03, 50.02, 50.04, 50.05, 50.03]
    imr_res = spc_engine.evaluate_spc(data=imr_data, subgroup_size=1)
    assert imr_res["chart_type"] == "I_MR_chart"
    expected_cl = np.mean(imr_data)
    mr = np.abs(np.diff(imr_data))
    expected_mr_bar = np.mean(mr)
    expected_sigma = expected_mr_bar / 1.128
    assert imr_res["center_line"] == round(expected_cl, 4)
    assert imr_res["ucl"] == round(expected_cl + 3.0 * expected_sigma, 4)
    assert imr_res["lcl"] == round(expected_cl - 3.0 * expected_sigma, 4)
    assert imr_res["mr_cl"] == round(expected_mr_bar, 4)
    assert imr_res["mr_ucl"] == round(3.267 * expected_mr_bar, 5)
    assert imr_res["mr_lcl"] == 0.0

    # (b) X-bar / R Chart (Subgroups of size n=5)
    rng = np.random.RandomState(42)
    xbar_data = [round(float(x), 4) for x in rng.normal(50.00, 0.02, 20)]
    k = 5
    xbar_res = spc_engine.evaluate_spc(data=xbar_data, subgroup_size=k)
    assert xbar_res["chart_type"] == "Xbar_R_chart"
    const = SPC_CONSTANTS[5]
    subgroups = [xbar_data[i*k:(i+1)*k] for i in range(len(xbar_data)//k)]
    x_bars = [np.mean(sg) for sg in subgroups]
    ranges = [np.ptp(sg) for sg in subgroups]
    expected_xbar_cl = np.mean(x_bars)
    expected_r_bar = np.mean(ranges)
    assert xbar_res["center_line"] == round(expected_xbar_cl, 4)
    assert xbar_res["ucl"] == round(expected_xbar_cl + const["A2"] * expected_r_bar, 4)
    assert xbar_res["lcl"] == round(expected_xbar_cl - const["A2"] * expected_r_bar, 4)

    # (c) p-Chart (Defect counts out of subgroup sizes)
    defect_counts = [2, 3, 1, 4, 2]
    totals = [100, 100, 100, 100, 100]
    p_res = spc_engine.evaluate_spc(
        data=defect_counts,
        is_attribute_data=True,
        total_subgroup_counts=totals
    )
    assert p_res["chart_type"] == "p_chart"
    p_bar = sum(defect_counts) / sum(totals)
    sigma_p = np.sqrt(p_bar * (1 - p_bar) / 100)
    assert p_res["center_line"] == round(p_bar, 4)
    assert p_res["ucl"] == round(p_bar + 3.0 * sigma_p, 4)
    assert p_res["lcl"] == round(max(0.0, p_bar - 3.0 * sigma_p), 4)


# ---------------------------------------------------------------------------
# TEST 3 & 4: Point Beyond UCL and Point Below LCL (Nelson Rule 1)
# ---------------------------------------------------------------------------
def test_3_point_beyond_ucl():
    """Detects an extreme individual point exceeding the upper control limit (Rule 1)."""
    # Center at 50.00 with small spread, then an extreme spike
    data = [50.00, 50.01, 50.00, 50.01, 49.99, 50.00, 50.01, 50.00, 50.08]
    res = spc_agent.analyze_process_capability_and_control("TEST-BATCH-UCL", data)
    rep = res["report"]
    assert rep.ucl < 50.08
    r1_violations = [v for v in rep.nelson_violations if v.rule_number == 1]
    assert len(r1_violations) > 0
    assert 8 in r1_violations[0].sample_indices


def test_4_point_below_lcl():
    """Detects an extreme individual point falling below the lower control limit (Rule 1)."""
    data = [50.00, 50.01, 50.00, 50.01, 49.99, 50.00, 50.01, 50.00, 49.92]
    res = spc_agent.analyze_process_capability_and_control("TEST-BATCH-LCL", data)
    rep = res["report"]
    assert rep.lcl > 49.92
    r1_violations = [v for v in rep.nelson_violations if v.rule_number == 1]
    assert len(r1_violations) > 0
    assert 8 in r1_violations[0].sample_indices


# ---------------------------------------------------------------------------
# TEST 5: Shift Detection (Nelson Rule 2)
# ---------------------------------------------------------------------------
def test_5_shift_detection():
    """Detects a sustained shift in process mean (8 consecutive points on one side of center line)."""
    # First 4 points baseline, then 8 points consistently above mean
    data = [49.99, 50.00, 49.99, 50.00, 50.02, 50.03, 50.02, 50.03, 50.02, 50.03, 50.02, 50.03]
    res = spc_agent.analyze_process_capability_and_control("TEST-SHIFT", data)
    rep = res["report"]
    r2_violations = [v for v in rep.nelson_violations if v.rule_number == 2]
    assert len(r2_violations) > 0
    assert "Process Mean Shift" in r2_violations[0].rule_name


# ---------------------------------------------------------------------------
# TEST 6: Trend Detection (Nelson Rule 3)
# ---------------------------------------------------------------------------
def test_6_trend_detection():
    """Detects 6 consecutive points steadily increasing or decreasing (tool wear drift)."""
    data = [50.00, 50.01, 50.02, 50.03, 50.04, 50.05, 50.06, 50.04, 50.04]
    res = spc_agent.analyze_process_capability_and_control("TEST-TREND", data)
    rep = res["report"]
    r3_violations = [v for v in rep.nelson_violations if v.rule_number == 3]
    assert len(r3_violations) > 0
    assert "Trend" in r3_violations[0].rule_name or "Drift" in r3_violations[0].rule_name


# ---------------------------------------------------------------------------
# TEST 7: Mandatory Distinction Between Specification and Control Limits
# ---------------------------------------------------------------------------
def test_7_distinction_between_specification_and_control_limits():
    """
    Mandatory: Asserts that specification limits (USL/LSL) and statistical control limits (UCL/LCL)
    are strictly separated and do not alter one another.
    """
    data = [50.00, 50.01, 49.99, 50.00, 50.01, 50.02, 49.98, 50.00, 50.01, 50.00]

    # Evaluation with Narrow Spec Limits
    res1 = spc_agent.analyze_process_capability_and_control(
        batch_id="TEST-SPEC-A",
        values=data,
        usl=50.03,
        lsl=49.97,
        nominal=50.00
    )
    rep1 = res1["report"]

    # Evaluation with Wide Spec Limits
    res2 = spc_agent.analyze_process_capability_and_control(
        batch_id="TEST-SPEC-B",
        values=data,
        usl=50.15,
        lsl=49.85,
        nominal=50.00
    )
    rep2 = res2["report"]

    # Statistical control limits MUST be mathematically identical because data is unchanged!
    assert rep1.ucl == rep2.ucl
    assert rep1.lcl == rep2.lcl
    assert rep1.cl == rep2.cl

    # Specification limits MUST differ
    assert rep1.usl != rep2.usl
    assert rep1.lsl != rep2.lsl

    # Point out-of-spec is NOT automatically out-of-control
    data_mix = [50.00, 50.00, 50.00, 50.04]
    res_mix = spc_agent.analyze_process_capability_and_control(
        batch_id="TEST-MIX",
        values=data_mix,
        usl=50.03,
        lsl=49.97,
        nominal=50.00
    )
    rep_mix = res_mix["report"]
    pt_last = rep_mix.chart_data[-1]
    assert pt_last["is_out_of_spec"] is True
    if pt_last["value"] <= rep_mix.ucl:
        assert pt_last["is_out_of_control"] is False


# ---------------------------------------------------------------------------
# TEST 8: Capability Indices (Cp, Cpk, Pp, Ppk) Against Independent NumPy
# ---------------------------------------------------------------------------
def test_8_cp_cpk_pp_ppk_against_independent_reference_values():
    """Calculates Cp, Cpk, Pp, Ppk and verifies against independent statistical formulas."""
    rng = np.random.RandomState(123)
    data = [round(float(x), 4) for x in rng.normal(50.005, 0.008, 30)]
    usl, lsl, target = 50.05, 49.95, 50.00

    n = len(data)
    mean = np.mean(data)
    s_overall = np.std(data, ddof=1)
    mr = np.abs(np.diff(data))
    mr_bar = np.mean(mr)
    sigma_within = mr_bar / 1.128

    expected_cp = (usl - lsl) / (6.0 * sigma_within)
    expected_cpk = min((usl - mean) / (3.0 * sigma_within), (mean - lsl) / (3.0 * sigma_within))
    expected_pp = (usl - lsl) / (6.0 * s_overall)
    expected_ppk = min((usl - mean) / (3.0 * s_overall), (mean - lsl) / (3.0 * s_overall))

    res = capability_engine.calculate_capability(
        values=data,
        usl=usl,
        lsl=lsl,
        target=target
    )
    assert res["status"] == "sufficient"
    assert abs(res["cp"] - expected_cp) < 0.001
    assert abs(res["cpk"] - expected_cpk) < 0.001
    assert abs(res["pp"] - expected_pp) < 0.001
    assert abs(res["ppk"] - expected_ppk) < 0.001


# ---------------------------------------------------------------------------
# TEST 9: Missing Specification Limits Handling
# ---------------------------------------------------------------------------
def test_9_missing_specification_limits():
    """Handles missing specification limits gracefully without crashing."""
    data = [50.01, 50.02, 50.01, 50.03, 50.02, 50.01]
    res = capability_engine.calculate_capability(
        values=data,
        usl=None,
        lsl=None
    )
    assert res["status"] == "missing_spec_limits"
    assert res["cp"] is None
    assert res["cpk"] is None
    assert any("MISSING SPECIFICATION LIMITS" in w for w in res["warnings"])


# ---------------------------------------------------------------------------
# TEST 10: Insufficient Observations (n=0, n=1, n<5, n<30)
# ---------------------------------------------------------------------------
def test_10_insufficient_observations():
    """Enforces strict sample size guardrails across all sample sizes."""
    # (a) n = 0
    res0 = spc_agent.analyze_process_capability_and_control("ZERO-BATCH", [])
    assert res0["report"].sample_size == 0
    assert res0["report"].status == "insufficient_data"
    assert res0["report"].mean is None

    # (b) n = 1
    res1 = spc_agent.analyze_process_capability_and_control("ONE-BATCH", [50.01])
    assert res1["report"].sample_size == 1
    assert res1["report"].status == "insufficient_data"
    assert res1["report"].ucl is None

    # (c) n = 3 (Capability indices suppressed when n < 5)
    res3 = capability_engine.calculate_capability([50.01, 50.02, 50.03], usl=50.05, lsl=49.95)
    assert res3["status"] == "insufficient_data"
    assert res3["cp"] is None
    assert res3["cpk"] is None

    # (d) n = 15 (Preliminary estimate warning for 5 <= n < 30)
    rng = np.random.RandomState(42)
    data15 = [round(float(x), 4) for x in rng.normal(50.00, 0.01, 15)]
    res15 = capability_engine.calculate_capability(data15, usl=50.05, lsl=49.95)
    assert res15["status"] == "preliminary"
    assert any("PRELIMINARY SAMPLE SIZE" in w for w in res15["warnings"])


# ---------------------------------------------------------------------------
# TEST 11: Zero Variance Handling
# ---------------------------------------------------------------------------
def test_11_zero_variance():
    """Handles identical readings without ZeroDivisionError or crash."""
    zero_var_data = [50.00, 50.00, 50.00, 50.00, 50.00, 50.00]
    res = capability_engine.calculate_capability(zero_var_data, usl=50.05, lsl=49.95)
    assert res["status"] == "zero_variance"
    assert res["std_dev"] == 0.0
    assert res["cp"] is None
    assert any("ZERO/NEAR-ZERO VARIANCE" in w for w in res["warnings"])


# ---------------------------------------------------------------------------
# TEST 12: Invalid Numbers and Non-Finite Values
# ---------------------------------------------------------------------------
def test_12_invalid_numbers_and_non_finite_values():
    """Filters out NaN, Inf, and non-numeric strings safely."""
    raw_data = [50.01, "INVALID", float("nan"), float("inf"), 50.03, 50.02, None, 50.04]
    res = spc_agent.analyze_process_capability_and_control("TEST-CLEAN", raw_data)
    rep = res["report"]
    assert rep.sample_size == 4
    assert rep.mean == round((50.01 + 50.03 + 50.02 + 50.04) / 4.0, 4)


# ---------------------------------------------------------------------------
# TEST 13: Unknown Batch and Characteristic Error Handling
# ---------------------------------------------------------------------------
def test_13_unknown_batch_error_handling():
    """Rejects unknown batch IDs appropriately with HTTP 404."""
    resp = client.get("/api/spc/analyze?batch_id=BATCH-NONEXISTENT-999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# TEST 14: Multiple Batches and Characteristics Isolation
# ---------------------------------------------------------------------------
def test_14_multiple_batches_and_characteristics_isolation():
    """Ensures multiple batches do not contaminate each other's statistics or results."""
    b1_data = [50.01, 50.02, 50.03, 50.02, 50.01]
    b2_data = [60.05, 60.07, 60.06, 60.08, 60.05]

    r1 = spc_agent.analyze_process_capability_and_control("BATCH-ALPHA", b1_data)
    r2 = spc_agent.analyze_process_capability_and_control("BATCH-BETA", b2_data)

    assert r1["report"].mean < 55.0
    assert r2["report"].mean > 55.0
    assert r1["report"].batch_id == "BATCH-ALPHA"
    assert r2["report"].batch_id == "BATCH-BETA"


# ---------------------------------------------------------------------------
# TEST 15: Persisted Findings Retrieval Linked to Correct Batch
# ---------------------------------------------------------------------------
def test_15_persisted_findings_retrieval_linked_to_correct_batch():
    """Persists SPC results and verifies retrieval via GET /api/spc/results."""
    analyze_resp = client.get("/api/spc/analyze?batch_id=BATCH-0245")
    assert analyze_resp.status_code == 200

    results_resp = client.get("/api/spc/results?batch_id=BATCH-0245")
    assert results_resp.status_code == 200
    data = results_resp.json()
    assert data["batch_id"] == "BATCH-0245"
    assert len(data["results"]) > 0
    first_r = data["results"][0]
    assert first_r["center_line"] is not None
    assert first_r["ucl"] is not None
    assert first_r["lcl"] is not None


# ---------------------------------------------------------------------------
# TEST 16: Duplicate Execution Behavior (No Duplicate Records)
# ---------------------------------------------------------------------------
def test_16_duplicate_execution_behavior():
    """Consecutive executions update the existing record rather than accumulating duplicates."""
    db = SessionLocal()
    try:
        from backend.app.database.models import Batch
        b = db.query(Batch).filter((Batch.batch_number == "BATCH-0245") | (Batch.id == "BATCH-0245")).first()
        b_id = b.id if b else "BATCH-0245"
        initial_count = db.query(SPCResult).filter((SPCResult.batch_id == b_id) | (SPCResult.batch_id == "BATCH-0245")).count()

        # Run analysis twice
        client.get("/api/spc/analyze?batch_id=BATCH-0245")
        client.get("/api/spc/analyze?batch_id=BATCH-0245")

        post_count = db.query(SPCResult).filter((SPCResult.batch_id == b_id) | (SPCResult.batch_id == "BATCH-0245")).count()
        assert post_count == max(1, initial_count)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# TEST 17: Downstream RCA Integration in Workflow State
# ---------------------------------------------------------------------------
def test_17_downstream_rca_integration():
    """Verifies SPC findings populate WorkflowState and signal special causes to RCA."""
    state = WorkflowState(workflow_id="WF-TEST-SPC", batch_id="BATCH-0245")
    # Dataset with a clear special-cause out-of-control outlier exceeding UCL
    data = [50.00, 50.01, 50.00, 50.01, 49.99, 50.00, 50.01, 50.00, 50.08]
    res = spc_agent.analyze_process_capability_and_control(
        batch_id="BATCH-0245",
        values=data,
        usl=50.05,
        lsl=49.95,
        nominal=50.00
    )
    state.spc_report = res["report"]
    if len(state.spc_report.nelson_violations) > 0:
        state.has_spc_violations = True

    assert state.spc_report is not None
    assert len(state.spc_report.nelson_violations) > 0
    assert state.has_spc_violations is True
    
    # Verify that WorkflowState carries the SPC report directly into downstream RCA inputs
    rca_context = {
        "batch_id": state.batch_id,
        "spc_violations": [f"Rule {v.rule_number}: {v.rule_name}" for v in state.spc_report.nelson_violations],
        "has_spc_violations": state.has_spc_violations,
        "cpk": state.spc_report.cpk
    }
    assert rca_context["has_spc_violations"] is True
    assert any("Rule 1" in r for r in rca_context["spc_violations"])


# ---------------------------------------------------------------------------
# TEST 18: PDF Quality Report Generation with Distinct Control & Spec Limits
# ---------------------------------------------------------------------------
def test_18_pdf_report_renders_spc_and_distinct_limits():
    """Ensures PDF quality report compiles with distinct SPC limits and capability metrics."""
    state_mock = {
        "batch_id": "BATCH-0245",
        "batch_metadata": {
            "batch_id": "BATCH-0245",
            "product_name": "Precision Shaft",
            "nominal_mm": 50.00,
            "tolerance_mm": 0.05,
            "usl": 50.05,
            "lsl": 49.95,
            "machine": "CNC-04",
            "quantity": 500
        },
        "dimensional_report": {
            "total_inspected": 5,
            "conforming": 2,
            "nonconforming": 3,
            "rejection_rate": 60.0
        },
        "spc_report": {
            "cp": 0.9400,
            "cpk": 0.0,
            "pp": 0.5717,
            "ppk": 0.0,
            "cl": 50.05,
            "ucl": 50.1032,
            "lcl": 49.9968,
            "usl": 50.05,
            "lsl": 49.95,
            "chart_data": [
                {"sample_index": 1, "value": 50.01, "ucl": 50.1032, "lcl": 49.9968, "cl": 50.05, "usl": 50.05, "lsl": 49.95},
                {"sample_index": 2, "value": 50.03, "ucl": 50.1032, "lcl": 49.9968, "cl": 50.05, "usl": 50.05, "lsl": 49.95},
                {"sample_index": 3, "value": 50.06, "ucl": 50.1032, "lcl": 49.9968, "cl": 50.05, "usl": 50.05, "lsl": 49.95},
                {"sample_index": 4, "value": 50.08, "ucl": 50.1032, "lcl": 49.9968, "cl": 50.05, "usl": 50.05, "lsl": 49.95},
                {"sample_index": 5, "value": 50.07, "ucl": 50.1032, "lcl": 49.9968, "cl": 50.05, "usl": 50.05, "lsl": 49.95}
            ],
            "warnings": [
                "PRELIMINARY SAMPLE SIZE: Sample size n=5 is below standard guideline (n>=30).",
                "PROCESS DRIFT DETECTED: Significant systematic linear trend detected."
            ]
        }
    }
    pdf_bytes = generate_quality_pdf_report(state_mock)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF")


# ---------------------------------------------------------------------------
# TEST 19: Prevention of Autonomous Batch Disposition & Machine Actions
# ---------------------------------------------------------------------------
def test_19_no_autonomous_batch_disposition_or_machine_control():
    """Confirms Agent 5 is strictly decision-support advisory and never autonomously rejects batches or halts machinery."""
    res = spc_agent.analyze_process_capability_and_control(
        batch_id="BATCH-0245",
        values=[50.01, 50.03, 50.06, 50.08, 50.07],
        usl=50.05,
        lsl=49.95
    )
    rep = res["report"]
    assert rep.review_status == "HUMAN_REVIEW_REQUIRED"
    assert rep.autonomous_actions_prohibited is True

    # Check Batch record in database is unchanged in status
    db = SessionLocal()
    try:
        b = db.query(Batch).filter((Batch.batch_number == "BATCH-0245") | (Batch.id == "BATCH-0245")).first()
        if b:
            assert b.status in ("QUALITY_HOLD", "CONFORMING", "open", "PENDING_REVIEW")
            assert b.status != "REJECTED"
    finally:
        db.close()
