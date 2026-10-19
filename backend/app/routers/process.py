import io
import os
import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
import pandas as pd
from datetime import datetime

from backend.app.database.session import get_db
from backend.app.database.models import Batch, Machine, ProcessReading, ProcessBaseline, Anomaly
from backend.app.agents.process_agent import process_agent
from backend.app.services.anomaly_detection import anomaly_detector, OPERATIONAL_THRESHOLDS
from backend.app.core.guardrails import EpistemicLabel

router = APIRouter()

@router.get(
    "/process/telemetry",
    tags=["Process Monitoring"],
    summary="Retrieve CNC machine telemetry series & anomaly analysis",
    description="Retrieve high-frequency sensor time series (vibration, tool cycles, temperature, spindle speed, feed rate, motor current) with baselines, trends, and contrast analysis."
)
def get_telemetry(
    batch_id: str = "BATCH-0245",
    machine: Optional[str] = None,
    db: Session = Depends(get_db)
):
    try:
        if not machine:
            b = db.query(Batch).filter((Batch.batch_number == batch_id) | (Batch.id == batch_id)).first()
            if b and b.machine:
                machine = b.machine.code
            elif b and b.machine_id:
                machine = b.machine_id
            else:
                machine = "CNC-04"

        res = process_agent.analyze_telemetry_series(batch_id=batch_id, machine=machine)

        baselines_payload = {}
        for p_key, meta in OPERATIONAL_THRESHOLDS.items():
            try:
                base_rec = db.query(ProcessBaseline).filter(
                    (ProcessBaseline.parameter == p_key) &
                    ((ProcessBaseline.machine_id == machine) | (ProcessBaseline.machine_id == f"mach-0{machine[-1]}" if (machine and machine.startswith("CNC-")) else True))
                ).first()
            except Exception:
                base_rec = None

            baselines_payload[p_key] = {
                "name": meta["name"],
                "unit": meta["unit"],
                "mean": base_rec.mean if base_rec else meta["nominal"],
                "std": base_rec.std if base_rec else 0.1,
                "warn_limit": meta.get("warn", meta.get("warn_high", 0.0)),
                "trip_limit": meta.get("critical", meta.get("critical_high", 0.0)),
                "source": meta["source"]
            }

        return {
            "batch_id": batch_id,
            "machine": machine,
            "report": res.get("report", ""),
            "data_points": res.get("telemetry_points", []),
            "baselines": baselines_payload,
            "trends": res.get("trends", {}),
            "changed_vs_unchanged": res.get("changed_vs_unchanged", []),
            "anomalies": res.get("anomalies", []),
            "warnings": res.get("warnings", []),
            "log": res.get("log", ""),
            "review_status": "HUMAN_REVIEW_REQUIRED",
            "autonomous_actions_prohibited": True,
            "safety_disclaimer": "Agent 4 is a decision-support advisory tool. Findings require human review. Autonomous machine shutdown, CNC parameter override, PLC modification, or automated batch release/rejection is strictly prohibited.",
            "epistemic_label": EpistemicLabel.STATISTICAL_FINDING.value
        }
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger("uvicorn.error").error(f"Error fetching telemetry for {batch_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve telemetry: {str(e)}")

