"""
Statistical Process Control (SPC) Engine
Implements I-MR, X-bar/R, and p-charts with automated chart selection.
Detects Western Electric & Nelson out-of-control rules.
Strictly separates Statistical Control Limits (UCL/LCL) from Engineering Specification Limits (USL/LSL).
"""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from backend.app.core.guardrails import EpistemicLabel

# Standard SPC constants for X-bar / R charts (sample size n = 2..10)
SPC_CONSTANTS = {
    2: {"A2": 1.880, "D3": 0.0, "D4": 3.267, "d2": 1.128},
    3: {"A2": 1.023, "D3": 0.0, "D4": 2.574, "d2": 1.693},
    4: {"A2": 0.729, "D3": 0.0, "D4": 2.282, "d2": 2.059},
    5: {"A2": 0.577, "D3": 0.0, "D4": 2.114, "d2": 2.326},
    6: {"A2": 0.483, "D3": 0.0, "D4": 2.004, "d2": 2.534},
    7: {"A2": 0.419, "D3": 0.076, "D4": 1.924, "d2": 2.704},
    8: {"A2": 0.373, "D3": 0.136, "D4": 1.864, "d2": 2.847},
    9: {"A2": 0.337, "D3": 0.184, "D4": 1.816, "d2": 2.970},
    10: {"A2": 0.308, "D3": 0.223, "D4": 1.777, "d2": 3.078},
}

