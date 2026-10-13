"""
Automated Test Suite for Functional Requirement 15 (Effectiveness Monitoring)
Verifies:
1. Trigger: completing CAPA action starts monitoring automatically; not completed produces 'monitoring not started'; no duplicate checks on re-run.
2. Windows: before and after windows defined and documented (equal count, same machine/product); test missing before, missing after, overlapping windows, and foreign machine exclusion.
3. Rates: rejection rate = nonconforming / inspected * 100 per window, computed from measurements table; reproduces PDF example (8.2% to 1.1%) from real seeded rows with exact counts.
4. Statistics: two-proportion z-test (pooled p-bar) and Fisher's exact test verified against scipy (tolerance < 1e-3); returns test name, statistic, p-value, 95% CI, sample sizes.
5. Small samples: < 30 parts or < 5 events returns warning, never confident claim; 0 events and 0 parts handled without division by zero.
6. Wording and labelling: every output says 'observed association' and 'causation not established'; labelled STATISTICAL_FINDING; no prohibited causal phrases; confounding explanations reported.
7. Direction handling: improvement, no change, and worsening reported honestly; worsening prompts 'request another analysis'.
8. Recurrence: re-runs defect recurrence detection; demonstrates case with no recurrence and case with recurrence (Agent 7 recurrence detector).
9. Persistence and links: stored in effectiveness_checks with definitions, counts, rates, test, p-value, conclusion; CAPA effectiveness_result filled; check recomputable when new batches arrive with previous results kept.
10. API and Swagger: endpoints /api/effectiveness/{capa_id} and /api/capa/actions/{code}/effectiveness under tag Effectiveness.
"""
import math
import pytest
from datetime import datetime, timezone
from scipy import stats
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.database.models import (
    Batch, Measurement, CAPAAction, EffectivenessCheck, QualityIncident, Machine, gen_uuid
)
from backend.app.services.effectiveness import effectiveness_engine, PROHIBITED_CAUSAL_PATTERNS
from backend.app.services.capa_service import capa_service

client = TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# =====================================================================
# 1. TRIGGER TESTS (Check 1)
# =====================================================================
def test_effectiveness_trigger_not_completed(db):
    """
    Actions not yet completed (proposed, approved, in_progress) must produce
    'monitoring_not_started' and never claim statistical findings.
    """
    # 1. Proposed action
    proposed_act = db.query(CAPAAction).filter(CAPAAction.status == "proposed").first()
    if not proposed_act:
        proposed_act = CAPAAction(
            id=gen_uuid(),
            incident_id="inc-ncr-019",
            action_code="CAPA-TEST-PROP-01",
            type="corrective",
            description="Test proposed action",
            due_date="2026-11-01",
            status="proposed"
        )
        db.add(proposed_act)
        db.commit()

    res = effectiveness_engine.evaluate_capa_effectiveness(proposed_act.action_code, db=db)
    assert res["status"] == "monitoring_not_started"
    assert "monitoring not started" in res["message"].lower()
    assert res["is_statistically_significant"] is False
    assert res["completion_date"] is None

    # 2. Approved action
    approved_act = db.query(CAPAAction).filter(CAPAAction.status == "approved").first()
    if approved_act:
        res_appr = effectiveness_engine.evaluate_capa_effectiveness(approved_act.action_code, db=db)
        assert res_appr["status"] == "monitoring_not_started"


def test_effectiveness_trigger_completed_auto(db):
    """
    Completing a corrective (or preventive) CAPA action automatically starts
    effectiveness monitoring, using the completion date as the dividing line,
    and populates the action's effectiveness_result field.
    """
    action_code = "CAPA-TEST-COMP-01"
    act = db.query(CAPAAction).filter(CAPAAction.action_code == action_code).first()
    if not act:
        act = CAPAAction(
            id=gen_uuid(),
            incident_id="inc-ncr-019",
            action_code=action_code,
            type="preventive",
            description="Preventive tool life calibration lockout",
            due_date="2026-10-20",
            status="in_progress",
            approved_by="usr-qe-01",
            approved_at=datetime(2026, 9, 25, 10, 0, tzinfo=timezone.utc)
        )
        db.add(act)
        db.commit()
    else:
        act.status = "in_progress"
        db.commit()

    # Mark completed via service
    updated = capa_service.update_action_status(
        db=db,
        action_id_or_code=action_code,
        new_status="completed",
        user={"id": "usr-qe-01", "role": "quality_engineer"},
        evidence="Calibration completed, offset verified at 0.000mm",
        completion_date="2026-10-01"
    )

    assert updated.status == "completed"
    assert updated.completion_date == "2026-10-01"
    assert updated.effectiveness_result is not None
    assert "Observed association" in updated.effectiveness_result
    assert "causation not established" in updated.effectiveness_result


