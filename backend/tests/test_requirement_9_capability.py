import pytest
import numpy as np
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.capability import capability_engine
from backend.app.agents.spc_agent import spc_agent
from backend.app.services.pdf_report import generate_quality_pdf_report
from backend.app.database.session import SessionLocal
from backend.app.database.models import SPCResult

client = TestClient(app)

def independent_calc_capability(values, usl=None, lsl=None, subgroup_size=1):
    vals = np.array(values, dtype=float)
    n = len(vals)
    mean = float(np.mean(vals))
    s_overall = float(np.std(vals, ddof=1)) if n > 1 else 0.0

    if subgroup_size > 1 and n >= subgroup_size:
        d2_map = {2: 1.128, 3: 1.693, 4: 2.059, 5: 2.326}
        d2 = d2_map.get(subgroup_size, 1.128)
        num_sg = n // subgroup_size
        reshaped = vals[:num_sg * subgroup_size].reshape(num_sg, subgroup_size)
        ranges = np.ptp(reshaped, axis=1)
        r_bar = float(np.mean(ranges))
        sigma_within = r_bar / d2
    else:
        mr = np.abs(np.diff(vals))
        mr_bar = float(np.mean(mr)) if len(mr) > 0 else s_overall
        sigma_within = mr_bar / 1.128

    cp, cpk, cpu, cpl = None, None, None, None
    pp, ppk, ppu, ppl = None, None, None, None

    if usl is not None and lsl is not None:
        tol = usl - lsl
        cp = tol / (6.0 * sigma_within)
        cpu = (usl - mean) / (3.0 * sigma_within)
        cpl = (mean - lsl) / (3.0 * sigma_within)
        cpk = min(cpu, cpl)

        pp = tol / (6.0 * s_overall)
        ppu = (usl - mean) / (3.0 * s_overall)
        ppl = (mean - lsl) / (3.0 * s_overall)
        ppk = min(ppu, ppl)
    elif usl is not None:
        cpu = (usl - mean) / (3.0 * sigma_within)
        cpk = cpu
        ppu = (usl - mean) / (3.0 * s_overall)
        ppk = ppu
    elif lsl is not None:
        cpl = (mean - lsl) / (3.0 * sigma_within)
        cpk = cpl
        ppl = (mean - lsl) / (3.0 * s_overall)
        ppk = ppl

    return {
        "n": n,
        "mean": mean,
        "s_overall": s_overall,
        "sigma_within": sigma_within,
        "cp": cp,
        "cpk": cpk,
        "pp": pp,
        "ppk": ppk,
        "cpu": cpu,
        "cpl": cpl,
        "ppu": ppu,
        "ppl": ppl
    }

def test_golden_dataset_batch_0245():
    values = [50.01, 50.03, 50.06, 50.08, 50.07]
    usl, lsl = 50.05, 49.95

    app_res = capability_engine.calculate_capability(values, usl=usl, lsl=lsl)
    indep = independent_calc_capability(values, usl=usl, lsl=lsl)

    assert abs(app_res["mean"] - 50.05) < 1e-4
    assert abs(indep["mean"] - 50.05) < 1e-4
    assert abs(app_res["mean"] - indep["mean"]) < 1e-6

    assert abs(app_res["std_dev"] - 0.029155) < 1e-4
    assert abs(indep["s_overall"] - 0.029155) < 1e-4

    assert abs(app_res["sigma_within"] - 0.017730) < 1e-4
    assert abs(indep["sigma_within"] - 0.017730) < 1e-4

    assert abs(app_res["pp"] - 0.5717) < 1e-4
    assert abs(indep["pp"] - 0.5717) < 1e-4

    assert abs(app_res["ppk"] - 0.0) < 1e-4
    assert abs(indep["ppk"] - 0.0) < 1e-4

    assert abs(app_res["cp"] - 0.9400) < 1e-4
    assert abs(indep["cp"] - 0.9400) < 1e-4

    assert abs(app_res["cpk"] - 0.0) < 1e-4
    assert abs(indep["cpk"] - 0.0) < 1e-4

    assert "MR-bar" in app_res["sigma_within_method"]
    assert "s (ddof=1)" in app_res["sigma_overall_method"]

    assert len(app_res["warnings"]) > 0
    assert any("preliminary" in w.lower() for w in app_res["warnings"])

