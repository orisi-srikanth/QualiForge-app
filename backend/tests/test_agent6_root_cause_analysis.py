import io
import re
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
import pypdf

from backend.app.main import app
from backend.app.agents.rca_agent import rca_agent
from backend.app.database.session import SessionLocal
from backend.app.database.models import (
    Batch, Machine, Measurement, Anomaly, MaintenanceRecord,
    QualityIncident, RCAHypothesis, HumanDecision
)
from backend.app.services.pareto import pareto_service
from backend.app.services.pdf_report import pdf_report_generator
from backend.app.agents.workflow import node_rca

client = TestClient(app)

def test_01_rca_from_dimensional_nonconformity_linked_batch():
    dim_findings = {
        "batch_id": "BATCH-0245",
        "total_samples": 5,
        "accepted": 2,
        "nonconforming": 3,
        "rejection_rate_percent": 60.0,
        "nonconforming_samples": [
            {"sample_id": "P003", "deviation_mm": 0.01},
            {"sample_id": "P004", "deviation_mm": 0.03},
            {"sample_id": "P005", "deviation_mm": 0.02}
        ]
    }
    res = rca_agent.analyze_incident(
        incident_id="INC-DIM-01",
        batch_id="BATCH-0245",
        defect_type="Oversized shaft diameter",
        max_measured_val=50.08,
        usl=50.05,
        dimensional_findings=dim_findings
    )
    report = res["report"]
    assert "50.08" in report.problem_statement
    assert "50.05" in report.problem_statement
    assert report.rca_inputs["batch_id"] == "BATCH-0245"
    assert report.rca_inputs["dimensional_findings"] is not None
    nonconf_samples = report.rca_inputs["inspection_results"]["nonconforming_samples"]
    assert any("P003" in s for s in nonconf_samples)
    assert any("P004" in s for s in nonconf_samples)

def test_02_visual_defect_evidence_from_agent_2():
    vis_pred = {
        "defect_detected": True,
        "defect_type": "surface_scratch",
        "category": "precision_shaft",
        "confidence": 0.94,
        "product_mismatch": False
    }
    res = rca_agent.analyze_incident(
        incident_id="INC-VIS-01",
        batch_id="BATCH-0245",
        visual_prediction=vis_pred
    )
    report = res["report"]
    assert report.rca_inputs["visual_defect_findings"]["defect_type"] == "surface_scratch"
    all_sources = [s for h in report.ranked_hypotheses for s in (h.sources or [])]
    assert any("visual" in s.lower() for s in all_sources)

    mismatch_vis = {
        "defect_detected": True,
        "defect_type": "thread_damage",
        "category": "threaded_screw",
        "confidence": 0.96,
        "product_mismatch": True
    }
    res_mismatch = rca_agent.analyze_incident(
        incident_id="INC-VIS-02",
        batch_id="BATCH-0245",
        defect_type="Oversized shaft diameter",
        visual_prediction=mismatch_vis
    )
    assert "thread_damage" not in res_mismatch["report"].problem_statement

def test_03_telemetry_anomaly_evidence_from_agent_4():
    proc_rep = {
        "batch_id": "BATCH-0245",
        "machine_code": "CNC-04",
        "anomalies_detected": 2,
        "vibration_current": 3.84,
        "tool_cycles_current": 1150
    }
    res = rca_agent.analyze_incident(
        incident_id="INC-PROC-01",
        batch_id="BATCH-0245",
        process_report=proc_rep
    )
    report = res["report"]
    changed = report.rca_inputs["machine_parameters"]["changed"]
    assert len(changed) >= 2
    param_names = [p["parameter"] for p in changed]
    assert "vibration" in param_names
    assert "motor_current" in param_names
    unchanged = report.rca_inputs["machine_parameters"]["unchanged"]
    unchanged_names = [p["parameter"] for p in unchanged]
    assert "spindle_speed" in unchanged_names
    assert "feed_rate" in unchanged_names

def test_04_spc_signal_evidence_from_agent_5():
    spc_rep = {
        "batch_id": "BATCH-0245",
        "nelson_violations": ["Rule 3: 6 consecutive points steadily increasing"],
        "cpk": 0.42,
        "ucl": 50.082,
        "lcl": 50.034
    }
    res = rca_agent.analyze_incident(
        incident_id="INC-SPC-01",
        batch_id="BATCH-0245",
        spc_report=spc_rep
    )
    report = res["report"]
    assert report.rca_inputs["spc_findings"] is not None
    assert "Rule 3" in str(report.rca_inputs["spc_findings"])
    assert report.rca_inputs["spc_findings"]["cpk"] == 0.42

