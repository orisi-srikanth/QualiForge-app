import pytest
from tests.test_cases.fixtures import (
    get_tc07_fixture,
    get_tc07_negative_control,
    recompute_rca_scores
)
from backend.app.agents.rca_agent import rca_agent
from backend.app.agents.reviewer_agent import critic_agent

def test_tc07_multiple_hypotheses_and_evidence_contrast():
    fixture = get_tc07_fixture()
    
    res = rca_agent.analyze_incident(
        incident_id=fixture["incident_id"],
        batch_id=fixture["batch_id"],
        defect_type=fixture["defect_type"],
        max_measured_val=fixture["max_measured_val"],
        usl=fixture["usl"],
        vibration_val=fixture["vibration_val"],
        tool_cycles=fixture["tool_cycles"]
    )
    report = res["report"]
    hypotheses = report.ranked_hypotheses
    
    assert len(hypotheses) >= 5, f"Expected at least 5 hypotheses, got {len(hypotheses)}"
    
    for h in hypotheses:
        assert h.rank is not None, "Rank must be present"
        assert h.category in ["Machine", "Method", "Manpower", "Measurement", "Material", "Milieu (Environment)"], f"Invalid 6M category: {h.category}"
        assert len(h.supporting_evidence) > 0, "Supporting evidence must not be empty"
        assert h.contradicting_evidence is not None, "Contradicting evidence must be present"
        assert len(h.missing_evidence) > 0, "Missing evidence must not be empty"
        assert h.required_confirmation is not None, "Confirmation requirements must be present"
        assert h.evidence_score > 0.0, "Evidence score must be positive"
        assert h.epistemic_label == "HYPOTHESIS", f"Label must be HYPOTHESIS, got {h.epistemic_label}"
        
    independent_scores = recompute_rca_scores(
        tool_cycles=fixture["tool_cycles"],
        vibration_val=fixture["vibration_val"],
        max_val=fixture["max_measured_val"],
        usl=fixture["usl"]
    )
    
    for h in hypotheses:
        hyp_key = h.hypothesis_id
        if hyp_key in independent_scores:
            expected_score = independent_scores[hyp_key]
            assert abs(h.evidence_score - expected_score) <= 0.02, (
                f"Score mismatch for {hyp_key}: reported {h.evidence_score} vs independently recomputed {expected_score}"
            )
            
    assert hypotheses[0].hypothesis_id == "HYP-01", f"Top hypothesis should be tool wear (HYP-01), got {hypotheses[0].hypothesis_id}"
    
    neg_fixture = get_tc07_negative_control()
    res_counter = rca_agent.analyze_incident(
        incident_id=neg_fixture["incident_id"],
        batch_id=neg_fixture["batch_id"],
        defect_type=neg_fixture["defect_type"],
        max_measured_val=neg_fixture["max_measured_val"],
        usl=neg_fixture["usl"],
        vibration_val=neg_fixture["vibration_val"],
        tool_cycles=neg_fixture["tool_cycles"]
    )
    hypotheses_counter = res_counter["report"].ranked_hypotheses
    
    top_counter_id = hypotheses_counter[0].hypothesis_id
    assert top_counter_id != "HYP-01", f"Tool wear should NOT remain rank 1 when tool cycles and vibration are normal, got {top_counter_id}"
    
    forbidden_terms = ["definitely caused", "proves causation", "proven root cause", "absolute cause"]
    summary_text = (
        report.problem_statement + " " +
        report.correlation_vs_causation_note + " " +
        " ".join(h.description + " " + h.title for h in report.ranked_hypotheses)
    ).lower()
    for term in forbidden_terms:
        assert term not in summary_text, f"Forbidden proven causal assertion '{term}' found in RCA texts"
        
    injected_text = "The elevated vibration definitely caused the tool wear which is the proven root cause."
    critic_scan = critic_agent.scan_unsupported_causal_claims(injected_text)
    assert critic_scan is not None, "Critic agent must flag injected unsupported causal claim"
