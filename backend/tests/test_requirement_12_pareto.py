"""
Requirement 12 Verification Test Suite: Pareto Analysis (IATF 16949 / 80-20 Rule)
Verifies:
1. Five dimensions (defect types, machines, product families, confirmed root causes, rejection reasons)
2. Formulas, deterministic tie-breaking, cumulative percentage ending at 100.0%, 80% vital-few cutoff
3. Real database sources, non-mock data rows
4. Root causes: ONLY confirmed causes counted (lifecycle test: proposed excluded, confirmed included, rejected omitted)
5. Date-range filter: inclusive bounds, single-day, empty range (zero div avoided), reversed (400), invalid (422)
6. Edge cases: single category, ties, unspecified null handling
7. Wording and epistemic labelling: STATISTICAL_FINDING, confirmed causes only, non-causal disclaimer
8. UI integration & screenshot artifact existence
9. Dashboard integration parity and Swagger schema documentation
10. Independent SQL recomputation parity against raw database rows
"""
import pytest
import sqlite3
import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from datetime import datetime, timezone
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.database.models import QualityIncident, RCAHypothesis, Batch, Machine, Product
from backend.app.services.pareto import pareto_service
from backend.app.core.security import create_access_token, UserRole

client = TestClient(app)
_token = create_access_token({"sub": "engineer@precisionaero.com", "role": UserRole.QUALITY_ENGINEER.value})
client.headers["Authorization"] = f"Bearer {_token}"

# =====================================================================
# CHECK 1: Five Dimensions & Response Shapes
# =====================================================================
def test_check_1_five_dimensions():
    """Confirms API supports all five dimensions and returns expected payload schema."""
    dimensions = ["defect_type", "machine", "product_family", "root_cause", "rejection_reason"]
    for dim in dimensions:
        res = client.get(f"/api/pareto?dimension={dim}")
        assert res.status_code == 200, f"Failed on dimension: {dim}"
        data = res.json()

        assert data["dimension"] == dim
        assert "total" in data
        assert "total_incidents" in data
        assert data["total"] > 0, f"Dimension {dim} must have non-zero events"
        assert "items" in data
        assert len(data["items"]) > 0
        assert "vital_few_categories" in data
        assert "label" in data
        assert "analysis_note" in data
        assert "date_range_applied" in data

        # Check item schema
        first_item = data["items"][0]
        for key in ["category", "count", "percentage", "cumulative_percentage", "is_vital_few"]:
            assert key in first_item, f"Missing key '{key}' in item schema for {dim}"

# =====================================================================
# CHECK 2: Mathematical Formulas & Deterministic Tie-Breaking
# =====================================================================
def test_check_2_formulas_sorting_and_vital_few_rule():
    """
    Verifies:
    - Sorted descending by count
    - Stable, deterministic tie-break (count desc, then category name asc)
    - percentage = round(count / total * 100, 1)
    - cumulative percentage ends at exactly 100.0%
    - vital few = categories until cumulative percentage reaches >= 80%
    """
    res = client.get("/api/pareto?dimension=defect_type")
    assert res.status_code == 200
    data = res.json()
    items = data["items"]
    total = data["total"]

    cum_sum = 0
    cutoff_found = False
    expected_vital_few = []

    for idx, item in enumerate(items):
        cum_sum += item["count"]
        expected_pct = round((item["count"] / total) * 100.0, 1)
        assert abs(item["percentage"] - expected_pct) < 0.05, f"Percentage mismatch for {item['category']}"

        # Deterministic sorting check
        if idx > 0:
            prev = items[idx - 1]
            if prev["count"] == item["count"]:
                assert prev["category"] < item["category"], f"Tie-break alphabetical sort failed: {prev['category']} vs {item['category']}"
            else:
                assert prev["count"] > item["count"], "Count descending sort failed"

        # Vital few rule check
        if not cutoff_found:
            expected_vital_few.append(item["category"])
            assert item["is_vital_few"] is True
            if item["cumulative_percentage"] >= 80.0:
                cutoff_found = True
        else:
            assert item["is_vital_few"] is False

    # Cumulative percentage must end at exactly 100.0%
    assert items[-1]["cumulative_percentage"] == 100.0
    assert data["vital_few_categories"] == expected_vital_few