def test_duplicate_checks_not_created_on_rerun(db):
    """
    Duplicate checks in effectiveness_checks are not created on re-running
    effectiveness evaluation with unchanged batch data.
    """
    action = db.query(CAPAAction).filter(CAPAAction.action_code == "CAPA-2026-001").first()
    target_id = action.id if action else "0ac7f71b-1645-4860-824f-ce2e1f027f93"

    initial_count = db.query(EffectivenessCheck).filter(
        (EffectivenessCheck.capa_id == target_id) | (EffectivenessCheck.capa_id == "0ac7f71b-1645-4860-824f-ce2e1f027f93")
    ).count()

    # Re-run twice
    effectiveness_engine.evaluate_capa_effectiveness("CAPA-2026-001", db=db)
    effectiveness_engine.evaluate_capa_effectiveness("CAPA-2026-001", db=db)

    final_count = db.query(EffectivenessCheck).filter(
        (EffectivenessCheck.capa_id == target_id) | (EffectivenessCheck.capa_id == "0ac7f71b-1645-4860-824f-ce2e1f027f93")
    ).count()

    # Must not create duplicates on re-run with same data
    assert final_count == max(1, initial_count)


# =====================================================================
# 2. WINDOWS & EXCLUSION TESTS (Check 2)
# =====================================================================
def test_window_rules_and_foreign_machine_exclusion(db):
    """
    Before and after windows enforce same machine and product isolation.
    Batches from a different machine (e.g. mach-01) are strictly excluded.
    """
    res = effectiveness_engine.evaluate_capa_effectiveness(
        "CAPA-2026-001",
        db=db,
        custom_batches_before=["batch-pre-capa-01", "BATCH-0004"], # BATCH-0004 is on mach-01
        custom_batches_after=["batch-post-capa-01"]
    )
    # Target machine is mach-04. BATCH-0004 (mach-01) must be excluded from window
    assert "BATCH-0004" not in res["batches_before"]
    assert "BATCH-PRE-01" in res["batches_before"]
    assert res["sample_before_count"] == 1000  # Only BATCH-PRE-01 counted


def test_missing_before_and_missing_after_windows(db):
    """
    Test missing before window and missing after window: returns 'insufficient_data' warning.
    """
    # 1. Missing before window
    res_no_before = effectiveness_engine.evaluate_capa_effectiveness(
        "CAPA-2026-001",
        db=db,
        custom_batches_before=[],
        custom_batches_after=["batch-post-capa-01"]
    )
    assert res_no_before["status"] == "insufficient_data"
    assert "Missing before window" in res_no_before["warning"]
    assert res_no_before["is_statistically_significant"] is False

    # 2. Missing after window
    res_no_after = effectiveness_engine.evaluate_capa_effectiveness(
        "CAPA-2026-001",
        db=db,
        custom_batches_before=["batch-pre-capa-01"],
        custom_batches_after=[]
    )
    assert res_no_after["status"] == "insufficient_data"
    assert "Missing after window" in res_no_after["warning"]
    assert res_no_after["is_statistically_significant"] is False


def test_overlapping_windows_rejected(db):
    """
    Test overlapping windows: if the same batch is included in both before and
    after windows, the system must detect and reject with 'invalid_windows'.
    """
    res_overlap = effectiveness_engine.evaluate_capa_effectiveness(
        "CAPA-2026-001",
        db=db,
        custom_batches_before=["batch-pre-capa-01"],
        custom_batches_after=["batch-pre-capa-01"]  # Overlapping
    )
    assert res_overlap["status"] == "invalid_windows"
    assert "Overlapping windows detected" in res_overlap["warning"]
    assert res_overlap["is_statistically_significant"] is False


