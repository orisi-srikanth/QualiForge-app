"""
Automated Verification Suite for QualiForge Agent 3 — Dimensional & Specification Compliance Agent
Standard: IATF 16949 Section 8.5.2 & ISO 9001 Section 8.5.6

Tests all 12 core requirements:
1. QE Product Specification Retrieval (nominal, tolerances, limits from actual DB catalog)
2. Deterministic USL/LSL and Boundary Evaluation (below-limit, exactly-at-lower-limit, nominal, exactly-at-upper-limit, above-limit)
3. Signed Deviations and Limit Breach Distance Calculation
4. Supported Unit Normalization (mm, in, um, cm) & Unsupported Unit Rejection
5. Required Columns, Missing Values, and Invalid Data Rejection
6. Unknown Batch 404 Verification
7. Rejection Percentage Calculation (valid inspected measurements as denominator)
8. Sequential Trend Identification Rule & Data Sufficiency (n >= 5)
9. Validation Against cmm_measurements.xlsx (10 measurements: 8 conforming, 2 nonconforming, 20% rejection)
10. Relational Database Persistence (Measurement records with batch association and source traceability)
11. Shared Workflow State Exposure & PDF Quality Report Generation
12. Autonomous Release/Rejection Prohibition (Human Review Disposition Safeguard)
"""
import io
import os
import pytest
import pandas as pd
from decimal import Decimal
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.database.models import Batch, Product, InspectionCharacteristic, Measurement, QualityIncident
from backend.app.services.spec_check import SpecificationEngine
from backend.app.services.inspection_service import process_inspection_file, get_batch_and_spec, SUPPORTED_UNITS
from backend.app.agents.dimensional_agent import dimensional_agent
from backend.app.orchestrator.state import WorkflowState
from backend.app.services.pdf_report import generate_quality_pdf_report
from backend.app.core.security import create_access_token, UserRole


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        token = create_access_token({"sub": "quality_engineer@precisionaero.com", "role": UserRole.QUALITY_ENGINEER.value})
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


@pytest.fixture(scope="module", autouse=True)
def restore_batch_0245_after_tests():
    """Teardown fixture ensuring BATCH-0245 golden baseline is restored after the test suite."""
    yield
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
                    file_name="golden_batch_0245.csv",
                    uploaded_by="quality_engineer@precisionaero.com"
                ))
            db.commit()
    finally:
        db.close()


class TestAgent3SpecificationRetrieval:
    """Requirement 1: Retrieve nominal dimensions, tolerances, and limits from actual QE configuration."""

    def test_01_retrieve_specifications_from_actual_qe_database(self):
        db = SessionLocal()
        try:
            # Test Precision Ground Shaft (PS-2026-101)
            spec_ps = dimensional_agent.retrieve_specification(batch_id="BATCH-0245", db=db)
            assert spec_ps["part_number"] == "PS-2026-101"
            assert spec_ps["nominal_mm"] == 50.00
            assert spec_ps["tolerance_mm"] == 0.05
            assert spec_ps["usl_mm"] == 50.05
            assert spec_ps["lsl_mm"] == 49.95
            assert spec_ps["parameter"] == "shaft_diameter"

            # Test Bearing Housing (BH-2026-202)
            spec_bh = dimensional_agent.retrieve_specification(product_id="prod-bh-202", db=db)
            assert spec_bh["part_number"] == "BH-2026-202"
            assert spec_bh["nominal_mm"] == 85.00
            assert spec_bh["tolerance_mm"] == 0.03
            assert spec_bh["usl_mm"] == 85.03
            assert spec_bh["lsl_mm"] == 84.97
            assert spec_bh["parameter"] == "bore_inner_diameter"

            # Test Flanged Bushing (FB-2026-303)
            spec_fb = dimensional_agent.retrieve_specification(product_id="prod-fb-303", db=db)
            assert spec_fb["part_number"] == "FB-2026-303"
            assert spec_fb["nominal_mm"] == 12.50
            assert spec_fb["tolerance_mm"] == 0.08
            assert spec_fb["usl_mm"] == 12.58
            assert spec_fb["lsl_mm"] == 12.42
            assert spec_fb["parameter"] == "flange_thickness"
        finally:
            db.close()


