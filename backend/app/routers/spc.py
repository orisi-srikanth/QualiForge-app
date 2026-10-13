"""
Statistical Process Control & Capability Endpoints (Agent 5)
Calculates control limits (UCL, CL, LCL), Nelson rules, and capability indices (Cp, Cpk, Pp, Ppk).
Strictly adheres to AIAG SPC guidelines and IATF 16949:2016 Section 8.5.1.
Enforces sample size guardrails (n < 5 suppressed, 5 <= n < 30 preliminary with warnings)
and assumption checks (normality, stability, variance, drift, outliers, mixed lots).
"""
import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, Body, status, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.database.models import Batch, InspectionCharacteristic, SPCResult, Measurement
from backend.app.agents.intake_agent import intake_agent
from backend.app.agents.spc_agent import spc_agent
from backend.app.services.capability import capability_engine
from backend.app.services.spc_charts import spc_engine
from backend.app.schemas.schemas import CapabilityRequest, CapabilityResponse

router = APIRouter()

def _persist_spc_result(
    db: Session,
    batch_identifier: str,
    cl: float,
    ucl: float,
    lcl: float,
    cp: Optional[float],
    cpk: Optional[float],
    pp: Optional[float],
    ppk: Optional[float],
    n: int,
    violations: list,
    warnings: list,
    characteristic_id: Optional[str] = None
) -> Optional[str]:
    """Helper to persist capability and control metrics into spc_results table with deduplication."""
    try:
        # Resolve batch
        batch = db.query(Batch).filter(
            (Batch.id == batch_identifier) | (Batch.batch_number == batch_identifier)
        ).first()
        actual_batch_id = batch.id if batch else batch_identifier

        # Resolve characteristic
        char_obj = None
        if characteristic_id:
            char_obj = db.query(InspectionCharacteristic).filter(
                (InspectionCharacteristic.id == characteristic_id) |
                (InspectionCharacteristic.name == characteristic_id)
            ).first()
        if not char_obj:
            char_obj = db.query(InspectionCharacteristic).filter(
                InspectionCharacteristic.name == "shaft_diameter"
            ).first()
        actual_char_id = char_obj.id if char_obj else (characteristic_id or "char-ps-01")

        violations_serialized = []
        for v in violations:
            if hasattr(v, "model_dump"):
                violations_serialized.append(v.model_dump())
            elif hasattr(v, "dict"):
                violations_serialized.append(v.dict())
            elif isinstance(v, dict):
                violations_serialized.append(v)
            else:
                violations_serialized.append(str(v))

        existing = db.query(SPCResult).filter(
            SPCResult.batch_id == actual_batch_id,
            SPCResult.characteristic_id == actual_char_id
        ).first()

        if existing:
            existing.chart_type = "I-MR"
            existing.center_line = float(cl) if cl is not None else 0.0
            existing.ucl = float(ucl) if ucl is not None else 0.0
            existing.lcl = float(lcl) if lcl is not None else 0.0
            existing.violations_json = json.dumps(violations_serialized)
            existing.cp = float(cp) if cp is not None else None
            existing.cpk = float(cpk) if cpk is not None else None
            existing.pp = float(pp) if pp is not None else None
            existing.ppk = float(ppk) if ppk is not None else None
            existing.n = int(n)
            existing.warnings_json = json.dumps(warnings)
            db.commit()
            db.refresh(existing)
            return existing.id

        record = SPCResult(
            batch_id=actual_batch_id,
            characteristic_id=actual_char_id,
            chart_type="I-MR",
            center_line=float(cl) if cl is not None else 0.0,
            ucl=float(ucl) if ucl is not None else 0.0,
            lcl=float(lcl) if lcl is not None else 0.0,
            violations_json=json.dumps(violations_serialized),
            cp=float(cp) if cp is not None else None,
            cpk=float(cpk) if cpk is not None else None,
            pp=float(pp) if pp is not None else None,
            ppk=float(ppk) if ppk is not None else None,
            n=int(n),
            warnings_json=json.dumps(warnings)
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record.id
    except Exception as e:
        db.rollback()
        return None

SUFFICIENT_EXAMPLE = {
    "batch_id": "BATCH-SUFFICIENT-01",
    "status": "sufficient",
    "sample_size": 100,
    "mean": 50.0012,
    "std_dev": 0.0098,
    "sigma_within": 0.0096,
    "sigma_within_method": "Moving Range MR-bar / d2 (d2=1.128 for n=2 consecutive differences)",
    "sigma_overall": 0.0098,
    "sigma_overall_method": "Sample Standard Deviation s (ddof=1)",
    "usl": 50.05,
    "lsl": 49.95,
    "target": 50.00,
    "tolerance_band": 0.10,
    "cp": 1.7361,
    "cpk": 1.6944,
    "cpu": 1.6944,
    "cpl": 1.7778,
    "pp": 1.7007,
    "ppk": 1.6599,
    "ppu": 1.6599,
    "ppl": 1.7415,
    "cpk_ci_95": {
        "lower": 1.4852,
        "upper": 1.9036,
        "standard_error": 0.1067,
        "confidence_level": 0.95,
        "note": "95% confidence interval [1.4852, 1.9036] based on n=100 observations."
    },
    "normality_test": {
        "test": "Shapiro-Wilk",
        "statistic": 0.9912,
        "p_value": 0.7421,
        "alpha": 0.05,
        "is_normal": True
    },
    "stability_test": {
        "is_in_control": True,
        "violations": []
    },
    "trend_test": {
        "is_trending": False,
        "slope": 0.00001,
        "p_value": 0.6512,
        "alpha": 0.05
    },
    "outliers": [],
    "assessment": "Capable Process (1.33 <= Cpk < 1.67) — Conforms to standard industrial quality benchmarks.",
    "interpretation_band": "Capable (1.33 to 1.67)",
    "benchmark_source": "AIAG Statistical Process Control (SPC) Reference Manual (2nd Edition) & IATF 16949:2016 Section 8.5.1",
    "warnings": [],
    "guidance_notice": "DECISION GUIDANCE ONLY: Capability indices are statistical indicators for process improvement and supervision. QualityMind does not perform automatic lot acceptance, rejection, or quarantine decisions solely based on capability metrics without authorized quality engineering disposition.",
    "future_guarantee_disclaimer": "DISCLAIMER: Process capability metrics reflect historical statistical performance under observed conditions and do NOT constitute a guarantee of future zero-defect production or parts conformity.",
    "label": "[STATISTICAL_FINDING]"
}

INSUFFICIENT_EXAMPLE = {
    "batch_id": "BATCH-SMALL-03",
    "status": "insufficient_data",
    "sample_size": 3,
    "mean": None,
    "std_dev": None,
    "sigma_within": None,
    "sigma_within_method": None,
    "sigma_overall": None,
    "sigma_overall_method": "Sample Standard Deviation s (ddof=1)",
    "usl": 50.05,
    "lsl": 49.95,
    "target": 50.00,
    "tolerance_band": None,
    "cp": None,
    "cpk": None,
    "cpu": None,
    "cpl": None,
    "pp": None,
    "ppk": None,
    "ppu": None,
    "ppl": None,
    "cpk_ci_95": None,
    "normality_test": None,
    "stability_test": None,
    "trend_test": None,
    "outliers": [],
    "assessment": "Insufficient Data for Capability Assessment",
    "interpretation_band": None,
    "benchmark_source": "AIAG Statistical Process Control (SPC) Reference Manual (2nd Edition) & IATF 16949:2016 Section 8.5.1",
    "warnings": [
        "INSUFFICIENT DATA: Sample size n=3 is below minimum threshold (n >= 5) required for statistical capability estimation. Numeric capability indices suppressed."
    ],
    "guidance_notice": "DECISION GUIDANCE ONLY: Capability indices are statistical indicators for process improvement and supervision. QualityMind does not perform automatic lot acceptance, rejection, or quarantine decisions solely based on capability metrics without authorized quality engineering disposition.",
    "future_guarantee_disclaimer": "DISCLAIMER: Process capability metrics reflect historical statistical performance under observed conditions and do NOT constitute a guarantee of future zero-defect production or parts conformity.",
    "label": "[STATISTICAL_FINDING]"
}

@router.get(
    "/spc/analyze",
    tags=["SPC & Capability"],
    summary="Run Statistical Process Control analysis and Nelson rules",
    description="Generates auto-selected control chart (I-MR or X-bar/R), center line, UCL, LCL, Nelson rule violations, and capability metrics with DB persistence."
)
def analyze_spc(
    batch_id: str = "BATCH-0245",
    characteristic_id: Optional[str] = None,
    subgroup_size: int = 1,
    db: Session = Depends(get_db)
):
    # 1. Resolve batch
    batch = db.query(Batch).filter((Batch.batch_number == batch_id) | (Batch.id == batch_id)).first()

    # 2. Extract measurements from DB
    measurements = []
    if batch:
        db_meas = db.query(Measurement).filter(
            Measurement.batch_id == batch.id
        ).order_by(Measurement.measured_at, Measurement.component_id).all()
        if db_meas:
            measurements = [float(m.value) for m in db_meas]

    # 3. Fallback to intake_agent
    if not measurements:
        try:
            intake = intake_agent.process_batch_and_measurements(batch_meta={"batch_id": batch_id})
            measurements = [m["measured_value"] for m in intake["batch_data"].get("measurements", [])]
        except Exception:
            measurements = []

    # 4. Unknown batch handling
    if not batch and not measurements:
        raise HTTPException(
            status_code=404,
            detail=f"Batch '{batch_id}' not found in manufacturing system."
        )

    # 5. Extract QE engineering specifications
    nominal = 50.00
    usl = 50.05
    lsl = 49.95
    if batch and batch.product and batch.product.characteristics:
        char_match = None
        if characteristic_id:
            char_match = next((c for c in batch.product.characteristics if c.id == characteristic_id or c.name == characteristic_id), None)
        if not char_match:
            char_match = next((c for c in batch.product.characteristics if c.name == "shaft_diameter"), batch.product.characteristics[0])
        if char_match:
            nominal = float(char_match.nominal)
            usl = float(char_match.usl)
            lsl = float(char_match.lsl)

    res = spc_agent.analyze_process_capability_and_control(
        batch_id=batch_id,
        values=measurements,
        usl=usl,
        lsl=lsl,
        nominal=nominal,
        subgroup_size=subgroup_size
    )
    rep = res["report"]
    _persist_spc_result(
        db=db,
        batch_identifier=batch_id,
        cl=rep.cl,
        ucl=rep.ucl,
        lcl=rep.lcl,
        cp=rep.cp,
        cpk=rep.cpk,
        pp=rep.pp,
        ppk=rep.ppk,
        n=rep.sample_size,
        violations=rep.nelson_violations,
        warnings=rep.warnings,
        characteristic_id=characteristic_id
    )
    return {"report": rep, "log": res["log"]}

@router.get(
    "/spc/capability",
    tags=["SPC & Capability"],
    summary="Calculate process capability metrics with guardrails",
    description=(
        "Calculates process capability indices (Cp, Cpk, Pp, Ppk) with sample size adequacy checks "
        "(insufficient-data status and numeric suppression for n < 5; prominent warning for 5 <= n < 30). "
        "Evaluates normality (Shapiro-Wilk), statistical stability (Nelson rules), process drift, "
        "and zero-variance conditions."
    ),
    responses={
        200: {
            "description": "Calculated capability metrics or insufficient-data status with guardrails.",
            "content": {
                "application/json": {
                    "examples": {
                        "sufficient_sample": {
                            "summary": "Sufficient In-Control Sample (n = 100)",
                            "description": "Demonstrates normal in-control dataset exceeding n >= 30 sufficiency threshold.",
                            "value": SUFFICIENT_EXAMPLE
                        },
                        "insufficient_sample": {
                            "summary": "Insufficient Sample (n = 3)",
                            "description": "Demonstrates strict refusal and numeric suppression for sample size n < 5.",
                            "value": INSUFFICIENT_EXAMPLE
                        }
                    }
                }
            }
        }
    }
)
def get_spc_capability(batch_id: str = "BATCH-0245", db: Session = Depends(get_db)):
    # 1. Resolve batch
    batch = db.query(Batch).filter((Batch.batch_number == batch_id) | (Batch.id == batch_id)).first()

    # 2. Extract measurements from DB
    vals = []
    if batch:
        db_meas = db.query(Measurement).filter(
            Measurement.batch_id == batch.id
        ).order_by(Measurement.measured_at, Measurement.component_id).all()
        if db_meas:
            vals = [float(m.value) for m in db_meas]

    # 3. Fallback to intake_agent
    if not vals:
        try:
            intake = intake_agent.process_batch_and_measurements(batch_meta={"batch_id": batch_id})
            vals = [m["measured_value"] for m in intake["batch_data"].get("measurements", [])]
        except Exception:
            vals = []

    # 4. Unknown batch handling
    if not batch and not vals:
        raise HTTPException(
            status_code=404,
            detail=f"Batch '{batch_id}' not found in manufacturing system."
        )

    # 5. Extract QE engineering specifications
    nominal = 50.00
    usl = 50.05
    lsl = 49.95
    if batch and batch.product and batch.product.characteristics:
        char_match = next((c for c in batch.product.characteristics if c.name == "shaft_diameter"), batch.product.characteristics[0])
        if char_match:
            nominal = float(char_match.nominal)
            usl = float(char_match.usl)
            lsl = float(char_match.lsl)

    res = spc_agent.analyze_process_capability_and_control(
        batch_id=batch_id,
        values=vals,
        usl=usl,
        lsl=lsl,
        nominal=nominal
    )
    rep = res["report"]

    _persist_spc_result(
        db=db,
        batch_identifier=batch_id,
        cl=rep.cl,
        ucl=rep.ucl,
        lcl=rep.lcl,
        cp=rep.cp,
        cpk=rep.cpk,
        pp=rep.pp,
        ppk=rep.ppk,
        n=rep.sample_size,
        violations=rep.nelson_violations,
        warnings=rep.warnings
    )

    return {
        "batch_id": batch_id,
        "status": rep.status,
        "sample_size": rep.sample_size,
        "mean": rep.mean,
        "std_dev": rep.std_dev,
        "min_value": rep.min_value,
        "max_value": rep.max_value,
        "range_value": rep.range_value,
        "chart_type": rep.chart_type,
        "review_status": "HUMAN_REVIEW_REQUIRED",
        "autonomous_actions_prohibited": True,
        "sigma_within": rep.sigma_within,
        "sigma_within_method": rep.sigma_within_method,
        "sigma_overall": rep.sigma_overall,
        "sigma_overall_method": rep.sigma_overall_method,
        "usl": rep.usl,
        "lsl": rep.lsl,
        "target": nominal,
        "tolerance_band": round(rep.usl - rep.lsl, 4) if (rep.usl is not None and rep.lsl is not None) else None,
        "cp": rep.cp,
        "cpk": rep.cpk,
        "pp": rep.pp,
        "ppk": rep.ppk,
        "cpk_ci_95": rep.cpk_ci_95,
        "assessment": rep.capability_assessment,
        "interpretation_band": rep.interpretation_band,
        "benchmark_source": "AIAG Statistical Process Control (SPC) Reference Manual (2nd Edition) & IATF 16949:2016 Section 8.5.1",
        "warnings": rep.warnings,
        "guidance_notice": rep.guidance_notice or (
            "DECISION GUIDANCE ONLY: Capability indices are statistical indicators for process improvement and supervision. "
            "QualityMind does not perform automatic lot acceptance, rejection, or quarantine decisions solely based on capability metrics "
            "without authorized quality engineering disposition."
        ),
        "future_guarantee_disclaimer": rep.future_guarantee_disclaimer or (
            "DISCLAIMER: Process capability metrics reflect historical statistical performance under observed conditions "
            "and do NOT constitute a guarantee of future zero-defect production or parts conformity."
        ),
        "label": "[STATISTICAL_FINDING]"
    }

@router.get(
    "/spc/results",
    tags=["SPC & Capability"],
    summary="Retrieve persisted SPC results by batch",
    description="Retrieves historical persisted SPC findings, control limits, and capability indices for a given batch."
)
def get_spc_results(batch_id: str = "BATCH-0245", db: Session = Depends(get_db)):
    batch = db.query(Batch).filter((Batch.batch_number == batch_id) | (Batch.id == batch_id)).first()
    target_id = batch.id if batch else batch_id
    records = db.query(SPCResult).filter((SPCResult.batch_id == target_id) | (SPCResult.batch_id == batch_id)).all()
    out = []
    for r in records:
        v_list = []
        try:
            v_list = json.loads(r.violations_json) if r.violations_json else []
        except Exception:
            pass
        w_list = []
        try:
            w_list = json.loads(r.warnings_json) if r.warnings_json else []
        except Exception:
            pass
        out.append({
            "id": r.id,
            "batch_id": batch_id,
            "characteristic_id": r.characteristic_id,
            "chart_type": r.chart_type,
            "center_line": r.center_line,
            "ucl": r.ucl,
            "lcl": r.lcl,
            "cp": r.cp,
            "cpk": r.cpk,
            "pp": r.pp,
            "ppk": r.ppk,
            "n": r.n,
            "violations": v_list,
            "warnings": w_list,
            "review_status": "HUMAN_REVIEW_REQUIRED",
            "autonomous_actions_prohibited": True
        })
    return {"batch_id": batch_id, "results": out}

@router.get(
    "/spc/chart",
    tags=["SPC & Capability"],
    summary="Get full SPC control chart series and separation notice",
    description="Returns ordered measurements, center line, UCL, LCL, USL, LSL, and Nelson rule signal detections with explicit limit separation."
)
def get_spc_chart(
    batch_id: str = "BATCH-0245",
    subgroup_size: int = 1,
    db: Session = Depends(get_db)
):
    batch = db.query(Batch).filter((Batch.batch_number == batch_id) | (Batch.id == batch_id)).first()
    vals = []
    if batch:
        db_meas = db.query(Measurement).filter(
            Measurement.batch_id == batch.id
        ).order_by(Measurement.measured_at, Measurement.component_id).all()
        if db_meas:
            vals = [float(m.value) for m in db_meas]
    if not vals:
        try:
            intake = intake_agent.process_batch_and_measurements(batch_meta={"batch_id": batch_id})
            vals = [m["measured_value"] for m in intake["batch_data"].get("measurements", [])]
        except Exception:
            vals = []
    if not batch and not vals:
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found in manufacturing system.")

    nominal = 50.00
    usl = 50.05
    lsl = 49.95
    if batch and batch.product and batch.product.characteristics:
        char_match = next((c for c in batch.product.characteristics if c.name == "shaft_diameter"), batch.product.characteristics[0])
        if char_match:
            nominal = float(char_match.nominal)
            usl = float(char_match.usl)
            lsl = float(char_match.lsl)

    chart_res = spc_engine.evaluate_spc(
        data=vals,
        subgroup_size=subgroup_size,
        usl=usl,
        lsl=lsl
    )
    chart_res["batch_id"] = batch_id
    chart_res["review_status"] = "HUMAN_REVIEW_REQUIRED"
    chart_res["autonomous_actions_prohibited"] = True
    return chart_res

@router.post(
    "/spc/capability",
    tags=["SPC & Capability"],
    summary="Compute process capability for custom measurement dataset",
    description="Submits arbitrary measurement readings, tolerance specifications, and metadata to evaluate capability and statistical assumptions.",
    response_model=CapabilityResponse,
    responses={
        200: {
            "description": "Calculated capability metrics or guardrail refusal.",
            "content": {
                "application/json": {
                    "examples": {
                        "sufficient_sample": {
                            "summary": "Sufficient Sample Example (n = 100)",
                            "value": SUFFICIENT_EXAMPLE
                        },
                        "insufficient_sample": {
                            "summary": "Insufficient Sample Example (n = 3)",
                            "value": INSUFFICIENT_EXAMPLE
                        }
                    }
                }
            }
        }
    }
)
def compute_custom_capability(
    payload: CapabilityRequest = Body(...),
    db: Session = Depends(get_db)
):
    cap_res = capability_engine.calculate_capability(
        values=payload.values,
        usl=payload.usl,
        lsl=payload.lsl,
        target=payload.nominal,
        subgroup_size=payload.subgroup_size,
        machine_ids=payload.machine_ids,
        batch_ids=payload.batch_ids
    )

    # Persist if batch_id provided
    if payload.batch_id and cap_res["sample_size"] >= 2:
        cl_val = cap_res.get("mean") or 0.0
        s_val = cap_res.get("sigma_within") or cap_res.get("sigma_overall") or 0.001
        ucl_val = cl_val + 3.0 * s_val
        lcl_val = cl_val - 3.0 * s_val
        _persist_spc_result(
            db=db,
            batch_identifier=payload.batch_id,
            cl=cl_val,
            ucl=ucl_val,
            lcl=lcl_val,
            cp=cap_res.get("cp"),
            cpk=cap_res.get("cpk"),
            pp=cap_res.get("pp"),
            ppk=cap_res.get("ppk"),
            n=cap_res["sample_size"],
            violations=[],
            warnings=cap_res.get("warnings", [])
        )

    cap_res["batch_id"] = payload.batch_id
    return cap_res
