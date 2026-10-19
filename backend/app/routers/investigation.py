from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.database.models import Batch, QualityIncident
from backend.app.services.investigation_service import build_investigation_report

router = APIRouter()

class RunInvestigationPayload(BaseModel):
    batch_id: str = Field(..., description="Target batch number or ID", json_schema_extra={"example": "BATCH-0245"})
    force_refresh: bool = Field(False, description="Whether to recompute investigation from live records")

@router.get(
    "/investigation/{batch_id}",
    tags=["Manufacturing Process Investigation"],
    summary="Retrieve process investigation for a batch",
    description="Returns defect classification, dynamically selected investigation strategy, specification limits, measurement results, hypotheses, and missing process evidence."
)
def get_process_investigation(
    batch_id: str,
    db: Session = Depends(get_db)
):
    clean_id = batch_id.strip()
    try:
        report = build_investigation_report(batch_id=clean_id, db=db)
        return report
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import logging
        logging.getLogger("uvicorn.error").error(f"Error generating investigation for {clean_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate process investigation: {str(e)}")

@router.post(
    "/investigation/run",
    tags=["Manufacturing Process Investigation"],
    summary="Execute or refresh process investigation",
    description="Initiates or refreshes a defect-specific process investigation for the specified batch."
)
def run_process_investigation(
    payload: RunInvestigationPayload,
    db: Session = Depends(get_db)
):
    clean_id = payload.batch_id.strip()
    try:
        report = build_investigation_report(batch_id=clean_id, db=db)
        return report
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import logging
        logging.getLogger("uvicorn.error").error(f"Error running investigation for {clean_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to run process investigation: {str(e)}")