class TestAgent3DeterministicComplianceCalculations:
    """Requirements 4, 5, 6: Deterministic USL/LSL, boundary comparison, signed deviations, limit distance."""

    def test_02_deterministic_limits_and_boundary_cases(self):
        measurements = [
            {"sample_id": "P_BELOW", "measured_value": 49.90},   # Below LSL (nonconforming)
            {"sample_id": "P_AT_LSL", "measured_value": 49.95},  # Exactly at LSL (conforming)
            {"sample_id": "P_NOMINAL", "measured_value": 50.00}, # Nominal (conforming)
            {"sample_id": "P_AT_USL", "measured_value": 50.05},  # Exactly at USL (conforming)
            {"sample_id": "P_ABOVE", "measured_value": 50.08},   # Above USL (nonconforming)
            {"sample_id": "P_FLOAT_NOISE", "measured_value": 50.050000000000004}, # Float noise safe at USL
        ]

        res = SpecificationEngine.evaluate_compliance(
            batch_id="BATCH-TEST",
            nominal_mm=50.00,
            tol_plus=0.05,
            tol_minus=0.05,
            measurements=measurements
        )

        assert res["usl"] == 50.05
        assert res["lsl"] == 49.95
        assert res["total_inspected"] == 6
        assert res["accepted"] == 4
        assert res["nonconforming"] == 2

        item_map = {m["sample_id"]: m for m in res["measurements"]}

        # 1. Below limit: 49.90 mm
        p_below = item_map["P_BELOW"]
        assert p_below["is_conforming"] is False
        assert p_below["status"] == "BELOW_LSL"
        assert p_below["deviation_from_nominal"] == -0.1000
        assert p_below["deviation_from_limit"] == 0.0500  # 49.95 - 49.90

        # 2. Exactly at lower limit: 49.95 mm
        p_at_lsl = item_map["P_AT_LSL"]
        assert p_at_lsl["is_conforming"] is True
        assert p_at_lsl["status"] == "CONFORMING"
        assert p_at_lsl["deviation_from_nominal"] == -0.0500
        assert p_at_lsl["deviation_from_limit"] == 0.0000

        # 3. Nominal: 50.00 mm
        p_nom = item_map["P_NOMINAL"]
        assert p_nom["is_conforming"] is True
        assert p_nom["status"] == "CONFORMING"
        assert p_nom["deviation_from_nominal"] == 0.0000
        assert p_nom["deviation_from_limit"] == 0.0000

        # 4. Exactly at upper limit: 50.05 mm
        p_at_usl = item_map["P_AT_USL"]
        assert p_at_usl["is_conforming"] is True
        assert p_at_usl["status"] == "CONFORMING"
        assert p_at_usl["deviation_from_nominal"] == 0.0500
        assert p_at_usl["deviation_from_limit"] == 0.0000

        # 5. Above upper limit: 50.08 mm
        p_above = item_map["P_ABOVE"]
        assert p_above["is_conforming"] is False
        assert p_above["status"] == "EXCEEDS_USL"
        assert p_above["deviation_from_nominal"] == 0.0800
        assert p_above["deviation_from_limit"] == 0.0300  # 50.08 - 50.05

        # 6. Float boundary noise: 50.050000000000004 mm
        p_noise = item_map["P_FLOAT_NOISE"]
        assert p_noise["is_conforming"] is True
        assert p_noise["status"] == "CONFORMING"


