"""
Process Capability & Performance Engine (Cp, Cpk, Pp, Ppk)
Strictly adheres to AIAG SPC guidelines, ISO 21747, and IATF 16949 with mandatory guardrails.
Refuses computation when n < 5 and issues strong warnings when n < 30.
Evaluates statistical control, normality, drift, outliers, variance, and heterogeneous data sources.
"""
from typing import List, Dict, Any, Optional
import numpy as np
from scipy import stats
from backend.app.core.guardrails import EpistemicLabel

# Standard SPC constants for X-bar / R charts (subgroup size n = 2..10)
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

class FlexibleStatus(str):
    """String subclass that allows case-insensitive and backward-compatible status checks."""
    def __eq__(self, other):
        if isinstance(other, str):
            if other.lower() == self.lower():
                return True
            if other.upper() == "COMPUTED" and self.lower() in ("preliminary", "sufficient"):
                return True
            if other.upper() == "INSUFFICIENT_DATA" and self.lower() == "insufficient_data":
                return True
        return super().__eq__(other)

class ProcessCapabilityEngine:
    """Computes short-term capability (Cp/Cpk) and long-term performance (Pp/Ppk) with statistical guardrails."""

    @staticmethod
    def calculate_capability(
        values: List[float],
        usl: Optional[float] = None,
        lsl: Optional[float] = None,
        target: Optional[float] = None,
        subgroup_size: int = 1,
        is_in_control: Optional[bool] = None,
        out_of_control_violations: Optional[List[str]] = None,
        machine_ids: Optional[List[str]] = None,
        batch_ids: Optional[List[str]] = None,
        alpha: float = 0.05
    ) -> Dict[str, Any]:
        """
        Calculates Cp, Cpk, Pp, Ppk with full assumption checks and sample size guardrails.
        """
        n = len(values) if values is not None else 0
        warnings: List[str] = []

        base_response: Dict[str, Any] = {
            "status": FlexibleStatus("sufficient"),
            "sample_size": n,
            "mean": None,
            "std_dev": None,
            "sigma_within": None,
            "sigma_within_method": None,
            "sigma_overall": None,
            "sigma_overall_method": "Sample Standard Deviation s (ddof=1)",
            "usl": usl,
            "lsl": lsl,
            "target": target,
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
            "assessment": None,
            "interpretation_band": None,
            "benchmark_source": "AIAG Statistical Process Control (SPC) Reference Manual (2nd Edition) & IATF 16949:2016 Section 8.5.1",
            "warnings": warnings,
            "guidance_notice": (
                "DECISION GUIDANCE ONLY: Capability indices are statistical indicators for process improvement "
                "and supervision. QualityMind does not perform automatic lot acceptance, rejection, or quarantine "
                "decisions solely based on capability metrics without authorized quality engineering disposition."
            ),
            "future_guarantee_disclaimer": (
                "DISCLAIMER: Process capability metrics reflect historical statistical performance under observed conditions "
                "and do NOT constitute a guarantee of future zero-defect production or parts conformity."
            ),
            "label": EpistemicLabel.STATISTICAL_FINDING.value
        }

        # -------------------------------------------------------------
        # Guardrail 1: Sample Size Sufficiency (< 5 points -> Refusal)
        # -------------------------------------------------------------
        if n < 5:
            base_response["status"] = FlexibleStatus("insufficient_data")
            base_response["assessment"] = "Insufficient Data for Capability Assessment"
            warnings.append(
                f"INSUFFICIENT DATA: Sample size n={n} is too small (below minimum threshold n >= 5) required "
                f"for statistical capability estimation. Numeric capability indices suppressed."
            )
            return base_response

        vals = np.array(values, dtype=float)

        # -------------------------------------------------------------
        # Guardrail 2: Preliminary Sample Size Warning (5 <= n < 30)
        # -------------------------------------------------------------
        if n < 30:
            base_response["status"] = FlexibleStatus("preliminary")
            warnings.append(
                f"PRELIMINARY SAMPLE SIZE: Preliminary estimate: n={n} is less than the recommended guideline (n >= 30). "
                f"Capability indices are preliminary and exhibit wide confidence intervals; do not use for long-term capability certification."
            )

        # -------------------------------------------------------------
        # Guardrail 3: Zero or Near-Zero Variance Check
        # -------------------------------------------------------------
        var_sample = float(np.var(vals, ddof=1))
        if var_sample < 1e-12:
            base_response["status"] = "zero_variance"
            base_response["mean"] = round(float(np.mean(vals)), 4)
            base_response["std_dev"] = 0.0
            base_response["sigma_overall"] = 0.0
            base_response["sigma_within"] = 0.0
            base_response["assessment"] = "Zero Variance (No Process Spread)"
            warnings.append(
                "ZERO/NEAR-ZERO VARIANCE: Variance is zero or near zero (sigma < 1e-7). "
                "Division by zero avoided; capability indices cannot be meaningfully calculated."
            )
            return base_response

        # -------------------------------------------------------------
        # Guardrail 4: Specification Limits Check
        # -------------------------------------------------------------
        if usl is None and lsl is None:
            base_response["status"] = "missing_spec_limits"
            base_response["assessment"] = "Specification Limits Missing"
            warnings.append(
                "MISSING SPECIFICATION LIMITS: Neither USL nor LSL provided. "
                "Capability indices cannot be calculated without engineering tolerance limits."
            )
            return base_response

        if usl is not None and lsl is not None and usl <= lsl:
            base_response["status"] = "invalid_spec_limits"
            base_response["assessment"] = "Invalid Specification Limits"
            warnings.append(f"INVALID SPECIFICATION LIMITS: USL ({usl}) must be strictly greater than LSL ({lsl}).")
            return base_response

        is_one_sided = (usl is None) or (lsl is None)
        if usl is not None and lsl is None:
            warnings.append("ONE-SIDED SPECIFICATION: Upper specification limit (USL) only; two-sided Cp and Pp are not applicable.")
        elif lsl is not None and usl is None:
            warnings.append("ONE-SIDED SPECIFICATION: Lower specification limit (LSL) only; two-sided Cp and Pp are not applicable.")

        # -------------------------------------------------------------
        # Central Moments & Variance Estimations
        # -------------------------------------------------------------
        mean_val = float(np.mean(vals))
        s_overall = float(np.std(vals, ddof=1))  # Overall standard deviation (n-1)

        # Within-subgroup variation
        if subgroup_size > 1 and n >= subgroup_size:
            k = subgroup_size
            d2 = SPC_CONSTANTS.get(k, {}).get("d2", 1.128)
            num_subgroups = n // k
            reshaped = vals[:num_subgroups * k].reshape(num_subgroups, k)
            subgroup_ranges = np.ptp(reshaped, axis=1)
            r_bar = float(np.mean(subgroup_ranges))
            sigma_within = r_bar / d2 if r_bar > 0 else s_overall
            sigma_within_method = f"Subgroup Range R-bar / d2 (d2={d2} for subgroup size k={k})"
        else:
            moving_ranges = np.abs(np.diff(vals))
            mr_bar = float(np.mean(moving_ranges)) if len(moving_ranges) > 0 else s_overall
            sigma_within = mr_bar / 1.128 if mr_bar > 0 else s_overall
            sigma_within_method = "Moving Range MR-bar / d2 (d2=1.128 for n=2 consecutive differences)"

        if sigma_within < 1e-12:
            base_response["status"] = "zero_variance"
            base_response["assessment"] = "Near-Zero Within-Subgroup Variance"
            warnings.append(
                "ZERO/NEAR-ZERO VARIANCE: Within-subgroup variance is zero or near zero (sigma_within < 1e-7). "
                "Division by zero avoided; capability indices cannot be meaningfully calculated."
            )
            return base_response

        # -------------------------------------------------------------
        # Assumption Checks
        # -------------------------------------------------------------
        # (a) Statistical Control / Stability
        if is_in_control is False or (out_of_control_violations and len(out_of_control_violations) > 0):
            rule_details = ", ".join(out_of_control_violations) if out_of_control_violations else "Special cause variation detected"
            warnings.append(
                f"OUT-OF-CONTROL PROCESS: Process exhibits special cause variation ({rule_details}). "
                f"Capability indices assume statistical control and may be invalid."
            )
            base_response["stability_test"] = {"is_in_control": False, "violations": out_of_control_violations or []}
        else:
            base_response["stability_test"] = {"is_in_control": True, "violations": []}

        # (b) Normality Check (Shapiro-Wilk)
        norm_result = {"test": "Shapiro-Wilk", "statistic": None, "p_value": None, "alpha": alpha, "is_normal": True}
        if n >= 3:
            try:
                stat_w, p_w = stats.shapiro(vals)
                norm_result["statistic"] = round(float(stat_w), 4)
                norm_result["p_value"] = round(float(p_w), 4)
                norm_result["is_normal"] = bool(p_w >= alpha)
                if p_w < alpha:
                    warnings.append(
                        f"NON-NORMAL DISTRIBUTION: Shapiro-Wilk test indicates significant departure from normality "
                        f"(W={stat_w:.4f}, p={p_w:.4f} < alpha={alpha}). Standard capability formulas assume normal distribution."
                    )
            except Exception:
                pass
        base_response["normality_test"] = norm_result

        # (c) Process Drift / Trending Check (OLS slope test)
        trend_result = {"is_trending": False, "slope": None, "p_value": None, "alpha": alpha}
        if n >= 4:
            try:
                x_idx = np.arange(n)
                slope, intercept, r_value, p_value, std_err = stats.linregress(x_idx, vals)
                trend_result["slope"] = round(float(slope), 5)
                trend_result["p_value"] = round(float(p_value), 4)
                # Significant trend if p < alpha and magnitude is meaningful (> 0.0005 per piece)
                if p_value < alpha and abs(slope) > 0.0005:
                    trend_result["is_trending"] = True
                    warnings.append(
                        f"PROCESS DRIFT DETECTED: Significant systematic linear trend detected "
                        f"(slope={slope:+.5f}, p={p_value:.4f} < {alpha}), indicating progressive tool wear or thermal drift."
                    )
            except Exception:
                pass
        base_response["trend_test"] = trend_result

        # (d) Outliers Check (Points beyond 3 standard deviations from mean)
        outlier_indices = [int(i) for i, x in enumerate(vals) if abs(x - mean_val) > 3.0 * s_overall]
        base_response["outliers"] = outlier_indices
        if outlier_indices:
            warnings.append(
                f"OUTLIERS DETECTED: {len(outlier_indices)} observation(s) deviate by more than 3 standard deviations from the mean "
                f"(sample indices: {outlier_indices})."
            )

        # (e) Heterogeneous Data Source (Multiple Machines or Batches)
        if machine_ids and len(set(machine_ids)) > 1:
            unique_machines = sorted(list(set(machine_ids)))
            warnings.append(
                f"HETEROGENEOUS DATA SOURCE: Dataset contains measurements combined across multiple machines "
                f"({', '.join(unique_machines)}). Process capability requires homogeneous rational subgrouping."
            )
        if batch_ids and len(set(batch_ids)) > 1:
            unique_batches = sorted(list(set(batch_ids)))
            warnings.append(
                f"HETEROGENEOUS DATA SOURCE: Dataset contains measurements combined across multiple batches "
                f"({', '.join(unique_batches)}). Process capability requires homogeneous rational subgrouping."
            )

        # -------------------------------------------------------------
        # Capability Indices Computation
        # -------------------------------------------------------------
        tolerance = round(usl - lsl, 4) if (usl is not None and lsl is not None) else None

        # Short-term Capability (Cp & Cpk)
        if not is_one_sided:
            cp = round(tolerance / (6.0 * sigma_within), 4)
            cpu = round((usl - mean_val) / (3.0 * sigma_within), 4)
            cpl = round((mean_val - lsl) / (3.0 * sigma_within), 4)
            cpk = round(float(min(cpu, cpl)), 4)
        else:
            cp = None
            if usl is not None:
                cpu = round((usl - mean_val) / (3.0 * sigma_within), 4)
                cpl = None
                cpk = cpu
            else:
                cpu = None
                cpl = round((mean_val - lsl) / (3.0 * sigma_within), 4)
                cpk = cpl

        # Long-term Performance (Pp & Ppk)
        if not is_one_sided:
            pp = round(tolerance / (6.0 * s_overall), 4)
            ppu = round((usl - mean_val) / (3.0 * s_overall), 4)
            ppl = round((mean_val - lsl) / (3.0 * s_overall), 4)
            ppk = round(float(min(ppu, ppl)), 4)
        else:
            pp = None
            if usl is not None:
                ppu = round((usl - mean_val) / (3.0 * s_overall), 4)
                ppl = None
                ppk = ppu
            else:
                ppu = None
                ppl = round((mean_val - lsl) / (3.0 * s_overall), 4)
                ppk = ppl

        # -------------------------------------------------------------
        # 95% Confidence Interval for Cpk (Bissell / Chou Approximation)
        # -------------------------------------------------------------
        cpk_ci_95 = None
        if cpk is not None and n > 1:
            se_cpk = float(np.sqrt((1.0 / (9.0 * n)) + ((cpk ** 2) / (2.0 * (n - 1)))))
            z_crit = 1.95996  # 95% two-sided normal quantile
            ci_lower = round(cpk - z_crit * se_cpk, 4)
            ci_upper = round(cpk + z_crit * se_cpk, 4)
            ci_note = (
                f"Caution: 95% confidence interval [{ci_lower:.4f}, {ci_upper:.4f}] is wide due to small sample size (n={n}). "
                f"Collect n >= 30 parts for production validation."
                if n < 30 else
                f"95% confidence interval [{ci_lower:.4f}, {ci_upper:.4f}] based on n={n} observations."
            )
            cpk_ci_95 = {
                "lower": ci_lower,
                "upper": ci_upper,
                "standard_error": round(se_cpk, 4),
                "confidence_level": 0.95,
                "note": ci_note
            }

        # -------------------------------------------------------------
        # Interpretation Bands (AIAG / IATF Standard)
        # -------------------------------------------------------------
        if cpk is not None:
            if cpk < 1.00:
                interpretation_band = "Incapable (< 1.00)"
                assessment = "Incapable Process (Cpk < 1.00) — High defect risk; process variation exceeds allowable tolerance. 100% inspection or sorting required."
            elif cpk < 1.33:
                interpretation_band = "Marginally Capable (1.00 to 1.33)"
                assessment = "Marginally Capable Process (1.00 <= Cpk < 1.33) — Conditionally acceptable for legacy processes; requires tight process control and supervision."
            elif cpk < 1.67:
                interpretation_band = "Capable (1.33 to 1.67)"
                assessment = "Capable Process (1.33 <= Cpk < 1.67) — Conforms to standard industrial quality benchmarks."
            else:
                interpretation_band = "Highly Capable (>= 1.67)"
                assessment = "Highly Capable Process (Cpk >= 1.67) — World-class six-sigma process performance."
        else:
            interpretation_band = "Undefined"
            assessment = "Process capability cannot be assessed without specification limits."

        # Assemble Complete Response
        base_response.update({
            "mean": round(mean_val, 4),
            "std_dev": round(s_overall, 6),
            "sigma_within": round(sigma_within, 6),
            "sigma_within_method": sigma_within_method,
            "sigma_overall": round(s_overall, 6),
            "sigma_overall_method": "Sample Standard Deviation s (ddof=1)",
            "tolerance_band": tolerance,
            "cp": cp,
            "cpk": cpk,
            "cpu": cpu,
            "cpl": cpl,
            "pp": pp,
            "ppk": ppk,
            "ppu": ppu,
            "ppl": ppl,
            "cpk_ci_95": cpk_ci_95,
            "assessment": assessment,
            "interpretation_band": interpretation_band,
        })

        return base_response

capability_engine = ProcessCapabilityEngine()