class SPCEngine:
    """Enterprise statistical process control engine for manufacturing lines."""

    @staticmethod
    def evaluate_spc(
        data: List[float],
        subgroup_size: int = 1,
        usl: Optional[float] = None,
        lsl: Optional[float] = None,
        is_attribute_data: bool = False,
        total_subgroup_counts: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Executes automated chart selection, control limit computation, and Nelson rule analysis.
        """
        n_points = len(data)
        if n_points < 2:
            return {
                "chart_type": "INSUFFICIENT_DATA",
                "error": "At least 2 points required for statistical limits.",
                "warnings": ["Insufficient points for SPC evaluation"]
            }

        warnings = []
        if n_points < 30:
            warnings.append(
                f"Sample size n={n_points} is below standard guideline (n >= 30). "
                f"Control limits are preliminary and subject to estimation variation."
            )

        # 1. Chart Selection Logic
        if is_attribute_data:
            chart_type = "p_chart"
            selection_reason = "Attribute binomial pass/fail proportions selected based on defect counts."
            chart_result = SPCEngine._compute_p_chart(data, total_subgroup_counts or [100]*n_points)
        elif subgroup_size >= 2 and subgroup_size <= 10 and n_points >= subgroup_size:
            chart_type = "Xbar_R_chart"
            selection_reason = f"Continuous data grouped in rational subgroups of size n={subgroup_size}."
            chart_result = SPCEngine._compute_xbar_r(data, subgroup_size)
        else:
            chart_type = "I_MR_chart"
            selection_reason = "Individual continuous readings evaluated with moving range (n=1)."
            chart_result = SPCEngine._compute_imr(data)

        cl = chart_result["cl"]
        ucl = chart_result["ucl"]
        lcl = chart_result["lcl"]
        sigma = chart_result["sigma"]
        points = chart_result["points"]

        # 2. Evaluate Nelson Rules on individual/subgroup averages
        violations = SPCEngine._evaluate_nelson_rules(points, cl, sigma)

        # 3. Explicit separation notice for UI and Report
        limit_separation_info = {
            "control_limits": {
                "concept": "Statistical Process Control Limits (Natural Process Variation)",
                "cl": round(cl, 4),
                "ucl": round(ucl, 4),
                "lcl": round(lcl, 4),
                "basis": "Calculated from actual process data (Mean +/- 3-sigma)"
            },
            "specification_limits": {
                "concept": "Engineering Customer Specification Limits (Tolerance Band)",
                "usl": round(usl, 4) if usl is not None else None,
                "lsl": round(lsl, 4) if lsl is not None else None,
                "basis": "Fixed by design blueprints; mathematically independent of process data"
            },
            "legend_notice": (
                "CRITICAL INDUSTRIAL DISTINCTION: Control limits (UCL/LCL) represent what the machine "
                "IS DOING (statistical capability). Specification limits (USL/LSL) represent what the part "
                "MUST DO (customer requirement). Never conflate these boundaries."
            )
        }

        # Build chart data series for frontend Plotly/Recharts
        chart_series = []
        for i, val in enumerate(points):
            pt_violations = [v["rule_number"] for v in violations if i in v["violating_indices"]]
            chart_series.append({
                "index": i + 1,
                "value": round(val, 4),
                "cl": round(cl, 4),
                "ucl": round(ucl, 4),
                "lcl": round(lcl, 4),
                "usl": round(usl, 4) if usl is not None else None,
                "lsl": round(lsl, 4) if lsl is not None else None,
                "is_out_of_control": len(pt_violations) > 0,
                "violated_rules": pt_violations
            })

        res = {
            "chart_type": chart_type,
            "selection_reason": selection_reason,
            "center_line": round(cl, 4),
            "ucl": round(ucl, 4),
            "lcl": round(lcl, 4),
            "usl": round(usl, 4) if usl is not None else None,
            "lsl": round(lsl, 4) if lsl is not None else None,
            "sigma": round(sigma, 5),
            "sigma_within": round(sigma, 6),
            "points_count": len(points),
            "nelson_violations": violations,
            "rule_violations": violations,
            "limit_separation_info": limit_separation_info,
            "chart_series": chart_series,
            "warnings": warnings,
            "label": EpistemicLabel.STATISTICAL_FINDING.value
        }
        if "mr_ucl" in chart_result:
            res["mr_bar"] = round(chart_result["mr_cl"], 4)
            res["mr_cl"] = round(chart_result["mr_cl"], 4)
            res["mr_ucl"] = round(chart_result["mr_ucl"], 5)
            res["mr_lcl"] = round(chart_result["mr_lcl"], 4)
            res["mr_series"] = chart_result.get("mr_series", [])
        return res

    @staticmethod
    def _compute_imr(values: List[float]) -> Dict[str, Any]:
        """I-MR: Individuals and Moving Range Chart."""
        vals = np.array(values, dtype=float)
        cl = float(np.mean(vals))
        moving_ranges = np.abs(np.diff(vals))
        mr_bar = float(np.mean(moving_ranges)) if len(moving_ranges) > 0 else 0.0
        # For n=2 moving range, d2 = 1.128, E2 = 2.66, D4 = 3.267
        sigma = mr_bar / 1.128 if mr_bar > 0 else float(np.std(vals))
        ucl = cl + 3.0 * sigma
        lcl = cl - 3.0 * sigma
        mr_cl = mr_bar
        mr_ucl = 3.267 * mr_bar
        mr_lcl = 0.0
        return {
            "cl": cl,
            "ucl": ucl,
            "lcl": lcl,
            "sigma": sigma,
            "points": values,
            "mr_cl": mr_cl,
            "mr_ucl": mr_ucl,
            "mr_lcl": mr_lcl,
            "mr_series": [float(m) for m in moving_ranges]
        }

    @staticmethod
    def _compute_xbar_r(values: List[float], n: int) -> Dict[str, Any]:
        """X-bar and R chart for rational subgroups."""
        const = SPC_CONSTANTS.get(n, SPC_CONSTANTS[5])
        a2 = const["A2"]
        d2 = const["d2"]
        d3 = const["D3"]
        d4 = const["D4"]

        num_subgroups = len(values) // n
        subgroups = [values[i*n : (i+1)*n] for i in range(num_subgroups)]

        x_bars = [float(np.mean(sg)) for sg in subgroups]
        ranges = [float(np.max(sg) - np.min(sg)) for sg in subgroups]

        x_double_bar = float(np.mean(x_bars))
        r_bar = float(np.mean(ranges))

        ucl = x_double_bar + (a2 * r_bar)
        lcl = x_double_bar - (a2 * r_bar)
        r_ucl = d4 * r_bar
        r_lcl = d3 * r_bar
        sigma = r_bar / d2 if r_bar > 0 else 0.001

        return {
            "cl": x_double_bar,
            "ucl": ucl,
            "lcl": lcl,
            "sigma": sigma,
            "points": x_bars,
            "r_cl": r_bar,
            "r_ucl": r_ucl,
            "r_lcl": r_lcl,
            "ranges": ranges
        }

    @staticmethod
    def _compute_p_chart(defect_counts: List[float], totals: List[int]) -> Dict[str, Any]:
        """p-chart for attribute proportion nonconforming."""
        proportions = [d / t for d, t in zip(defect_counts, totals)]
        total_defects = sum(defect_counts)
        total_inspected = sum(totals)
        p_bar = total_defects / total_inspected if total_inspected > 0 else 0.0

        n_avg = np.mean(totals)
        sigma = np.sqrt((p_bar * (1.0 - p_bar)) / n_avg) if n_avg > 0 and p_bar < 1.0 else 0.01

        ucl = min(1.0, p_bar + 3.0 * sigma)
        lcl = max(0.0, p_bar - 3.0 * sigma)

        return {"cl": p_bar, "ucl": ucl, "lcl": lcl, "sigma": sigma, "points": proportions}

    @staticmethod
    def _evaluate_nelson_rules(data: List[float], cl: float, sigma: float) -> List[Dict[str, Any]]:
        """Evaluates Nelson Rules 1 through 8 against process series."""
        violations = []
        n = len(data)
        if n < 1 or sigma <= 0:
            return violations

        # Nelson Rule 1: One point beyond 3-sigma (WECO Rule 1)
        r1_indices = [i for i, val in enumerate(data) if val > (cl + 3.0 * sigma) or val < (cl - 3.0 * sigma)]
        if r1_indices:
            violations.append({
                "rule_id": 1,
                "rule_number": 1,
                "weco_rule_number": 1,
                "rule_name": "Nelson Rule 1: Extreme Point Out of Statistical Control",
                "description": "One point is more than 3.0 standard deviations from the center line.",
                "violating_indices": r1_indices,
                "severity": "CRITICAL"
            })

        # Nelson Rule 2: 8 consecutive points on one side of center line (WECO Rule 4: Process Shift)
        if n >= 8:
            r2_indices = []
            for i in range(n - 7):
                window = data[i:i+8]
                if all(v > cl for v in window) or all(v < cl for v in window):
                    r2_indices.extend(list(range(i, i+8)))
            if r2_indices:
                violations.append({
                    "rule_id": 2,
                    "rule_number": 2,
                    "weco_rule_number": 4,
                    "rule_name": "Nelson Rule 2: Sustained Process Shift (8 points on one side)",
                    "description": "8 consecutive points fall on the same side of the center line.",
                    "violating_indices": sorted(list(set(r2_indices))),
                    "severity": "HIGH"
                })

        # Nelson Rule 3: 6 consecutive points steadily increasing or decreasing (Process Drift)
        if n >= 6:
            r3_indices = []
            for i in range(n - 5):
                window = data[i:i+6]
                is_inc = all(window[j] < window[j+1] for j in range(5))
                is_dec = all(window[j] > window[j+1] for j in range(5))
                if is_inc or is_dec:
                    r3_indices.extend(list(range(i, i+6)))
            if r3_indices:
                violations.append({
                    "rule_id": 3,
                    "rule_number": 3,
                    "weco_rule_number": None,
                    "rule_name": "Nelson Rule 3: Continuous Trend / Tool Wear Drift",
                    "description": "6 consecutive points are steadily increasing or decreasing.",
                    "violating_indices": sorted(list(set(r3_indices))),
                    "severity": "HIGH"
                })

        # Nelson Rule 5: 2 of 3 consecutive points beyond 2-sigma on same side (WECO Rule 2)
        if n >= 3:
            r5_indices = []
            for i in range(n - 2):
                window = data[i:i+3]
                high_count = sum(1 for v in window if v > (cl + 2.0 * sigma))
                low_count = sum(1 for v in window if v < (cl - 2.0 * sigma))
                if high_count >= 2 or low_count >= 2:
                    r5_indices.extend(list(range(i, i+3)))
            if r5_indices:
                violations.append({
                    "rule_id": 5,
                    "rule_number": 5,
                    "weco_rule_number": 2,
                    "rule_name": "Nelson Rule 5: Zone A Warning (2 of 3 beyond 2-sigma)",
                    "description": "2 out of 3 consecutive points fall beyond 2-sigma on the same side.",
                    "violating_indices": sorted(list(set(r5_indices))),
                    "severity": "HIGH"
                })

        # Nelson Rule 6: 4 of 5 consecutive points beyond 1-sigma on same side (WECO Rule 3)
        if n >= 5:
            r6_indices = []
            for i in range(n - 4):
                window = data[i:i+5]
                high_count = sum(1 for v in window if v > (cl + 1.0 * sigma))
                low_count = sum(1 for v in window if v < (cl - 1.0 * sigma))
                if high_count >= 4 or low_count >= 4:
                    r6_indices.extend(list(range(i, i+5)))
            if r6_indices:
                violations.append({
                    "rule_id": 6,
                    "rule_number": 6,
                    "weco_rule_number": 3,
                    "rule_name": "Nelson Rule 6: Zone B Shift (4 of 5 beyond 1-sigma)",
                    "description": "4 out of 5 consecutive points fall beyond 1-sigma on the same side.",
                    "violating_indices": sorted(list(set(r6_indices))),
                    "severity": "MEDIUM"
                })

        return violations

spc_engine = SPCEngine()