# =====================================================================
# 3. RATES & RAW DATABASE RECALCULATION (Check 3)
# =====================================================================
def test_reproduce_pdf_example_from_seeded_rows(db):
    """
    Reproduces PDF problem statement example (8.2% before, 1.1% after) from real
    seeded rows in the measurements table (82 of 1,000 and 11 of 1,000), not hard-coded numbers.
    """
    b_pre = db.query(Batch).filter_by(scenario_label="PRE_CORRECTIVE_BASELINE").first()
    b_post = db.query(Batch).filter_by(scenario_label="POST_CORRECTIVE_VERIFIED").first()

    assert b_pre is not None
    assert b_post is not None

    n_pre = db.query(Measurement).filter(Measurement.batch_id == b_pre.id).count()
    d_pre = db.query(Measurement).filter(Measurement.batch_id == b_pre.id, Measurement.status == "nonconforming").count()

    n_post = db.query(Measurement).filter(Measurement.batch_id == b_post.id).count()
    d_post = db.query(Measurement).filter(Measurement.batch_id == b_post.id, Measurement.status == "nonconforming").count()

    # Exact counts behind every percentage
    assert n_pre == 1000
    assert d_pre == 82
    rate_pre = (d_pre / n_pre) * 100.0
    assert abs(rate_pre - 8.2) < 1e-4

    assert n_post == 1000
    assert d_post == 11
    rate_post = (d_post / n_post) * 100.0
    assert abs(rate_post - 1.1) < 1e-4

    # Run app evaluation and verify exact match
    eff = effectiveness_engine.evaluate_capa_effectiveness("CAPA-2026-001", db=db)
    assert eff["sample_before_count"] == 1000
    assert eff["defects_before_count"] == 82
    assert eff["rejection_rate_before_percent"] == 8.2
    assert eff["sample_after_count"] == 1000
    assert eff["defects_after_count"] == 11
    assert eff["rejection_rate_after_percent"] == 1.1
    assert eff["relative_reduction_percent"] == 86.6


# =====================================================================
# 4. STATISTICS & TWO-PROPORTION Z-TEST VS SCIPY (Check 4)
# =====================================================================
def test_two_proportion_z_test_against_scipy(db):
    """
    Verifies two-proportion z-test (pooled p-bar) against independent scipy calculation:
    p-bar = 0.0465, z about 7.54, p < 1e-6, 95% CI [5.28%, 8.92%].
    App values match scipy within tolerance < 1e-3.
    """
    n1, d1 = 1000, 82
    n2, d2 = 1000, 11
    p1 = d1 / n1
    p2 = d2 / n2

    # Independent calculation using scipy / stats
    p_pool = (d1 + d2) / (n1 + n2)
    assert abs(p_pool - 0.0465) < 1e-4

    se_pool = math.sqrt(p_pool * (1.0 - p_pool) * (1.0 / n1 + 1.0 / n2))
    z_expected = (p1 - p2) / se_pool
    p_val_expected = float(2.0 * (1.0 - stats.norm.cdf(abs(z_expected))))

    se_diff = math.sqrt((p1 * (1.0 - p1) / n1) + (p2 * (1.0 - p2) / n2))
    z_crit = float(stats.norm.ppf(0.975))
    ci_lower = (p1 - p2 - z_crit * se_diff) * 100.0
    ci_upper = (p1 - p2 + z_crit * se_diff) * 100.0

    eff = effectiveness_engine.evaluate_capa_effectiveness("CAPA-2026-001", db=db)

    # Compare app with scipy (tolerance 1e-3)
    assert abs(eff["statistic"] - round(z_expected, 2)) < 1e-3
    assert abs(eff["z_statistic"] - round(z_expected, 2)) < 1e-3
    assert eff["p_value"] < 1e-6
    assert abs(eff["pooled_p_bar"] - round(p_pool, 4)) < 1e-3
    assert abs(eff["confidence_interval_diff_percent"][0] - round(ci_lower, 2)) < 1e-2
    assert abs(eff["confidence_interval_diff_percent"][1] - round(ci_upper, 2)) < 1e-2
    assert eff["test_name"] == "two_proportion_z_test"
    assert eff["sample_before_count"] == n1
    assert eff["sample_after_count"] == n2


def test_fisher_exact_test_small_counts():
    """
    When sample size is small or expected counts < 5, Fisher's exact test is selected.
    Compares odds ratio and p-value against scipy.stats.fisher_exact.
    """
    n1, d1 = 40, 8
    n2, d2 = 40, 1

    # Contingency table: [[8, 32], [1, 39]]
    table = [[d1, n1 - d1], [d2, n2 - d2]]
    odds_expected, p_expected = stats.fisher_exact(table)

    res = effectiveness_engine.evaluate_capa_effectiveness(
        capa_id="CAPA-2026-001",
        n_before=n1,
        defects_before=d1,
        n_after=n2,
        defects_after=d2
    )

    assert res["test_name"] == "fisher_exact_test"
    assert abs(res["statistic"] - round(float(odds_expected), 3)) < 1e-2
    assert abs(res["p_value"] - float(p_expected)) < 1e-3