class TestAgent3UnitHandlingAndNormalization:
    """Requirements 2 & 3: Normalize supported units (mm, in, um, cm) and reject unsupported/ambiguous units."""

    def test_03_unit_conversion_normalization(self):
        # CSV with inches, microns, and centimeters
        csv_content = (
            "component_id,value,unit\n"
            "C_INCH,1.9685039,in\n"    # 1.9685039 * 25.4 = 50.00 mm
            "C_MICRON,50000,um\n"      # 50000 * 0.001 = 50.00 mm
            "C_CM,5.00,cm\n"           # 5.00 * 10.0 = 50.00 mm
            "C_MM,50.02,mm\n"          # 50.02 mm
        )
        res = process_inspection_file(
            file_bytes=csv_content.encode("utf-8"),
            filename="unit_test.csv",
            requested_batch_id="BATCH-0245"
        )
        assert res["status"] == "success"
        assert res["total_inspected"] == 4
        assert res["accepted"] == 4
        assert res["nonconforming"] == 0

        conversions = {c["sample_id"]: c for c in res["unit_conversions"]}
        assert "C_INCH" in conversions
        assert conversions["C_INCH"]["converted_value_mm"] == 50.0
        assert conversions["C_MICRON"]["converted_value_mm"] == 50.0
        assert conversions["C_CM"]["converted_value_mm"] == 50.0

    def test_04_reject_unsupported_or_ambiguous_units(self):
        csv_unsupported = (
            "component_id,value,unit\n"
            "C_YARD,54.68,yards\n"
        )
        with pytest.raises(Exception) as exc_info:
            process_inspection_file(
                file_bytes=csv_unsupported.encode("utf-8"),
                filename="unsupported_unit.csv",
                requested_batch_id="BATCH-0245"
            )
        assert "Unsupported measurement unit" in str(exc_info.value) or exc_info.value.status_code == 422


class TestAgent3FileValidationMissingDataAndErrors:
    """Requirements 2 & 7: Validate columns, duplicate component identifiers, missing values, corrupt data."""

    def test_05_missing_required_columns(self):
        csv_bad = "batch_id,operator,notes\nBATCH-0245,OP-44,routine inspection notes\n"
        with pytest.raises(Exception) as exc:
            process_inspection_file(file_bytes=csv_bad.encode("utf-8"), filename="bad_cols.csv")
        assert exc.value.status_code == 422
        assert "Missing required columns" in str(exc.value.detail)

    def test_06_blank_or_null_measurement_values(self):
        csv_null = (
            "component_id,measured_value\n"
            "P001,50.01\n"
            "P002,\n"
            "P003,50.03\n"
        )
        with pytest.raises(Exception) as exc:
            process_inspection_file(file_bytes=csv_null.encode("utf-8"), filename="null_val.csv")
        assert exc.value.status_code == 422
        assert len(exc.value.detail["missing_values"]) > 0

    def test_07_invalid_non_numeric_values(self):
        csv_corrupt = (
            "component_id,measured_value\n"
            "P001,50.01\n"
            "P002,NOT_A_NUMBER\n"
        )
        with pytest.raises(Exception) as exc:
            process_inspection_file(file_bytes=csv_corrupt.encode("utf-8"), filename="corrupt.csv")
        assert exc.value.status_code == 422
        assert any("Invalid numeric measurement value" in e for e in exc.value.detail["errors"])

    def test_08_duplicate_component_identifiers(self):
        csv_dups = (
            "component_id,measured_value\n"
            "P001,50.01\n"
            "P001,50.03\n"
        )
        with pytest.raises(Exception) as exc:
            process_inspection_file(file_bytes=csv_dups.encode("utf-8"), filename="duplicate_ids.csv")
        assert exc.value.status_code == 422
        assert any("Duplicate component identifier" in e for e in exc.value.detail["errors"])

    def test_09_unknown_batch_returns_404(self):
        csv_content = "component_id,measured_value\nP001,50.01\n"
        db = SessionLocal()
        try:
            with pytest.raises(Exception) as exc:
                process_inspection_file(
                    file_bytes=csv_content.encode("utf-8"),
                    filename="unknown_batch.csv",
                    requested_batch_id="NONEXISTENT_UNKNOWN_BATCH_9999",
                    db=db
                )
            assert exc.value.status_code == 404
        finally:
            db.close()


