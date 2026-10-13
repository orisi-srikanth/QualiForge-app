"""
Test Case TC-02: Measurement exceeds USL.
Binding Expected Results:
- LSL 49.95, USL 50.05
- P003, P004, P005 nonconforming with deviations 0.01, 0.03, 0.02
- 2 accepted, 3 nonconforming
- 60.0% sample rejection
- an incident is created automatically
- batch status is NOT changed to rejected (autonomous rejection prohibited)
- Independently recomputed with plain Decimal script and assert exact match.
Agents: 1, 3, 6.
"""
import pytest
from tests.test_cases.fixtures import (
    get_tc02_fixture,
    get_tc02_negative_control,
    recompute_tc02_decimal
)
from backend.app.agents.dimensional_agent import compliance_agent
from backend.app.database.session import SessionLocal
from backend.app.database.models import Batch, QualityIncident


def test_tc02_measurement_exceeds_usl():
    """Verify out-of-spec measurements, exact deviations, decimal recomputation, and batch status safety."""
    fixture = get_tc02_fixture()
    
    # 1. Run through compliance agent
    result = compliance_agent.evaluate_compliance(
        batch_id=fixture["batch_id"],
        measurements=fixture["measurements"],
        nominal_mm=fixture["nominal_mm"],
        tolerance_mm=fixture["tolerance_mm"]
    )
    report = result["report"]
    
    # 2. Independent Decimal recomputation
    decimal_eval = recompute_tc02_decimal(
        raw_vals=fixture["raw_values"],
        usl=fixture["usl"],
        lsl=fixture["lsl"]
    )
    
    # 3. Assert exact compliance metrics
    assert report.total_inspected == 5, f"Expected 5 total inspected, got {report.total_inspected}"
    assert report.accepted == 2, f"Expected 2 accepted, got {report.accepted}"
    assert report.nonconforming == 3, f"Expected 3 nonconforming, got {report.nonconforming}"
    assert report.rejection_rate_percent == 60.0, f"Expected 60.0% rejection, got {report.rejection_rate_percent}"
    assert report.usl == 50.05, f"Expected USL 50.05, got {report.usl}"
    assert report.lsl == 49.95, f"Expected LSL 49.95, got {report.lsl}"
    
    # 4. Assert exact deviations: P003 (+0.01), P004 (+0.03), P005 (+0.02)
    nonconforming_samples = {m.sample_id: m for m in report.measurements if not m.is_conforming}
    assert "P003" in nonconforming_samples, "P003 (50.06 mm) must be nonconforming"
    assert "P004" in nonconforming_samples, "P004 (50.08 mm) must be nonconforming"
    assert "P005" in nonconforming_samples, "P005 (50.07 mm) must be nonconforming"
    
    assert round(nonconforming_samples["P003"].deviation_from_limit, 4) == 0.01
    assert round(nonconforming_samples["P004"].deviation_from_limit, 4) == 0.03
    assert round(nonconforming_samples["P005"].deviation_from_limit, 4) == 0.02
    
    # 5. Assert independent Decimal script recomputation matches exactly
    assert decimal_eval["total"] == report.total_inspected
    assert decimal_eval["accepted_count"] == report.accepted
    assert decimal_eval["nonconforming_count"] == report.nonconforming
    assert decimal_eval["rejection_rate_percent"] == report.rejection_rate_percent
    
    # 6. Safety requirement: Batch status is NOT autonomously changed to REJECTED
    db = SessionLocal()
    try:
        batch_rec = db.query(Batch).filter(Batch.batch_number == "BATCH-0245").first()
        if batch_rec:
            assert batch_rec.status != "REJECTED", f"Safety violation: Batch status was autonomously set to '{batch_rec.status}'"
    finally:
        db.close()


def test_tc02_negative_control_conforming_batch():
    """Negative control: 5 conforming parts must have 0 nonconforming and 0% rejection."""
    neg_fixture = get_tc02_negative_control()
    
    result = compliance_agent.evaluate_compliance(
        batch_id=neg_fixture["batch_id"],
        measurements=neg_fixture["measurements"],
        nominal_mm=neg_fixture["nominal_mm"],
        tolerance_mm=neg_fixture["tolerance_mm"]
    )
    report = result["report"]
    
    assert report.nonconforming == 0, "Conforming parts must yield 0 nonconforming"
    assert report.rejection_rate_percent == 0.0, "Conforming parts must yield 0.0% rejection"
    assert report.accepted == 5, "All 5 parts must be accepted"
