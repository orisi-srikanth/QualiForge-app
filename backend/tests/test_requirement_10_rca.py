import re
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.agents.rca_agent import rca_agent
from backend.app.agents.reviewer_agent import critic_agent
from backend.app.agents.workflow import node_rca, route_after_spc, route_after_critic
from backend.app.schemas.schemas import HypothesisEvidence, CertaintyLevel
from backend.app.database.session import SessionLocal
from backend.app.database.models import QualityIncident, HumanDecision
from backend.app.scenarios.test_scenarios import run_test_scenario
from backend.app.services.rag_search import vector_store

client = TestClient(app)

def test_01_automatic_initiation_and_conforming_skip():
    conforming_state = {
        "batch_id": "BATCH-0001",
        "batch_metadata": {"batch_id": "BATCH-0001"},
        "measurements": [],
        "dimensional_report": {
            "batch_id": "BATCH-0001",
            "total_samples": 5,
            "accepted": 5,
            "nonconforming": 0,
            "rejection_rate_percent": 0.0,
            "nonconforming_samples": [],
            "tolerance_type": "bilateral"
        },
        "process_report": {
            "batch_id": "BATCH-0001",
            "machine_code": "CNC-01",
            "anomalies_detected": 0,
            "vibration_status": "NORMAL"
        },
        "has_defects": False,
        "has_anomalies": False,
        "has_spc_violations": False
    }
    assert route_after_spc(conforming_state) == "final_report"

    nonconforming_state = {
        "batch_id": "BATCH-0245",
        "batch_metadata": {"batch_id": "BATCH-0245"},
        "measurements": [],
        "dimensional_report": {
            "batch_id": "BATCH-0245",
            "total_samples": 5,
            "accepted": 2,
            "nonconforming": 3,
            "rejection_rate_percent": 60.0,
            "nonconforming_samples": [{"sample_id": "P003"}],
            "tolerance_type": "bilateral"
        },
        "process_report": {
            "batch_id": "BATCH-0245",
            "machine_code": "CNC-04",
            "anomalies_detected": 2,
            "vibration_status": "ABNORMAL_CRITICAL"
        },
        "has_defects": True,
        "has_anomalies": True,
        "has_spc_violations": True
    }
    assert route_after_spc(nonconforming_state) == "root_cause_analysis"

    db = SessionLocal()
    try:
        initial_count = db.query(QualityIncident).filter(QualityIncident.batch_id == "BATCH-0245").count()
        s1 = node_rca(nonconforming_state)
        merged = {**nonconforming_state, **s1}
        s2 = node_rca(merged)
        final_count = db.query(QualityIncident).filter(QualityIncident.batch_id == "BATCH-0245").count()
        assert final_count <= initial_count + 1, "Duplicate incident rows must not be created on re-run"
    finally:
        db.close()

def test_02_eight_inputs_present_and_not_available_fallback():
    res = rca_agent.analyze_incident(
        incident_id="INC-2026-088",
        batch_id="BATCH-0245",
        defect_type="Oversized shaft diameter",
        max_measured_val=50.08,
        usl=50.05,
        vibration_val=3.84,
        tool_cycles=1150
    )
    report = res["report"]
    rca_in = report.rca_inputs
    
    assert "defect_type" in rca_in
    assert "time_of_occurrence" in rca_in
    assert "machine_parameters" in rca_in
    assert "tool_condition" in rca_in
    assert "material_information" in rca_in
    assert "maintenance_history" in rca_in
    assert "previous_incidents" in rca_in
    assert "inspection_results" in rca_in
    
    empty_res = rca_agent.analyze_incident(
        incident_id="INC-EMPTY",
        batch_id="BATCH-EMPTY",
        defect_type="Oversized shaft diameter",
        max_measured_val=50.00,
        usl=50.05,
        vibration_val=2.1,
        tool_cycles=None
    )
    empty_in = empty_res["report"].rca_inputs
    assert empty_in["tool_condition"]["tool_cycles"] == "not available"
    assert empty_in["material_information"]["material_lot"] == "not available"

