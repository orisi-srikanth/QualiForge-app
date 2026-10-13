"""
Inspection & Dimensional Compliance Endpoints (Agents 1 & 3)
100% deterministic evaluation of measurements against engineering limits (USL/LSL).
Supports CSV and Excel uploads, unit normalization, manual entry CRUD, and verified image intake.
"""
import io
import os
import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, UploadFile, File, Form, Response, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from PIL import Image

import html
from backend.app.database.session import get_db
from backend.app.database.models import Batch, Product, InspectionCharacteristic, Measurement, InspectionImage, QualityIncident, HumanDecision, VisualFinding
from backend.app.core.security import require_authenticated_user, require_authenticated_role
from backend.app.schemas.schemas import CertaintyLevel
from backend.app.agents.dimensional_agent import dimensional_agent
from backend.app.agents.visual_agent import visual_agent
from backend.app.services.inspection_service import (
    process_inspection_file,
    process_inspection_csv,
    generate_csv_template,
    get_batch_and_spec,
    SUPPORTED_UNITS
)


router = APIRouter()


class ManualInspectionPayload(BaseModel):
    batch_id: str = Field("BATCH-0245", json_schema_extra={"example": "BATCH-0245"})
    nominal_mm: float = Field(50.00, json_schema_extra={"example": 50.00})
    tolerance_mm: float = Field(0.05, json_schema_extra={"example": 0.05})
    measurements: List[Dict[str, Any]] = Field(
        default=[
            {"sample_id": "P001", "measured_value": 50.01},
            {"sample_id": "P002", "measured_value": 50.03},
            {"sample_id": "P003", "measured_value": 50.06},
            {"sample_id": "P004", "measured_value": 50.08},
            {"sample_id": "P005", "measured_value": 50.07}
        ],
        json_schema_extra={
            "example": [
                {"sample_id": "P001", "measured_value": 50.01},
                {"sample_id": "P002", "measured_value": 50.03},
                {"sample_id": "P003", "measured_value": 50.06},
                {"sample_id": "P004", "measured_value": 50.08},
                {"sample_id": "P005", "measured_value": 50.07}
            ]
        }
    )


class SingleMeasurementCreatePayload(BaseModel):
    batch_id: str = Field(..., description="Batch number or ID", json_schema_extra={"example": "BATCH-0245"})
    component_id: str = Field(..., description="Sample or piece identifier", json_schema_extra={"example": "P006"})
    value: float = Field(..., description="Measured dimensional value", json_schema_extra={"example": 50.02})
    unit: str = Field("mm", description="Measurement unit (mm, in, um, cm)", json_schema_extra={"example": "mm"})


class SingleMeasurementUpdatePayload(BaseModel):
    component_id: Optional[str] = Field(None, description="Sample identifier")
    value: Optional[float] = Field(None, description="Measured dimensional value")
    unit: Optional[str] = Field(None, description="Measurement unit")


# ==============================================================================
# 1. Measurement Upload Endpoints (CSV & Excel)
# ==============================================================================

@router.post(
    "/inspection/measurements/upload",
    tags=["Inspection"],
    summary="Upload inspection measurements (CSV or Excel)",
    description="Upload multipart CSV or Excel (.xlsx, .xls) file containing physical inspection measurements. Validates schema, converts units deterministically to mm, enforces bounds, records source traceability, and evaluates dimensional compliance."
)
async def upload_inspection_measurements(
    file: UploadFile = File(..., description="CSV or Excel inspection measurement file"),
    batch_id: Optional[str] = Form(None, description="Target batch identifier"),
    product_id: Optional[str] = Form(None, description="Product identifier for intake validation"),
    allow_partial: bool = Form(False, description="Whether to import valid rows when errors exist"),
    user: Dict[str, Any] = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
):
    content = await file.read()
    username = user.get("username", user.get("email", "operator"))
    result = process_inspection_file(
        file_bytes=content,
        filename=file.filename or "uploaded_inspection.csv",
        requested_batch_id=batch_id,
        db=db,
        user=username,
        allow_partial=allow_partial,
        product_id=product_id
    )
    return result