class TestAgent3RejectionPercentageDenominatorLogic:
    """Requirement 7: Calculate rejection percentage using valid inspected measurements as denominator."""

    def test_10_rejection_percentage_calculation_with_valid_denominator(self):
        # 8 valid measurements: 6 conforming, 2 nonconforming -> 2/8 = 25.0%
        # plus 2 invalid rows handled by SpecificationEngine exclusion tracking
        raw_items = [
            {"sample_id": "S1", "measured_value": 50.00},
            {"sample_id": "S2", "measured_value": 50.01},
            {"sample_id": "S3", "measured_value": 50.02},
            {"sample_id": "S4", "measured_value": 50.03},
            {"sample_id": "S5", "measured_value": 50.04},
            {"sample_id": "S6", "measured_value": 50.05},
            {"sample_id": "S7", "measured_value": 50.08},  # Nonconforming 1
            {"sample_id": "S8", "measured_value": 49.92},  # Nonconforming 2
            {"sample_id": "S9", "measured_value": None},   # Excluded blank
            {"sample_id": "S10", "measured_value": "NAN"}, # Excluded non-numeric
        ]
        res = SpecificationEngine.evaluate_compliance(
            batch_id="BATCH-TEST-DENOM",
            nominal_mm=50.00,
            tol_plus=0.05,
            tol_minus=0.05,
            measurements=raw_items
        )

        assert res["total_inspected"] == 8  # Only valid inspected rows count in denominator
        assert res["accepted"] == 6
        assert res["nonconforming"] == 2
        assert res["rejection_rate_percent"] == 25.0
        assert res["excluded_count"] == 2


class TestAgent3SequentialTrendDetection:
    """Requirement 8: Trend identification toward specification limits and data sufficiency rule (n >= 5)."""

    def test_11_insufficient_data_does_not_claim_trend(self):
        few_values = [50.01, 50.02, 50.03]  # n = 3 < 5
        trend = SpecificationEngine.evaluate_trend(
            values=few_values,
            nominal_mm=50.00,
            usl=50.05,
            lsl=49.95,
            min_points_for_trend=5
        )
        assert trend["trend_detected"] is False
        assert trend["trend_direction"] == "INSUFFICIENT_DATA"
        assert trend["sample_count"] == 3
        assert "minimum 5 required" in trend["rule_description"]

    def test_12_detects_sequential_run_toward_usl(self):
        increasing_run = [50.01, 50.02, 50.03, 50.04, 50.05]  # 5 increasing measurements
        trend = SpecificationEngine.evaluate_trend(
            values=increasing_run,
            nominal_mm=50.00,
            usl=50.05,
            lsl=49.95
        )
        assert trend["trend_detected"] is True
        assert trend["trend_direction"] == "DRIFT_TOWARD_USL"
        assert trend["consecutive_direction"] == "INCREASING"
        assert trend["proximity_warning"] is True

    def test_13_detects_sequential_run_toward_lsl(self):
        decreasing_run = [49.99, 49.98, 49.97, 49.96, 49.95]  # 5 decreasing measurements
        trend = SpecificationEngine.evaluate_trend(
            values=decreasing_run,
            nominal_mm=50.00,
            usl=50.05,
            lsl=49.95
        )
        assert trend["trend_detected"] is True
        assert trend["trend_direction"] == "DRIFT_TOWARD_LSL"
        assert trend["consecutive_direction"] == "DECREASING"
        assert trend["proximity_warning"] is True

    def test_14_stable_distribution_flags_no_trend(self):
        stable_values = [50.00, 50.01, 49.99, 50.01, 50.00]
        trend = SpecificationEngine.evaluate_trend(
            values=stable_values,
            nominal_mm=50.00,
            usl=50.05,
            lsl=49.95
        )
        assert trend["trend_detected"] is False
        assert trend["trend_direction"] == "STABLE"


