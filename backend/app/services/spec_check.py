"""
Deterministic Specification & Dimensional Compliance Engine
100% Deterministic Arithmetic (NumPy / Decimal). Zero LLM involvement in conformance decisions.
Guarantees boundary safety (e.g. 50.05 mm is strictly conforming for 50.00 +/- 0.05).
Supports symmetric, asymmetric, and one-sided engineering tolerances.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Optional
import numpy as np
from backend.app.core.guardrails import EpistemicLabel


class SpecificationEngine:
    """Computes engineering limits, evaluations, and tolerance band proximity."""

    @staticmethod
    def evaluate_trend(
        values: List[float],
        nominal_mm: float,
        usl: Optional[float] = None,
        lsl: Optional[float] = None,
        min_points_for_trend: int = 5,
        consecutive_run: int = 5,
        slope_threshold: float = 0.003
    ) -> Dict[str, Any]:
        """
        Explicit, configurable rule to detect sequential trends toward specification limits.
        Enforces data sufficiency rule: does not claim a trend from insufficient data (minimum 5 points).
        
        Rules:
        1. Data Sufficiency: If len(values) < min_points_for_trend, status is INSUFFICIENT_DATA.
        2. Consecutive Directional Run:
           - 5 consecutive increasing measurements ending above nominal -> DRIFT_TOWARD_USL
           - 5 consecutive decreasing measurements ending below nominal -> DRIFT_TOWARD_LSL
        3. Linear Regression Drift:
           - Slope >= slope_threshold with latest point > nominal -> DRIFT_TOWARD_USL
           - Slope <= -slope_threshold with latest point < nominal -> DRIFT_TOWARD_LSL
        4. Stability: Otherwise, trend is STABLE.
        """
        n = len(values)
        if n < min_points_for_trend:
            return {
                "trend_detected": False,
                "trend_direction": "INSUFFICIENT_DATA",
                "trend_slope": 0.0,
                "sample_count": n,
                "min_points_required": min_points_for_trend,
                "rule_description": f"Insufficient data to determine trend: {n} measurement(s) provided; minimum {min_points_for_trend} required.",
                "rule_triggered": None,
                "consecutive_direction": "NONE",
                "proximity_warning": False
            }

        x = np.arange(n)
        slope, _ = np.polyfit(x, values, 1)
        slope_val = round(float(slope), 5)

        # Check consecutive runs in the most recent consecutive_run window
        window = values[-consecutive_run:]
        is_increasing_run = all(window[i] < window[i+1] for i in range(len(window)-1))
        is_decreasing_run = all(window[i] > window[i+1] for i in range(len(window)-1))

        latest_val = values[-1]
        trend_detected = False
        trend_direction = "STABLE"
        rule_triggered = None

        tol_half = (usl - nominal_mm) if usl is not None else 0.05
        proximity_warning = False
        if usl is not None and latest_val >= (nominal_mm + 0.75 * tol_half):
            proximity_warning = True
        elif lsl is not None and latest_val <= (nominal_mm - 0.75 * tol_half):
            proximity_warning = True

        if is_increasing_run and latest_val > nominal_mm:
            trend_detected = True
            trend_direction = "DRIFT_TOWARD_USL"
            rule_triggered = f"{consecutive_run} consecutive increasing measurements ending at {latest_val:.4f} mm drifting toward Upper Specification Limit (USL)."
        elif is_decreasing_run and latest_val < nominal_mm:
            trend_detected = True
            trend_direction = "DRIFT_TOWARD_LSL"
            rule_triggered = f"{consecutive_run} consecutive decreasing measurements ending at {latest_val:.4f} mm drifting toward Lower Specification Limit (LSL)."
        elif slope_val >= slope_threshold and latest_val > nominal_mm:
            trend_detected = True
            trend_direction = "DRIFT_TOWARD_USL"
            rule_triggered = f"Linear regression slope (+{slope_val:.5f} mm/sample) indicates directional drift toward Upper Specification Limit (USL)."
        elif slope_val <= -slope_threshold and latest_val < nominal_mm:
            trend_detected = True
            trend_direction = "DRIFT_TOWARD_LSL"
            rule_triggered = f"Linear regression slope ({slope_val:.5f} mm/sample) indicates directional drift toward Lower Specification Limit (LSL)."

        return {
            "trend_detected": trend_detected,
            "trend_direction": trend_direction,
            "trend_slope": slope_val,
            "sample_count": n,
            "min_points_required": min_points_for_trend,
            "rule_description": rule_triggered or "Measurements are stable within tolerance band; no directional drift detected.",
            "rule_triggered": rule_triggered,
            "consecutive_direction": "INCREASING" if is_increasing_run else ("DECREASING" if is_decreasing_run else "MIXED"),
            "proximity_warning": proximity_warning
        }

    @staticmethod
    def evaluate_compliance(
        batch_id: str,
        nominal_mm: float = 50.00,
        tol_plus: Optional[float] = 0.05,
        tol_minus: Optional[float] = 0.05,
        measurements: Optional[List[Dict[str, Any]]] = None,
        parameter_name: str = "shaft_diameter",
        usl: Optional[float] = None,
        lsl: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Evaluates physical sample measurements against engineering specification limits.
        Uses 4-decimal precision quantization to eliminate IEEE 754 float boundary noise.
        Supports:
        - Symmetric tolerances (nominal +/- tol)
        - Asymmetric tolerances (tol_plus != tol_minus)
        - One-sided tolerances (usl only or lsl only)
        - Decimal boundary safety (50.05 and 49.95 strictly conforming; 50.0501 nonconforming)
        - Float noise safety (50.050000000000004 strictly conforming)
        - Deterministic sample standard deviation (ddof=1, n-1)
        """
        if measurements is None:
            measurements = []

        # Decimal conversions for deterministic engineering limits
        d_nom = Decimal(str(nominal_mm))
        
        # Determine USL
        d_usl = None
        if usl is not None:
            d_usl = Decimal(str(usl)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        elif tol_plus is not None:
            d_plus = Decimal(str(tol_plus))
            d_usl = (d_nom + d_plus).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        # Determine LSL
        d_lsl = None
        if lsl is not None:
            d_lsl = Decimal(str(lsl)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        elif tol_minus is not None:
            d_minus = Decimal(str(tol_minus))
            d_lsl = (d_nom - d_minus).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        eff_usl = float(d_usl) if d_usl is not None else None
        eff_lsl = float(d_lsl) if d_lsl is not None else None
        tolerance_band = (eff_usl - eff_lsl) if (eff_usl is not None and eff_lsl is not None) else None

        # Tolerance delta for band usage
        band_half = (Decimal(str(tolerance_band)) / Decimal("2")) if tolerance_band is not None else None

        evaluated_items = []
        conforming_count = 0
        nonconforming_count = 0
        max_deviation = 0.0
        values = []
        excluded_items = []
        warnings = []
        seen_component_ids = set()

        for idx, m in enumerate(measurements):
            # Extract raw value and component identifier
            raw_val = None
            if isinstance(m, (int, float, Decimal)):
                raw_val = m
                comp_id = f"P{idx+1:03d}"
            elif isinstance(m, dict):
                raw_val = m.get("measured_value", m.get("value"))
                comp_id = str(m.get("component_id", m.get("sample_id", f"P{idx+1:03d}")))
            else:
                raw_val = None
                comp_id = f"P{idx+1:03d}"

            # Check duplicate component identifier
            if comp_id in seen_component_ids:
                warnings.append(f"Duplicate sample identifier '{comp_id}' encountered at row {idx+1}.")
            seen_component_ids.add(comp_id)

            # Validate null / empty
            if raw_val is None or str(raw_val).strip() == "" or str(raw_val).strip().lower() in ("none", "null", "nan"):
                excluded_items.append({"sample_id": comp_id, "row": idx+1, "raw_value": raw_val, "reason": "Null or blank measurement"})
                warnings.append(f"Sample '{comp_id}' (row {idx+1}) had null/blank value and was excluded from calculation.")
                continue

            # Validate numeric parse
            try:
                val_float = float(raw_val)
                if np.isnan(val_float) or np.isinf(val_float):
                    raise ValueError("NaN/Inf")
            except (ValueError, TypeError):
                excluded_items.append({"sample_id": comp_id, "row": idx+1, "raw_value": str(raw_val), "reason": "Non-numeric measurement"})
                warnings.append(f"Sample '{comp_id}' (row {idx+1}) had non-numeric value '{raw_val}' and was excluded from calculation.")
                continue

            # Round float noise to 4 decimals and convert to Decimal for strict boundary checks
            val = round(val_float, 4)
            values.append(val)
            d_val = Decimal(str(val)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

            # Boundary evaluation
            is_conforming = True
            dev_from_limit = 0.0
            status = "CONFORMING"

            if d_usl is not None and d_val > d_usl:
                is_conforming = False
                status = "EXCEEDS_USL"
                dev_from_limit = float(d_val - d_usl)
            elif d_lsl is not None and d_val < d_lsl:
                is_conforming = False
                status = "BELOW_LSL"
                dev_from_limit = float(d_lsl - d_val)

            if is_conforming:
                conforming_count += 1
            else:
                nonconforming_count += 1

            dev_from_nominal = float(d_val - d_nom)
            if abs(dev_from_limit) > max_deviation:
                max_deviation = abs(dev_from_limit)

            # Tolerance band usage
            part_usage = 0.0
            if band_half is not None and band_half > 0:
                part_usage = float(abs(d_val - d_nom) / band_half)
            elif tol_plus is not None and tol_plus > 0:
                part_usage = float(abs(d_val - d_nom) / Decimal(str(tol_plus)))

            evaluated_items.append({
                "sample_id": comp_id,
                "component_id": comp_id,
                "measured_value": val,
                "nominal_mm": nominal_mm,
                "deviation_from_nominal": round(dev_from_nominal, 4),
                "deviation_from_limit": round(dev_from_limit, 4),
                "tolerance_band_usage": round(part_usage, 4),
                "tolerance_band_usage_percent": round(part_usage * 100.0, 2),
                "is_conforming": is_conforming,
                "status": status,
                "label": EpistemicLabel.OBSERVED_FACT.value
            })

        total = len(values)
        rejection_rate = round((nonconforming_count / total * 100.0), 2) if total > 0 else 0.0

        # Descriptive statistics (mean, sample std dev n-1, min, max)
        mean_val = round(float(np.mean(values)), 4) if total > 0 else None
        std_sample = round(float(np.std(values, ddof=1)), 6) if total > 1 else 0.0
        std_pop = round(float(np.std(values, ddof=0)), 6) if total > 0 else 0.0
        min_val = round(float(np.min(values)), 4) if total > 0 else None
        max_val = round(float(np.max(values)), 4) if total > 0 else None
        # Trend analysis across sequence
        trend_slope = 0.0
        if total >= 2:
            x = np.arange(total)
            slope, _ = np.polyfit(x, values, 1)
            trend_slope = round(float(slope), 5)

        # Explicit trend evaluation
        trend_eval = SpecificationEngine.evaluate_trend(
            values=values,
            nominal_mm=nominal_mm,
            usl=eff_usl,
            lsl=eff_lsl
        )

        # Proximity to limit (% of tolerance band consumed by mean)
        tolerance_used_pct = 0.0
        if mean_val is not None and tolerance_band is not None and tolerance_band > 0:
            tolerance_used_pct = round((abs(mean_val - nominal_mm) / (tolerance_band / 2.0)) * 100.0, 1)

        # Histogram bins aligned with specification limits
        histogram_bins = []
        if total > 0:
            below_lsl_count = sum(1 for v in values if (eff_lsl is not None and v < eff_lsl))
            lower_spec_count = sum(1 for v in values if (eff_lsl is not None and eff_lsl <= v < nominal_mm))
            upper_spec_count = sum(1 for v in values if (eff_usl is not None and nominal_mm <= v <= eff_usl))
            above_usl_count = sum(1 for v in values if (eff_usl is not None and v > eff_usl))

            histogram_bins = [
                {
                    "bin": f"< {eff_lsl:.2f} (Below LSL)" if eff_lsl is not None else "< Spec",
                    "edge_low": round(min_val - 0.05, 2) if min_val is not None else 0.0,
                    "edge_high": eff_lsl if eff_lsl is not None else nominal_mm,
                    "count": below_lsl_count,
                    "is_out_of_spec": True,
                    "color": "#EF4444"
                },
                {
                    "bin": f"{eff_lsl:.2f} - {nominal_mm:.2f} (Lower Spec)" if eff_lsl is not None else f"< {nominal_mm:.2f}",
                    "edge_low": eff_lsl if eff_lsl is not None else nominal_mm - (tol_minus or 0.05),
                    "edge_high": nominal_mm,
                    "count": lower_spec_count,
                    "is_out_of_spec": False,
                    "color": "#10B981"
                },
                {
                    "bin": f"{nominal_mm:.2f} - {eff_usl:.2f} (Upper Spec)" if eff_usl is not None else f"> {nominal_mm:.2f}",
                    "edge_low": nominal_mm,
                    "edge_high": eff_usl if eff_usl is not None else nominal_mm + (tol_plus or 0.05),
                    "count": upper_spec_count,
                    "is_out_of_spec": False,
                    "color": "#10B981"
                },
                {
                    "bin": f"> {eff_usl:.2f} (Above USL)" if eff_usl is not None else "> Spec",
                    "edge_low": eff_usl if eff_usl is not None else nominal_mm,
                    "edge_high": round(max_val + 0.05, 2) if max_val is not None else 1000.0,
                    "count": above_usl_count,
                    "is_out_of_spec": True,
                    "color": "#EF4444"
                }
            ]

        # Compute empirical histogram edges and counts
        bin_edges = []
        counts = []
        if total > 0:
            hist_counts, hist_edges = np.histogram(values, bins=min(5, max(1, total)))
            bin_edges = [round(float(e), 4) for e in hist_edges]
            counts = [int(c) for c in hist_counts]

        # Extract nonconforming items list
        nonconforming_items = [
            {
                "sample_id": item["sample_id"],
                "component_id": item["component_id"],
                "measured_value": item["measured_value"],
                "nominal_mm": item["nominal_mm"],
                "limit_breached": item["status"],
                "deviation_from_limit": item["deviation_from_limit"],
                "deviation_from_nominal": item["deviation_from_nominal"],
                "tolerance_band_usage_percent": item["tolerance_band_usage_percent"],
                "label": item["label"]
            }
            for item in evaluated_items if not item["is_conforming"]
        ]

        status_result = "EVALUATED" if total > 0 else "NO_DATA"

        return {
            "status": status_result,
            "batch_id": batch_id,
            "parameter": parameter_name,
            "nominal_mm": nominal_mm,
            "tolerance_plus": tol_plus,
            "tolerance_minus": tol_minus,
            "usl": eff_usl,
            "lsl": eff_lsl,
            "total_inspected": total,
            "accepted": conforming_count,
            "accepted_count": conforming_count,
            "conforming_count": conforming_count,
            "nonconforming": nonconforming_count,
            "nonconforming_count": nonconforming_count,
            "rejection_rate_percent": rejection_rate,
            "rejection_percentage": rejection_rate,
            "max_deviation_from_limit": round(max_deviation, 4),
            "max_deviation_mm": round(max_deviation, 4),
            "spec_limits": {
                "nominal": nominal_mm,
                "tolerance": tol_plus if tol_plus is not None else 0.05,
                "tolerance_plus": tol_plus,
                "tolerance_minus": tol_minus,
                "usl": eff_usl,
                "lsl": eff_lsl
            },
            "distribution": {
                "mean": mean_val,
                "std_dev_sample": std_sample,
                "std_dev_pop": std_pop,
                "min": min_val,
                "max": max_val,
                "bin_edges": bin_edges,
                "counts": counts
            },
            "mean_measured": mean_val,
            "mean": mean_val,
            "std_dev_sample": std_sample,
            "std_dev_pop": std_pop,
            "min_measured": min_val,
            "trend_slope": trend_slope,
            "trend_analysis": trend_eval,
            "trend_direction": trend_eval["trend_direction"],
            "trend_detected": trend_eval["trend_detected"],
            "trend_rule": trend_eval["rule_description"],
            "tolerance_band_used_percent": tolerance_used_pct,
            "histogram_bins": histogram_bins,
            "nonconforming_items": nonconforming_items,
            "measurements": evaluated_items,
            "evaluated_items": evaluated_items,
            "excluded_count": len(excluded_items),
            "excluded_items": excluded_items,
            "warnings": warnings,
            "label": EpistemicLabel.OBSERVED_FACT.value,
            "certainty": EpistemicLabel.OBSERVED_FACT.value,
            "disposition_notice": "Observed sample result. Final physical product disposition is an authorized human decision. System does not automatically reject batches."
        }


spec_engine = SpecificationEngine()