@router.post(
    "/inspection/upload-csv",
    tags=["Inspection"],
    summary="Upload inspection CSV (Alias)",
    description="Multi-format CSV intake with deterministic unit conversion and database persistence."
)
async def upload_csv_inspection(
    file: UploadFile = File(...),
    batch_id: Optional[str] = Form(None),
    user: Dict[str, Any] = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
):
    content = await file.read()
    username = user.get("username", user.get("email", "operator"))
    result = process_inspection_file(
        file_bytes=content,
        filename=file.filename or "uploaded_inspection.csv",
        requested_batch_id=batch_id,
        db=db,
        user=username
    )
    # Ensure backward compatibility structure
    result["batch_data"] = {
        "batch_id": result["batch_id"],
        "measurements": result["measurements"],
        "nominal_mm": result["specification"]["nominal_mm"],
        "tolerance_mm": result["specification"]["tolerance_mm"]
    }
    return result


@router.post(
    "/inspection/upload-excel",
    tags=["Inspection"],
    summary="Upload inspection Excel workbook (.xlsx, .xls)",
    description="Intake inspection data from Excel workbooks. Supports multiple sheets and cached formula evaluations without macro risks."
)
async def upload_excel_inspection(
    file: UploadFile = File(...),
    batch_id: Optional[str] = Form(None),
    user: Dict[str, Any] = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
):
    content = await file.read()
    username = user.get("username", user.get("email", "operator"))
    return process_inspection_file(
        file_bytes=content,
        filename=file.filename or "uploaded_inspection.xlsx",
        requested_batch_id=batch_id,
        db=db,
        user=username
    )


# ==============================================================================
# 2. Manual Measurement Entry Endpoints (CRUD)
# ==============================================================================

@router.get("/inspection/measurements", tags=["Inspection"], summary="List inspection measurements for a batch", description="Retrieves persisted dimensional measurements with source traceability (CSV, Excel, Manual).")
def list_batch_measurements(
    batch_id: str = Query("BATCH-0245", description="Target batch number or ID"),
    db: Session = Depends(get_db)
):
    b = db.query(Batch).filter((Batch.batch_number == batch_id) | (Batch.id == batch_id)).first()
    if not b:
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found.")

    measurements = db.query(Measurement).filter(Measurement.batch_id == b.id).order_by(Measurement.measured_at.asc()).all()
    return [
        {
            "id": m.id,
            "batch_id": b.batch_number,
            "component_id": m.component_id,
            "value": m.value,
            "unit": m.unit,
            "status": m.status,
            "deviation_from_limit": m.deviation_from_limit,
            "source_type": m.source_type or "manual",
            "file_name": m.file_name,
            "uploaded_by": m.uploaded_by,
            "upload_time": m.upload_time.strftime("%Y-%m-%d %H:%M:%S") if m.upload_time else None,
            "measured_at": m.measured_at.strftime("%Y-%m-%d %H:%M:%S") if m.measured_at else None,
        }
        for m in measurements
    ]