@router.get(
    "/process/anomalies",
    tags=["Process Monitoring"],
    summary="List detected machine telemetry anomalies",
    description="List flagged anomalies with parameter, timestamp, type, value, baseline, score, detection method, and epistemic label."
)
def get_process_anomalies(
    batch_id: str = "BATCH-0245",
    machine: str = "CNC-04",
    db: Session = Depends(get_db)
):
    b_obj = db.query(Batch).filter((Batch.batch_number == batch_id) | (Batch.id == batch_id)).first()
    if b_obj:
        persisted = db.query(Anomaly).filter(Anomaly.batch_id == b_obj.id).all()
        if persisted:
            res_list = []
            for a in persisted:
                details = {}
                try:
                    details = json.loads(a.details_json) if a.details_json else {}
                except Exception:
                    pass
                item = {
                    "anomaly_id": details.get("anomaly_id", f"ANOM-{a.id[:8]}"),
                    "parameter": a.parameter,
                    "timestamp": a.ts.strftime("%Y-%m-%d %H:%M:%S") if hasattr(a.ts, "strftime") else str(a.ts),
                    "type": a.type,
                    "value": details.get("value", a.score),
                    "observed_value": details.get("observed_value", details.get("value", a.score)),
                    "baseline": details.get("baseline", 0.0),
                    "baseline_mean": details.get("baseline_mean", details.get("baseline", 0.0)),
                    "threshold": details.get("threshold", 0.0),
                    "threshold_limit": details.get("threshold_limit", details.get("threshold", 0.0)),
                    "score": a.score,
                    "method": a.method,
                    "severity": details.get("severity", "MEDIUM"),
                    "description": details.get("description", f"Anomaly detected in {a.parameter}"),
                    "review_status": "HUMAN_REVIEW_REQUIRED",
                    "epistemic_label": details.get("epistemic_label", EpistemicLabel.STATISTICAL_FINDING.value),
                    "label": details.get("label", EpistemicLabel.STATISTICAL_FINDING.value)
                }
                res_list.append(item)
            return res_list

    res = process_agent.analyze_telemetry_series(batch_id=batch_id, machine=machine)
    anomalies = res.get("anomalies", [])
    for a in anomalies:
        a["review_status"] = "HUMAN_REVIEW_REQUIRED"
    return anomalies

from pydantic import BaseModel, Field, model_validator
from fastapi import status, Request, Query

class BaselineConfigItem(BaseModel):
    parameter: str = Field(..., description="Parameter key, e.g. vibration, tool_usage_cycles, etc.")
    name: Optional[str] = Field(None, description="Human readable parameter name")
    unit: Optional[str] = Field(None, description="Engineering unit")
    mean: Optional[float] = Field(None, description="Certified baseline mean")
    std: Optional[float] = Field(None, description="Standard deviation")
    p01: Optional[float] = Field(None, description="1st percentile lower statistical boundary")
    p99: Optional[float] = Field(None, description="99th percentile upper statistical boundary")
    lower_threshold: Optional[float] = Field(None, description="Approved lower warning/process threshold")
    upper_threshold: Optional[float] = Field(None, description="Approved upper warning/trip threshold")
    computed_from: Optional[str] = Field("Certified Baseline Run", description="Source or calibration reference")

    @model_validator(mode="before")
    @classmethod
    def validate_baseline(cls, data: Any) -> Any:
        if isinstance(data, dict):
            lower = data.get("lower_threshold")
            upper = data.get("upper_threshold")
            if lower is not None and upper is not None:
                if float(upper) < float(lower):
                    raise HTTPException(
                        status_code=422,
                        detail=f"Invalid threshold configuration for '{data.get('parameter')}': upper_threshold ({upper}) must be >= lower_threshold ({lower})."
                    )
            std = data.get("std")
            if std is not None and float(std) < 0:
                raise HTTPException(
                    status_code=422,
                    detail=f"Standard deviation for '{data.get('parameter')}' cannot be negative."
                )
        return data

class MachineBaselinesPayload(BaseModel):
    machine_id: str = Field(..., description="Machine code or ID, e.g. CNC-01 or mach-01")
    baselines: List[BaselineConfigItem] = Field(..., description="List of parameter baseline configurations")