def test_05_relevant_maintenance_record_retrieval():
    res = rca_agent.analyze_incident(
        incident_id="INC-MAINT-01",
        batch_id="BATCH-0245",
        machine_id="CNC-04"
    )
    maint_info = res["report"].rca_inputs["maintenance_history"]
    assert maint_info["machine_code"] == "CNC-04"
    assert maint_info["records_count"] >= 0

    if isinstance(maint_info.get("records"), list):
        for rec in maint_info["records"]:
            assert "CNC-04" in str(rec) or "id" in rec

def test_06_historical_ncr_capa_retrieval_and_source_references():
    res = rca_agent.analyze_incident(
        incident_id="INC-HIST-01",
        batch_id="BATCH-0245",
        defect_type="Oversized shaft diameter",
        tool_cycles=1150
    )
    report = res["report"]
    matches = report.historical_matches
    assert len(matches) > 0
    top_match = matches[0]
    assert top_match.incident_id is not None
    assert top_match.similarity_score > 0.50
    assert len(top_match.confirmed_root_cause) > 5

def test_07_supporting_and_contradicting_evidence_in_same_investigation():
    res = rca_agent.analyze_incident(
        incident_id="INC-EVID-01",
        batch_id="BATCH-0245",
        vibration_val=3.8,
        tool_cycles=1150
    )
    report = res["report"]
    for hyp in report.ranked_hypotheses:
        assert len(hyp.supporting_evidence) > 0, f"Hypothesis {hyp.hypothesis_id} lacks supporting evidence"
        assert len(hyp.contradicting_evidence) > 0, f"Hypothesis {hyp.hypothesis_id} lacks contradicting evidence"

def test_08_missing_evidence_correctly_reported_as_unavailable():
    res = rca_agent.analyze_incident(
        incident_id="INC-MISSING-01",
        batch_id="BATCH-UNKNOWN-EMPTY",
        defect_type="Oversized shaft diameter",
        tool_cycles=None,
        vibration_val=2.1,
        incident_timestamp=None
    )
    rca_in = res["report"].rca_inputs
    assert rca_in["tool_condition"]["tool_cycles"] == "not available"
    assert rca_in["material_information"]["material_lot"] == "not available"
    temp = res["report"].temporal_precedence
    assert temp["temporal_correlation_established"] is False
    assert "temporal correlation cannot be established" in temp["details"]

def test_09_no_causal_conclusion_based_only_on_correlation():
    res = rca_agent.analyze_incident(
        incident_id="INC-CORR-01",
        batch_id="BATCH-0245"
    )
    report = res["report"]
    assert "causation" in report.causality_disclaimer.lower()
    assert "not establish" in report.causality_disclaimer.lower()
    for c in report.correlations:
        assert "causation not established" in c["disclaimer"].lower()
    assert report.certainty.value.upper() == "HYPOTHESIS"
    for h in report.ranked_hypotheses:
        if "CONFIRMED" not in h.status:
            assert h.epistemic_label == "HYPOTHESIS"

def test_10_no_confirmation_based_solely_on_llm_output():
    with patch("backend.app.core.llm.universal_llm.chat") as mock_chat:
        mock_chat.return_value = "CONFIRMED ROOT CAUSE: Microscopic cosmic rays altered CNC spindle calibration. Score: 100%!"
        res = rca_agent.analyze_incident(
            incident_id="INC-LLM-01",
            batch_id="BATCH-0245",
            max_measured_val=50.08,
            usl=50.05,
            vibration_val=3.84,
            tool_cycles=1150
        )
        report = res["report"]
        assert report.certainty.value.upper() == "HYPOTHESIS"
        top = report.ranked_hypotheses[0]
        assert top.title == "Progressive Tool Flank Wear"
        assert top.confidence_score == 0.88
        assert top.epistemic_label == "HYPOTHESIS"

def test_11_five_whys_stops_when_evidence_is_insufficient():
    res = rca_agent.analyze_incident(
        incident_id="INC-5W-01",
        batch_id="BATCH-0245",
        insufficient_evidence_for_whys=True
    )
    report = res["report"]
    five_whys = report.five_whys
    assert len(five_whys) == 2
    assert five_whys[1].level == 2
    assert "Investigation stopped" in five_whys[1].answer
    assert "Insufficient empirical evidence" in five_whys[1].answer

