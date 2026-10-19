import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.security import create_access_token

client = TestClient(app)

def get_auth_headers(role: str, email: str = "test@precisionaero.com"):
    token = create_access_token({"sub": email, "role": role})
    return {"Authorization": f"Bearer {token}"}

admin_headers = get_auth_headers("admin", "admin@precisionaero.com")
qe_headers = get_auth_headers("quality_engineer", "engineer@precisionaero.com")
operator_headers = get_auth_headers("operator", "operator@precisionaero.com")

class TestRequirement1ProductProcessConfiguration:

    def test_01_machines_crud(self):
        payload = {
            "code": "CNC-04",
            "type": "DMG Mori NLX 2500/700 High-Precision Lathe",
            "location": "Cell B - Turning & Grinding"
        }
        res = client.post("/api/machines", json=payload, headers=admin_headers)
        assert res.status_code in [200, 201]

        res_list = client.get("/api/machines", headers=operator_headers)
        assert res_list.status_code == 200
        codes = [m.get("code") for m in res_list.json()]
        assert "CNC-04" in codes

    def test_02_product_crud_and_spec_limits(self):
        client.delete("/api/products/PS-2026-REGRESS", headers=admin_headers)

        prod_payload = {
            "name": "Precision Shaft Unit Test",
            "part_number": "PS-2026-REGRESS",
            "process": "CNC Turning",
            "material": "Carbon Steel AISI 1045",
            "family": "Precision Shafts",
            "machine_id": "CNC-04"
        }
        res = client.post("/api/products", json=prod_payload, headers=admin_headers)
        assert res.status_code == 201
        prod = res.json()
        prod_id = prod["product_id"]

        char_payload = {
            "name": "shaft_diameter",
            "unit": "mm",
            "nominal": 50.00,
            "tol_plus": 0.05,
            "tol_minus": 0.05,
            "inspection_frequency": "100% Critical Feature",
            "lsl": 10.0,
            "usl": 99.0
        }
        res_char = client.post(f"/api/products/{prod_id}/characteristics", json=char_payload, headers=admin_headers)
        assert res_char.status_code == 201
        char_data = res_char.json()
        assert char_data["lsl"] == 49.95
        assert char_data["usl"] == 50.05
        char_id = char_data["characteristic_id"]

        res_get = client.get(f"/api/products/{prod_id}", headers=operator_headers)
        assert res_get.status_code == 200
        assert res_get.json()["lsl"] == 49.95
        assert res_get.json()["usl"] == 50.05

        res_asym = client.put(f"/api/characteristics/{char_id}", json={"nominal": 50.00, "tol_plus": 0.10, "tol_minus": 0.05}, headers=admin_headers)
        assert res_asym.status_code == 200
        assert res_asym.json()["usl"] == 50.10
        assert res_asym.json()["lsl"] == 49.95

        res_onesided = client.put(f"/api/characteristics/{char_id}", json={"nominal": 50.00, "tol_plus": 0.05, "tol_minus": 0.00}, headers=admin_headers)
        assert res_onesided.status_code == 200
        assert res_onesided.json()["usl"] == 50.05
        assert res_onesided.json()["lsl"] == 50.00

        res_upd = client.put(f"/api/products/{prod_id}", json={"process": "CNC Turning & Grinding"}, headers=admin_headers)
        assert res_upd.status_code == 200
        assert res_upd.json()["manufacturing_process"] == "CNC Turning & Grinding"

        res_del = client.delete(f"/api/products/{prod_id}", headers=admin_headers)
        assert res_del.status_code == 200

    def test_03_validations(self):
        dup = client.post("/api/products", json={"name": "Duplicate", "part_number": "PS-2026-101", "process": "CNC"}, headers=admin_headers)
        assert dup.status_code == 409
        assert "already exists" in dup.text

        neg = client.post("/api/products/prod-ps-101/characteristics", json={"name": "test", "nominal": 50.0, "tol_plus": -0.05, "tol_minus": 0.05}, headers=admin_headers)
        assert neg.status_code == 422
        assert "non-negative" in neg.text

        missing = client.post("/api/products/prod-ps-101/characteristics", json={"name": "test", "tol_plus": 0.05, "tol_minus": 0.05}, headers=admin_headers)
        assert missing.status_code == 422

        unit_err = client.post("/api/products/prod-ps-101/characteristics", json={"name": "test", "nominal": 50.0, "unit": "kelvin", "tol_plus": 0.05, "tol_minus": 0.05}, headers=admin_headers)
        assert unit_err.status_code == 422
        assert "Unknown measurement unit" in unit_err.text

        chars = client.get("/api/products/prod-ps-101/characteristics", headers=admin_headers).json()
        char_id = chars[0]["characteristic_id"]
        zero_band = client.put(f"/api/characteristics/{char_id}", json={"nominal": 50.0, "tol_plus": 0.0, "tol_minus": 0.0}, headers=admin_headers)
        assert zero_band.status_code == 422
        assert "strictly greater" in zero_band.text

    def test_04_rbac_permissions(self):
        assert client.get("/api/products", headers=operator_headers).status_code == 200
        assert client.get("/api/machines", headers=operator_headers).status_code == 200

        client.delete("/api/products/PRD-TEMP-99", headers=operator_headers)
        post_res = client.post("/api/products", json={"name": "Temp Test Product", "part_number": "PRD-TEMP-99", "process": "CNC Turning"}, headers=operator_headers)
        assert post_res.status_code == 201
        temp_prod_id = post_res.json()["product_id"]

        assert client.put(f"/api/products/{temp_prod_id}", json={"process": "Modified"}, headers=operator_headers).status_code == 200
        assert client.delete(f"/api/products/{temp_prod_id}", headers=operator_headers).status_code == 200

        assert client.put("/api/products/prod-ps-101", json={"material": "Carbon Steel (AISI 1045)"}, headers=qe_headers).status_code == 200

    def test_05_integration_batch_0245_and_safe_delete(self):
        client.put("/api/products/prod-ps-101", json={"nominal": 50.00, "tol_plus": 0.05, "tol_minus": 0.05}, headers=admin_headers)

        res = client.get("/api/inspection/BATCH-0245/spec-check")
        assert res.status_code == 200
        data = res.json()
        assert data["nonconforming_count"] == 3
        assert data["accepted_count"] == 2
        nonconf_samples = [m["sample_id"] for m in data["measurements"] if not m.get("is_conforming", True) or m.get("status") == "NONCONFORMING"]
        assert set(nonconf_samples) == {"P003", "P004", "P005"}

        client.put("/api/products/prod-ps-101", json={"nominal": 50.00, "tol_plus": 0.10, "tol_minus": 0.10}, headers=admin_headers)
        res_relaxed = client.get("/api/inspection/BATCH-0245/spec-check")
        assert res_relaxed.json()["nonconforming_count"] == 0

        client.put("/api/products/prod-ps-101", json={"nominal": 50.00, "tol_plus": 0.05, "tol_minus": 0.05}, headers=admin_headers)
        res_restored = client.get("/api/inspection/BATCH-0245/spec-check")
        assert res_restored.json()["nonconforming_count"] == 3

        res_del = client.delete("/api/products/prod-ps-101", headers=admin_headers)
        assert res_del.status_code == 409
        assert "batches are linked" in res_del.text or "Traceability" in res_del.text