# =====================================================================
# CHECK 3: Real Database Sources & Non-Mock Rows
# =====================================================================
def test_check_3_real_database_sources():
    """Confirms all dimensions query real tables without hard-coded static arrays."""
    db = SessionLocal()
    try:
        # Check database table row counts
        assert db.query(QualityIncident).count() >= 20
        assert db.query(Batch).count() >= 10
        assert db.query(Machine).count() >= 4
        assert db.query(Product).count() >= 3
        assert db.query(RCAHypothesis).count() >= 20

        # Verify rejection_reason is a populated column
        non_null_rejections = db.query(QualityIncident).filter(QualityIncident.rejection_reason.isnot(None)).count()
        assert non_null_rejections >= 20, "Rejection reason column must be populated on raw rows"
    finally:
        db.close()

# =====================================================================
# CHECK 4: Root Cause Lifecycle (ONLY Confirmed Causes Counted)
# =====================================================================
def test_check_4_confirmed_only_root_causes_lifecycle():
    """
    Proves:
    1. Proposed hypothesis does NOT appear in root_cause Pareto.
    2. Once confirmed by QE, it DOES appear (+1 count).
    3. Rejected hypothesis NEVER appears in root_cause Pareto.
    """
    db = SessionLocal()
    try:
        base_res = pareto_service.compute_pareto(db=db, dimension="root_cause")
        base_total = base_res["total"]

        # Step 1: Create proposed hypothesis (not confirmed)
        prop_hyp = RCAHypothesis(
            id="hyp-test-life-01",
            incident_id="inc-ncr-019",
            rank=4,
            category="Machine",
            title="TEST_HYPOTHESIS: Unconfirmed Belt Slippage",
            label="HYPOTHESIS",
            status="proposed"
        )
        db.add(prop_hyp)
        db.commit()

        p1 = pareto_service.compute_pareto(db=db, dimension="root_cause")
        assert p1["total"] == base_total, "Proposed hypothesis must NOT alter Pareto total"
        assert not any(it["category"] == "TEST_HYPOTHESIS: Unconfirmed Belt Slippage" for it in p1["items"])

        # Step 2: Confirm it as Lead Quality Engineer
        prop_hyp.status = "confirmed"
        prop_hyp.label = "CONFIRMED_ROOT_CAUSE"
        prop_hyp.reviewer_id = "usr-qe-01"
        prop_hyp.comment = "Confirmed by Sarah Chen, Lead Quality Engineer"
        db.commit()

        p2 = pareto_service.compute_pareto(db=db, dimension="root_cause")
        assert p2["total"] == base_total + 1, "Confirmed root cause MUST appear in Pareto"
        assert any(it["category"] == "TEST_HYPOTHESIS: Unconfirmed Belt Slippage" for it in p2["items"])

        # Step 3: Create a rejected hypothesis
        rej_hyp = RCAHypothesis(
            id="hyp-test-life-02",
            incident_id="inc-ncr-019",
            rank=5,
            category="Environment",
            title="TEST_HYPOTHESIS: Cosmic Radiation Noise",
            label="HYPOTHESIS",
            status="rejected",
            reviewer_id="usr-qe-01",
            comment="Rejected by QE: Physically impossible."
        )
        db.add(rej_hyp)
        db.commit()

        p3 = pareto_service.compute_pareto(db=db, dimension="root_cause")
        assert p3["total"] == base_total + 1, "Rejected hypothesis must NEVER appear in Pareto"
        assert not any(it["category"] == "TEST_HYPOTHESIS: Cosmic Radiation Noise" for it in p3["items"])

        # Cleanup test records
        db.delete(prop_hyp)
        db.delete(rej_hyp)
        db.commit()
    finally:
        db.close()