class TestAgent3CMMMeasurementsBenchmarkValidation:
    """
    Core Benchmark: Validate against cmm_measurements.xlsx
    Nominal: 50.00 mm, Tolerance: +/- 0.05 mm (LSL=49.95, USL=50.05).
    Expected Results: 10 measurements, 8 conforming, 2 nonconforming, 20% rejection.
    """

    def test_15_validate_cmm_measurements_excel_artifact(self):
        excel_path = "cmm_measurements.xlsx"
        if not os.path.exists(excel_path):
            excel_path = "backend/data/inspection/cmm_measurements.xlsx"
        assert os.path.exists(excel_path), f"cmm_measurements.xlsx not found at {excel_path}"

        with open(excel_path, "rb") as f:
            content = f.read()

        db = SessionLocal()
        try:
            res = process_inspection_file(
                file_bytes=content,
                filename="cmm_measurements.xlsx",
                requested_batch_id="BATCH-0245",
                db=db,
                user="qa_lead@precisionaero.com"
            )
            # Invariant checks
            assert res["status"] == "success"
            assert res["total_inspected"] == 10
            assert res["accepted"] == 8
            assert res["nonconforming"] == 2
            assert res["rejection_rate_percent"] == 20.0

            # Verify the two nonconforming components
            nc_items = [m for m in res["measurements"] if not m["is_conforming"]]
            assert len(nc_items) == 2
            nc_ids = {m["sample_id"] for m in nc_items}
            assert "COMP-005" in nc_ids  # 50.08 mm (0.03 mm above USL)
            assert "COMP-010" in nc_ids  # 50.06 mm (0.01 mm above USL)

            comp_005 = next(m for m in nc_items if m["sample_id"] == "COMP-005")
            assert comp_005["measured_value"] == 50.08
            assert comp_005["deviation_from_nominal"] == 0.08
            assert comp_005["deviation_from_limit"] == 0.03

            comp_010 = next(m for m in nc_items if m["sample_id"] == "COMP-010")
            assert comp_010["measured_value"] == 50.06
            assert comp_010["deviation_from_nominal"] == 0.06
            assert comp_010["deviation_from_limit"] == 0.01
        finally:
            db.close()


class TestAgent3DatabasePersistenceAndTraceability:
    """Requirement 9: Persist inspection results in database models (Measurement) with batch association."""

    def test_16_database_records_traceability_evidence(self):
        excel_path = "cmm_measurements.xlsx"
        if not os.path.exists(excel_path):
            excel_path = "backend/data/inspection/cmm_measurements.xlsx"

        with open(excel_path, "rb") as f:
            content = f.read()

        db = SessionLocal()
        try:
            # Process and persist to database
            process_inspection_file(
                file_bytes=content,
                filename="cmm_measurements.xlsx",
                requested_batch_id="BATCH-0245",
                db=db,
                user="auditor@qualitymind.com"
            )

            # Query database records directly
            db_batch = db.query(Batch).filter(Batch.batch_number == "BATCH-0245").first()
            assert db_batch is not None

            measurements = db.query(Measurement).filter(Measurement.batch_id == db_batch.id).all()
            assert len(measurements) == 10

            m_map = {m.component_id: m for m in measurements}
            assert "COMP-001" in m_map
            assert m_map["COMP-001"].value == 50.00
            assert m_map["COMP-001"].status == "conforming"
            assert m_map["COMP-001"].source_type == "excel"
            assert m_map["COMP-001"].file_name == "cmm_measurements.xlsx"
            assert m_map["COMP-001"].uploaded_by == "auditor@qualitymind.com"

            assert "COMP-005" in m_map
            assert m_map["COMP-005"].value == 50.08
            assert m_map["COMP-005"].status == "nonconforming"
            assert m_map["COMP-005"].deviation_from_limit == 0.03

            assert "COMP-010" in m_map
            assert m_map["COMP-010"].value == 50.06
            assert m_map["COMP-010"].status == "nonconforming"
            assert m_map["COMP-010"].deviation_from_limit == 0.01
        finally:
            db.close()


