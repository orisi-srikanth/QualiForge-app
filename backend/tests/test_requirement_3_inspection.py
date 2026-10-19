import os
import io
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.security import create_access_token, UserRole
from backend.app.database.session import SessionLocal
from backend.app.database.models import Batch, Measurement, InspectionImage

client = TestClient(app)

FIXTURES_DIR = os.path.abspath("tests/fixtures/inspection_upload")

@pytest.fixture(scope="module")
def tokens():
    return {
        "admin": create_access_token({"sub": "admin@precisionaero.com", "role": UserRole.ADMIN.value}),
        "quality_engineer": create_access_token({"sub": "engineer@precisionaero.com", "role": UserRole.QUALITY_ENGINEER.value}),
        "operator": create_access_token({"sub": "operator@precisionaero.com", "role": UserRole.OPERATOR.value}),
    }

class TestRequirement3InspectionUpload:

    def test_01_csv_upload_good_and_spec_check(self, tokens):
        good_csv_path = os.path.join(FIXTURES_DIR, "good.csv")
        assert os.path.exists(good_csv_path), "good.csv fixture missing"

        with open(good_csv_path, "rb") as f:
            res = client.post(
                "/api/inspection/measurements/upload",
                headers={"Authorization": f"Bearer {tokens['quality_engineer']}"},
                data={"batch_id": "BATCH-0245"},
                files={"file": ("good.csv", f, "text/csv")}
            )

        assert res.status_code == 200, res.text
        data = res.json()
        assert data["status"] == "success"
        assert data["accepted_rows"] == 5
        assert data["spec_check"]["total_inspected"] == 5
        assert data["spec_check"]["accepted"] == 2
        assert data["spec_check"]["nonconforming"] == 3
        assert data["spec_check"]["rejection_rate_percent"] == 60.0

        spec_res = client.get("/api/inspection/BATCH-0245/spec-check")
        assert spec_res.status_code == 200
        spec_data = spec_res.json()
        assert spec_data["total_inspected"] == 5
        assert spec_data["accepted_count"] == 2
        assert spec_data["nonconforming_count"] == 3
        assert spec_data["rejection_rate_percent"] == 60.0

        nonconf_samples = [m["sample_id"] for m in spec_data["measurements"] if not m["is_conforming"]]
        assert sorted(nonconf_samples) == ["P003", "P004", "P005"]

    def test_02_excel_upload_good_and_multiple_sheets(self, tokens):
        good_xlsx_path = os.path.join(FIXTURES_DIR, "good.xlsx")
        assert os.path.exists(good_xlsx_path), "good.xlsx fixture missing"

        with open(good_xlsx_path, "rb") as f:
            res = client.post(
                "/api/inspection/measurements/upload",
                headers={"Authorization": f"Bearer {tokens['quality_engineer']}"},
                data={"batch_id": "BATCH-0245"},
                files={"file": ("good.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            )

        assert res.status_code == 200, res.text
        data = res.json()
        assert data["status"] == "success"
        assert data["accepted_rows"] == 5
        assert data["sheet_name"] == "Inspection_Data"
        assert data["spec_check"]["total_inspected"] == 5
        assert data["spec_check"]["accepted"] == 2
        assert data["spec_check"]["nonconforming"] == 3

    def test_03_manual_measurement_crud_and_spec_check(self, tokens):
        create_res = client.post(
            "/api/inspection/measurements",
            headers={"Authorization": f"Bearer {tokens['operator']}"},
            json={
                "batch_id": "BATCH-0245",
                "component_id": "P006",
                "value": 50.02,
                "unit": "mm"
            }
        )
        assert create_res.status_code == 201, create_res.text
        created = create_res.json()
        m_id = created["id"]
        assert created["component_id"] == "P006"
        assert created["is_conforming"] is True
        assert created["source_type"] == "manual"

        list_res = client.get("/api/inspection/measurements?batch_id=BATCH-0245")
        assert list_res.status_code == 200
        meas_list = list_res.json()
        assert any(m["id"] == m_id for m in meas_list)

        update_res = client.put(
            f"/api/inspection/measurements/{m_id}",
            headers={"Authorization": f"Bearer {tokens['operator']}"},
            json={"value": 50.09, "unit": "mm"}
        )
        assert update_res.status_code == 200, update_res.text
        updated = update_res.json()
        assert updated["value"] == 50.09
        assert updated["conformance_status"] == "nonconforming"

        del_res = client.delete(
            f"/api/inspection/measurements/{m_id}",
            headers={"Authorization": f"Bearer {tokens['operator']}"}
        )
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "DELETED"

    def test_04_image_upload_content_validation_and_vision_agent(self, tokens):
        png_path = os.path.join(FIXTURES_DIR, "normal.png")
        with open(png_path, "rb") as f:
            res_png = client.post(
                "/api/inspection/images/upload",
                headers={"Authorization": f"Bearer {tokens['quality_engineer']}"},
                data={"batch_id": "BATCH-0245", "component_id": "P001"},
                files={"file": ("normal.png", f, "image/png")}
            )
        assert res_png.status_code == 200, res_png.text
        png_data = res_png.json()
        assert png_data["status"] == "success"
        assert png_data["component_id"] == "P001"
        assert "vision_prediction" in png_data

        spoofed_path = os.path.join(FIXTURES_DIR, "spoofed_image.jpg")
        with open(spoofed_path, "rb") as f:
            res_spoofed = client.post(
                "/api/inspection/images/upload",
                headers={"Authorization": f"Bearer {tokens['quality_engineer']}"},
                data={"batch_id": "BATCH-0245", "component_id": "P002"},
                files={"file": ("spoofed_image.jpg", f, "image/jpeg")}
            )
        assert res_spoofed.status_code == 422
        assert "corrupted or not a valid image" in res_spoofed.text

        corrupt_path = os.path.join(FIXTURES_DIR, "corrupted.jpg")
        with open(corrupt_path, "rb") as f:
            res_corrupt = client.post(
                "/api/inspection/images/upload",
                headers={"Authorization": f"Bearer {tokens['quality_engineer']}"},
                data={"batch_id": "BATCH-0245", "component_id": "P003"},
                files={"file": ("corrupted.jpg", f, "image/jpeg")}
            )
        assert res_corrupt.status_code == 422
        assert "corrupted or not a valid image" in res_corrupt.text

        oversized_path = os.path.join(FIXTURES_DIR, "oversized.png")
        with open(oversized_path, "rb") as f:
            res_oversized = client.post(
                "/api/inspection/images/upload",
                headers={"Authorization": f"Bearer {tokens['quality_engineer']}"},
                data={"batch_id": "BATCH-0245", "component_id": "P004"},
                files={"file": ("oversized.png", f, "image/png")}
            )
        assert res_oversized.status_code == 413
        assert "exceeds maximum allowed limit" in res_oversized.text

    def test_05_missing_value_validation_and_reporting(self, tokens):
        missing_csv_path = os.path.join(FIXTURES_DIR, "missing.csv")
        with open(missing_csv_path, "rb") as f:
            res = client.post(
                "/api/inspection/measurements/upload",
                headers={"Authorization": f"Bearer {tokens['quality_engineer']}"},
                data={"batch_id": "BATCH-0245"},
                files={"file": ("missing.csv", f, "text/csv")}
            )

        assert res.status_code == 422
        detail = res.json()["detail"]
        assert detail["status"] == "rejected"
        assert len(detail["missing_values"]) >= 2

        mv_rows = [mv["row"] for mv in detail["missing_values"]]
        assert 3 in mv_rows
        assert 5 in mv_rows

    def test_06_unit_validation_conversions_and_independent_calc(self, tokens):
        inches_path = os.path.join(FIXTURES_DIR, "units_inches.csv")
        with open(inches_path, "rb") as f:
            res_in = client.post(
                "/api/inspection/measurements/upload",
                headers={"Authorization": f"Bearer {tokens['quality_engineer']}"},
                data={"batch_id": "BATCH-0245"},
                files={"file": ("units_inches.csv", f, "text/csv")}
            )
        assert res_in.status_code == 200, res_in.text
        in_data = res_in.json()
        assert len(in_data["unit_conversions"]) == 5
        first_conv = in_data["unit_conversions"][0]
        assert first_conv["sample_id"] == "P001"
        assert first_conv["original_unit"] == "in"
        expected_mm = round(1.9689 * 25.4, 4)
        assert first_conv["converted_value_mm"] == expected_mm

        microns_path = os.path.join(FIXTURES_DIR, "units_microns.csv")
        with open(microns_path, "rb") as f:
            res_um = client.post(
                "/api/inspection/measurements/upload",
                headers={"Authorization": f"Bearer {tokens['quality_engineer']}"},
                data={"batch_id": "BATCH-0245"},
                files={"file": ("units_microns.csv", f, "text/csv")}
            )
        assert res_um.status_code == 200, res_um.text
        um_data = res_um.json()
        assert len(um_data["unit_conversions"]) == 5
        assert um_data["unit_conversions"][0]["converted_value_mm"] == 50.01

        mixed_path = os.path.join(FIXTURES_DIR, "mixed_units.csv")
        with open(mixed_path, "rb") as f:
            res_mixed = client.post(
                "/api/inspection/measurements/upload",
                headers={"Authorization": f"Bearer {tokens['quality_engineer']}"},
                data={"batch_id": "BATCH-0245"},
                files={"file": ("mixed_units.csv", f, "text/csv")}
            )
        assert res_mixed.status_code == 200, res_mixed.text
        assert res_mixed.json()["accepted_rows"] == 5

        unknown_csv = b"component_id,diameter,unit\nP001,50.01,kg\n"
        res_unk = client.post(
            "/api/inspection/measurements/upload",
            headers={"Authorization": f"Bearer {tokens['quality_engineer']}"},
            data={"batch_id": "BATCH-0245"},
            files={"file": ("unknown_unit.csv", io.BytesIO(unknown_csv), "text/csv")}
        )
        assert res_unk.status_code == 422
        assert "Unsupported measurement unit 'kg'" in res_unk.text

    def test_07_validation_bad_file_types_and_bounds(self, tokens):
        bad_path = os.path.join(FIXTURES_DIR, "bad.csv")
        with open(bad_path, "rb") as f:
            res_bad = client.post(
                "/api/inspection/measurements/upload",
                headers={"Authorization": f"Bearer {tokens['quality_engineer']}"},
                data={"batch_id": "BATCH-0245"},
                files={"file": ("bad.csv", f, "text/csv")}
            )
        assert res_bad.status_code == 422
        bad_detail = res_bad.json()["detail"]
        assert len(bad_detail["errors"]) >= 4

        variants_path = os.path.join(FIXTURES_DIR, "header_variants.csv")
        with open(variants_path, "rb") as f:
            res_var = client.post(
                "/api/inspection/measurements/upload",
                headers={"Authorization": f"Bearer {tokens['quality_engineer']}"},
                data={"batch_id": "BATCH-0245"},
                files={"file": ("header_variants.csv", f, "text/csv")}
            )
        assert res_var.status_code == 200, res_var.text
        assert res_var.json()["accepted_rows"] == 5

        empty_path = os.path.join(FIXTURES_DIR, "empty.csv")
        with open(empty_path, "rb") as f:
            res_empty = client.post(
                "/api/inspection/measurements/upload",
                headers={"Authorization": f"Bearer {tokens['quality_engineer']}"},
                data={"batch_id": "BATCH-0245"},
                files={"file": ("empty.csv", f, "text/csv")}
            )
        assert res_empty.status_code == 422
        assert "contains no measurement rows" in res_empty.text

        corrupt_xlsx_path = os.path.join(FIXTURES_DIR, "corrupt.xlsx")
        with open(corrupt_xlsx_path, "rb") as f:
            res_corrupt_xl = client.post(
                "/api/inspection/measurements/upload",
                headers={"Authorization": f"Bearer {tokens['quality_engineer']}"},
                data={"batch_id": "BATCH-0245"},
                files={"file": ("corrupt.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            )
        assert res_corrupt_xl.status_code == 422
        assert "Malformed or corrupt Excel file" in res_corrupt_xl.text

        spoofed_csv_path = os.path.join(FIXTURES_DIR, "spoofed_text.csv")
        with open(spoofed_csv_path, "rb") as f:
            res_spoofed_csv = client.post(
                "/api/inspection/measurements/upload",
                headers={"Authorization": f"Bearer {tokens['quality_engineer']}"},
                data={"batch_id": "BATCH-0245"},
                files={"file": ("spoofed_text.csv", f, "text/csv")}
            )
        assert res_spoofed_csv.status_code == 422
        assert "not a valid delimited CSV table" in res_spoofed_csv.text

        large_path = os.path.join(FIXTURES_DIR, "large_50k.csv")
        with open(large_path, "rb") as f:
            res_large = client.post(
                "/api/inspection/measurements/upload",
                headers={"Authorization": f"Bearer {tokens['quality_engineer']}"},
                data={"batch_id": "BATCH-0245"},
                files={"file": ("large_50k.csv", f, "text/csv")}
            )
        assert res_large.status_code == 200
        assert res_large.json()["accepted_rows"] == 50000

    def test_08_roles_security_and_traceability(self, tokens):
        good_csv_path = os.path.join(FIXTURES_DIR, "good.csv")

        with open(good_csv_path, "rb") as f:
            res_unauth = client.post(
                "/api/inspection/measurements/upload",
                data={"batch_id": "BATCH-0245"},
                files={"file": ("good.csv", f, "text/csv")}
            )
        assert res_unauth.status_code == 200

        db = SessionLocal()
        try:
            b = db.query(Batch).filter(Batch.batch_number == "BATCH-0245").first()
            assert b is not None
            meas = db.query(Measurement).filter(Measurement.batch_id == b.id).all()
            assert len(meas) == 5
            for m in meas:
                assert m.source_type == "csv"
                assert m.file_name == "good.csv"
                assert m.uploaded_by is not None
                assert m.upload_time is not None
        finally:
            db.close()