# =====================================================================
# CHECK 5: Date-Range Filtering (Inclusive, Empty, Reversed, Invalid)
# =====================================================================
def test_check_5_date_range_filtering():
    """
    Verifies:
    - Date filtering excludes non-matching records
    - Single-day range works inclusively
    - Empty range returns total: 0 and items: [] without division by zero
    - Reversed range returns HTTP 400
    - Malformed date returns HTTP 422
    """
    # 1. Exclude early March incidents
    res_aug = client.get("/api/pareto?dimension=defect_type&start_date=2026-08-01&end_date=2026-10-31")
    assert res_aug.status_code == 200
    data_aug = res_aug.json()
    assert data_aug["total"] == 19  # March incident excluded

    # 2. Single-day range (2026-08-22)
    res_single = client.get("/api/pareto?dimension=defect_type&start_date=2026-08-22&end_date=2026-08-22")
    assert res_single.status_code == 200
    data_single = res_single.json()
    assert data_single["total"] == 2
    assert len(data_single["items"]) == 1
    assert data_single["items"][0]["category"] == "Oversized shaft diameter"

    # 3. Empty range (2025-01-01 to 2025-01-31)
    res_empty = client.get("/api/pareto?dimension=defect_type&start_date=2025-01-01&end_date=2025-01-31")
    assert res_empty.status_code == 200
    data_empty = res_empty.json()
    assert data_empty["total"] == 0
    assert data_empty["total_incidents"] == 0
    assert data_empty["items"] == []
    assert data_empty["vital_few_categories"] == []

    # 4. Reversed range (2026-10-01 to 2026-08-01) -> HTTP 400
    res_rev = client.get("/api/pareto?dimension=defect_type&start_date=2026-10-01&end_date=2026-08-01")
    assert res_rev.status_code == 400
    assert "Reversed date range" in res_rev.json()["detail"]

    # 5. Invalid date string ("not-a-date") -> HTTP 422
    res_inv = client.get("/api/pareto?dimension=defect_type&start_date=not-a-date")
    assert res_inv.status_code == 422
    assert "Invalid start_date format" in res_inv.json()["detail"]

# =====================================================================
# CHECK 6: Edge Cases (Single Category, Ties, Unspecified Nulls)
# =====================================================================
def test_check_6_edge_cases():
    """Verifies single category math, tied sorting stability, and unspecified category handling."""
    db = SessionLocal()
    b_first = db.query(Batch).first()
    b_id = b_first.id if b_first else "batch-0245"

    single_inc = QualityIncident(
        id="inc-test-single-edge",
        batch_id=b_id,
        title="Single Test Edge Case",
        defect_type="UNIQUE_SINGULAR_DEFECT",
        rejection_reason="Single Reason",
        severity="LOW",
        created_at=datetime(2028, 1, 1, 10, 0, tzinfo=timezone.utc)
    )
    null_inc = QualityIncident(
        id="inc-test-null-edge",
        batch_id=b_id,
        title="Null Reason Test Edge Case",
        defect_type="ANOTHER_DEFECT",
        rejection_reason=None,
        severity="LOW",
        created_at=datetime(2028, 1, 1, 11, 0, tzinfo=timezone.utc)
    )

    try:
        db.add_all([single_inc, null_inc])
        db.commit()

        # 1. Single category window
        res_single = pareto_service.compute_pareto(db=db, dimension="defect_type", start_date="2028-01-01T09:00:00", end_date="2028-01-01T10:30:00")
        assert res_single["total"] == 1
        assert len(res_single["items"]) == 1
        assert res_single["items"][0]["percentage"] == 100.0
        assert res_single["items"][0]["cumulative_percentage"] == 100.0
        assert res_single["items"][0]["is_vital_few"] is True

        # 2. Null rejection_reason mapped to "Unspecified"
        res_null = pareto_service.compute_pareto(db=db, dimension="rejection_reason", start_date="2028-01-01", end_date="2028-01-02")
        cats = [it["category"] for it in res_null["items"]]
        assert "Unspecified" in cats, "Null categories must be represented as 'Unspecified' rather than omitted"
    finally:
        db.delete(single_inc)
        db.delete(null_inc)
        db.commit()
        db.close()

# =====================================================================
# CHECK 7: Wording & Epistemic Labelling
# =====================================================================
def test_check_7_wording_and_epistemic_labelling():
    """Verifies epistemic status, confirmed-causes-only label, and non-causal disclaimer."""
    # 1. Root causes endpoint
    res_rc = client.get("/api/pareto?dimension=root_cause")
    assert res_rc.status_code == 200
    data_rc = res_rc.json()
    assert data_rc["label"] == "STATISTICAL_FINDING"
    assert "Confirmed causes only" in data_rc["analysis_note"]
    assert "does not autonomously establish causation" in data_rc["analysis_note"]

    # 2. Defect type endpoint
    res_dt = client.get("/api/pareto?dimension=defect_type")
    assert res_dt.status_code == 200
    data_dt = res_dt.json()
    assert data_dt["label"] == "STATISTICAL_FINDING"
    assert "Pareto frequency reflects observed event distribution" in data_dt["analysis_note"]

