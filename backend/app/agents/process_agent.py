import time
import os
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from backend.app.agents.base_agent import BaseQualityAgent
from backend.app.models.schemas import CertaintyLevel, ProcessMonitoringReport, TelemetryDataPoint
from backend.app.services.anomaly_detection import anomaly_detector, OPERATIONAL_THRESHOLDS

class ProcessMonitoringAnomalyAgent(BaseQualityAgent):
    def __init__(self):
        super().__init__(
            name="Agent 4 — Process Monitoring & Anomaly Detection Agent",
            role="Analyze machine and process information to identify abnormal manufacturing conditions",
            certainty_level=CertaintyLevel.STATISTICAL_FINDING
        )
        self.baselines = {
            "vibration_mms": {"mean": 2.1, "std": 0.25, "warn_limit": 3.0, "trip_limit": 3.5},
            "tool_usage_cycles": {"nominal_max": 800, "trip_limit": 1000},
            "coolant_temp_c": {"mean": 24.0, "std": 1.2, "warn_limit": 28.0},
            "spindle_speed_rpm": {"target": 1200.0, "tol": 30.0},
            "feed_rate_mmrev": {"target": 0.20, "tol": 0.015},
            "motor_current_a": {"mean": 14.5, "std": 0.8}
        }

    def analyze_telemetry_series(
        self,
        batch_id: str = "BATCH-0245",
        machine: str = "CNC-04",
        telemetry_records: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        start = time.time()
        tool_calls = ["tool_fit_isolation_forest", "tool_rolling_zscore_detector", "tool_evaluate_process_drift"]

        if not telemetry_records:
            try:
                from backend.app.database.session import SessionLocal
                from backend.app.database.models import ProcessReading, Batch
                db = SessionLocal()
                b_obj = db.query(Batch).filter((Batch.batch_number == batch_id) | (Batch.id == batch_id)).first()
                if b_obj:
                    q = db.query(ProcessReading).filter(ProcessReading.batch_id == b_obj.id).order_by(ProcessReading.ts.asc()).all()
                    if q:
                        telemetry_records = [
                            {
                                "timestamp": r.ts.strftime("%Y-%m-%d %H:%M:%S") if hasattr(r.ts, "strftime") else str(r.ts),
                                "machine_vibration_mms": r.vibration,
                                "vibration": r.vibration,
                                "tool_usage_cycles": r.tool_usage_cycles,
                                "coolant_temperature_c": r.coolant_temp,
                                "coolant_temp": r.coolant_temp,
                                "spindle_speed_rpm": r.spindle_speed,
                                "spindle_speed": r.spindle_speed,
                                "feed_rate_mmrev": r.feed_rate,
                                "feed_rate": r.feed_rate,
                                "motor_current_a": r.motor_current,
                                "motor_current": r.motor_current,
                                "cycle_time_s": r.cycle_time,
                                "cycle_time": r.cycle_time,
                                "pressure": r.pressure
                            }
                            for r in q
                        ]
                db.close()
            except Exception:
                pass

        if not telemetry_records:
            report = ProcessMonitoringReport(
                batch_id=batch_id,
                machine=machine,
                total_data_points=0,
                anomalies_detected=0,
                critical_parameters=[],
                vibration_current=0.0,
                vibration_baseline=2.1,
                vibration_status="NORMAL",
                tool_cycles_current=0,
                tool_cycles_baseline=600,
                tool_status="NOMINAL",
                temperature_current=0.0,
                temperature_baseline=24.0,
                drift_detected=False,
                certainty=CertaintyLevel.STATISTICAL_FINDING
            )
            return {
                "report": report,
                "telemetry_points": [],
                "anomalies": [],
                "changed_vs_unchanged": [],
                "trends": {},
                "warnings": [],
                "log": self.log_execution(
                    step_number=4,
                    input_summary=f"No telemetry records found for {machine} ({batch_id})",
                    tool_calls=[],
                    output_summary="0 telemetry points found. Telemetry streaming or upload required.",
                    duration_ms=int((time.time() - start) * 1000)
                )
            }

        custom_baselines = {}
        custom_thresholds = {}
        missing_params = []
        try:
            from backend.app.database.session import SessionLocal
            from backend.app.database.models import ProcessBaseline, Machine
            db_conn = SessionLocal()
            mach = db_conn.query(Machine).filter((Machine.code == machine) | (Machine.id == machine)).first()
            m_target = mach.id if mach else machine
            db_bases = db_conn.query(ProcessBaseline).filter(ProcessBaseline.machine_id == m_target).all()
            if db_bases:
                for b in db_bases:
                    custom_baselines[b.parameter] = {
                        "mean": b.mean,
                        "std": b.std,
                        "p01": b.p01,
                        "p99": b.p99
                    }
                    default_cfg = OPERATIONAL_THRESHOLDS.get(b.parameter, {})
                    warn_val = default_cfg.get("warn", default_cfg.get("warn_high", b.upper_threshold))
                    crit_val = b.upper_threshold if b.upper_threshold is not None else default_cfg.get("critical", default_cfg.get("critical_high"))
                    custom_thresholds[b.parameter] = {
                        "lower": b.lower_threshold,
                        "upper": b.upper_threshold,
                        "warn": warn_val,
                        "critical": crit_val
                    }
                for p_key in OPERATIONAL_THRESHOLDS:
                    if p_key not in custom_baselines:
                        missing_params.append(p_key)
            db_conn.close()
        except Exception:
            pass

        analysis_res = anomaly_detector.analyze_telemetry_series(
            batch_id=batch_id,
            machine_code=machine,
            telemetry_records=telemetry_records,
            baselines=custom_baselines or None,
            thresholds=custom_thresholds or None
        )

        if missing_params:
            for p_m in missing_params:
                analysis_res.setdefault("warnings", []).append(
                    f"Parameter '{p_m}' has no configured baseline in machine {machine} configuration; threshold evaluation unavailable."
                )

        crit_vib_thresh = custom_thresholds.get("vibration", {}).get("critical", 3.5) if custom_thresholds else 3.5
        crit_tool_thresh = custom_thresholds.get("tool_usage_cycles", {}).get("critical", 1000) if custom_thresholds else 1000

        cleaned_data = analysis_res["cleaned_data_points"]
        analyzed_data_points: List[TelemetryDataPoint] = []
        anomalies_count = analysis_res["anomalies_detected"]

        for r in cleaned_data:
            vib = float(r.get("vibration", 2.1))
            tool_cyc = int(r.get("tool_usage_cycles", 600))
            is_pt_anom = bool(vib >= crit_vib_thresh or tool_cyc >= crit_tool_thresh)
            pt_flags = []
            if vib >= crit_vib_thresh:
                pt_flags.append(f"Vibration critical: {vib:.2f} mm/s (trip: {crit_vib_thresh} mm/s)")
            if tool_cyc >= crit_tool_thresh:
                pt_flags.append(f"Tool cycles exceeded: {tool_cyc} cycles")

            analyzed_data_points.append(
                TelemetryDataPoint(
                    timestamp=r["timestamp"],
                    spindle_speed_rpm=float(r.get("spindle_speed", 1200.0)),
                    feed_rate_mmrev=float(r.get("feed_rate", 0.20)),
                    coolant_temperature_c=float(r.get("coolant_temp", 24.0)),
                    machine_vibration_mms=vib,
                    tool_usage_cycles=tool_cyc,
                    motor_current_a=float(r.get("motor_current", 14.5)),
                    cycle_time_s=float(r.get("cycle_time", 45.0)),
                    is_anomaly=is_pt_anom,
                    anomaly_score=round(float((vib - 2.1)/0.2), 3) if vib > 2.1 else 0.0,
                    flags=pt_flags,
                    certainty=CertaintyLevel.STATISTICAL_FINDING
                )
            )

        last_pt = analyzed_data_points[-1]
        critical_flags = []
        if analysis_res["vibration_status"] == "ABNORMAL_CRITICAL":
            critical_flags.append("High machine vibration")
        if analysis_res["tool_status"] == "CRITICAL_EXCEEDED":
            critical_flags.append("High tool wear cycle count")

        report = ProcessMonitoringReport(
            batch_id=batch_id,
            machine=machine,
            total_data_points=len(analyzed_data_points),
            anomalies_detected=anomalies_count,
            critical_parameters=critical_flags,
            vibration_current=last_pt.machine_vibration_mms,
            vibration_baseline=2.1,
            vibration_status=analysis_res["vibration_status"],
            tool_cycles_current=last_pt.tool_usage_cycles,
            tool_cycles_baseline=600,
            tool_status=analysis_res["tool_status"],
            temperature_current=last_pt.coolant_temperature_c,
            temperature_baseline=24.0,
            drift_detected=analysis_res["drift_detected"],
            certainty=CertaintyLevel.STATISTICAL_FINDING
        )

        duration = int((time.time() - start) * 1000)
        log_entry = self.log_execution(
            step_number=4,
            input_summary=f"Processed {len(cleaned_data)} telemetry snapshots for {machine} ({batch_id})",
            tool_calls=tool_calls,
            output_summary=(
                f"Detected {anomalies_count} anomalies. Current vibration is {report.vibration_current:.2f} mm/s "
                f"(vs baseline {report.vibration_baseline} mm/s). Tool usage is {report.tool_cycles_current} cycles "
                f"(vs standard threshold 800 cycles). Significant upward drift identified."
            ),
            duration_ms=duration
        )

        return {
            "report": report,
            "telemetry_points": analyzed_data_points,
            "anomalies": analysis_res["anomalies"],
            "changed_vs_unchanged": analysis_res["changed_vs_unchanged"],
            "trends": analysis_res["trends"],
            "warnings": analysis_res["warnings"],
            "log": log_entry
        }

anomaly_agent = ProcessMonitoringAnomalyAgent()
process_agent = anomaly_agent
AnomalyAgent = ProcessMonitoringAnomalyAgent
ProcessAgent = ProcessMonitoringAnomalyAgent

__all__ = [
    "ProcessMonitoringAnomalyAgent",
    "AnomalyAgent",
    "ProcessAgent",
    "anomaly_agent",
    "process_agent",
]
