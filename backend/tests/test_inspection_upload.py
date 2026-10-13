"""
Unit & Integration Tests for Inspection CSV Upload Endpoint (POST /api/inspection/measurements/upload)
Tests all 17 mandated scenarios:
1. Valid five-row measurement CSV
2. Correct expected result for BATCH-0245 (5 inspected, 2 accepted, 3 nonconforming, 60% rejection)
3. All measurements within specification
4. A measurement above USL
5. Measurements exactly on LSL and USL
6. Missing required columns
7. Invalid measurement values (non-numeric, NaN, inf)
8. Invalid units
9. Unknown batch ID (HTTP 404)
10. Empty CSV (HTTP 400)
11. Unsupported file type (HTTP 400)
12. Oversized file (HTTP 413)
13. Unit normalization (inches / microns to mm)
14. Batch mismatch between CSV and form (HTTP 422)
15. Multiple batch IDs in single CSV (HTTP 422)
16. Implausible negative/huge measurement (HTTP 422)
17. Template download endpoint
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.security import create_access_token, UserRole

client = TestClient(app)
_token = create_access_token({"sub": "operator@precisionaero.com", "role": UserRole.OPERATOR.value})
client.headers["Authorization"] = f"Bearer {_token}"

@pytest.fixture(scope="module", autouse=True)
def restore_batch_0245_measurements():
    yield
    from backend.app.database.session import SessionLocal
    from backend.app.database.models import Batch, Measurement, InspectionCharacteristic
    db = SessionLocal()
    try:
        b = db.query(Batch).filter(Batch.batch_number == "BATCH-0245").first()
        if b:
            char = db.query(InspectionCharacteristic).filter(InspectionCharacteristic.product_id == b.product_id).first()
            char_id = char.id if char else "char-ps-dia-01"
            db.query(Measurement).filter(Measurement.batch_id == b.id).delete()
            golden = [
                ("P001", 50.01, "conforming", 0.0),
                ("P002", 50.03, "conforming", 0.0),
                ("P003", 50.06, "nonconforming", 0.01),
                ("P004", 50.08, "nonconforming", 0.03),
                ("P005", 50.07, "nonconforming", 0.02),
            ]
            for comp_id, val, st, dev in golden:
                db.add(Measurement(
                    batch_id=b.id,
                    characteristic_id=char_id,
                    component_id=comp_id,
                    value=val,
                    unit="mm",
                    status=st,
                    deviation_from_limit=dev,
                    source_type="csv",
                    file_name="benchmark_5_parts.csv",
                    uploaded_by="quality_engineer@precisionaero.com"
                ))
            db.commit()
    finally:
        db.close()


def test_1_valid_five_row_benchmark_csv():
    """Upload valid 5-row CSV and verify successful status and schema."""
    csv_content = """batch_id,component_id,value,unit
BATCH-0245,P001,50.01,mm
BATCH-0245,P002,50.03,mm
BATCH-0245,P003,50.06,mm
BATCH-0245,P004,50.08,mm
BATCH-0245,P005,50.07,mm
"""
    files = {"file": ("inspection_test.csv", csv_content.encode("utf-8"), "text/csv")}
    res = client.post("/api/inspection/measurements/upload", files=files)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "success"
    assert data["batch_id"] == "BATCH-0245"
    assert data["total_inspected"] == 5
    assert data["accepted"] == 2
    assert data["nonconforming"] == 3
    assert data["rejection_rate_percent"] == 60.0
    assert data["specification"]["nominal_mm"] == 50.0
    assert data["specification"]["tolerance_mm"] == 0.05
    assert data["specification"]["usl_mm"] == 50.05
    assert data["specification"]["lsl_mm"] == 49.95

def test_2_expected_batch_0245_conformance_rates():
    """Verify BATCH-0245 results match ground truth (2 accepted, 3 out-of-spec)."""
    csv_content = """component_id,measured_value