@router.post("/inspection/measurements", tags=["Inspection"], status_code=status.HTTP_201_CREATED, summary="Add single measurement manually", description="Manually register a single dimensional measurement. Validates unit, checks bounds, and links to batch spec.")
def add_manual_measurement(
    payload: SingleMeasurementCreatePayload,
    user: Dict[str, Any] = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
):
    b_id = payload.batch_id.strip()
    b = db.query(Batch).filter((Batch.batch_number == b_id) | (Batch.id == b_id)).first()
    if not b:
        raise HTTPException(status_code=404, detail=f"Batch '{b_id}' not found.")

    c_id = payload.component_id.strip()
    if not c_id:
        raise HTTPException(status_code=422, detail="Field 'component_id' is required.")

    # Unit validation
    unit_clean = payload.unit.strip().lower()
    if unit_clean not in SUPPORTED_UNITS:
        raise HTTPException(status_code=422, detail=f"Unsupported unit '{payload.unit}'. Supported units: mm, in, um, cm.")

    # Value normalization and bounds check
    mult = SUPPORTED_UNITS[unit_clean]
    val_mm = round(payload.value * mult, 4)

    if val_mm <= 0:
        raise HTTPException(status_code=422, detail=f"Measurement value must be strictly positive (> 0), received {val_mm} mm.")
    if val_mm > 1000.0:
        raise HTTPException(status_code=422, detail=f"Measurement value exceeds maximum threshold limit (1,000 mm), received {val_mm} mm.")

    # Get characteristic
    char = db.query(InspectionCharacteristic).filter(InspectionCharacteristic.product_id == b.product_id).first()
    if not char:
        nom = 50.00
        tol = 0.05
        usl = 50.05
        lsl = 49.95
    else:
        nom = char.nominal
        tol = char.tol_plus
        usl = char.usl
        lsl = char.lsl

    is_conforming = (lsl <= val_mm <= usl)
    dev_limit = round(val_mm - usl if val_mm > usl else (lsl - val_mm if val_mm < lsl else 0.0), 4)

    meas = Measurement(
        batch_id=b.id,
        characteristic_id=char.id if char else "char-manual",
        component_id=c_id,
        value=val_mm,
        unit="mm",
        status="conforming" if is_conforming else "nonconforming",
        deviation_from_limit=dev_limit,
        source_type="manual",
        file_name=None,
        uploaded_by=user.get("username", user.get("email", "operator")),
        upload_time=datetime.now(timezone.utc)
    )
    db.add(meas)
    db.commit()
    db.refresh(meas)

    # Automatic Quality Incident handling (Requirement 4 Check 7)
    if not is_conforming:
        inc = db.query(QualityIncident).filter(QualityIncident.batch_id == b.id).first()
        if not inc:
            inc = QualityIncident(
                batch_id=b.id,
                title="Dimensional Nonconformance flagged via manual measurement entry",
                defect_type="Oversized shaft diameter",
                severity="HIGH",
                status="open"
            )
            db.add(inc)
            db.commit()

    return {
        "status": "CREATED",
        "id": meas.id,
        "batch_id": b.batch_number,
        "component_id": meas.component_id,
        "value": meas.value,
        "unit": meas.unit,
        "original_value": payload.value,
        "original_unit": payload.unit,
        "is_conforming": is_conforming,
        "conformance_status": meas.status,
        "deviation_from_limit": meas.deviation_from_limit,
        "source_type": meas.source_type,
        "uploaded_by": meas.uploaded_by
    }


@router.put("/inspection/measurements/{measurement_id}", tags=["Inspection"], summary="Update single measurement", description="Edit an existing measurement value or unit with recalculation of tolerance compliance.")
def update_manual_measurement(
    measurement_id: str,
    payload: SingleMeasurementUpdatePayload,
    user: Dict[str, Any] = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
):
    meas = db.query(Measurement).filter(Measurement.id == measurement_id).first()
    if not meas:
        raise HTTPException(status_code=404, detail=f"Measurement '{measurement_id}' not found.")

    if payload.component_id is not None:
        c_clean = payload.component_id.strip()
        if not c_clean:
            raise HTTPException(status_code=422, detail="Component identifier cannot be empty.")
        meas.component_id = c_clean

    if payload.value is not None:
        unit_str = (payload.unit or meas.unit or "mm").strip().lower()
        if unit_str not in SUPPORTED_UNITS:
            raise HTTPException(status_code=422, detail=f"Unsupported unit '{unit_str}'.")
        mult = SUPPORTED_UNITS[unit_str]
        val_mm = round(payload.value * mult, 4)

        if val_mm <= 0:
            raise HTTPException(status_code=422, detail="Measurement value must be strictly positive (> 0).")
        if val_mm > 1000.0:
            raise HTTPException(status_code=422, detail="Measurement value exceeds maximum threshold limit (1,000 mm).")

        meas.value = val_mm
        meas.unit = "mm"

        # Re-evaluate conformance
        char = db.query(InspectionCharacteristic).filter(InspectionCharacteristic.id == meas.characteristic_id).first()
        usl = char.usl if char else 50.05
        lsl = char.lsl if char else 49.95

        is_conf = (lsl <= val_mm <= usl)
        meas.status = "conforming" if is_conf else "nonconforming"
        meas.deviation_from_limit = round(val_mm - usl if val_mm > usl else (lsl - val_mm if val_mm < lsl else 0.0), 4)

    db.commit()
    db.refresh(meas)

    # Automatic Quality Incident handling (Requirement 4 Check 7)
    if meas.status == "nonconforming":
        inc = db.query(QualityIncident).filter(QualityIncident.batch_id == meas.batch_id).first()
        if not inc:
            inc = QualityIncident(
                batch_id=meas.batch_id,
                title="Dimensional Nonconformance updated via manual measurement edit",
                defect_type="Oversized shaft diameter",
                severity="HIGH",
                status="open"
            )
            db.add(inc)
            db.commit()

    return {
        "status": "UPDATED",
        "id": meas.id,
        "component_id": meas.component_id,
        "value": meas.value,
        "unit": meas.unit,
        "conformance_status": meas.status,
        "deviation_from_limit": meas.deviation_from_limit
    }


