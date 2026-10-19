import os
from fastapi import APIRouter, Response, Depends, Query, HTTPException
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.app.services.pdf_report import generate_quality_pdf_report
from backend.app.orchestrator.engine import orchestrator
from backend.app.services.pareto import pareto_service
from backend.app.database.session import get_db

router = APIRouter()

@router.get(
    "/pareto",
    tags=["Pareto"],
    summary="Pareto distribution across 5 dimensions with 80/20 Vital Few analysis",
    description="Calculates Pareto frequency distributions and cumulative percentages across 5 dimensions: defect_type, machine, product_family, root_cause (confirmed only), and rejection_reason. Supports inclusive date-range filtering, deterministic tie-breaking, and isolates vital-few categories under IATF 16949."
)
def get_pareto(
    dimension: str = Query("defect_type", description="Analysis dimension: defect_type, machine, product_family, root_cause, rejection_reason"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD or ISO-8601, inclusive)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD or ISO-8601, inclusive)"),
    from_date: Optional[str] = Query(None, description="Alias for start_date"),
    to_date: Optional[str] = Query(None, description="Alias for end_date"),
    db: Session = Depends(get_db)
):
    s_date = start_date or from_date
    e_date = end_date or to_date
    try:
        return pareto_service.compute_pareto(
            db=db,
            dimension=dimension,
            start_date=s_date,
            end_date=e_date
        )
    except ValueError as e:
        msg = str(e)
        if "Reversed date range" in msg:
            raise HTTPException(status_code=400, detail=msg)
        elif "Invalid" in msg:
            raise HTTPException(status_code=422, detail=msg)
        else:
            raise HTTPException(status_code=400, detail=msg)

@router.get(
    "/effectiveness/{capa_id}",
    tags=["Effectiveness"],
    summary="Statistical verification of CAPA intervention efficacy",
    description="Two-proportion z-test (or Fisher's exact test) evaluation comparing pre- and post-intervention rejection rates with statistical p-value, 95% confidence interval, machine isolation, small-sample guardrails, and anti-causal association disclaimers."
)
def get_capa_effectiveness(
    capa_id: str = "CAPA-2026-001",
    db: Session = Depends(get_db)
):
    from backend.app.services.effectiveness import effectiveness_engine
    return effectiveness_engine.evaluate_capa_effectiveness(capa_id=capa_id, db=db)

from backend.app.services.dashboard import dashboard_service
from backend.app.core.security import require_authenticated_user

DASHBOARD_EXAMPLE_RESPONSE = {
    "filter_applied": {"start_date": None, "end_date": None, "is_filtered": False},
    "production_batches": {
        "total_count": 29,
        "status_split": {"CONFORMING": 15, "IN_PROGRESS": 1, "QUALITY_HOLD": 13},
        "active_batches_count": 14
    },
    "inspection_quantity": {
        "total_inspected_parts": 2472,
        "accepted_parts": 2327,
        "nonconforming_parts": 145,
        "unit": "parts"
    },
    "acceptance_rate_percent": 94.13,
    "acceptance_rate_label": "Recorded Sample Result",
    "rejection_rate_percent": 5.87,
    "rejection_rate_label": "Recorded Sample Result",
    "rates_sum_percent": 100.0,
    "active_quality_incidents": 1,
    "total_incidents": 20,
    "top_defect_categories": [
        {"defect": "Oversized shaft diameter", "count": 9, "percentage": 45.0},
        {"defect": "Surface scratch / score", "count": 5, "percentage": 25.0},
        {"defect": "Flange thickness deviation", "count": 2, "percentage": 10.0},
        {"defect": "Machine vibration chatter", "count": 2, "percentage": 10.0},
        {"defect": "Undersized bore diameter", "count": 2, "percentage": 10.0}
    ],
    "machine_anomalies": {
        "detected_count": 3,
        "primary_machine": "CNC-04",
        "active_anomalies_count": 3
    },
    "machine_anomalies_detected": 3,
    "open_capas": 32,
    "overdue_capas": 1,
    "process_control_status": {
        "status": "OUT_OF_CONTROL",
        "is_in_control": False,
        "characteristics": [
            {
                "name": "shaft_diameter",
                "status": "OUT_OF_CONTROL",
                "is_in_control": False,
                "reason": "Process drift detected (slope=+0.017, p=0.026 < 0.05); Cpk=0.00 indicates mean shifted to USL (50.05mm).",
                "cpk": 0.0
            }
        ],
        "reason": "Process drift detected (slope=+0.017, p=0.026 < 0.05); Cpk=0.00 indicates mean shifted to USL (50.05mm).",
        "notice": "statistical signal, not a product decision",
        "label": "[STATISTICAL FINDING]"
    },
    "overall_health_score": 83.3,
    "governance_notice": "Decision-support only. Final product disposition is a human decision.",
    "synthetic_data_note": "Synthetic demonstration dataset calibrated to aerospace CNC lathe production (Okuma LB3000 / Precision Shaft PS-2026-101)."
}