def test_centered_in_control_100_points_benchmark():
    rng = np.random.RandomState(42)
    values = [round(float(x), 4) for x in rng.normal(50.00, 0.01, 100)]
    usl, lsl = 50.05, 49.95

    app_res = capability_engine.calculate_capability(values, usl=usl, lsl=lsl)
    indep = independent_calc_capability(values, usl=usl, lsl=lsl)

    assert app_res["status"] == "sufficient"
    assert app_res["sample_size"] == 100
    assert abs(app_res["mean"] - indep["mean"]) < 1e-4
    assert abs(app_res["sigma_within"] - indep["sigma_within"]) < 1e-4
    assert abs(app_res["sigma_overall"] - indep["s_overall"]) < 1e-4
    assert abs(app_res["cp"] - indep["cp"]) < 1e-4
    assert abs(app_res["cpk"] - indep["cpk"]) < 1e-4
    assert abs(app_res["pp"] - indep["pp"]) < 1e-4
    assert abs(app_res["ppk"] - indep["ppk"]) < 1e-4

    assert app_res["cp"] > 1.33
    assert app_res["cpk"] > 1.33

def test_one_sided_specification_limits():
    rng = np.random.RandomState(42)
    values = [round(float(x), 4) for x in rng.normal(50.00, 0.01, 50)]

    res_upper = capability_engine.calculate_capability(values, usl=50.05, lsl=None)
    indep_upper = independent_calc_capability(values, usl=50.05, lsl=None)
    assert res_upper["cp"] is None
    assert res_upper["pp"] is None
    assert abs(res_upper["cpk"] - indep_upper["cpk"]) < 1e-4
    assert abs(res_upper["ppk"] - indep_upper["ppk"]) < 1e-4
    assert any("ONE-SIDED SPECIFICATION: Upper" in w for w in res_upper["warnings"])

    res_lower = capability_engine.calculate_capability(values, usl=None, lsl=49.95)
    indep_lower = independent_calc_capability(values, usl=None, lsl=49.95)
    assert res_lower["cp"] is None
    assert res_lower["pp"] is None
    assert abs(res_lower["cpk"] - indep_lower["cpk"]) < 1e-4
    assert abs(res_lower["ppk"] - indep_lower["ppk"]) < 1e-4
    assert any("ONE-SIDED SPECIFICATION: Lower" in w for w in res_lower["warnings"])

@pytest.mark.parametrize("n", [1, 2, 4])
def test_sufficiency_threshold_insufficient_refusal(n):
    vals = [50.00 + 0.01 * i for i in range(n)]
    res = capability_engine.calculate_capability(vals, usl=50.05, lsl=49.95)

    assert res["status"] == "insufficient_data"
    assert res["cp"] is None
    assert res["cpk"] is None
    assert res["pp"] is None
    assert res["ppk"] is None
    assert isinstance(res["warnings"], list)
    assert len(res["warnings"]) > 0
    assert any("insufficient" in w.lower() for w in res["warnings"])

@pytest.mark.parametrize("n", [5, 29])
def test_sufficiency_threshold_preliminary_warning(n):
    rng = np.random.RandomState(42)
    vals = [round(float(x), 4) for x in rng.normal(50.00, 0.01, n)]
    res = capability_engine.calculate_capability(vals, usl=50.05, lsl=49.95)

    assert res["status"] == "preliminary"
    assert res["cp"] is not None
    assert res["cpk"] is not None
    assert res["pp"] is not None
    assert res["ppk"] is not None
    assert isinstance(res["warnings"], list)
    assert len(res["warnings"]) > 0
    assert any("preliminary" in w.lower() for w in res["warnings"])

def test_sufficiency_threshold_sufficient_normal():
    rng = np.random.RandomState(42)
    vals = [round(float(x), 4) for x in rng.normal(50.00, 0.01, 30)]
    res = capability_engine.calculate_capability(vals, usl=50.05, lsl=49.95)

    assert res["status"] == "sufficient"
    assert res["cp"] is not None
    assert res["cpk"] is not None
    assert isinstance(res["warnings"], list)
    assert not any("preliminary" in w.lower() for w in res["warnings"])