# =====================================================================
# CHECK 8: UI Screenshots Artifacts Existence
# =====================================================================
def test_check_8_screenshots_exist():
    """Confirms that UI screenshots exist in docs/screenshots/requirement12/."""
    expected_files = [
        "docs/screenshots/requirement12/01_pareto_defect_types.png",
        "docs/screenshots/requirement12/02_pareto_machines.png",
        "docs/screenshots/requirement12/03_pareto_confirmed_root_causes.png",
        "docs/screenshots/requirement12/04_pareto_rejection_reasons.png",
        "docs/screenshots/requirement12/05_pareto_date_filter_empty_state.png",
    ]
    for path in expected_files:
        assert os.path.exists(path), f"Required screenshot missing: {path}"
        assert os.path.getsize(path) > 1000, f"Screenshot file empty or corrupt: {path}"

# =====================================================================
# CHECK 9: Integration with Dashboard Summary & Swagger Documentation
# =====================================================================
def test_check_9_dashboard_integration_and_swagger():
    """
    Verifies:
    - Dashboard summary's top defect categories match live Pareto defect data.
    - Route definition lists /api/pareto under 'Pareto' tag with documentation.
    """
    # 1. Dashboard summary integration parity
    res_dash = client.get("/api/dashboard/summary")
    assert res_dash.status_code == 200
    dash_top = res_dash.json()["top_defect_categories"]

    res_pareto = client.get("/api/pareto?dimension=defect_type")
    assert res_pareto.status_code == 200
    pareto_items = res_pareto.json()["items"]

    assert len(dash_top) == min(5, len(pareto_items))
    for d_item, p_item in zip(dash_top, pareto_items):
        assert d_item["defect"] == p_item["category"]
        assert d_item["count"] == p_item["count"]
        assert d_item["percentage"] == p_item["percentage"]

    # 2. FastAPI route registration check
    from backend.app.routers.reports import router as reports_router
    pareto_route = next((r for r in reports_router.routes if r.path == "/pareto"), None)
    assert pareto_route is not None, "Route /pareto must be registered on reports_router"
    assert "Pareto" in pareto_route.tags
    assert "Pareto distribution across 5 dimensions" in pareto_route.summary

# =====================================================================
# CHECK 10: Independent SQL Recomputation Parity
# =====================================================================
def test_check_10_independent_sql_recomputation_parity():
    """
    Directly queries raw SQLite rows and validates 100% mathematical parity
    with the Pareto service outputs across all 5 dimensions.
    """
    conn = sqlite3.connect("backend/data/quality_system.db")
    cursor = conn.cursor()

    dimensions_sql = {
        "defect_type": "SELECT COALESCE(defect_type, 'Unspecified'), COUNT(*) FROM quality_incidents GROUP BY 1",
        "machine": """
            SELECT COALESCE(m.code, 'Unspecified'), COUNT(*)
            FROM quality_incidents qi
            JOIN batches b ON qi.batch_id = b.id
            JOIN machines m ON b.machine_id = m.id
            GROUP BY 1
        """,
        "product_family": """
            SELECT COALESCE(p.family, 'Unspecified'), COUNT(*)
            FROM quality_incidents qi
            JOIN batches b ON qi.batch_id = b.id
            JOIN products p ON b.product_id = p.id
            GROUP BY 1
        """,
        "rejection_reason": "SELECT COALESCE(rejection_reason, 'Unspecified'), COUNT(*) FROM quality_incidents GROUP BY 1",
        "root_cause": """
            SELECT COALESCE(rh.title, 'Unspecified'), COUNT(*)
            FROM rca_hypotheses rh
            JOIN quality_incidents qi ON rh.incident_id = qi.id
            WHERE rh.label = 'CONFIRMED_ROOT_CAUSE' OR rh.status = 'confirmed'
            GROUP BY 1
        """
    }

    for dim, query in dimensions_sql.items():
        cursor.execute(query)
        rows = cursor.fetchall()
        indep_total = sum(r[1] for r in rows)
        sorted_indep = sorted(rows, key=lambda x: (-x[1], str(x[0])))

        res = client.get(f"/api/pareto?dimension={dim}")
        app_data = res.json()

        assert app_data["total"] == indep_total, f"Total mismatch for {dim}"
        assert len(app_data["items"]) == len(sorted_indep), f"Length mismatch for {dim}"

        for indep_row, app_item in zip(sorted_indep, app_data["items"]):
            assert indep_row[0] == app_item["category"]
            assert indep_row[1] == app_item["count"]

    conn.close()
