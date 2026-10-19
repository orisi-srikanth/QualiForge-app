import pytest
from tests.test_cases.fixtures import (
    get_tc08_fixture,
    get_tc08_negative_control,
    recompute_two_proportion_z
)
from backend.app.services.effectiveness import effectiveness_engine
from backend.app.database.session import SessionLocal
from backend.app.database.models import CAPAAction, EffectivenessCheck

def test_tc08_effectiveness_monitoring_and_statistical_test():
    fixture = get_tc08_fixture()
    action_code = fixture["action_code"]
    
    eff_res = effectiveness_engine.evaluate_capa_effectiveness(
        capa_id=action_code,
        n_before=fixture["sample_before"],
        defects_before=fixture["defects_before"],
        n_after=fixture["sample_after"],
        defects_after=fixture["defects_after"]
    )
    
    independent_stats = recompute_two_proportion_z(
        n1=fixture["sample_before"],
        x1=fixture["defects_before"],
        n2=fixture["sample_after"],
        x2=fixture["defects_after"]
    )
    
    assert eff_res["rejection_rate_before_percent"] == 8.2, f"Expected 8.2% before, got {eff_res['rejection_rate_before_percent']}"
    assert eff_res["rejection_rate_after_percent"] == 1.1, f"Expected 1.1% after, got {eff_res['rejection_rate_after_percent']}"
    assert eff_res["sample_before_count"] == 1000
    assert eff_res["sample_after_count"] == 1000
    
    reported_z = round(eff_res["z_statistic"], 2)
    expected_z = independent_stats["z_statistic"]
    assert abs(reported_z - expected_z) <= 0.05, f"Z-stat mismatch: reported {reported_z} vs recomputed {expected_z}"
    assert eff_res["p_value"] < 0.0001, f"P-value must be < 0.0001, got {eff_res['p_value']}"
    
    ci_diff = eff_res["confidence_interval_diff_percent"]
    assert ci_diff is not None and len(ci_diff) == 2
    assert abs(ci_diff[0] - independent_stats["ci_95"][0]) <= 0.20, f"CI lower bound mismatch: {ci_diff[0]} vs {independent_stats['ci_95'][0]}"
    assert abs(ci_diff[1] - independent_stats["ci_95"][1]) <= 0.20, f"CI upper bound mismatch: {ci_diff[1]} vs {independent_stats['ci_95'][1]}"
    
    conclusion = eff_res.get("conclusion_label", "").lower()
    assert "observed association" in conclusion, f"Conclusion missing 'observed association': {conclusion}"
    assert "causation not established" in conclusion, f"Conclusion missing 'causation not established': {conclusion}"
    
    db = SessionLocal()
    try:
        capa_rec = db.query(CAPAAction).filter(
            (CAPAAction.action_code == action_code) | (CAPAAction.id == action_code)
        ).first()
        if capa_rec:
            assert capa_rec.effectiveness_result is not None, "CAPAAction.effectiveness_result must be populated in DB"
    finally:
        db.close()

def test_tc08_negative_control_small_sample_warning():
    neg_fixture = get_tc08_negative_control()
    
    eff_res = effectiveness_engine.evaluate_capa_effectiveness(
        capa_id=neg_fixture["action_code"],
        n_before=neg_fixture["sample_before"],
        defects_before=neg_fixture["defects_before"],
        n_after=neg_fixture["sample_after"],
        defects_after=neg_fixture["defects_after"]
    )
    
    assert eff_res.get("is_small_sample") is True, "Small sample (n=15) must be flagged as small sample"
    assert eff_res.get("warning") is not None, "Warning must be present for small sample size"
    assert any(term in eff_res["warning"].lower() for term in ["small", "insufficient", "below", "too little data", "threshold"]), (
        f"Warning must explain sample size limitations, got '{eff_res.get('warning')}'"
    )