def test_no_capability_result_ever_lacks_warnings_array():
    test_cases = [
        [],
        [50.01],
        [50.01, 50.02],
        [50.01, 50.02, 50.03, 50.04, 50.05],
        [50.00] * 10,
    ]
    for tc in test_cases:
        res = capability_engine.calculate_capability(tc, usl=50.05, lsl=49.95)
        assert "warnings" in res
        assert isinstance(res["warnings"], list)

def test_assumption_process_out_of_statistical_control():
    vals = [50.00, 50.01, 50.02, 50.03, 50.04, 50.05, 50.06]
    res = capability_engine.calculate_capability(
        vals,
        usl=50.05,
        lsl=49.95,
        is_in_control=False,
        out_of_control_violations=["Rule 1: Extreme Point Out of Control", "Rule 3: Trend"]
    )
    assert any("OUT-OF-CONTROL PROCESS" in w for w in res["warnings"])
    assert res["stability_test"]["is_in_control"] is False

def test_assumption_non_normal_distribution():
    vals = [49.95] * 20 + [50.05] * 20
    res = capability_engine.calculate_capability(vals, usl=50.05, lsl=49.95)

    assert any("NON-NORMAL DISTRIBUTION" in w for w in res["warnings"])
    assert res["normality_test"]["test"] == "Shapiro-Wilk"
    assert res["normality_test"]["is_normal"] is False
    assert res["normality_test"]["alpha"] == 0.05

def test_assumption_zero_variance_no_division_by_zero():
    vals = [50.02, 50.02, 50.02, 50.02, 50.02]
    res = capability_engine.calculate_capability(vals, usl=50.05, lsl=49.95)

    assert res["status"] == "zero_variance"
    assert res["cp"] is None
    assert res["cpk"] is None
    assert res["pp"] is None
    assert res["ppk"] is None
    assert any("ZERO/NEAR-ZERO VARIANCE" in w for w in res["warnings"])

def test_assumption_process_drift_detected():
    vals = [50.00 + 0.005 * i for i in range(10)]
    res = capability_engine.calculate_capability(vals, usl=50.05, lsl=49.95)

    assert res["trend_test"]["is_trending"] is True
    assert any("PROCESS DRIFT DETECTED" in w for w in res["warnings"])

def test_assumption_outliers_detected():
    rng = np.random.RandomState(42)
    vals = [round(float(x), 4) for x in rng.normal(50.00, 0.005, 30)]
    vals[15] = 50.035
    res = capability_engine.calculate_capability(vals, usl=50.05, lsl=49.95)

    assert 15 in res["outliers"]
    assert any("OUTLIERS DETECTED" in w for w in res["warnings"])

def test_assumption_heterogeneous_machines_and_batches():
    vals = [50.01, 50.02, 50.01, 50.02, 50.03]
    res = capability_engine.calculate_capability(
        vals,
        usl=50.05,
        lsl=49.95,
        machine_ids=["CNC-01", "CNC-01", "CNC-02", "CNC-02", "CNC-03"],
        batch_ids=["BATCH-01", "BATCH-01", "BATCH-02", "BATCH-02", "BATCH-02"]
    )
    assert any("HETEROGENEOUS DATA SOURCE: Dataset contains measurements combined across multiple machines" in w for w in res["warnings"])
    assert any("HETEROGENEOUS DATA SOURCE: Dataset contains measurements combined across multiple batches" in w for w in res["warnings"])

def test_assumption_missing_and_invalid_specification_limits():
    vals = [50.01, 50.02, 50.03, 50.04, 50.05]
    res_missing = capability_engine.calculate_capability(vals, usl=None, lsl=None)
    assert res_missing["status"] == "missing_spec_limits"
    assert any("MISSING SPECIFICATION LIMITS" in w for w in res_missing["warnings"])

    res_invalid = capability_engine.calculate_capability(vals, usl=49.90, lsl=50.10)
    assert res_invalid["status"] == "invalid_spec_limits"
    assert any("INVALID SPECIFICATION LIMITS" in w for w in res_invalid["warnings"])

def test_interpretation_bands_and_confidence_interval():
    vals = [50.01, 50.03, 50.06, 50.08, 50.07]
    res = capability_engine.calculate_capability(vals, usl=50.05, lsl=49.95)

    assert "AIAG" in res["benchmark_source"]
    assert "IATF 16949" in res["benchmark_source"]
    assert "DECISION GUIDANCE ONLY" in res["guidance_notice"]
    assert "DISCLAIMER" in res["future_guarantee_disclaimer"]
    assert res["label"] == "STATISTICAL_FINDING"

    ci = res["cpk_ci_95"]
    assert ci is not None
    assert ci["confidence_level"] == 0.95
    assert "wide due to small sample size" in ci["note"]