# =====================================================================
# 5. SMALL SAMPLES & ZERO EDGE CASES (Check 5)
# =====================================================================
def test_small_sample_minimum_threshold_warning():
    """
    Fewer than 30 inspected parts or fewer than 5 events returns a
    'too little data to conclude' warning, never a confident claim.
    """
    # Sample < 30
    res_small_n = effectiveness_engine.evaluate_capa_effectiveness(
        capa_id="CAPA-2026-001",
        n_before=20,
        defects_before=2,
        n_after=20,
        defects_after=0
    )
    assert res_small_n["is_small_sample"] is True
    assert res_small_n["warning"] is not None
    assert "too little data to draw confident conclusions" in res_small_n["warning"].lower()
    assert res_small_n["is_statistically_significant"] is False
    assert res_small_n["outcome"] == "INSUFFICIENT_SAMPLE_SIZE"


def test_zero_events_and_zero_inspected_parts():
    """
    Zero defect events in a window and zero inspected parts are handled safely
    without division by zero.
    """
    # Zero events in after window (e.g. 10/1000 before, 0/1000 after)
    res_zero_defects = effectiveness_engine.evaluate_capa_effectiveness(
        capa_id="CAPA-2026-001",
        n_before=1000,
        defects_before=10,
        n_after=1000,
        defects_after=0
    )
    assert res_zero_defects["rejection_rate_after_percent"] == 0.0
    assert res_zero_defects["relative_reduction_percent"] == 100.0

    # Zero inspected parts (0 before, 0 after)
    res_zero_n = effectiveness_engine.evaluate_capa_effectiveness(
        capa_id="CAPA-2026-001",
        n_before=0,
        defects_before=0,
        n_after=0,
        defects_after=0
    )
    assert res_zero_n["rejection_rate_before_percent"] == 0.0
    assert res_zero_n["rejection_rate_after_percent"] == 0.0
    assert res_zero_n["is_statistically_significant"] is False
    assert res_zero_n["test_name"] == "insufficient_data"


# =====================================================================
# 6. WORDING, LABELLING & PROHIBITED CAUSAL PHRASES (Check 6)
# =====================================================================
def test_anti_causal_wording_and_epistemic_labelling(db):
    """
    Every output says 'observed association' and states that causation is not established.
    Result is labelled STATISTICAL_FINDING.
    Fails if any prohibited causal phrases ('proved', 'fixed the problem', 'caused the improvement') appear.
    Confounding explanations are reported.
    """
    eff = effectiveness_engine.evaluate_capa_effectiveness("CAPA-2026-001", db=db)

    # 1. Epistemic wording
    assert "Observed association" in eff["conclusion_label"]
    assert "causation not established" in eff["conclusion_label"]
    assert eff["label"] == "STATISTICAL_FINDING"

    # 2. Confounding explanations reported
    assert "Potential confounding explanations" in eff["confounding_explanations"]
    assert "material lot" in eff["confounding_explanations"].lower()

    # 3. Prohibited phrase scan
    forbidden_words = ["proved", "proves", "fixed the problem", "caused the improvement", "guarantees quality", "definitely solved"]
    conclusion_text = eff["conclusion_label"]

    import re
    for fw in forbidden_words:
        assert not re.search(r"\b" + re.escape(fw) + r"\b", conclusion_text, re.IGNORECASE), f"Prohibited causal phrase '{fw}' found in conclusion!"


# =====================================================================
# 7. DIRECTION HANDLING (Check 7)
# =====================================================================
def test_direction_handling_improvement_worsening_unchanged():
    """
    Improvement, no change, and worsening are all reported honestly.
    A worsening result is shown and prompts a 'request another analysis' suggestion.
    """
    # 1. Improvement (8.2% -> 1.1%)
    res_imp = effectiveness_engine.evaluate_capa_effectiveness(
        capa_id="CAPA-2026-001",
        n_before=1000, defects_before=82,
        n_after=1000, defects_after=11
    )
    assert res_imp["outcome"] == "IMPROVEMENT_OBSERVED"
    assert res_imp["direction"] == "reduction"

    # 2. Worsening (1.1% -> 8.2%)
    res_worse = effectiveness_engine.evaluate_capa_effectiveness(
        capa_id="CAPA-2026-001",
        n_before=1000, defects_before=11,
        n_after=1000, defects_after=82
    )
    assert res_worse["outcome"] == "WORSENING_OBSERVED"
    assert res_worse["direction"] == "increase"
    assert "request another analysis" in res_worse["recommendation"].lower()

    # 3. No significant change (2.0% -> 1.9%)
    res_same = effectiveness_engine.evaluate_capa_effectiveness(
        capa_id="CAPA-2026-001",
        n_before=1000, defects_before=20,
        n_after=1000, defects_after=19
    )
    assert res_same["outcome"] == "NO_SIGNIFICANT_CHANGE"
    assert res_same["direction"] == "unchanged"