@router.delete("/inspection/measurements/{measurement_id}", tags=["Inspection"], summary="Delete single measurement", description="Removes a measurement from the batch.")
def delete_manual_measurement(
    measurement_id: str,
    user: Dict[str, Any] = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
):
    meas = db.query(Measurement).filter(Measurement.id == measurement_id).first()
    if not meas:
        raise HTTPException(status_code=404, detail=f"Measurement '{measurement_id}' not found.")

    db.delete(meas)
    db.commit()
    return {"status": "DELETED", "id": measurement_id}


# ==============================================================================
# 3. Image Upload & Content Verification Endpoints (Agent 2)
# ==============================================================================

MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit

@router.post(
    "/inspection/images/upload",
    tags=["Inspection"],
    summary="Upload and inspect component image",
    description="Multipart image upload with real binary content validation (PIL Image verify), path traversal sanitization, size limit enforcement, duplicate tracking, and automated computer vision defect classification."
)
async def upload_inspection_image(
    file: UploadFile = File(..., description="High-resolution part image (PNG, JPEG, WEBP)"),
    batch_id: Optional[str] = Form("BATCH-0245", description="Target batch identifier"),
    component_id: Optional[str] = Form("P001", description="Component or piece identifier"),
    user: Dict[str, Any] = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
):
    content = await file.read()

    # 1. Size limit check
    if len(content) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image file size ({len(content)/(1024*1024):.2f} MB) exceeds maximum allowed limit ({MAX_IMAGE_SIZE_BYTES // (1024*1024)} MB)."
        )

    # 2. Content verification by reading magic bytes / PIL verify (rejects spoofed text files and corrupt images)
    try:
        pil_img = Image.open(io.BytesIO(content))
        pil_img.verify()
        img_format = pil_img.format.lower() if pil_img.format else "unknown"
        if img_format not in ("png", "jpeg", "jpg", "webp", "tiff", "bmp"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported image format '{img_format}'. Only PNG, JPEG, and WEBP are supported."
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid image content: file is corrupted or not a valid image format. ({str(e)})"
        )

    # 3. Safe filename generation (Guards against path traversal ../../)
    raw_name = os.path.basename(file.filename or "part_image.png")
    # Clean non-alphanumeric except dots and dashes
    clean_name = "".join(c for c in raw_name if c.isalnum() or c in ".-_")
    unique_prefix = uuid.uuid4().hex[:8]
    safe_filename = f"{unique_prefix}_{clean_name}"

    upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "uploads", "inspection"))
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, safe_filename)

    with open(file_path, "wb") as f:
        f.write(content)

    # 4. SHA-256 duplicate detection
    sha256 = hashlib.sha256(content).hexdigest()

    # 5. DB Persistence
    b_ref = batch_id or "BATCH-0245"
    db_batch = db.query(Batch).filter((Batch.batch_number == b_ref) | (Batch.id == b_ref)).first()
    batch_pk = db_batch.id if db_batch else b_ref

    img_record = InspectionImage(
        batch_id=batch_pk,
        component_id=component_id or "P001",
        file_path=file_path,
        file_name=raw_name,
        file_size_bytes=len(content),
        sha256_hash=sha256,
        uploaded_by=user.get("username", user.get("email", "operator")),
        uploaded_at=datetime.now(timezone.utc)
    )
    db.add(img_record)
    db.commit()
    db.refresh(img_record)

    # 6. Computer Vision Inspection (Agent 2)
    cv_res = visual_agent.inspect(
        image_path=file_path,
        batch_id=b_ref,
        image_id=f"IMG-{component_id or '001'}",
        category="precision_shaft"
    )

    return {
        "status": "success",
        "image_id": img_record.id,
        "batch_id": b_ref,
        "component_id": component_id or "P001",
        "safe_filename": safe_filename,
        "original_filename": raw_name,
        "file_size_bytes": len(content),
        "sha256_hash": sha256,
        "vision_prediction": cv_res
    }