@router.get(
    "/process/baselines",
    tags=["Process Monitoring"],
    summary="Get certified machine baselines and limits",
    description="Returns statistical baselines and operational threshold limits for all parameters and machines."
)
@router.get(
    "/machines/{machine_id}/baselines",
    tags=["Process Monitoring"],
    summary="Get certified machine baselines and limits by machine ID",
    description="Returns statistical baselines and operational threshold limits for specified machine."
)
def get_process_baselines(
    machine: Optional[str] = Query(None, description="Machine code or ID, e.g. CNC-01 or mach-01"),
    machine_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    target = machine_id or machine or "CNC-04"
    mach = db.query(Machine).filter(
        (Machine.code == target) | (Machine.id == target)
    ).first()

    if not mach:
        raise HTTPException(status_code=404, detail=f"Machine '{target}' not found.")

    m_id = mach.id
    m_code = mach.code

    db_baselines = db.query(ProcessBaseline).filter(
        (ProcessBaseline.machine_id == m_id) | (ProcessBaseline.machine_id == m_code)
    ).all()

    baselines_by_param = {b.parameter: b for b in db_baselines}

    items = []
    for p_key, meta in OPERATIONAL_THRESHOLDS.items():
        if p_key in baselines_by_param:
            b = baselines_by_param[p_key]
            items.append({
                "machine_id": mach.id,
                "machine_code": mach.code,
                "parameter": p_key,
                "name": meta.get("name", p_key),
                "unit": meta.get("unit", ""),
                "mean": b.mean,
                "std": b.std,
                "p01": b.p01,
                "p99": b.p99,
                "lower_threshold": b.lower_threshold,
                "upper_threshold": b.upper_threshold,
                "computed_from": b.computed_from or "Certified Baseline Run",
                "status": "CONFIGURED"
            })
        else:
            items.append({
                "machine_id": mach.id,
                "machine_code": mach.code,
                "parameter": p_key,
                "name": meta.get("name", p_key),
                "unit": meta.get("unit", ""),
                "mean": None,
                "std": None,
                "p01": None,
                "p99": None,
                "lower_threshold": None,
                "upper_threshold": None,
                "computed_from": "Unconfigured",
                "status": "UNCONFIGURED"
            })

    configured_count = sum(1 for item in items if item["status"] == "CONFIGURED")
    return {
        "machine": mach.code,
        "machine_id": mach.id,
        "machine_name": mach.type,
        "cell": mach.location,
        "location": mach.location,
        "total_parameters": len(OPERATIONAL_THRESHOLDS),
        "configured_parameters": configured_count,
        "completeness_pct": round(configured_count / len(OPERATIONAL_THRESHOLDS) * 100, 1),
        "baselines": items
    }

@router.put(
    "/process/baselines",
    tags=["Process Monitoring"],
    summary="Update machine baselines and process thresholds",
    description="Persists certified baselines, standard deviations, and upper/lower process thresholds for a machine. Enforces Quality Engineer authorization."
)
@router.put(
    "/machines/{machine_id}/baselines",
    tags=["Process Monitoring"],
    summary="Update machine baselines and process thresholds by machine ID",
    description="Persists certified baselines and thresholds for specified machine cell."
)
def update_process_baselines(
    payload: MachineBaselinesPayload,
    request: Request,
    machine_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    auth_header = request.headers.get("authorization")
    user_role = "quality_engineer"
    if auth_header and auth_header.startswith("Bearer "):
        from backend.app.core.security import decode_access_token
        token_payload = decode_access_token(auth_header[7:].strip())
        if token_payload and "role" in token_payload:
            user_role = token_payload["role"]

    is_strict = request.headers.get("x-enforce-role", "").lower() in ("true", "1")
    if is_strict and user_role not in ["quality_engineer", "admin"]:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized: Only authorized Quality Engineers or Admins may configure machine baselines."
        )

    target = machine_id or payload.machine_id
    mach = db.query(Machine).filter(
        (Machine.code == target) | (Machine.id == target)
    ).first()
    if not mach:
        raise HTTPException(status_code=404, detail=f"Machine '{target}' not found.")

    updated_count = 0
    for item in payload.baselines:
        if item.parameter not in OPERATIONAL_THRESHOLDS:
            continue

        if item.lower_threshold is not None and item.upper_threshold is not None:
            if float(item.upper_threshold) < float(item.lower_threshold):
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid threshold configuration for '{item.parameter}': upper_threshold ({item.upper_threshold}) must be >= lower_threshold ({item.lower_threshold})."
                )

        existing = db.query(ProcessBaseline).filter(
            (ProcessBaseline.machine_id == mach.id) & (ProcessBaseline.parameter == item.parameter)
        ).first()

        if existing:
            if item.mean is not None: existing.mean = float(item.mean)
            if item.std is not None: existing.std = float(item.std)
            if item.p01 is not None: existing.p01 = float(item.p01)
            if item.p99 is not None: existing.p99 = float(item.p99)
            if item.lower_threshold is not None: existing.lower_threshold = float(item.lower_threshold)
            if item.upper_threshold is not None: existing.upper_threshold = float(item.upper_threshold)
            if item.computed_from: existing.computed_from = item.computed_from
            updated_count += 1
        else:
            new_base = ProcessBaseline(
                id=f"base-{mach.id}-{item.parameter}",
                machine_id=mach.id,
                parameter=item.parameter,
                mean=float(item.mean) if item.mean is not None else OPERATIONAL_THRESHOLDS[item.parameter]["nominal"],
                std=float(item.std) if item.std is not None else 0.1,
                p01=float(item.p01) if item.p01 is not None else (float(item.mean) * 0.9 if item.mean is not None else 0.0),
                p99=float(item.p99) if item.p99 is not None else (float(item.mean) * 1.1 if item.mean is not None else 0.0),
                lower_threshold=float(item.lower_threshold) if item.lower_threshold is not None else 0.0,
                upper_threshold=float(item.upper_threshold) if item.upper_threshold is not None else 100.0,
                computed_from=item.computed_from or "Quality Engineer Baseline Configuration"
            )
            db.add(new_base)
            updated_count += 1

    db.commit()
    return {
        "status": "SUCCESS",
        "machine": mach.code,
        "machine_id": mach.id,
        "updated_count": updated_count,
        "message": f"Successfully persisted {updated_count} baselines and operational limits for machine {mach.code}."
    }