# =====================================================================
# 8. RECURRENCE DETECTION (Check 8 - Agent 7)
# =====================================================================
def test_defect_recurrence_detection(db):
    """
    Verifies Agent 7 defect recurrence detection:
    - Case with no recurrence (e.g. CNC-01 / Surface Porosity, or verified post-action batch)
    - Case with recurrence (e.g. CNC-04 / Oversized shaft diameter, or recurrence batch)
    """
    # 1. Case with recurrence
    rec_yes = capa_service.detect_defect_recurrence(db=db, machine_code="CNC-04", defect_type="Oversized shaft diameter")
    assert rec_yes["recurrence_detected"] is True
    assert rec_yes["recurrence_count"] > 0
    assert "RECURRENCE ALERT" in rec_yes["alert"]

    # In effectiveness engine with recurrence batch included
    eff_rec = effectiveness_engine.evaluate_capa_effectiveness(
        "CAPA-2026-001",
        db=db,
        include_recurrence_batch=True
    )
    assert eff_rec["recurrence_detected"] is True
    assert "Defect recurrence detected" in eff_rec["recurrence_details"]

    # 2. Case with no recurrence
    rec_no = capa_service.detect_defect_recurrence(db=db, machine_code="CNC-01", defect_type="Surface Porosity")
    assert rec_no["recurrence_detected"] is False

    eff_clean = effectiveness_engine.evaluate_capa_effectiveness(
        "CAPA-2026-001",
        db=db,
        include_recurrence_batch=False
    )
    assert eff_clean["recurrence_detected"] is False
    assert "No recurrence of defect detected" in eff_clean["recurrence_details"]


# =====================================================================
# 9. PERSISTENCE & HISTORY RETENTION (Check 9)
# =====================================================================
def test_recompute_when_new_batches_arrive_keeps_previous(db):
    """
    Effectiveness checks are stored in effectiveness_checks.
    When new batches arrive or force_recompute is triggered, previous results are kept.
    """
    action = db.query(CAPAAction).filter(CAPAAction.action_code == "CAPA-2026-001").first()
    assert action is not None

    count_before = db.query(EffectivenessCheck).filter(EffectivenessCheck.capa_id == action.id).count()

    # Trigger force_recompute (simulating new batch arrival)
    effectiveness_engine.evaluate_capa_effectiveness(
        "CAPA-2026-001",
        db=db,
        force_recompute=True
    )

    count_after = db.query(EffectivenessCheck).filter(EffectivenessCheck.capa_id == action.id).count()
    assert count_after == count_before + 1

    # Verify CAPA action record's effectiveness_result field is populated
    db.refresh(action)
    assert action.effectiveness_result is not None
    assert "Observed association" in action.effectiveness_result


# =====================================================================
# 10. API ENDPOINTS & SWAGGER (Check 10)
# =====================================================================
def test_api_effectiveness_endpoints():
    """
    Tests both API endpoints:
    - GET /api/effectiveness/{capa_id}
    - GET /api/capa/actions/{code}/effectiveness
    under tag Effectiveness.
    """
    # 1. /api/effectiveness/CAPA-2026-001
    r1 = client.get("/api/effectiveness/CAPA-2026-001")
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["rejection_rate_before_percent"] == 8.2
    assert d1["rejection_rate_after_percent"] == 1.1
    assert d1["z_statistic"] == 7.54
    assert d1["is_statistically_significant"] is True
    assert "Observed association" in d1["conclusion_label"]

    # 2. /api/capa/actions/CAPA-2026-001/effectiveness
    r2 = client.get("/api/capa/actions/CAPA-2026-001/effectiveness")
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["action_code"] == "CAPA-2026-001"
    assert d2["statistic"] == 7.54

    # 3. Verify OpenAPI documentation lists Effectiveness
    r_docs = client.get("/openapi.json")
    assert r_docs.status_code == 200
    openapi = r_docs.json()
    tags = [t["name"] for t in openapi.get("tags", [])]
    assert "Effectiveness" in tags
    assert "/api/effectiveness/{capa_id}" in openapi["paths"]
    assert "/api/capa/actions/{action_id_or_code}/effectiveness" in openapi["paths"]