@router.get("/inspection/images", tags=["Inspection"], summary="List inspection images for a batch", description="Retrieves registered component images and links to findings.")
def list_inspection_images(
    batch_id: str = Query("BATCH-0245", description="Batch identifier"),
    db: Session = Depends(get_db)
):
    db_batch = db.query(Batch).filter((Batch.batch_number == batch_id) | (Batch.id == batch_id)).first()
    b_pk = db_batch.id if db_batch else batch_id
    images = db.query(InspectionImage).filter(InspectionImage.batch_id == b_pk).order_by(InspectionImage.uploaded_at.desc()).all()
    return [
        {
            "id": img.id,
            "batch_id": batch_id,
            "component_id": img.component_id,
            "file_name": img.file_name or os.path.basename(img.file_path),
            "file_size_bytes": img.file_size_bytes,
            "sha256_hash": img.sha256_hash,
            "uploaded_at": img.uploaded_at.strftime("%Y-%m-%d %H:%M:%S") if img.uploaded_at else None,
            "uploaded_by": img.uploaded_by
        }
        for img in images
    ]


# ==============================================================================
# 4. Specification Check & Template Download Endpoints
# ==============================================================================

@router.get("/inspection/measurements/template", tags=["Inspection"], summary="Download inspection CSV template", description="Returns downloadable CSV template formatted with expected headers for inspection measurement intake.")
def download_inspection_template(batch_id: str = "BATCH-0245"):
    csv_text = generate_csv_template(batch_id=batch_id)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="inspection_template_{batch_id}.csv"'
        }
    )


