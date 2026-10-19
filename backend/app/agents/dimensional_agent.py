import time
from typing import Dict, Any, List, Optional
from backend.app.agents.base_agent import BaseQualityAgent
from backend.app.models.schemas import CertaintyLevel, InspectionReport, MeasurementItem
from backend.app.services.spec_check import SpecificationEngine

class DimensionalComplianceAgent(BaseQualityAgent):
    def __init__(self):
        super().__init__(
            name="Agent 3 — Dimensional & Specification Compliance Agent",
            role="Compare measured product characteristics against engineering specifications",
            certainty_level=CertaintyLevel.OBSERVED_FACT
        )

    def retrieve_specification(
        self,
        batch_id: Optional[str] = None,
        product_id: Optional[str] = None,
        db: Optional[Any] = None
    ) -> Dict[str, Any]:
        from backend.app.services.inspection_service import get_batch_and_spec
        if batch_id:
            spec = get_batch_and_spec(batch_id, db=db, product_id=product_id)
            if spec:
                return spec

        if db and product_id:
            from backend.app.database.models import Product, InspectionCharacteristic
            prod = db.query(Product).filter((Product.id == product_id) | (Product.part_number == product_id)).first()
            if prod:
                char = db.query(InspectionCharacteristic).filter(InspectionCharacteristic.product_id == prod.id).first()
                if char:
                    return {
                        "product_id": prod.id,
                        "part_number": prod.part_number,
                        "product_name": prod.name,
                        "parameter": char.name,
                        "nominal_mm": char.nominal,
                        "tolerance_mm": char.tol_plus,
                        "tolerance_plus": char.tol_plus,
                        "tolerance_minus": char.tol_minus,
                        "usl_mm": char.usl,
                        "lsl_mm": char.lsl,
                        "unit": char.unit
                    }

        return {
            "part_number": "PS-2026-101",
            "product_id": "prod-ps-101",
            "product_name": "Precision Ground Shaft",
            "parameter": "shaft_diameter",
            "nominal_mm": 50.00,
            "tolerance_mm": 0.05,
            "tolerance_plus": 0.05,
            "tolerance_minus": 0.05,
            "usl_mm": 50.05,
            "lsl_mm": 49.95,
            "unit": "mm"
        }

    def evaluate_compliance(
        self,
        batch_id: str,
        measurements: List[Dict[str, Any]],
        nominal_mm: Optional[float] = None,
        tolerance_mm: Optional[float] = None,
        tol_plus: Optional[float] = None,
        tol_minus: Optional[float] = None,
        usl: Optional[float] = None,
        lsl: Optional[float] = None,
        parameter_name: Optional[str] = None,
        product_id: Optional[str] = None,
        db: Optional[Any] = None
    ) -> Dict[str, Any]:
        start = time.time()
        tool_calls = ["tool_calculate_spec_limits", "tool_deterministic_tolerance_check"]

        if db is not None or (nominal_mm is None and tolerance_mm is None):
            spec_info = self.retrieve_specification(batch_id=batch_id, product_id=product_id, db=db)
            if nominal_mm is None:
                nominal_mm = spec_info.get("nominal_mm", 50.00)
            if tolerance_mm is None:
                tolerance_mm = spec_info.get("tolerance_mm", 0.05)
            if usl is None:
                usl = spec_info.get("usl_mm")
            if lsl is None:
                lsl = spec_info.get("lsl_mm")
            if parameter_name is None:
                parameter_name = spec_info.get("parameter", "shaft_diameter")

        eff_nom = nominal_mm if nominal_mm is not None else 50.00
        eff_tol = tolerance_mm if tolerance_mm is not None else 0.05
        eff_plus = tol_plus if tol_plus is not None else eff_tol
        eff_minus = tol_minus if tol_minus is not None else eff_tol
        eff_param = parameter_name or "shaft_diameter"

        spec_result = SpecificationEngine.evaluate_compliance(
            batch_id=batch_id,
            nominal_mm=eff_nom,
            tol_plus=eff_plus,
            tol_minus=eff_minus,
            measurements=measurements,
            parameter_name=eff_param,
            usl=usl,
            lsl=lsl
        )

        evaluated_items: List[MeasurementItem] = []
        for item in spec_result["measurements"]:
            evaluated_items.append(
                MeasurementItem(
                    sample_id=item["sample_id"],
                    measured_value=item["measured_value"],
                    deviation_from_nominal=item["deviation_from_nominal"],
                    deviation_from_limit=item["deviation_from_limit"],
                    is_conforming=item["is_conforming"],
                    status=item["status"],
                    certainty=CertaintyLevel.OBSERVED_FACT
                )
            )

        eff_usl = spec_result["usl"] if spec_result["usl"] is not None else round(eff_nom + eff_plus, 4)
        eff_lsl = spec_result["lsl"] if spec_result["lsl"] is not None else round(eff_nom - eff_minus, 4)

        report = InspectionReport(
            batch_id=batch_id,
            total_inspected=spec_result["total_inspected"],
            accepted=spec_result["accepted"],
            nonconforming=spec_result["nonconforming"],
            rejection_rate_percent=spec_result["rejection_rate_percent"],
            measurements=evaluated_items,
            nominal_mm=eff_nom,
            tolerance_mm=eff_plus,
            usl=eff_usl,
            lsl=eff_lsl,
            trend_analysis=spec_result.get("trend_analysis"),
            trend_direction=spec_result.get("trend_direction"),
            trend_slope=spec_result.get("trend_slope"),
            trend_detected=spec_result.get("trend_detected"),
            max_deviation_from_limit=spec_result.get("max_deviation_from_limit"),
            mean=spec_result.get("mean"),
            std_dev_sample=spec_result.get("std_dev_sample"),
            distribution=spec_result.get("distribution"),
            certainty=CertaintyLevel.OBSERVED_FACT
        )

        duration = int((time.time() - start) * 1000)
        max_dev = spec_result["max_deviation_from_limit"]
        trend_status_desc = spec_result.get("trend_direction", "STABLE")
        log_entry = self.log_execution(
            step_number=3,
            input_summary=f"Evaluated {spec_result['total_inspected']} measurements against USL={eff_usl}mm, LSL={eff_lsl}mm",
            tool_calls=tool_calls,
            output_summary=(
                f"Inspection Results: {spec_result['nonconforming']}/{spec_result['total_inspected']} nonconforming "
                f"({spec_result['rejection_rate_percent']}% rejection rate). Max deviation: +{max_dev:.4f} mm. "
                f"Trend: {trend_status_desc}. Final batch disposition reserved for human review."
            ),
            duration_ms=duration
        )

        return {
            "report": report,
            "spec_data": spec_result,
            "log": log_entry,
            "disposition_notice": (
                "Dimensional findings recorded as observed facts. "
                "Agent 3 does not autonomously release or reject the production batch; "
                "final disposition requires authorized engineering sign-off."
            )
        }

compliance_agent = DimensionalComplianceAgent()
dimensional_agent = compliance_agent
ComplianceAgent = DimensionalComplianceAgent
DimensionalAgent = DimensionalComplianceAgent

__all__ = [
    "DimensionalComplianceAgent",
    "ComplianceAgent",
    "DimensionalAgent",
    "compliance_agent",
    "dimensional_agent",
]