def test_03_five_pdf_hypotheses_and_schema():
    db = SessionLocal()
    try:
        db.query(HumanDecision).filter(HumanDecision.entity_id == "HYP-01").delete()
        db.commit()
    finally:
        db.close()

    res = rca_agent.analyze_incident(
        incident_id="INC-2026-088",
        batch_id="BATCH-0245",
        defect_type="Oversized shaft diameter",
        max_measured_val=50.08,
        usl=50.05,
        vibration_val=3.84,
        tool_cycles=1150
    )
    report = res["report"]
    titles = [h.title.lower() for h in report.ranked_hypotheses]
    
    assert any("tool" in t and "wear" in t for t in titles), "Missing Tool Wear hypothesis"
    assert any("offset" in t for t in titles), "Missing Tool Offset hypothesis"
    assert any("vibration" in t for t in titles), "Missing Machine Vibration hypothesis"
    assert any("fixture" in t for t in titles), "Missing Fixture Instability hypothesis"
    assert any("measurement" in t or "gauge" in t for t in titles), "Missing Measurement System Issue hypothesis"
    
    top = report.ranked_hypotheses[0]
    assert top.rank == 1
    assert top.category in ["Machine", "Method", "Material", "Man", "Measurement", "Environment"]
    assert len(top.supporting_evidence) > 0
    assert isinstance(top.contradicting_evidence, list)
    assert isinstance(top.missing_evidence, list)
    assert top.required_confirmation is not None and len(top.required_confirmation) > 5
    assert 0.0 <= (top.evidence_score or top.confidence_score) <= 1.0
    assert top.epistemic_label == "HYPOTHESIS"
    assert "requires engineering verification" in top.confidence_text.lower()

def test_04_evidence_traceability_concrete_sources():
    res = rca_agent.analyze_incident(
        incident_id="INC-2026-088",
        batch_id="BATCH-0245",
        defect_type="Oversized shaft diameter",
        max_measured_val=50.08,
        usl=50.05,
        vibration_val=3.84,
        tool_cycles=1150
    )
    report = res["report"]
    
    for h in report.ranked_hypotheses:
        assert h.sources is not None and len(h.sources) > 0, f"Hypothesis {h.title} must have concrete sources"

    top = report.ranked_hypotheses[0]
    all_supp_texts = " ".join(top.supporting_evidence)
    assert "1,150" in all_supp_texts or "1150" in all_supp_texts, "Tool usage 1,150 cycles must be cited"
    assert "600" in all_supp_texts, "Threshold 600 cycles must be cited"

def test_05_deterministic_scoring_and_counterfactual_shift():
    res_anchor = rca_agent.analyze_incident(
        incident_id="INC-2026-088",
        batch_id="BATCH-0245",
        defect_type="Oversized shaft diameter",
        max_measured_val=50.08,
        usl=50.05,
        vibration_val=3.84,
        tool_cycles=1150
    )
    top_anchor = res_anchor["report"].ranked_hypotheses[0]
    assert top_anchor.title == "Progressive Tool Flank Wear"
    assert (top_anchor.evidence_score or top_anchor.confidence_score) >= 0.85

    res_counterfactual = rca_agent.analyze_incident(
        incident_id="INC-CF",
        batch_id="BATCH-CF",
        defect_type="Oversized shaft diameter",
        max_measured_val=50.08,
        usl=50.05,
        vibration_val=2.10,
        tool_cycles=450
    )
    cf_hypotheses = res_counterfactual["report"].ranked_hypotheses
    tool_wear_cf = next(h for h in cf_hypotheses if "wear" in h.title.lower())
    score_cf = tool_wear_cf.evidence_score or tool_wear_cf.confidence_score
    assert score_cf <= 0.20, f"Expected Tool Wear score <= 0.20 under counterfactual, got {score_cf}"
    assert cf_hypotheses[0].title != "Progressive Tool Flank Wear"

def test_06_correlation_and_causation_guardrails():
    res = rca_agent.analyze_incident(
        incident_id="INC-2026-088",
        batch_id="BATCH-0245",
        defect_type="Oversized shaft diameter",
        max_measured_val=50.08,
        usl=50.05,
        vibration_val=3.84,
        tool_cycles=1150
    )
    report = res["report"]
    
    assert report.correlations is not None and len(report.correlations) > 0
    for corr in report.correlations:
        assert "pearson_p_value" in corr or "p_value" in corr
        assert "sample_size" in corr
        disclaimer = corr.get("disclaimer") or corr.get("notice", "")
        assert "association, not causation" in disclaimer.lower() or "causation not established" in disclaimer.lower()
        assert corr["sample_size"] == 5

    assert report.temporal_precedence is not None
    assert report.temporal_precedence.get("preceded_defect") is True

    forbidden_patterns = [
        re.compile(r"\broot cause is\b", re.IGNORECASE),
        re.compile(r"\bdefinitely caused\b", re.IGNORECASE),
        re.compile(r"\bproven root cause\b", re.IGNORECASE),
    ]
    texts_to_scan = [report.problem_statement]
    for h in report.ranked_hypotheses:
        texts_to_scan.append(h.description)
        texts_to_scan.append(h.confidence_text)
        texts_to_scan.extend(h.supporting_evidence)

    for txt in texts_to_scan:
        for pat in forbidden_patterns:
            matches = pat.findall(txt)
            assert len(matches) == 0, f"Found forbidden causal assertion matching '{pat.pattern}' in text: {txt}"