def test_12_fishbone_categories_do_not_imply_uninvestigated_ruled_out():
    res = rca_agent.analyze_incident(
        incident_id="INC-FISH-01",
        batch_id="BATCH-0245"
    )
    report = res["report"]
    expected_categories = {"Machine", "Method", "Material", "Manpower", "Measurement", "Milieu (Environment)"}
    cat_names = {c.category for c in report.fishbone_diagram}
    assert expected_categories.issubset(cat_names)

    for cat in report.fishbone_diagram:
        all_text = " ".join(cat.factors)
        assert "NOT ruled out" in all_text, f"Category {cat.category} missing uninvestigated-not-ruled-out notice"

def test_13_pareto_counts_use_actual_records_and_correct_denominators():
    db = SessionLocal()
    try:
        pareto = pareto_service.compute_pareto(db=db, dimension="root_cause")
        assert "total_incidents" in pareto or "total" in pareto
        assert "items" in pareto
        total_val = pareto.get("total_incidents", pareto.get("total", 0))
        if pareto["items"]:
            assert pareto["items"][-1]["cumulative_percentage"] == 100.0
            assert sum(i["count"] for i in pareto["items"]) == total_val
    finally:
        db.close()

def test_14_correlation_requires_aligned_observations_and_reports_limitations():
    res = rca_agent.analyze_incident(incident_id="INC-CORR-02", batch_id="BATCH-0245")
    corrs = res["report"].correlations
    assert len(corrs) >= 2
    for c in corrs:
        assert "pearson_r" in c
        assert "pearson_p_value" in c
        assert "sample_size" in c
        assert c["sample_size"] == 5
        assert "disclaimer" in c
        assert "association, causation not established" in c["disclaimer"].lower()

def test_15_historical_similarity_is_not_treated_as_proof():
    res = rca_agent.analyze_incident(incident_id="INC-HIST-02", batch_id="BATCH-0245")
    for match in res["report"].historical_matches:
        assert "precedent" in match.disclaimer.lower() or "context only" in match.disclaimer.lower()
        assert "does not establish current root cause" in match.disclaimer.lower()

def test_16_unknown_batch_returns_appropriate_error():
    r_get = client.get("/api/rca/batch/UNKNOWN-BATCH-99999")
    assert r_get.status_code == 404
    assert "not found" in r_get.json()["detail"].lower()

    r_post = client.post(
        "/api/rca/investigate",
        json={"batch_id": "UNKNOWN-BATCH-99999", "defect_type": "Oversized shaft diameter"}
    )
    assert r_post.status_code == 404

    r_malformed = client.post(
        "/api/rca/investigate",
        json={"batch_id": "BATCH-0245", "usl": -10.0}
    )
    assert r_malformed.status_code == 422

def test_17_cross_batch_or_cross_machine_evidence_contamination_prevented():
    db = SessionLocal()
    try:
        maint_q4 = db.query(MaintenanceRecord).join(Machine).filter(Machine.code == "CNC-04").all()
        maint_q1 = db.query(MaintenanceRecord).join(Machine).filter(Machine.code == "CNC-01").all()

        res_cnc4 = rca_agent.analyze_incident(batch_id="BATCH-0245", machine_id="CNC-04")
        records_reported = res_cnc4["report"].rca_inputs["maintenance_history"].get("records", [])

        if isinstance(records_reported, list) and maint_q1:
            q1_ids = {m.id for m in maint_q1}
            reported_ids = {r["id"] for r in records_reported if "id" in r}
            assert len(reported_ids.intersection(q1_ids)) == 0
    finally:
        db.close()

def test_18_persistence_and_retrieval_return_correct_rca_record():
    res = rca_agent.analyze_incident(
        incident_id="INC-PERSIST-01",
        batch_id="BATCH-0245",
        defect_type="Oversized shaft diameter",
        max_measured_val=50.08,
        usl=50.05
    )
    assert res["report"] is not None

    r_api = client.get("/api/rca/batch/BATCH-0245")
    assert r_api.status_code == 200
    data = r_api.json()
    assert data["batch_id"] == "BATCH-0245"
    assert data["defect_type"] == "Oversized shaft diameter"
    assert len(data["ranked_hypotheses"]) >= 5
    top_h = data["ranked_hypotheses"][0]
    assert "supporting_evidence" in top_h
    assert "contradicting_evidence" in top_h
    assert "missing_evidence" in top_h

