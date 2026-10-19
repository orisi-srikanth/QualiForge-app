import pytest
from tests.test_cases.fixtures import get_tc06_fixture, get_tc06_negative_control
from backend.app.agents.quality_knowledge_agent import quality_knowledge_agent
from backend.app.agents.rca_agent import rca_agent

def test_tc06_similar_ncr_retrieval_and_epistemic_isolation():
    fixture = get_tc06_fixture()
    
    res = quality_knowledge_agent.query(
        query_text=fixture["query"],
        top_k=3
    )
    matches = res.get("matches", [])
    assert len(matches) > 0, "RAG collection must return retrieved matches"
    
    matched_ids = [m.get("record_id") or m.get("metadata", {}).get("record_id", "") for m in matches]
    matched_titles = [m.get("title", "") for m in matches]
    ncr_019_found = any("NCR-019" in str(mid) for mid in matched_ids) or any("019" in str(t) for t in matched_titles)
    assert ncr_019_found, f"NCR-019 must be in top 3 retrieved results, got {matched_ids}"
    
    ncr_match = [m for m in matches if "NCR-019" in str(m.get("record_id") or "")][0]
    assert ncr_match.get("similarity_score") is not None, "Similarity score must be reported"
    assert ncr_match.get("similarity_score") > 0.60, f"Similarity score must be substantial (>0.60), got {ncr_match.get('similarity_score')}"
    
    rca_res = rca_agent.analyze_incident(
        incident_id="INC-TC06",
        batch_id="BATCH-0245",
        defect_type="Oversized shaft diameter",
        max_measured_val=50.08,
        usl=50.05,
        vibration_val=3.8,
        tool_cycles=1150
    )
    rca_report = rca_res["report"]
    
    assert rca_report.historical_matches is not None
    assert len(rca_report.historical_matches) > 0
    top_hist = rca_report.historical_matches[0]
    assert "NCR-019" in top_hist.incident_id, "Top historical incident in RCA report must be NCR-019"
    
    context_disclaimer = getattr(top_hist, "disclaimer", "") or getattr(rca_report, "correlation_vs_causation_note", "")
    assert "causation" in context_disclaimer.lower() or "not establish" in context_disclaimer.lower() or "historical" in context_disclaimer.lower(), (
        "Report must explicitly state historical context does not establish current root cause"
    )
    
    assert rca_report.ranked_hypotheses[0].epistemic_label == "HYPOTHESIS", (
        f"Hypothesis label must be HYPOTHESIS, got {rca_report.ranked_hypotheses[0].epistemic_label}"
    )

def test_tc06_negative_control_unrelated_query():
    neg_fixture = get_tc06_negative_control()
    res = quality_knowledge_agent.query(
        query_text=neg_fixture["query"],
        top_k=3
    )
    matches = res.get("matches", [])
    if matches:
        top_mid = matches[0].get("record_id") or ""
        assert "NCR-019" not in top_mid, f"Unrelated carton query should not have NCR-019 as #1 match, got {top_mid}"