def test_07_techniques_implemented():
    res = rca_agent.analyze_incident(
        incident_id="INC-2026-088",
        batch_id="BATCH-0245",
        defect_type="Oversized shaft diameter",
        max_measured_val=50.08,
        usl=50.05,
        vibration_val=3.84,
        tool_cycles=1150
    )
    report = res["report"]
    
    categories = {cat.category for cat in report.fishbone_diagram}
    assert "Machine" in categories
    assert "Method" in categories
    assert "Material" in categories
    assert "Measurement" in categories

    assert len(report.five_whys) >= 4
    for why_item in report.five_whys:
        assert "hypothetical" in why_item.reasoning_type.lower() or "hypothesis" in why_item.epistemic_label.lower()

    assert report.pareto_causes is not None
    assert len(report.pareto_causes["items"]) >= 3

    assert len(report.correlations) >= 2

def test_08_historical_retrieval_and_disclaimer():
    matches = vector_store.search(
        query="Oversized shaft diameter tool wear CNC-04 1150 cycles",
        top_k=3
    )
    assert len(matches) > 0
    top_doc = matches[0]
    assert "NCR-019" in top_doc["id"] or "NCR-019" in top_doc["title"]
    assert "similarity_score" in top_doc

    r_api = client.get("/api/rca/rag-search?q=Oversized+shaft+diameter+tool+wear")
    assert r_api.status_code == 200
    retrieval_data = r_api.json()
    assert len(retrieval_data["matches"]) > 0

def test_09_human_control_rbac_and_logging():
    resp = client.post(
        "/api/rca/hypotheses/HYP-01/decision",
        json={"decision": "CONFIRM", "comment": "Verified under toolmakers microscope."}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "CONFIRMED"
    assert data["epistemic_label"] == "Confirmed Root Cause"

    db = SessionLocal()
    try:
        dec = db.query(HumanDecision).filter(HumanDecision.entity_id == "HYP-01").order_by(HumanDecision.ts.desc()).first()
        assert dec is not None
        assert dec.decision == "CONFIRM"
    finally:
        db.close()

def test_10_critic_fault_injection_and_reassess_loop():
    bad_claim = critic_agent.scan_unsupported_causal_claims("The out-of-tolerance condition was caused by operator error.")
    assert bad_claim is not None
    assert "caused by" in bad_claim.lower()

    faulty_rca = {
        "report": {
            "ranked_hypotheses": [
                {
                    "title": "Injected Premature Claim",
                    "status": "Confirmed",
                    "contradicting_evidence": [],
                    "required_confirmation": "None"
                }
            ]
        }
    }
    review_res = critic_agent.review_workflow(
        intake_data={},
        compliance_data={"report": {"nonconforming": 3, "tolerance_type": "bilateral"}},
        vision_data=None,
        anomaly_data={"report": {"anomalies_detected": 1}},
        spc_data={"report": {}},
        rca_data=faulty_rca,
        capa_data={"capa": {}}
    )
    rev = review_res["review"]
    assert rev.critic_verdict == "REASSESS", "Critic must request REASSESS on premature confirmation"

    faulty_state = {
        "batch_id": "BATCH-0245",
        "rca_report": faulty_rca,
        "critic_review": rev.model_dump(),
        "reassessment_loops": 0,
    }
    next_node = route_after_critic(faulty_state)
    assert next_node == "root_cause_analysis", "Graph must route back to RCA on REASSESS verdict"

def test_11_llm_nonsense_mock_robustness():
    with patch("backend.app.core.llm.universal_llm.chat") as mock_chat:
        mock_chat.return_value = "HAL9000: Alien space lasers caused dimensional drift! Score: 99999%"

        res = rca_agent.analyze_incident(
            incident_id="INC-2026-088",
            batch_id="BATCH-0245",
            defect_type="Oversized shaft diameter",
            max_measured_val=50.08,
            usl=50.05,
            vibration_val=3.84,
            tool_cycles=1150
        )
        report = res["report"]
        assert report.ranked_hypotheses[0].title == "Progressive Tool Flank Wear"
        assert (report.ranked_hypotheses[0].evidence_score or report.ranked_hypotheses[0].confidence_score) == 0.88
        assert report.ranked_hypotheses[1].title == "Spindle Harmonic Vibration and Bearing Play"
        assert (report.ranked_hypotheses[1].evidence_score or report.ranked_hypotheses[1].confidence_score) == 0.62

def test_12_tc07_multiple_potential_causes_end_to_end():
    res = run_test_scenario("TC-07")
    assert res["status"] in ["PASS", "SUCCESS", "PASSED"]
    assert "Ranked" in res["actual_result"]