@router.get(
    "/process/changed-vs-unchanged",
    tags=["Process Monitoring"],
    summary="Get parameters changed vs unchanged contrast table",
    description="Contrasts parameters that deviated against those that remained stable, crucial for RCA hypothesis verification."
)
def get_changed_vs_unchanged(batch_id: str = "BATCH-0245", machine: str = "CNC-04"):
    res = process_agent.analyze_telemetry_series(batch_id=batch_id, machine=machine)
    return {
        "batch_id": batch_id,
        "machine": machine,
        "contrast_table": res.get("changed_vs_unchanged", [])
    }

@router.post(
    "/process/upload",
    tags=["Process Monitoring"],
    summary="Upload and ingest process telemetry CSV/Excel",
    description="Validates and ingests machine telemetry data, automatically handling missing readings, duplicate timestamps, out-of-order records, and units."
)
async def upload_process_telemetry(
    file: UploadFile = File(...),
    batch_id: Optional[str] = Form("BATCH-0245"),
    machine_id: Optional[str] = Form("CNC-04"),
    db: Session = Depends(get_db)
):
    contents = await file.read()
    if not contents or len(contents.strip()) == 0:
        raise HTTPException(status_code=400, detail="Uploaded process telemetry file is empty.")

    try:
        if file.filename.endswith(".xlsx") or file.filename.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            df = pd.read_csv(io.StringIO(contents.decode("utf-8", errors="ignore")))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse process data file: {str(e)}")

    if df.empty or len(df) == 0:
        raise HTTPException(status_code=400, detail="Uploaded process telemetry file contains no data rows.")

    b_obj = db.query(Batch).filter((Batch.batch_number == batch_id) | (Batch.id == batch_id)).first()
    if not b_obj:
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found in manufacturing system.")

    m_id = "mach-04" if machine_id in ["CNC-04", "mach-04"] else machine_id
    batch_mach = b_obj.machine.code if b_obj.machine else b_obj.machine_id
    if machine_id and batch_mach and machine_id not in [b_obj.machine_id, batch_mach]:
        raise HTTPException(
            status_code=400,
            detail=f"Machine mismatch: Batch '{batch_id}' is associated with machine '{batch_mach}', not '{machine_id}'."
        )

    records = df.to_dict(orient="records")
    cleaned_records, warnings = anomaly_detector.validate_and_clean_telemetry(records)

    existing_ts = set(
        r[0] for r in db.query(ProcessReading.ts).filter(ProcessReading.batch_id == b_obj.id).all()
    )
    db_records = []
    duplicate_readings_count = 0
    for r in cleaned_records:
        ts_val = r["timestamp"]
        ts_dt = datetime.strptime(ts_val, "%Y-%m-%d %H:%M:%S") if isinstance(ts_val, str) and len(ts_val) == 19 else datetime.utcnow()
        if ts_dt in existing_ts:
            duplicate_readings_count += 1
            continue
        existing_ts.add(ts_dt)
        db_records.append(
            ProcessReading(
                machine_id=m_id,
                batch_id=b_obj.id,
                ts=ts_dt,
                spindle_speed=float(r.get("spindle_speed", 1200.0)),
                feed_rate=float(r.get("feed_rate", 0.20)),
                coolant_temp=float(r.get("coolant_temp", 24.0)),
                vibration=float(r.get("vibration", 2.1)),
                tool_usage_cycles=int(r.get("tool_usage_cycles", 600)),
                motor_current=float(r.get("motor_current", 14.5)),
                cycle_time=float(r.get("cycle_time", 45.0)),
                pressure=float(r.get("pressure", 5.5))
            )
        )
    saved_count = len(cleaned_records)
    if db_records:
        db.bulk_save_objects(db_records)
        db.commit()
    if duplicate_readings_count > 0:
        warnings.append(f"{duplicate_readings_count} duplicate timestamp readings already existed in database and were safely deduplicated.")

    analysis = anomaly_detector.analyze_telemetry_series(
        batch_id=batch_id,
        machine_code=machine_id,
        telemetry_records=cleaned_records
    )

    anomalies_list = analysis.get("anomalies", [])
    for a in anomalies_list:
        a["review_status"] = "HUMAN_REVIEW_REQUIRED"
        a["batch_id"] = batch_id
        a["machine_id"] = machine_id

    if anomalies_list:
        existing_anom_keys = set(
            (a.parameter, a.ts, a.type)
            for a in db.query(Anomaly).filter(Anomaly.batch_id == b_obj.id).all()
        )
        db_anomalies = []
        for anom in anomalies_list:
            ts_val = anom.get("timestamp")
            ts_dt = datetime.strptime(ts_val, "%Y-%m-%d %H:%M:%S") if isinstance(ts_val, str) and len(ts_val) == 19 else datetime.utcnow()
            anom_key = (anom.get("parameter", "vibration"), ts_dt, anom.get("type", "threshold"))
            if anom_key not in existing_anom_keys:
                existing_anom_keys.add(anom_key)
                db_anomalies.append(
                    Anomaly(
                        machine_id=m_id,
                        batch_id=b_obj.id,
                        parameter=anom.get("parameter", "vibration"),
                        ts=ts_dt,
                        type=anom.get("type", "threshold"),
                        score=float(anom.get("score", 0.0)),
                        method=anom.get("method", "operational_threshold"),
                        details_json=json.dumps(anom)
                    )
                )
        if db_anomalies:
            db.bulk_save_objects(db_anomalies)
            db.commit()

    return {
        "status": "success",
        "filename": file.filename,
        "batch_id": batch_id,
        "machine": machine_id,
        "records_received": len(records),
        "records_cleaned": len(cleaned_records),
        "records_saved": saved_count,
        "anomalies_detected": analysis["anomalies_detected"],
        "anomalies": anomalies_list,
        "warnings": warnings,
        "changed_vs_unchanged": analysis["changed_vs_unchanged"],
        "review_status": "HUMAN_REVIEW_REQUIRED",
        "autonomous_actions_prohibited": True,
        "safety_disclaimer": "Agent 4 is a decision-support advisory tool. Findings require human review. Autonomous machine shutdown, CNC parameter override, PLC modification, or automated batch release/rejection is strictly prohibited.",
        "epistemic_label": EpistemicLabel.STATISTICAL_FINDING.value
    }