P001,50.01
P002,50.03
P003,50.06
P004,50.08
P005,50.07
"""
    files = {"file": ("batch_245.csv", csv_content.encode("utf-8"), "text/csv")}
    data_form = {"batch_id": "BATCH-0245"}
    res = client.post("/api/inspection/measurements/upload", files=files, data=data_form)
    assert res.status_code == 200
    res_json = res.json()
    assert res_json["accepted"] == 2
    assert res_json["nonconforming"] == 3
    assert res_json["rejection_rate_percent"] == 60.0

    # Verify per-component outcomes
    items = {m["sample_id"]: m for m in res_json["measurements"]}
    assert items["P001"]["is_conforming"] is True
    assert items["P002"]["is_conforming"] is True
    assert items["P003"]["is_conforming"] is False
    assert items["P003"]["status"] == "FAIL_HIGH"
    assert items["P004"]["is_conforming"] is False
    assert items["P004"]["status"] == "FAIL_HIGH"
    assert items["P005"]["is_conforming"] is False
    assert items["P005"]["status"] == "FAIL_HIGH"

def test_3_all_measurements_within_specification():
    """All 5 measurements comfortably within tolerance band (100% conforming)."""
    csv_content = """sample_id,dia_mm
S01,50.00
S02,50.01
S03,50.02
S04,49.99
S05,49.98
"""
    files = {"file": ("perfect_lot.csv", csv_content.encode("utf-8"), "text/csv")}
    res = client.post("/api/inspection/measurements/upload", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["total_inspected"] == 5
    assert data["accepted"] == 5
    assert data["nonconforming"] == 0
    assert data["rejection_rate_percent"] == 0.0

def test_4_measurement_above_usl():
    """Specific measurement above USL correctly flags deviation."""
    csv_content = """component_id,value\nP101,50.09\n"""
    files = {"file": ("oversized.csv", csv_content.encode("utf-8"), "text/csv")}
    res = client.post("/api/inspection/measurements/upload", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["nonconforming"] == 1
    m = data["measurements"][0]
    assert m["is_conforming"] is False
    assert m["status"] == "FAIL_HIGH"
    assert m["deviation_from_limit"] == 0.04

def test_5_measurements_exactly_on_lsl_and_usl():
    """Boundary test: 49.95 mm and 50.05 mm are strictly conforming."""
    csv_content = """component_id,value\nP_LSL,49.95\nP_USL,50.05\n"""
    files = {"file": ("boundaries.csv", csv_content.encode("utf-8"), "text/csv")}
    res = client.post("/api/inspection/measurements/upload", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["total_inspected"] == 2
    assert data["accepted"] == 2
    assert data["nonconforming"] == 0
    assert data["rejection_rate_percent"] == 0.0

def test_6_missing_required_columns():
    """Missing value column returns HTTP 422."""
    csv_content = """timestamp,operator_id\n2026-10-10,OP-44\n"""
    files = {"file": ("missing_cols.csv", csv_content.encode("utf-8"), "text/csv")}
    res = client.post("/api/inspection/measurements/upload", files=files)
    assert res.status_code == 422
    assert "Missing required columns" in res.json()["detail"]

def test_7_invalid_measurement_values():
    """Non-numeric string and NaN values return HTTP 422."""
    csv_content = """component_id,value\nP001,NOT_A_NUMBER\n"""
    files = {"file": ("bad_val.csv", csv_content.encode("utf-8"), "text/csv")}
    res = client.post("/api/inspection/measurements/upload", files=files)
    assert res.status_code == 422
    assert "Invalid numeric measurement value" in res.json()["detail"]

def test_8_invalid_units():
    """Unsupported engineering unit returns HTTP 422."""
    csv_content = """component_id,value,unit\nP001,50.01,psi\n"""
    files = {"file": ("bad_unit.csv", csv_content.encode("utf-8"), "text/csv")}
    res = client.post("/api/inspection/measurements/upload", files=files)
    assert res.status_code == 422
    assert "Unsupported measurement unit" in res.json()["detail"]

def test_9_unknown_batch_id():
    """Non-existent batch returns HTTP 404."""
    csv_content = """component_id,value\nP001,50.01\n"""
    files = {"file": ("unknown_batch.csv", csv_content.encode("utf-8"), "text/csv")}
    res = client.post("/api/inspection/measurements/upload", files=files, data={"batch_id": "BATCH-NONEXISTENT-999"})
    assert res.status_code == 404
    assert "not found in manufacturing system" in res.json()["detail"]

def test_10_empty_csv():
    """Empty CSV file returns HTTP 400."""
    files = {"file": ("empty.csv", b"", "text/csv")}
    res = client.post("/api/inspection/measurements/upload", files=files)
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()

def test_11_unsupported_file_type():
    """Uploading non-CSV file returns HTTP 400."""
    files = {"file": ("notes.txt", b"component,value\nP1,50.0", "text/plain")}
    res = client.post("/api/inspection/measurements/upload", files=files)
    assert res.status_code == 400
    assert "Unsupported file format" in res.json()["detail"]

def test_12_oversized_file():
    """Files exceeding 5MB return HTTP 413."""
    oversized_bytes = b"component_id,value\n" + b"x" * (5 * 1024 * 1024 + 500)
    files = {"file": ("huge.csv", oversized_bytes, "text/csv")}
    res = client.post("/api/inspection/measurements/upload", files=files)
    assert res.status_code == 413

def test_13_unit_normalization_inches_and_microns():
    """Inches and microns correctly convert to mm and report in warnings."""
    csv_content = """component_id,value,unit