@router.get(
    "/inspection/{batch_id}/spec-check",
    tags=["Inspection"],
    summary="Evaluate batch dimensional conformance and distribution",
    description="100% deterministic evaluation of batch measurements against engineering specification limits. Returns total inspected, accepted, nonconforming count, rejection %, distribution metrics (mean, sample std dev n-1, min, max, histogram bins), and nonconforming items.",
    responses={
        200: {
            "description": "Deterministic dimensional compliance evaluation result",
            "content": {
                "application/json": {
                    "example": {
                        "status": "EVALUATED",
                        "batch_id": "BATCH-0245",
                        "total_inspected": 5,
                        "accepted": 2,
                        "accepted_count": 2,
                        "nonconforming": 3,
                        "nonconforming_count": 3,
                        "rejection_rate_percent": 60.0,
                        "rejection_percentage": 60.0,
                        "max_deviation_from_limit": 0.03,
                        "max_deviation_mm": 0.03,
                        "mean": 50.05,
                        "mean_measured": 50.05,
                        "std_dev_sample": 0.029155,
                        "std_dev_pop": 0.026077,
                        "min": 50.01,
                        "max": 50.08,
                        "spec_limits": {
                            "nominal": 50.0,
                            "tolerance": 0.05,
                            "tolerance_plus": 0.05,
                            "tolerance_minus": 0.05,
                            "lsl": 49.95,
                            "usl": 50.05
                        },
                        "distribution": {
                            "mean": 50.05,
                            "std_dev_sample": 0.029155,
                            "std_dev_pop": 0.026077,
                            "min": 50.01,
                            "max": 50.08,
                            "bin_edges": [49.95, 50.0, 50.05, 50.1],
                            "counts": [0, 2, 3]
                        },
                        "histogram_bins": [
                            {"bin": "< 49.95 (Below LSL)", "count": 0, "is_out_of_spec": True, "color": "#EF4444"},
                            {"bin": "49.95 - 50.00 (Lower Spec)", "count": 0, "is_out_of_spec": False, "color": "#10B981"},
                            {"bin": "50.00 - 50.05 (Upper Spec)", "count": 2, "is_out_of_spec": False, "color": "#10B981"},
                            {"bin": "> 50.05 (Above USL)", "count": 3, "is_out_of_spec": True, "color": "#EF4444"}
                        ],
                        "nonconforming_items": [
                            {"sample_id": "P003", "measured_value": 50.06, "limit_breached": "EXCEEDS_USL", "deviation_from_limit": 0.01},
                            {"sample_id": "P004", "measured_value": 50.08, "limit_breached": "EXCEEDS_USL", "deviation_from_limit": 0.03},
                            {"sample_id": "P005", "measured_value": 50.07, "limit_breached": "EXCEEDS_USL", "deviation_from_limit": 0.02}
                        ],
                        "label": "Observed Fact",
                        "certainty": "Observed Fact",
                        "disposition_notice": "Observed sample result. Final physical product disposition is an authorized human decision. System does not automatically reject batches."
                    }
                }
            }
        }
    }
)
def get_batch_spec_check(batch_id: str = "BATCH-0245", db: Session = Depends(get_db)):
    spec_info = get_batch_and_spec(batch_id, db=db)
    nominal = spec_info.get("nominal_mm", 50.00) if spec_info else 50.00
    tolerance = spec_info.get("tolerance_mm", 0.05) if spec_info else 0.05
    tol_plus = spec_info.get("tolerance_plus", tolerance) if spec_info else tolerance
    tol_minus = spec_info.get("tolerance_minus", tolerance) if spec_info else tolerance
    usl = spec_info.get("usl_mm", 50.05) if spec_info else 50.05
    lsl = spec_info.get("lsl_mm", 49.95) if spec_info else 49.95

    # Check database measurements for this batch
    db_batch = db.query(Batch).filter((Batch.batch_number == batch_id) | (Batch.id == batch_id)).first()
    db_measurements = []
    if db_batch:
        db_m = db.query(Measurement).filter(Measurement.batch_id == db_batch.id).order_by(Measurement.component_id.asc()).all()
        if db_m:
            db_measurements = [{"sample_id": m.component_id, "measured_value": m.value} for m in db_m]

    if not db_measurements:
        return {
            "status": "NEEDS_DATA",
            "batch_id": batch_id,
            "message": f"Batch '{batch_id}' has no inspection measurements. Please upload an inspection CSV or Excel file, or enter manual measurements.",
            "total_inspected": 0,
            "accepted": 0,
            "accepted_count": 0,
            "nonconforming": 0,
            "nonconforming_count": 0,
            "rejection_rate_percent": 0.0,
            "rejection_percentage": 0.0,
            "max_deviation_from_limit": 0.0,
            "max_deviation_mm": 0.0,
            "measurements": [],
            "nonconforming_items": [],
            "spec_limits": {
                "nominal": nominal,
                "tolerance": tolerance,
                "tolerance_plus": tol_plus,
                "tolerance_minus": tol_minus,
                "lsl": lsl,
                "usl": usl
            },
            "distribution": {
                "mean": None,
                "std_dev_sample": 0.0,
                "std_dev_pop": 0.0,
                "min": None,
                "max": None,
                "bin_edges": [],
                "counts": []
            },
            "histogram_bins": [],
            "label": "Observed Fact",
            "certainty": "Observed Fact",
            "disposition_notice": "Observed sample result. Final physical product disposition is an authorized human decision. System does not automatically reject batches."
        }

    comp = dimensional_agent.evaluate_compliance(
        batch_id=batch_id,
        measurements=db_measurements,
        nominal_mm=nominal,
        tolerance_mm=tolerance,
        tol_plus=tol_plus,
        tol_minus=tol_minus,
        usl=usl,
        lsl=lsl
    )
    spec_data = comp["spec_data"]

    # Check 7: A nonconformance automatically creates or updates a quality incident
    if spec_data["nonconforming"] > 0 and db_batch:
        inc = db.query(QualityIncident).filter(QualityIncident.batch_id == db_batch.id).first()
        if not inc:
            inc = QualityIncident(
                batch_id=db_batch.id,
                title=f"Dimensional Nonconformance: {spec_data['nonconforming']}/{spec_data['total_inspected']} parts exceed engineering specification",
                defect_type="Oversized shaft diameter",
                severity="HIGH",
                status="open"
            )
            db.add(inc)
        else:
            inc.title = f"Dimensional Nonconformance: {spec_data['nonconforming']}/{spec_data['total_inspected']} parts exceed engineering specification"
            inc.status = "open"
        db.commit()

    return {
        "status": "EVALUATED",
        "batch_id": batch_id,
        "total_inspected": spec_data["total_inspected"],
        "accepted": spec_data["accepted"],
        "accepted_count": spec_data["accepted_count"],
        "nonconforming": spec_data["nonconforming"],
        "nonconforming_count": spec_data["nonconforming_count"],
        "rejection_rate_percent": spec_data["rejection_rate_percent"],
        "rejection_percentage": spec_data["rejection_percentage"],
        "max_deviation_from_limit": spec_data["max_deviation_from_limit"],
        "max_deviation_mm": spec_data["max_deviation_mm"],
        "mean": spec_data["mean"],
        "mean_measured": spec_data["mean_measured"],
        "std_dev_sample": spec_data["std_dev_sample"],
        "std_dev_pop": spec_data["std_dev_pop"],
        "min": spec_data["distribution"]["min"],
        "max": spec_data["distribution"]["max"],
        "spec_limits": spec_data["spec_limits"],
        "distribution": spec_data["distribution"],
        "histogram_bins": spec_data["histogram_bins"],
        "nonconforming_items": spec_data["nonconforming_items"],
        "trend_analysis": spec_data.get("trend_analysis"),
        "trend_direction": spec_data.get("trend_direction"),
        "trend_detected": spec_data.get("trend_detected"),
        "trend_slope": spec_data.get("trend_slope"),
        "trend_rule": spec_data.get("trend_rule"),
        "measurements": spec_data["measurements"],
        "excluded_count": spec_data.get("excluded_count", 0),
        "excluded_items": spec_data.get("excluded_items", []),
        "warnings": spec_data.get("warnings", []),
        "label": "Observed Fact",
        "certainty": "Observed Fact",
        "disposition_notice": "Observed sample result. Final physical product disposition is an authorized human decision. System does not automatically reject batches."
    }


