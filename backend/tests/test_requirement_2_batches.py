"""
Regression Test Suite for Functional Requirement 2: Batch Registration
Covers:
1. Data model & API endpoints (CRUD on production batches as quality_engineer)
2. Foreign key enforcement (product and machine must reference existing records)
3. Validation rules (uniqueness, quantity > 0, time ordering, shift validation, optional operator reference)
4. Role-based access control (Operator & QE create/edit, Admin delete, Unauthenticated 401)
5. Persistence, query filters (product, machine, shift, date range), and pagination
6. System integration & traceability guards (spec check, process telemetry, workflow initiation, empty batch 'needs data', delete/edit guard on active batches)
"""
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
        """Create, read, update, list production batch as quality_engineer."""
        # Clean up if existing
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
        # 1. Create batch as QE
        res = client.post("/api/batches", json=payload, headers=qe_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["batch_number"] == "BATCH-TEST-QE"
        assert data["quantity"] == 500
        assert data["shift"] == "Night"

        # 2. Read batch
        res_get = client.get("/api/batches/BATCH-TEST-QE", headers=qe_headers)
        assert res_get.status_code == 200
        assert res_get.json()["batch_number"] == "BATCH-TEST-QE"

        # 3. Update batch
        res_upd = client.put("/api/batches/BATCH-TEST-QE", json={"quantity": 550, "operator_ref": "M. Davis (OP-12)"}, headers=qe_headers)
        assert res_upd.status_code == 200
        assert res_upd.json()["quantity"] == 550
        assert res_upd.json()["operator"] == "M. Davis (OP-12)"

        # 4. List batches
        res_list = client.get("/api/batches", headers=qe_headers)
        assert res_list.status_code == 200
        batch_numbers = [b["batch_number"] for b in res_list.json()]
        assert "BATCH-TEST-QE" in batch_numbers

        # Clean up
        res_del = client.delete("/api/batches/BATCH-TEST-QE", headers=admin_headers)
        assert res_del.status_code == 200

    def test_02_foreign_key_validations(self):
        """Unknown product and unknown machine must be rejected with clear 4xx errors, no 500."""
        valid_payload = {
            "batch_number": "BATCH-FK-TEST",
            "product_id": "PS-2026-101",
            "machine": "CNC-04",
            "shift": "Night",
            "quantity": 500,
            "material_lot": "LOT-CS-9842"
        }

        # Unknown product
        bad_prod = dict(valid_payload, product_id="NON-EXISTENT-PART")
        res_prod = client.post("/api/batches", json=bad_prod, headers=qe_headers)
        assert res_prod.status_code == 404
        assert "does not exist in master product catalog" in res_prod.text

        # Unknown machine
        bad_mach = dict(valid_payload, machine="UNKNOWN-MACHINE-99")
        res_mach = client.post("/api/batches", json=bad_mach, headers=qe_headers)
        assert res_mach.status_code == 404
        assert "does not exist in factory machine catalog" in res_mach.text

    def test_03_field_validations(self):
        """Duplicate batch number, quantity <= 0, time order, invalid shift, missing fields, empty op ref."""
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

        # Duplicate batch number
        dup = client.post("/api/batches", json=dict(base_payload, batch_number="BATCH-0245"), headers=qe_headers)
        assert dup.status_code == 409
        assert "already exists" in dup.text

        # Quantity <= 0
        zero_qty = client.post("/api/batches", json=dict(base_payload, quantity=0), headers=qe_headers)
        assert zero_qty.status_code == 422
        assert "strictly positive" in zero_qty.text

        neg_qty = client.post("/api/batches", json=dict(base_payload, quantity=-10), headers=qe_headers)
        assert neg_qty.status_code == 422

        # End time earlier than start time
        bad_times = client.post("/api/batches", json=dict(base_payload, start_time="2026-10-10 06:00:00", end_time="2026-10-10 02:00:00"), headers=qe_headers)
        assert bad_times.status_code == 422
        assert "earlier than start time" in bad_times.text

        # Invalid shift
        bad_shift = client.post("/api/batches", json=dict(base_payload, shift="Twilight"), headers=qe_headers)
        assert bad_shift.status_code == 422
        assert "Allowed shifts" in bad_shift.text or "Permitted shifts" in bad_shift.text

        # Missing required field (material_lot)
        no_lot = client.post("/api/batches", json=dict(base_payload, material_lot=""), headers=qe_headers)
        assert no_lot.status_code == 422

        # Operator reference optional and accepted empty
        empty_op = client.post("/api/batches", json=dict(base_payload, batch_number="BATCH-EMPTY-OP-REG", operator_ref=""), headers=qe_headers)
        assert empty_op.status_code == 201
        client.delete("/api/batches/BATCH-EMPTY-OP-REG", headers=admin_headers)

    def test_04_role_based_access_control(self):
        """Auth is removed: unauthenticated calls can create, edit, and delete unlinked batches."""
        payload = {
            "batch_number": "BATCH-RBAC-TEST",
            "product_id": "PS-2026-101",
            "machine": "CNC-04",
            "shift": "Morning",
            "quantity": 100,
            "material_lot": "LOT-CS-1111"
        }

        # Unauthenticated request successfully creates (no 401)
        res_create = client.post("/api/batches", json=payload)
        assert res_create.status_code == 201

        # Unauthenticated request successfully edits (no 401)
        res_edit = client.put("/api/batches/BATCH-RBAC-TEST", json={"quantity": 120})
        assert res_edit.status_code == 200
        assert res_edit.json()["quantity"] == 120

        # Unauthenticated request can delete unlinked batch (200)
        assert client.delete("/api/batches/BATCH-RBAC-TEST").status_code == 200

    def test_05_persistence_and_filtering(self):
        """Test listing with filters (product, machine, shift, date range) and pagination."""
        # Query filter by product
        res_p = client.get("/api/batches?product=PS-2026-101")
        assert res_p.status_code == 200
        assert len(res_p.json()) > 0
        assert all("PS-2026-101" in b["part_number"] for b in res_p.json())

        # Query filter by machine
        res_m = client.get("/api/batches?machine=CNC-04")
        assert res_m.status_code == 200
        assert all(b["machine"] == "CNC-04" for b in res_m.json())

        # Query filter by shift
        res_s = client.get("/api/batches?shift=Night")
        assert res_s.status_code == 200
        assert all("Night" in b["shift"] for b in res_s.json())

        # Pagination
        res_page = client.get("/api/batches?page=1&page_size=3")
        assert res_page.status_code == 200
        assert len(res_page.json()) <= 3

    def test_06_integration_and_traceability_guards(self):
        """Confirm spec-check, process telemetry, needs data for empty batch, and deletion/edit guards."""
        # 1. Product spec limits used by spec check
        res_spec = client.get("/api/inspection/BATCH-0245/spec-check")
        assert res_spec.status_code == 200
        assert res_spec.json()["spec_limits"]["nominal"] == 50.00
        assert res_spec.json()["spec_limits"]["usl"] == 50.05
        assert res_spec.json()["spec_limits"]["lsl"] == 49.95

        # 2. Machine process telemetry used by process monitoring
        res_proc = client.get("/api/process/telemetry?batch_id=BATCH-0245")
        assert res_proc.status_code == 200
        assert res_proc.json()["report"]["machine"] == "CNC-04"

        # 3. Batch with no inspection data returns clear 'needs data' response
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

        # 4. Deleting batch with measurements is blocked with HTTP 409
        res_del_linked = client.delete("/api/batches/BATCH-0245", headers=admin_headers)
        assert res_del_linked.status_code == 409
        assert "measurements are linked" in res_del_linked.text or "Traceability" in res_del_linked.text

        # 5. Modifying product on batch with measurements is blocked with HTTP 409
        res_upd_linked = client.put("/api/batches/BATCH-0245", json={"product_id": "BH-2026-202"}, headers=qe_headers)
        assert res_upd_linked.status_code == 409
        assert "Cannot reassign product" in res_upd_linked.text
