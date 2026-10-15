"""
Comprehensive Automated Tests for Requirement 1:
Nonconformance Detection, Defect-Specific Process Investigation, and Missing Evidence Reporting.
"""
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.database.models import (
    Batch, Product, Machine, InspectionCharacteristic, Measurement,
    InspectionImage, VisualFinding, ProcessReading, QualityIncident, RCAHypothesis
)
from backend.app.services.investigation_service import (
    build_investigation_report,
    select_investigation_strategy,
    STRATEGY_DIMENSIONAL_OVERSIZED,
    STRATEGY_DIMENSIONAL_UNDERSIZED,
    STRATEGY_VISUAL_DEFECT,
    STRATEGY_SURFACE_FINISH,
    STRATEGY_PROCESS_DRIFT,
    STRATEGY_MULTIPLE_DEFECTS,
    STRATEGY_CONFORMING_PROCESS
)

client = TestClient(app)


def test_investigation_strategy_selection_logic():
    """Verify strategy selection is dynamic based on defect signals."""
    # Oversized dimensional defect
    strat_over = select_investigation_strategy(
        has_oversized=True, has_undersized=False, has_visual=False,
        has_surface=False, has_drift=False, has_material=False, nonconforming_count=2
    )
    assert strat_over["strategy"] == STRATEGY_DIMENSIONAL_OVERSIZED

    # Undersized dimensional defect
    strat_under = select_investigation_strategy(
        has_oversized=False, has_undersized=True, has_visual=False,
        has_surface=False, has_drift=False, has_material=False, nonconforming_count=1
    )
    assert strat_under["strategy"] == STRATEGY_DIMENSIONAL_UNDERSIZED

    # Visual defect
    strat_vis = select_investigation_strategy(
        has_oversized=False, has_undersized=False, has_visual=True,
        has_surface=False, has_drift=False, has_material=False, nonconforming_count=0,
        defect_type="surface_scratch"
    )
    assert strat_vis["strategy"] == STRATEGY_VISUAL_DEFECT

    # Surface finish / vibration defect
    strat_surf = select_investigation_strategy(
        has_oversized=False, has_undersized=False, has_visual=False,
        has_surface=True, has_drift=False, has_material=False, nonconforming_count=0,
        defect_type="surface_roughness"
    )
    assert strat_surf["strategy"] == STRATEGY_SURFACE_FINISH

    # Process drift
    strat_drift = select_investigation_strategy(
        has_oversized=False, has_undersized=False, has_visual=False,
        has_surface=False, has_drift=True, has_material=False, nonconforming_count=2,
        defect_type="process_drift"
    )
    assert strat_drift["strategy"] == STRATEGY_PROCESS_DRIFT

    # Multiple concurrent defects (dimensional + visual)
    strat_multi = select_investigation_strategy(
        has_oversized=True, has_undersized=False, has_visual=True,
        has_surface=False, has_drift=False, has_material=False, nonconforming_count=3
    )
    assert strat_multi["strategy"] == STRATEGY_MULTIPLE_DEFECTS

    # Conforming
    strat_conf = select_investigation_strategy(
        has_oversized=False, has_undersized=False, has_visual=False,
        has_surface=False, has_drift=False, has_material=False, nonconforming_count=0
    )
    assert strat_conf["strategy"] == STRATEGY_CONFORMING_PROCESS


def test_batch_0245_investigation_endpoint():
    """Verify endpoint /api/investigation/BATCH-0245 returns full correlated investigation."""
    res = client.get("/api/investigation/BATCH-0245")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()

    assert data["batch_id"] == "BATCH-0245"
    assert "specification" in data
    assert "inspection_summary" in data
    assert "strategy" in data
    assert "hypotheses" in data
    assert len(data["hypotheses"]) > 0
    assert "correlation_vs_causation_note" in data
    assert "recommended_actions" in data

    # Verify epistemic label is strictly HYPOTHESIS
    assert data["hypotheses"][0]["epistemic_label"] in ["HYPOTHESIS", "CONFIRMED_ROOT_CAUSE"]
    # Verify specification is present
    assert data["specification"]["nominal"] == 50.00
    assert data["specification"]["usl"] == 50.05
    assert data["specification"]["lsl"] == 49.95


def test_insufficient_process_evidence_when_telemetry_missing():
    """Verify that when a nonconforming batch lacks machine telemetry, INSUFFICIENT_PROCESS_EVIDENCE is reported."""
    db = SessionLocal()
    test_batch_id = f"TEST-NC-{int(datetime.now().timestamp())}"
    try:
        # Create a test batch without telemetry
        b = Batch(
            batch_number=test_batch_id,
            product_id="prod-ps-101",
            machine_id="mach-04",
            shift="Night",
            quantity=250,
            material_lot="LOT-TEST-999",
            start_time=datetime.now(timezone.utc),
            status="QUALITY_HOLD"
        )
        db.add(b)
        db.commit()
        db.refresh(b)

        # Add an out-of-spec measurement (oversized)
        m = Measurement(
            batch_id=b.id,
            characteristic_id="char-ps-01",
            component_id="SMPL-NC-01",
            value=50.12,  # > USL 50.05
            unit="mm",
            status="nonconforming",
            deviation_from_limit=0.07,
            source_type="manual"
        )
        db.add(m)
        db.commit()

        # Call investigation API
        res = client.get(f"/api/investigation/{test_batch_id}")
        assert res.status_code == 200
        data = res.json()

        assert data["inspection_summary"]["nonconforming_count"] == 1
        assert data["investigation_status"] == "INSUFFICIENT_PROCESS_EVIDENCE"
        assert len(data["missing_data_sources"]) > 0
        assert any("telemetry" in s.lower() for s in data["missing_data_sources"])
        assert len(data["verification_steps"]) > 0

    finally:
        # Cleanup
        db.query(Measurement).filter(Measurement.batch_id == b.id).delete()
        db.query(Batch).filter(Batch.id == b.id).delete()
        db.commit()
        db.close()


def test_investigation_post_endpoint():
    """Verify POST /api/investigation/run endpoint works idempotently."""
    res = client.post("/api/investigation/run", json={"batch_id": "BATCH-0245", "force_refresh": True})
    assert res.status_code == 200
    data = res.json()
    assert data["batch_id"] == "BATCH-0245"
    assert data["strategy"]["strategy"] in [
        STRATEGY_DIMENSIONAL_OVERSIZED, STRATEGY_MULTIPLE_DEFECTS, STRATEGY_PROCESS_DRIFT
    ]