@router.post("/inspection/evaluate", tags=["Inspection"], summary="Evaluate dimensional tolerance compliance", description="100% deterministic evaluation of sample measurements against engineering limits (USL/LSL).")
def evaluate_measurements(payload: ManualInspectionPayload):
    res = dimensional_agent.evaluate_compliance(
        batch_id=payload.batch_id,
        measurements=payload.measurements,
        nominal_mm=payload.nominal_mm,
        tolerance_mm=payload.tolerance_mm
    )
    return {"report": res["report"], "log": res["log"]}


class FindingDecisionPayload(BaseModel):
    finding_type: str = Field("dimensional", description="Type of finding: dimensional or visual", example="dimensional")
    decision: str = Field(..., description="Decision: CONFIRM or REJECT", example="CONFIRM")
    comment: Optional[str] = Field(None, description="Mandatory if REJECT", example="Confirmed dimensional nonconformance beyond upper spec limit.")


@router.post(
    "/inspection/findings/{finding_id}/decision",
    tags=["Inspection", "Workflows (Agents)"],
    summary="Confirm or reject dimensional or visual defect finding",
    description="Authorized Quality Engineer confirms or rejects defect finding. Enforces RBAC (operator gets 403, unauthenticated gets 401). Mandatory comment on rejection. Logs to human_decisions."
)
def decide_inspection_finding(
    finding_id: str,
    payload: FindingDecisionPayload,
    current_user: Dict[str, Any] = Depends(require_authenticated_role("quality_engineer", "admin")),
    db: Session = Depends(get_db)
):
    dec = payload.decision.upper().strip()
    if dec not in ["CONFIRM", "REJECT"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Decision must be CONFIRM or REJECT.")

    if dec == "REJECT" and (not payload.comment or not payload.comment.strip()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rejection requires a mandatory engineering justification/comment."
        )

    if payload.comment and len(payload.comment) > 2000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Comment exceeds maximum length of 2000 characters."
        )

    safe_comment = html.escape(payload.comment.strip()) if payload.comment else (
        f"Inspection finding {finding_id} {dec.lower()}ed by {current_user.get('name', 'Quality Engineer')}."
    )
    user_id = current_user.get("id", "usr-qe-01")
    f_type = payload.finding_type.lower().strip()

    if f_type == "dimensional":
        meas = db.query(Measurement).filter((Measurement.id == finding_id) | (Measurement.component_id == finding_id)).first()
        if not meas and not finding_id.startswith("DIM-") and not finding_id.startswith("MEAS-"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Dimensional finding '{finding_id}' not found.")
        if meas:
            if meas.status == "confirmed_nonconforming" and dec == "CONFIRM":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Measurement '{finding_id}' has already been confirmed.")
            if meas.status == "rejected_conforming" and dec == "REJECT":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Measurement '{finding_id}' has already been rejected.")
            meas.status = "confirmed_nonconforming" if dec == "CONFIRM" else "rejected_conforming"
    elif f_type == "visual":
        vis = db.query(VisualFinding).filter(VisualFinding.id == finding_id).first()
        if not vis and not finding_id.startswith("VF-"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Visual finding '{finding_id}' not found.")
        if vis:
            if vis.human_status == "confirmed" and dec == "CONFIRM":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Visual finding '{finding_id}' has already been confirmed.")
            if vis.human_status == "rejected" and dec == "REJECT":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Visual finding '{finding_id}' has already been rejected.")
            vis.human_status = "confirmed" if dec == "CONFIRM" else "rejected"
            vis.reviewer_id = user_id
            vis.comment = safe_comment
    else:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid finding_type '{payload.finding_type}'. Must be 'dimensional' or 'visual'.")

    # Log immutable decision into human_decisions table
    rec = HumanDecision(
        workflow_id=f"WF-FINDING-{finding_id}",
        entity_type=f"{f_type}_finding",
        entity_id=finding_id,
        decision=dec,
        comment=safe_comment,
        user_id=user_id,
        ts=datetime.now(timezone.utc)
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    return {
        "decision_id": rec.id,
        "finding_id": finding_id,
        "finding_type": f_type,
        "decision": dec,
        "status": "CONFIRMED" if dec == "CONFIRM" else "REJECTED",
        "epistemic_label": CertaintyLevel.OBSERVED_FACT.value if dec == "CONFIRM" else CertaintyLevel.HYPOTHESIS.value,
        "user": current_user.get("name", "Quality Engineer"),
        "role": current_user.get("role", "quality_engineer"),
        "comment": safe_comment,
        "timestamp": rec.ts.isoformat()
    }

