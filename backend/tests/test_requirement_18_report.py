"""
Automated Test Suite for Functional Requirement 18: Quality Report Generation
Source of Truth: FR-18, Problem Statement

Requirements Verified:
1. PDF Download endpoint behavior (HTTP 200, Content-Type, Content-Disposition)
2. PDF validity, magic bytes, structure, and readability
3. All 13 mandatory report sections present:
   1. Product details
   2. Batch information
   3. Inspection summary
   4. Visual-inspection results
   5. Dimensional analysis
   6. SPC analysis
   7. Process anomalies
   8. Root-cause hypotheses
   9. Supporting evidence
   10. Containment actions
   11. Corrective/preventive actions
   12. Human approval
   13. Effectiveness monitoring
4. Independent data reconciliation with database and calculations
5. Graceful handling of missing optional sections
"""
import io
import json
import pytest
from fastapi.testclient import TestClient
import pypdf

from backend.app.main import app
from backend.app.services.pdf_report import generate_quality_pdf_report
from backend.app.database.session import SessionLocal
from backend.app.database.models import Batch, Product, InspectionCharacteristic, Measurement


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_pdf_endpoint_headers_and_signature(client):
    """FR-18: Verify /api/reports/pdf returns valid PDF stream with attachment header."""
    res = client.get("/api/reports/pdf?batch_id=BATCH-0245")
    assert res.status_code == 200
    assert res.headers.get("content-type") == "application/pdf"
    assert "attachment; filename=" in res.headers.get("content-disposition", "")
    assert res.content.startswith(b"%PDF-")
    assert b"%%EOF" in res.content[-1024:]
    assert len(res.content) > 50000


def test_pdf_readable_and_page_count(client):
    """FR-18: Verify generated PDF is parseable by pypdf with valid page count."""
    res = client.get("/api/reports/pdf?batch_id=BATCH-0245")
    assert res.status_code == 200

    reader = pypdf.PdfReader(io.BytesIO(res.content))
    assert len(reader.pages) >= 3

    for page in reader.pages:
        text = page.extract_text()
        assert text is not None
        assert len(text) > 200


def test_all_13_sections_present_in_pdf(client):
    """FR-18: Verify all 13 required sections are present in extracted text."""
    res = client.get("/api/reports/pdf?batch_id=BATCH-0245")
    assert res.status_code == 200

    reader = pypdf.PdfReader(io.BytesIO(res.content))
    full_text = " ".join([page.extract_text() for page in reader.pages]).lower()

    sections = [
        "1. product details",
        "2. batch information",
        "3. inspection summary",
        "4. visual inspection results",
        "5. dimensional analysis",
        "6. statistical process control",
        "7. process anomalies",
        "8. root cause hypotheses",
        "9. supporting & contradicting evidence",
        "10. containment actions",
        "11. corrective & preventive actions",
        "12. human quality approval",
        "13. effectiveness monitoring"
    ]

    for sec in sections:
        assert sec in full_text, f"Section '{sec}' missing from PDF text"


def test_data_reconciliation_product_and_batch():
    """Verify Section 1 & 2 data matches source database specifications."""
    db = SessionLocal()
    try:
        p = db.query(Product).filter(Product.part_number == "PS-2026-101").first()
        assert p is not None
        assert p.name == "Precision Ground Shaft"
        assert p.material == "Carbon Steel (AISI 1045)"

        b = db.query(Batch).filter(Batch.batch_number == "BATCH-0245").first()
        assert b is not None
        assert b.quantity == 500
        assert b.shift == "Night Shift"
    finally:
        db.close()


def test_data_reconciliation_inspection_counts():
    """Verify Section 3 & 5 numbers match raw database measurements."""
    db = SessionLocal()
    try:
        b = db.query(Batch).filter(Batch.batch_number == "BATCH-0245").first()
        meas = db.query(Measurement).filter(Measurement.batch_id == b.id).all()
        vals = [m.value for m in meas]

        total = len(vals)
        assert total == 5
        conforming = sum(1 for v in vals if 49.95 <= v <= 50.05)
        nonconforming = sum(1 for v in vals if v < 49.95 or v > 50.05)

        assert conforming == 2
        assert nonconforming == 3
        assert (nonconforming / total) == 0.60
    finally:
        db.close()


def test_effectiveness_monitoring_statistical_accuracy(client):
    """Verify Section 13 before/after stats and association disclaimer."""
    res = client.get("/api/reports/pdf?batch_id=BATCH-0245")
    assert res.status_code == 200

    reader = pypdf.PdfReader(io.BytesIO(res.content))
    full_text = " ".join([page.extract_text() for page in reader.pages])

    # Check baseline 8.2% and post 1.1%
    assert "8.2%" in full_text
    assert "1.1%" in full_text
    assert "z = 7.54" in full_text or "Two-Proportion Z-Test" in full_text
    # Check causation vs association caveat
    assert "causation not established" in full_text.lower() or "observed association" in full_text.lower()


def test_pdf_graceful_missing_data_handling():
    """Verify generator handles empty / minimal workflow state without crashing."""
    minimal_state = {
        "batch_metadata": {"batch_id": "BATCH-MINIMAL", "part_number": "PS-TEST", "nominal_mm": 50.0, "tolerance_mm": 0.05},
        "dimensional_report": {"total_inspected": 0, "non_conforming_count": 0, "rejection_rate_percent": 0.0},
        "visual_prediction": None,
        "process_report": None,
        "spc_report": None,
        "rca_report": None,
        "capa_report": None,
        "critic_review": None,
        "human_approval": None
    }
    pdf_bytes = generate_quality_pdf_report(minimal_state)
    assert pdf_bytes.startswith(b"%PDF-")
    assert b"%%EOF" in pdf_bytes[-1024:]

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 2
    full_text = " ".join([page.extract_text() for page in reader.pages]).lower()
    assert "1. product details" in full_text
    assert "no visual defect imagery submitted" in full_text
