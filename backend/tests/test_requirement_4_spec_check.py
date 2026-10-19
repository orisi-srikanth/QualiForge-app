import pytest
from unittest.mock import patch
import numpy as np
from decimal import Decimal

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.database.models import Batch, Product, InspectionCharacteristic, Measurement, QualityIncident
from backend.app.services.spec_check import SpecificationEngine
from backend.app.agents.dimensional_agent import dimensional_agent
from backend.app.agents.workflow import route_after_spc

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def auth_tokens(client):
    return {
        "admin": "mock-admin-token",
        "quality_engineer": "mock-qe-token",
        "operator": "mock-op-token"
    }

class TestRequirement4SpecChecking:

    def test_01_golden_dataset_batch_0245_conformance_and_independent_math(self, client):
        res = client.get("/api/inspection/BATCH-0245/spec-check")
        assert res.status_code == 200
        data = res.json()

        assert data["status"] == "EVALUATED"
        assert data["batch_id"] == "BATCH-0245"
        assert data["total_inspected"] == 5
        assert data["accepted"] == 2
        assert data["accepted_count"] == 2
        assert data["nonconforming"] == 3
        assert data["nonconforming_count"] == 3
        assert data["rejection_rate_percent"] == 60.0
        assert data["rejection_percentage"] == 60.0

        assert data["accepted"] + data["nonconforming"] == data["total_inspected"]
        assert round((data["nonconforming"] / data["total_inspected"]) * 100.0, 2) == data["rejection_rate_percent"]

        assert data["spec_limits"]["nominal"] == 50.0
        assert data["spec_limits"]["usl"] == 50.05
        assert data["spec_limits"]["lsl"] == 49.95

        nc_map = {item["sample_id"]: item for item in data["nonconforming_items"]}
        assert "P003" in nc_map
        assert "P004" in nc_map
        assert "P005" in nc_map
        assert nc_map["P003"]["deviation_from_limit"] == 0.01
        assert nc_map["P004"]["deviation_from_limit"] == 0.03
        assert nc_map["P005"]["deviation_from_limit"] == 0.02
        assert data["max_deviation_from_limit"] == 0.03

        raw_vals = [50.01, 50.03, 50.06, 50.08, 50.07]
        expected_mean = round(float(np.mean(raw_vals)), 4)
        expected_std_sample = round(float(np.std(raw_vals, ddof=1)), 6)
        assert data["mean"] == expected_mean
        assert data["std_dev_sample"] == expected_std_sample

    def test_02_boundaries_and_floating_point_precision(self):
        res_b = SpecificationEngine.evaluate_compliance(
            batch_id="TEST-B",
            nominal_mm=50.0,
            tol_plus=0.05,
            tol_minus=0.05,
            measurements=[
                {"sample_id": "P_USL", "measured_value": 50.05},
                {"sample_id": "P_LSL", "measured_value": 49.95}
            ]
        )
        assert res_b["total_inspected"] == 2
        assert res_b["accepted"] == 2
        assert res_b["nonconforming"] == 0

        res_trip = SpecificationEngine.evaluate_compliance(
            batch_id="TEST-TRIP",
            nominal_mm=50.0,
            tol_plus=0.05,
            tol_minus=0.05,
            measurements=[
                {"sample_id": "P_HIGH", "measured_value": 50.0501},
                {"sample_id": "P_LOW", "measured_value": 49.9499}
            ]
        )
        assert res_trip["total_inspected"] == 2
        assert res_trip["accepted"] == 0
        assert res_trip["nonconforming"] == 2
        assert res_trip["measurements"][0]["status"] == "EXCEEDS_USL"
        assert res_trip["measurements"][0]["deviation_from_limit"] == 0.0001
        assert res_trip["measurements"][1]["status"] == "BELOW_LSL"
        assert res_trip["measurements"][1]["deviation_from_limit"] == 0.0001

        res_noise = SpecificationEngine.evaluate_compliance(
            batch_id="TEST-NOISE",
            nominal_mm=50.0,
            tol_plus=0.05,
            tol_minus=0.05,
            measurements=[{"sample_id": "P_NOISE", "measured_value": 50.050000000000004}]
        )
        assert res_noise["measurements"][0]["is_conforming"] is True
        assert res_noise["accepted"] == 1

        res_sub = SpecificationEngine.evaluate_compliance(
            batch_id="TEST-SUB",
            nominal_mm=50.0,
            tol_plus=0.05,
            tol_minus=0.05,
            measurements=[{"sample_id": "P_SUB", "measured_value": 49.90}]
        )
        assert res_sub["measurements"][0]["is_conforming"] is False
        assert res_sub["measurements"][0]["status"] == "BELOW_LSL"
        assert res_sub["measurements"][0]["deviation_from_limit"] == 0.05

    def test_03_asymmetric_and_one_sided_tolerances(self):
        res_asym = SpecificationEngine.evaluate_compliance(
            batch_id="TEST-ASYM",
            nominal_mm=50.00,
            tol_plus=0.05,
            tol_minus=0.02,
            measurements=[
                {"sample_id": "P1", "measured_value": 49.99},
                {"sample_id": "P2", "measured_value": 49.97}
            ]
        )
        assert res_asym["usl"] == 50.05
        assert res_asym["lsl"] == 49.98
        assert res_asym["measurements"][0]["is_conforming"] is True
        assert res_asym["measurements"][1]["is_conforming"] is False
        assert res_asym["measurements"][1]["deviation_from_limit"] == 0.01

        res_upper = SpecificationEngine.evaluate_compliance(
            batch_id="TEST-UPPER",
            nominal_mm=50.0,
            tol_plus=0.05,
            tol_minus=None,
            measurements=[
                {"sample_id": "P1", "measured_value": 20.0},
                {"sample_id": "P2", "measured_value": 50.06}
            ]
        )
        assert res_upper["lsl"] is None
        assert res_upper["usl"] == 50.05
        assert res_upper["measurements"][0]["is_conforming"] is True
        assert res_upper["measurements"][1]["is_conforming"] is False

        res_lower = SpecificationEngine.evaluate_compliance(
            batch_id="TEST-LOWER",
            nominal_mm=50.0,
            tol_plus=None,
            tol_minus=0.05,
            measurements=[
                {"sample_id": "P1", "measured_value": 80.0},
                {"sample_id": "P2", "measured_value": 49.94}
            ]
        )
        assert res_lower["usl"] is None
        assert res_lower["lsl"] == 49.95
        assert res_lower["measurements"][0]["is_conforming"] is True
        assert res_lower["measurements"][1]["is_conforming"] is False

    def test_04_edge_cases_empty_single_conforming_nonconforming_dirty(self):
        res_empty = SpecificationEngine.evaluate_compliance("TEST-EMPTY", measurements=[])
        assert res_empty["total_inspected"] == 0
        assert res_empty["accepted"] == 0
        assert res_empty["nonconforming"] == 0
        assert res_empty["rejection_rate_percent"] == 0.0
        assert res_empty["status"] == "NO_DATA"

        res_single = SpecificationEngine.evaluate_compliance("TEST-SINGLE", measurements=[{"value": 50.02}])
        assert res_single["total_inspected"] == 1
        assert res_single["accepted"] == 1
        assert res_single["std_dev_sample"] == 0.0

        res_all_c = SpecificationEngine.evaluate_compliance("TEST-ALL-C", measurements=[{"value": 50.01}, {"value": 50.02}])
        assert res_all_c["total_inspected"] == 2
        assert res_all_c["accepted"] == 2
        assert res_all_c["nonconforming"] == 0
        assert res_all_c["rejection_rate_percent"] == 0.0

        res_all_nc = SpecificationEngine.evaluate_compliance("TEST-ALL-NC", measurements=[{"value": 50.06}, {"value": 50.08}])
        assert res_all_nc["total_inspected"] == 2
        assert res_all_nc["accepted"] == 0
        assert res_all_nc["nonconforming"] == 2
        assert res_all_nc["rejection_rate_percent"] == 100.0

        res_dirty = SpecificationEngine.evaluate_compliance("TEST-DIRTY", measurements=[
            {"sample_id": "P1", "value": 50.01},
            {"sample_id": "P2", "value": None},
            {"sample_id": "P3", "value": "BAD_TEXT"},
            {"sample_id": "P4", "value": 50.03}
        ])
        assert res_dirty["total_inspected"] == 2
        assert res_dirty["excluded_count"] == 2
        assert len(res_dirty["warnings"]) == 2

    def test_05_dynamic_specification_change_and_persistence(self, client):
        db = SessionLocal()
        b = db.query(Batch).filter(Batch.batch_number == "BATCH-0245").first()
        char = db.query(InspectionCharacteristic).filter(InspectionCharacteristic.product_id == b.product_id).first()

        try:
            char.tol_plus = 0.10
            char.tol_minus = 0.10
            char.usl = 50.10
            char.lsl = 49.90
            db.commit()

            res = client.get("/api/inspection/BATCH-0245/spec-check")
            assert res.status_code == 200
            data = res.json()
            assert data["spec_limits"]["usl"] == 50.10
            assert data["spec_limits"]["lsl"] == 49.90
            assert data["accepted"] == 5
            assert data["nonconforming"] == 0
            assert data["rejection_rate_percent"] == 0.0

        finally:
            char.tol_plus = 0.05
            char.tol_minus = 0.05
            char.usl = 50.05
            char.lsl = 49.95
            db.commit()
            db.close()

        res_restored = client.get("/api/inspection/BATCH-0245/spec-check")
        assert res_restored.status_code == 200
        data_restored = res_restored.json()
        assert data_restored["spec_limits"]["usl"] == 50.05
        assert data_restored["accepted"] == 2
        assert data_restored["nonconforming"] == 3
        assert data_restored["rejection_rate_percent"] == 60.0

    def test_06_agent_3_deterministic_llm_mock_immunity(self):
        data = [
            {"sample_id": "P001", "measured_value": 50.01},
            {"sample_id": "P002", "measured_value": 50.03},
            {"sample_id": "P003", "measured_value": 50.06},
            {"sample_id": "P004", "measured_value": 50.08},
            {"sample_id": "P005", "measured_value": 50.07},
        ]

        with patch("backend.app.core.llm.UniversalLLMClient.chat", return_value="NONSENSE_HALLUCINATION_99999"):
            res = dimensional_agent.evaluate_compliance(
                batch_id="BATCH-0245",
                measurements=data,
                nominal_mm=50.00,
                tolerance_mm=0.05
            )
            rep = res["report"]
            assert rep.total_inspected == 5
            assert rep.accepted == 2
            assert rep.nonconforming == 3
            assert rep.rejection_rate_percent == 60.0

    def test_07_quality_incident_creation_and_workflow_routing(self, client):
        res = client.get("/api/inspection/BATCH-0245/spec-check")
        assert res.status_code == 200

        db = SessionLocal()
        b = db.query(Batch).filter(Batch.batch_number == "BATCH-0245").first()
        inc = db.query(QualityIncident).filter(QualityIncident.batch_id == b.id).first()
        assert inc is not None
        assert inc.defect_type == "Oversized shaft diameter"
        assert inc.severity == "HIGH"
        db.close()

        route_conforming = route_after_spc({"has_defects": False, "has_anomalies": False})
        assert route_conforming == "final_report"

        route_nonconforming = route_after_spc({"has_defects": True, "has_anomalies": False})
        assert route_nonconforming == "root_cause_analysis"

    def test_08_histogram_bins_and_epistemic_labelling(self, client):
        res = client.get("/api/inspection/BATCH-0245/spec-check")
        assert res.status_code == 200
        data = res.json()

        assert data["label"] == "Observed Fact"
        assert "Observed sample result" in data["disposition_notice"]
        assert "human decision" in data["disposition_notice"]

        bins = data["histogram_bins"]
        assert len(bins) == 4
        assert bins[2]["count"] == 2
        assert bins[2]["is_out_of_spec"] is False
        assert bins[3]["count"] == 3
        assert bins[3]["is_out_of_spec"] is True
        assert bins[3]["color"] == "#EF4444"