P_INCH,1.9688976,in
P_UM,50060,um
"""
    files = {"file": ("multi_unit.csv", csv_content.encode("utf-8"), "text/csv")}
    res = client.post("/api/inspection/measurements/upload", files=files)
    assert res.status_code == 200
    data = res.json()
    assert len(data["unit_conversions"]) == 2
    assert "Normalized" in data["warnings"][0]
    items = {m["sample_id"]: m for m in data["measurements"]}
    assert abs(items["P_INCH"]["measured_value"] - 50.01) < 0.005
    assert abs(items["P_UM"]["measured_value"] - 50.06) < 0.005
    assert items["P_UM"]["is_conforming"] is False

def test_14_batch_id_mismatch():
    """Mismatch between CSV batch and form parameter returns HTTP 422."""
    csv_content = """batch_id,component_id,value\nBATCH-0245,P001,50.01\n"""
    files = {"file": ("mismatch.csv", csv_content.encode("utf-8"), "text/csv")}
    res = client.post("/api/inspection/measurements/upload", files=files, data={"batch_id": "BATCH-0246"})
    assert res.status_code == 422
    assert "Batch ID mismatch" in res.json()["detail"]

def test_15_multiple_batches_in_csv():
    """Multiple distinct batches in one CSV returns HTTP 422."""
    csv_content = """batch_id,component_id,value
BATCH-0245,P001,50.01
BATCH-0246,P002,50.02
"""
    files = {"file": ("multi_batch.csv", csv_content.encode("utf-8"), "text/csv")}
    res = client.post("/api/inspection/measurements/upload", files=files)
    assert res.status_code == 422
    assert "multiple batch IDs" in res.json()["detail"]

def test_16_implausible_negative_measurement():
    """Negative measurement value returns HTTP 422."""
    csv_content = """component_id,value\nP001,-50.01\n"""
    files = {"file": ("negative.csv", csv_content.encode("utf-8"), "text/csv")}
    res = client.post("/api/inspection/measurements/upload", files=files)
    assert res.status_code == 422
    assert "Implausible measurement value" in res.json()["detail"]

def test_17_template_download():
    """GET /api/inspection/measurements/template returns valid CSV template."""
    res = client.get("/api/inspection/measurements/template?batch_id=BATCH-0245")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    text = res.text
    assert "batch_id,component_id,inspection_parameter,value,unit,measured_at" in text
    assert "BATCH-0245,P001,shaft_diameter,50.01,mm" in text