def test_llm_garbage_mock_immunity_agent_5():
    garbage_llm_payload = '{"cp": 99.9, "cpk": 99.9, "status": "APPROVED", "decision": "ACCEPT"}'

    with patch("backend.app.core.llm.universal_llm.chat", return_value=garbage_llm_payload):
        res = spc_agent.analyze_process_capability_and_control(
            batch_id="BATCH-0245",
            values=[50.01, 50.03, 50.06, 50.08, 50.07],
            usl=50.05,
            lsl=49.95,
            nominal=50.00
        )
        rep = res["report"]
        assert rep.cp == 0.9400
        assert rep.cpk == 0.0
        assert rep.pp == 0.5717
        assert rep.ppk == 0.0
        assert rep.sample_size == 5
        assert len(rep.warnings) > 0

def test_spc_results_database_persistence():
    response = client.get("/api/spc/analyze?batch_id=BATCH-0245")
    assert response.status_code == 200

    db = SessionLocal()
    try:
        from backend.app.database.models import Batch
        batch = db.query(Batch).filter((Batch.batch_number == "BATCH-0245") | (Batch.id == "BATCH-0245")).first()
        target_id = batch.id if batch else "BATCH-0245"
        spc_rec = db.query(SPCResult).filter((SPCResult.batch_id == target_id) | (SPCResult.batch_id == "BATCH-0245")).first()
        assert spc_rec is not None
        assert spc_rec.cp is not None
        assert spc_rec.cpk is not None
        assert spc_rec.n == 5
    finally:
        db.close()

def test_pdf_report_renders_capability_and_warnings():
    state_mock = {
        "batch_id": "BATCH-0245",
        "batch_metadata": {"batch_id": "BATCH-0245", "lsl": 49.95, "usl": 50.05, "nominal_mm": 50.00},
        "spc_report": {
            "cp": 0.9400,
            "cpk": 0.0,
            "pp": 0.5717,
            "ppk": 0.0,
            "ucl": 50.103,
            "lcl": 49.997,
            "cl": 50.05,
            "warnings": [
                "PRELIMINARY SAMPLE SIZE: Sample size n=5 is below standard threshold (n>=30).",
                "OUT-OF-CONTROL PROCESS: Process exhibits special cause variation."
            ],
            "future_guarantee_disclaimer": "DISCLAIMER: Historical statistical indicator only."
        }
    }
    pdf_bytes = generate_quality_pdf_report(state_mock)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")

def test_api_spc_capability_get_batch_0245():
    response = client.get("/api/spc/capability?batch_id=BATCH-0245")
    assert response.status_code == 200
    data = response.json()
    assert data["batch_id"] == "BATCH-0245"
    assert data["sample_size"] == 5
    assert data["cp"] == 0.9400
    assert data["cpk"] == 0.0
    assert data["pp"] == 0.5717
    assert data["ppk"] == 0.0
    assert len(data["warnings"]) > 0

def test_api_spc_capability_post_custom_sufficient_and_insufficient():
    resp_insuf = client.post("/api/spc/capability", json={
        "batch_id": "TEST-INSUF",
        "values": [50.01, 50.02, 50.03],
        "usl": 50.05,
        "lsl": 49.95
    })
    assert resp_insuf.status_code == 200
    d_insuf = resp_insuf.json()
    assert d_insuf["status"] == "insufficient_data"
    assert d_insuf["cp"] is None
    assert d_insuf["cpk"] is None
    assert len(d_insuf["warnings"]) > 0

    rng = np.random.RandomState(42)
    suf_vals = [round(float(x), 4) for x in rng.normal(50.00, 0.01, 35)]
    resp_suf = client.post("/api/spc/capability", json={
        "batch_id": "TEST-SUF",
        "values": suf_vals,
        "usl": 50.05,
        "lsl": 49.95
    })
    assert resp_suf.status_code == 200
    d_suf = resp_suf.json()
    assert d_suf["status"] == "sufficient"
    assert d_suf["cp"] is not None
    assert d_suf["cpk"] is not None
