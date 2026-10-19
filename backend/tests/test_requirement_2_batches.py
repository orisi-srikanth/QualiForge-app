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

class TestRequirement2BatchRegistration:

    def test_01_batch_crud_as_quality_engineer(self):
        client.delete("/api/batches/BATCH-TEST-QE", headers=admin_headers)

        payload = {
            "batch_number": "BATCH-TEST-QE",
            "product_id": "PS-2026-101",
            "machine": "CNC-04",
            "shift": "Night",
            "quantity": 500,
            "start_time": "2026-10-10 02:00:00",
            "end_time": "2026-10-10 06:30:00",
            "material_lot": "LOT-CS-9842",
            "operator_ref": "J. Smith (OP-44)",
            "status": "QUALITY_HOLD"
        }
        res = client.post("/api/batches", json=payload, headers=qe_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["batch_number"] == "BATCH-TEST-QE"
        assert data["quantity"] == 500
        assert data["shift"] == "Night"

        res_get = client.get("/api/batches/BATCH-TEST-QE", headers=qe_headers)
        assert res_get.status_code == 200
        assert res_get.json()["batch_number"] == "BATCH-TEST-QE"

        res_upd = client.put("/api/batches/BATCH-TEST-QE", json={"quantity": 550, "operator_ref": "M. Davis (OP-12)"}, headers=qe_headers)
        assert res_upd.status_code == 200
        assert res_upd.json()["quantity"] == 550
        assert res_upd.json()["operator"] == "M. Davis (OP-12)"

        res_list = client.get("/api/batches", headers=qe_headers)
        assert res_list.status_code == 200
        batch_numbers = [b["batch_number"] for b in res_list.json()]
        assert "BATCH-TEST-QE" in batch_numbers

        res_del = client.delete("/api/batches/BATCH-TEST-QE", headers=admin_headers)
        assert res_del.status_code == 200

    def test_02_foreign_key_validations(self):
        valid_payload = {
            "batch_number": "BATCH-FK-TEST",
            "product_id": "PS-2026-101",
            "machine": "CNC-04",
            "shift": "Night",
            "quantity": 500,
            "material_lot": "LOT-CS-9842"
        }

        bad_prod = dict(valid_payload, product_id="NON-EXISTENT-PART")
        res_prod = client.post("/api/batches", json=bad_prod, headers=qe_headers)
        assert res_prod.status_code == 404
        assert "does not exist in master product catalog" in res_prod.text

        bad_mach = dict(valid_payload, machine="UNKNOWN-MACHINE-99")
        res_mach = client.post("/api/batches", json=bad_mach, headers=qe_headers)
        assert res_mach.status_code == 404
        assert "does not exist in factory machine catalog" in res_mach.text

    def test_03_field_validations(self):
        base_payload = {
            "batch_number": "BATCH-VAL-TEST",
            "product_id": "PS-2026-101",
            "machine": "CNC-04",
            "shift": "Night",
            "quantity": 500,
            "material_lot": "LOT-CS-9842",
            "start_time": "2026-10-10 02:00:00",
            "end_time": "2026-10-10 06:30:00"
        }

        dup = client.post("/api/batches", json=dict(base_payload, batch_number="BATCH-0245"), headers=qe_headers)
        assert dup.status_code == 409
        assert "already exists" in dup.text

        zero_qty = client.post("/api/batches", json=dict(base_payload, quantity=0), headers=qe_headers)
        assert zero_qty.status_code == 422
        assert "strictly positive" in zero_qty.text

        neg_qty = client.post("/api/batches", json=dict(base_payload, quantity=-10), headers=qe_headers)
        assert neg_qty.status_code == 422

        bad_times = client.post("/api/batches", json=dict(base_payload, start_time="2026-10-10 06:00:00", end_time="2026-10-10 02:00:00"), headers=qe_headers)
        assert bad_times.status_code == 422
        assert "earlier than start time" in bad_times.text

        bad_shift = client.post("/api/batches", json=dict(base_payload, shift="Twilight"), headers=qe_headers)
        assert bad_shift.status_code == 422
        assert "Allowed shifts" in bad_shift.text or "Permitted shifts" in bad_shift.text

        no_lot = client.post("/api/batches", json=dict(base_payload, material_lot=""), headers=qe_headers)
        assert no_lot.status_code == 422

        empty_op = client.post("/api/batches", json=dict(base_payload, batch_number="BATCH-EMPTY-OP-REG", operator_ref=""), headers=qe_headers)
        assert empty_op.status_code == 201
        client.delete("/api/batches/BATCH-EMPTY-OP-REG", headers=admin_headers)

    def test_04_role_based_access_control(self):
        payload = {
            "batch_number": "BATCH-RBAC-TEST",
            "product_id": "PS-2026-101",
            "machine": "CNC-04",
            "shift": "Morning",
            "quantity": 100,
            "material_lot": "LOT-CS-1111"
        }

        res_create = client.post("/api/batches", json=payload)
        assert res_create.status_code == 201

        res_edit = client.put("/api/batches/BATCH-RBAC-TEST", json={"quantity": 120})
        assert res_edit.status_code == 200
        assert res_edit.json()["quantity"] == 120

        assert client.delete("/api/batches/BATCH-RBAC-TEST").status_code == 200

    def test_05_persistence_and_filtering(self):
        res_p = client.get("/api/batches?product=PS-2026-101")
        assert res_p.status_code == 200
        assert len(res_p.json()) > 0
        assert all("PS-2026-101" in b["part_number"] for b in res_p.json())

        res_m = client.get("/api/batches?machine=CNC-04")
        assert res_m.status_code == 200
        assert all(b["machine"] == "CNC-04" for b in res_m.json())

        res_s = client.get("/api/batches?shift=Night")
        assert res_s.status_code == 200
        assert all("Night" in b["shift"] for b in res_s.json())

        res_page = client.get("/api/batches?page=1&page_size=3")
        assert res_page.status_code == 200
        assert len(res_page.json()) <= 3

    def test_06_integration_and_traceability_guards(self):
        res_spec = client.get("/api/inspection/BATCH-0245/spec-check")
        assert res_spec.status_code == 200
        assert res_spec.json()["spec_limits"]["nominal"] == 50.00
        assert res_spec.json()["spec_limits"]["usl"] == 50.05
        assert res_spec.json()["spec_limits"]["lsl"] == 49.95

        res_proc = client.get("/api/process/telemetry?batch_id=BATCH-0245")
        assert res_proc.status_code == 200
        assert res_proc.json()["report"]["machine"] == "CNC-04"

        client.delete("/api/batches/BATCH-EMPTY-INTEG", headers=admin_headers)
        empty_payload = {
            "batch_number": "BATCH-EMPTY-INTEG",
            "product_id": "PS-2026-101",
            "machine": "CNC-04",
            "shift": "Morning",
            "quantity": 250,
            "material_lot": "LOT-CS-9999"
        }
        client.post("/api/batches", json=empty_payload, headers=qe_headers)

        res_empty = client.get("/api/inspection/BATCH-EMPTY-INTEG/spec-check")
        assert res_empty.status_code == 200
        assert res_empty.json()["status"] == "NEEDS_DATA"
        assert "no inspection measurements" in res_empty.json()["message"].lower()

        client.delete("/api/batches/BATCH-EMPTY-INTEG", headers=admin_headers)

        res_del_linked = client.delete("/api/batches/BATCH-0245", headers=admin_headers)
        assert res_del_linked.status_code == 409
        assert "measurements are linked" in res_del_linked.text or "Traceability" in res_del_linked.text

        res_upd_linked = client.put("/api/batches/BATCH-0245", json={"product_id": "BH-2026-202"}, headers=qe_headers)
        assert res_upd_linked.status_code == 409
        assert "Cannot reassign product" in res_upd_linked.text