@router.get(
    "/dashboard/summary",
    tags=["Dashboard"],
    summary="Retrieve executive quality dashboard KPIs across 10 critical items",
    description=(
        "Returns all 10 Quality Dashboard indicators computed directly from relational SQLite/Postgres tables: "
        "(1) production batches count and status split, (2) inspection quantity (total inspected parts), "
        "(3) acceptance rate %, (4) rejection rate %, (5) active quality incidents, "
        "(6) top defect categories (Pareto), (7) machine anomalies count, "
        "(8) open CAPAs, (9) overdue CAPAs, (10) process-control status per characteristic with reason. "
        "Supports inclusive date-range filtering (start_date/end_date) and enforces sample rate sum-to-100% integrity."
    ),
    responses={
        200: {
            "description": "Executive quality KPIs successfully computed from database records.",
            "content": {
                "application/json": {
                    "example": DASHBOARD_EXAMPLE_RESPONSE
                }
            }
        },
        400: {"description": "Reversed date range (start_date is after end_date)."},
        422: {"description": "Invalid date format (ISO-8601 YYYY-MM-DD expected)."}
    }
)
def get_dashboard_summary(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD or ISO-8601, inclusive)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD or ISO-8601, inclusive)"),
    from_date: Optional[str] = Query(None, description="Alias for start_date"),
    to_date: Optional[str] = Query(None, description="Alias for end_date"),
    user: Dict[str, Any] = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
):
    s_date = start_date or from_date
    e_date = end_date or to_date
    try:
        return dashboard_service.get_summary(db=db, start_date=s_date, end_date=e_date)
    except ValueError as e:
        msg = str(e)
        if "Reversed date range" in msg:
            raise HTTPException(status_code=400, detail=msg)
        elif "Invalid" in msg:
            raise HTTPException(status_code=422, detail=msg)
        else:
            raise HTTPException(status_code=400, detail=msg)

@router.get("/reports/pdf", tags=["Reports"], summary="Download ISO 9001 / IATF 16949 audit dossier PDF report", description="Generates and streams comprehensive 13-section ISO 9001 / IATF 16949 compliant Audit Report PDF with embedded charts and epistemic labels.")
def download_pdf_report(batch_id: str = "BATCH-0245", sample_name: Optional[str] = None, image_name: Optional[str] = None, db: Session = Depends(get_db)):
    chosen_sample = sample_name or image_name
    sample_img = None
    if chosen_sample:
        p = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "uploads", "samples", chosen_sample))
        if os.path.exists(p):
            sample_img = p

    if not sample_img:
        from backend.app.database.models import InspectionImage, Batch
        b_rec = db.query(Batch).filter((Batch.batch_number == batch_id) | (Batch.id == batch_id)).first()
        b_fk = b_rec.id if b_rec else batch_id
        db_img = db.query(InspectionImage).filter(InspectionImage.batch_id == b_fk).order_by(InspectionImage.uploaded_at.desc()).first()
        if db_img and db_img.file_path and os.path.exists(db_img.file_path):
            sample_img = db_img.file_path

    if not sample_img:
        for fname in ["screw_thread.png", "IMG-001.png", "shaft_scratch.png"]:
            p = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "uploads", "samples", fname))
            if os.path.exists(p):
                sample_img = p
                break

    existing_wf = orchestrator.get_latest_workflow_for_batch(batch_id)
    if existing_wf:
        state_dict = existing_wf.model_dump() if hasattr(existing_wf, "model_dump") else (existing_wf if isinstance(existing_wf, dict) else dict(existing_wf))
    else:
        state = orchestrator.run_full_pipeline(
            batch_meta={"batch_id": batch_id, "part_number": "PS-2026-101", "machine": "CNC-04", "quantity": 500, "nominal_mm": 50.00, "tolerance_mm": 0.05},
            image_path=sample_img
        )
        state_dict = state.model_dump()

    pdf_bytes = generate_quality_pdf_report(state_dict)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Quality_Audit_Report_{batch_id}.pdf"}
    )