class TestAgent3WorkflowStateAndReportConsumption:
    """Requirements 10 & 11: Shared workflow state exposure and autonomous disposition safeguard."""

    def test_17_workflow_state_exposure_and_pdf_report_generation(self):
        excel_path = "cmm_measurements.xlsx"
        if not os.path.exists(excel_path):
            excel_path = "backend/data/inspection/cmm_measurements.xlsx"

        with open(excel_path, "rb") as f:
            content = f.read()

        res = process_inspection_file(
            file_bytes=content,
            filename="cmm_measurements.xlsx",
            requested_batch_id="BATCH-0245"
        )

        rep_dict = res["report"]

        # Populate WorkflowState
        wf = WorkflowState(
            workflow_id="wf-test-agent3",
            batch_id="BATCH-0245",
            status="RUNNING"
        )
        wf.batch_metadata = {
            "batch_id": "BATCH-0245",
            "part_number": "PS-2026-101",
            "nominal_mm": 50.00,
            "tolerance_mm": 0.05,
            "usl": 50.05,
            "lsl": 49.95
        }
        wf.dimensional_report = rep_dict

        # Verify downstream consumption in PDF Report Generator
        state_dict = wf.model_dump()
        pdf_bytes = generate_quality_pdf_report(state_dict)
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 1000
        assert pdf_bytes.startswith(b"%PDF")

    def test_18_autonomous_release_rejection_prohibition(self):
        """Requirement 11: Agent 3 must not autonomously release or reject the batch."""
        db = SessionLocal()
        try:
            batch = db.query(Batch).filter(Batch.batch_number == "BATCH-0245").first()
            assert batch is not None
            # After inspection with nonconformances, batch status must remain QUALITY_HOLD
            # and not autonomously flipped to REJECTED or APPROVED
            assert batch.status == "QUALITY_HOLD"

            comp_res = dimensional_agent.evaluate_compliance(
                batch_id="BATCH-0245",
                measurements=[{"sample_id": "P1", "measured_value": 50.08}],
                nominal_mm=50.00,
                tolerance_mm=0.05
            )
            assert "disposition_notice" in comp_res
            assert "authorized" in comp_res["disposition_notice"].lower()
            assert "does not automatically reject" in comp_res["spec_data"]["disposition_notice"].lower()
        finally:
            db.close()


class TestAgent3LiveEndpoint:
    """Live API Endpoint verification for /api/inspection/measurements/upload and /api/inspection/{batch_id}/spec-check."""

    def test_19_live_multipart_upload_endpoint(self, client):
        excel_path = "cmm_measurements.xlsx"
        if not os.path.exists(excel_path):
            excel_path = "backend/data/inspection/cmm_measurements.xlsx"

        with open(excel_path, "rb") as f:
            file_bytes = f.read()

        response = client.post(
            "/api/inspection/measurements/upload",
            files={"file": ("cmm_measurements.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"batch_id": "BATCH-0245"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["total_inspected"] == 10
        assert data["accepted"] == 8
        assert data["nonconforming"] == 2
        assert data["rejection_rate_percent"] == 20.0

    def test_20_live_spec_check_endpoint(self, client):
        res = client.get("/api/inspection/BATCH-0245/spec-check")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "EVALUATED"
        assert data["batch_id"] == "BATCH-0245"
        assert data["total_inspected"] == 10
        assert data["accepted"] == 8
        assert data["nonconforming"] == 2
        assert data["rejection_rate_percent"] == 20.0
        assert "trend_analysis" in data
        assert "trend_direction" in data