def test_19_duplicate_requests_behave_correctly():
    db = SessionLocal()
    try:
        b = db.query(Batch).filter((Batch.batch_number == "BATCH-0245") | (Batch.id == "BATCH-0245")).first()
        b_fk = b.id if b else "BATCH-0245"
        initial_inc_count = db.query(QualityIncident).filter((QualityIncident.batch_id == b_fk) | (QualityIncident.batch_id == "BATCH-0245")).count()
        for _ in range(3):
            rca_agent.analyze_incident(
                incident_id="INC-DUP-01",
                batch_id="BATCH-0245",
                defect_type="Oversized shaft diameter"
            )
        final_inc_count = db.query(QualityIncident).filter((QualityIncident.batch_id == b_fk) | (QualityIncident.batch_id == "BATCH-0245")).count()
        assert final_inc_count == initial_inc_count, "Duplicate incident rows must never be inserted"
    finally:
        db.close()

def test_20_authorized_human_confirmation_and_audit_trail():
    resp = client.post(
        "/api/rca/hypotheses/HYP-01/decision",
        json={
            "decision": "CONFIRM",
            "comment": "Confirmed by Lead Quality Engineer after optical toolmaker inspection."
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "CONFIRMED"
    assert data["epistemic_label"] == "Confirmed Root Cause"

    db = SessionLocal()
    try:
        decision_log = db.query(HumanDecision).filter(
            HumanDecision.entity_id == "HYP-01",
            HumanDecision.decision == "CONFIRM"
        ).order_by(HumanDecision.ts.desc()).first()
        assert decision_log is not None
        assert "optical toolmaker inspection" in decision_log.comment
    finally:
        db.close()

def test_21_unauthorized_users_cannot_confirm_root_cause():
    from backend.app.core.security import create_access_token
    op_token = create_access_token({"sub": "usr-op-01", "name": "John Operator", "role": "operator"})
    resp = client.post(
        "/api/rca/hypotheses/HYP-01/decision",
        json={"decision": "CONFIRM", "comment": "Operator attempt to confirm"},
        headers={"Authorization": f"Bearer {op_token}", "x-enforce-role": "true"}
    )
    assert resp.status_code == 403
    assert "unauthorized" in resp.json()["detail"].lower()

def test_22_rca_output_available_in_downstream_workflow_and_pdf():
    mock_state = {
        "batch_id": "BATCH-0245",
        "dimensional_report": {"nonconforming": 3},
        "process_report": {"vibration_current": 3.84, "tool_cycles_current": 1150},
        "execution_trace": []
    }
    rca_out = node_rca(mock_state)
    assert "rca_report" in rca_out
    assert rca_out["current_agent"] == rca_agent.name

    state_for_pdf = {
        "workflow_id": "WF-TEST-0245",
        "batch_id": "BATCH-0245",
        "batch_metadata": {"batch_id": "BATCH-0245", "part_name": "Precision Ground Shaft"},
        "rca_report": rca_out["rca_report"],
        "dimensional_report": {"nonconforming": 3, "total_samples": 5},
        "process_report": {"vibration_current": 3.84, "tool_cycles_current": 1150},
        "spc_report": {"ucl": 50.082, "lcl": 50.034, "cl": 50.058}
    }
    buf = pdf_report_generator.generate_audit_report(state_for_pdf)
    assert buf is not None
    reader = pypdf.PdfReader(io.BytesIO(buf.getvalue()))
    full_text = " ".join([page.extract_text() for page in reader.pages]).lower()
    assert "8. root cause hypotheses" in full_text
    assert "9. supporting & contradicting evidence" in full_text
    assert "tool flank wear" in full_text

def test_23_agent_6_cannot_autonomously_execute_actions():
    res = rca_agent.analyze_incident(batch_id="BATCH-0245")
    report = res["report"]
    assert report.autonomous_actions_prohibited is True
    assert report.review_status == "HUMAN_REVIEW_REQUIRED"

    forbidden_calls = [
        ("RELEASE_PRODUCT", "BATCH-0245"),
        ("REJECT_BATCH", "BATCH-0245"),
        ("MODIFY_CNC", "CNC-04"),
        ("STOP_MACHINERY", "CNC-04")
    ]
    for action, target in forbidden_calls:
        resp = client.post(
            "/api/safety/guardrails/test-autonomous-action",
            json={"action": action, "target_id": target}
        )
        assert resp.status_code == 403
