import time
import numpy as np
from typing import Dict, Any, List
from backend.app.agents.base_agent import BaseQualityAgent
from backend.app.models.schemas import CertaintyLevel, SPCReport, NelsonRuleViolation
from backend.app.services.capability import capability_engine

class StatisticalProcessControlAgent(BaseQualityAgent):
    def __init__(self):
        super().__init__(
            name="Agent 5 — Statistical Process Control Agent",
            role="Monitor manufacturing-process stability using statistical techniques and capability indices",
            certainty_level=CertaintyLevel.STATISTICAL_FINDING
        )

    def analyze_process_capability_and_control(
        self,
        batch_id: str,
        values: List[float],
        usl: float = 50.05,
        lsl: float = 49.95,
        nominal: float = 50.00,
        subgroup_size: int = 1
    ) -> Dict[str, Any]:
        start = time.time()
        tool_calls = [
            "tool_compute_moments_mean_sigma",
            "tool_calculate_imr_control_limits",
            "tool_evaluate_nelson_rules",
            "tool_calculate_cp_cpk_indices"
        ]

        if not values or len(values) == 0:
            report = SPCReport(
                batch_id=batch_id,
                sample_size=0,
                mean=None,
                std_dev=None,
                ucl=None,
                lcl=None,
                cl=None,
                min_value=None,
                max_value=None,
                range_value=None,
                chart_type="I-MR",
                review_status="HUMAN_REVIEW_REQUIRED",
                autonomous_actions_prohibited=True,
                usl=usl,
                lsl=lsl,
                cp=None,
                cpk=None,
                pp=None,
                ppk=None,
                capability_assessment="Insufficient Data for Capability Assessment",
                chart_data=[],
                nelson_violations=[],
                distinction_warning="INSUFFICIENT DATA: No valid measurements provided for SPC evaluation.",
                certainty=CertaintyLevel.STATISTICAL_FINDING,
                status="insufficient_data",
                warnings=["INSUFFICIENT DATA: 0 observations provided. Statistical limits and capability suppressed."],
                guidance_notice="DECISION GUIDANCE ONLY: Capability indices require observed measurements.",
                future_guarantee_disclaimer="DISCLAIMER: Historical statistical indicator only."
            )
            duration = int((time.time() - start) * 1000)
            log_entry = self.log_execution(
                step_number=5,
                input_summary=f"Evaluated SPC for n=0 points against USL={usl}, LSL={lsl}",
                tool_calls=tool_calls,
                output_summary="No observations provided. SPC evaluation suppressed.",
                duration_ms=duration
            )
            return {"report": report, "log": log_entry}

        clean_vals = []
        for v in values:
            try:
                f_val = float(v)
                if not np.isnan(f_val) and not np.isinf(f_val):
                    clean_vals.append(f_val)
            except (ValueError, TypeError):
                continue

        data = np.array(clean_vals, dtype=float)
        n = len(data)

        if n == 0:
            report = SPCReport(
                batch_id=batch_id,
                sample_size=0,
                mean=None,
                std_dev=None,
                ucl=None,
                lcl=None,
                cl=None,
                min_value=None,
                max_value=None,
                range_value=None,
                chart_type="I-MR",
                review_status="HUMAN_REVIEW_REQUIRED",
                autonomous_actions_prohibited=True,
                usl=usl,
                lsl=lsl,
                cp=None,
                cpk=None,
                pp=None,
                ppk=None,
                capability_assessment="Insufficient Data for Capability Assessment",
                chart_data=[],
                nelson_violations=[],
                distinction_warning="INSUFFICIENT DATA: No valid numeric measurements provided.",
                certainty=CertaintyLevel.STATISTICAL_FINDING,
                status="insufficient_data",
                warnings=["INSUFFICIENT DATA: No valid numeric readings after cleaning."],
                guidance_notice="DECISION GUIDANCE ONLY: Capability indices require observed measurements.",
                future_guarantee_disclaimer="DISCLAIMER: Historical statistical indicator only."
            )
            duration = int((time.time() - start) * 1000)
            log_entry = self.log_execution(
                step_number=5,
                input_summary=f"Evaluated SPC for n=0 valid points against USL={usl}, LSL={lsl}",
                tool_calls=tool_calls,
                output_summary="No valid numeric readings provided.",
                duration_ms=duration
            )
            return {"report": report, "log": log_entry}

        mean = float(np.mean(data))
        min_val = float(np.min(data))
        max_val = float(np.max(data))
        range_val = float(np.ptp(data))
        std_dev = float(np.std(data, ddof=1)) if n > 1 else 0.0

        if n < 2:
            report = SPCReport(
                batch_id=batch_id,
                sample_size=n,
                mean=round(mean, 4),
                std_dev=0.0,
                ucl=None,
                lcl=None,
                cl=round(mean, 4),
                min_value=round(min_val, 4),
                max_value=round(max_val, 4),
                range_value=0.0,
                chart_type="I-MR",
                review_status="HUMAN_REVIEW_REQUIRED",
                autonomous_actions_prohibited=True,
                usl=usl,
                lsl=lsl,
                cp=None,
                cpk=None,
                pp=None,
                ppk=None,
                capability_assessment="Insufficient Data for Capability Assessment",
                chart_data=[{"sample_index": 1, "sample_id": "P001", "value": round(mean, 4)}],
                nelson_violations=[],
                distinction_warning="INSUFFICIENT DATA: At least 2 observations required for control limits.",
                certainty=CertaintyLevel.STATISTICAL_FINDING,
                status="insufficient_data",
                warnings=["INSUFFICIENT DATA: Single observation (n=1). Control limits and capability indices suppressed."],
                guidance_notice="DECISION GUIDANCE ONLY: Capability indices require observed measurements.",
                future_guarantee_disclaimer="DISCLAIMER: Historical statistical indicator only."
            )
            duration = int((time.time() - start) * 1000)
            log_entry = self.log_execution(
                step_number=5,
                input_summary=f"Evaluated SPC for n=1 point against USL={usl}, LSL={lsl}",
                tool_calls=tool_calls,
                output_summary="Single point provided; control limits suppressed.",
                duration_ms=duration
            )
            return {"report": report, "log": log_entry}

        spc_constants_subgroup = {
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

        if subgroup_size >= 2 and n >= subgroup_size:
            chart_type = "X-bar/R"
            k = subgroup_size
            const = spc_constants_subgroup.get(k, spc_constants_subgroup[5])
            a2 = const["A2"]
            d2 = const["d2"]
            num_sg = n // k
            subgroups = [data[i*k:(i+1)*k] for i in range(num_sg)]
            x_bars = [float(np.mean(sg)) for sg in subgroups]
            ranges = [float(np.ptp(sg)) for sg in subgroups]
            cl = round(float(np.mean(x_bars)), 4)
            r_bar = float(np.mean(ranges))
            ucl = round(cl + a2 * r_bar, 4)
            lcl = round(cl - a2 * r_bar, 4)
            sigma_within = r_bar / d2 if r_bar > 0 else (std_dev if std_dev > 0 else 0.001)
            eval_data = np.array(x_bars)
        else:
            chart_type = "I-MR"
            moving_ranges = np.abs(np.diff(data))
            mr_bar = float(np.mean(moving_ranges))
            sigma_mr = mr_bar / 1.128 if mr_bar > 0 else (std_dev if std_dev > 0 else 0.001)
            sigma_within = sigma_mr
            cl = round(mean, 4)
            ucl = round(mean + 3.0 * sigma_within, 4)
            lcl = round(mean - 3.0 * sigma_within, 4)
            eval_data = data

        violations: List[NelsonRuleViolation] = []
        n_eval = len(eval_data)

        rule1_hits = [i for i, x in enumerate(eval_data) if x > ucl or x < lcl]
        if rule1_hits:
            violations.append(
                NelsonRuleViolation(
                    rule_number=1,
                    rule_name="Extreme Point Out of Statistical Control",
                    description=f"{len(rule1_hits)} point(s) exceed 3-sigma statistical control limits [{lcl}, {ucl}].",
                    sample_indices=rule1_hits,
                    severity="Critical"
                )
            )

        if n_eval >= 8:
            r2_indices = []
            for i in range(n_eval - 7):
                window = eval_data[i:i+8]
                if all(v > cl for v in window) or all(v < cl for v in window):
                    r2_indices.extend(list(range(i, i+8)))
            if r2_indices:
                violations.append(
                    NelsonRuleViolation(
                        rule_number=2,
                        rule_name="Process Mean Shift",
                        description="8 or more consecutive points fall on the same side of the center line.",
                        sample_indices=sorted(list(set(r2_indices))),
                        severity="High"
                    )
                )

        if n_eval >= 6:
            r3_indices = []
            for i in range(n_eval - 5):
                window = eval_data[i:i+6]
                is_inc = all(window[j] < window[j+1] for j in range(5))
                is_dec = all(window[j] > window[j+1] for j in range(5))
                if is_inc or is_dec:
                    r3_indices.extend(list(range(i, i+6)))
            if r3_indices:
                violations.append(
                    NelsonRuleViolation(
                        rule_number=3,
                        rule_name="Continuous Trend / Tool Wear Drift",
                        description="Six consecutive points steadily increasing or decreasing, indicating tool wear or thermal drift.",
                        sample_indices=sorted(list(set(r3_indices))),
                        severity="High"
                    )
                )

        if n_eval >= 3 and sigma_within > 0:
            r5_indices = []
            for i in range(n_eval - 2):
                window = eval_data[i:i+3]
                high_count = sum(1 for v in window if v > (cl + 2.0 * sigma_within))
                low_count = sum(1 for v in window if v < (cl - 2.0 * sigma_within))
                if high_count >= 2 or low_count >= 2:
                    r5_indices.extend(list(range(i, i+3)))
            if r5_indices:
                violations.append(
                    NelsonRuleViolation(
                        rule_number=5,
                        rule_name="Zone A Warning (2 of 3 beyond 2-sigma)",
                        description="2 out of 3 consecutive points fall beyond 2-sigma on the same side of center line.",
                        sample_indices=sorted(list(set(r5_indices))),
                        severity="High"
                    )
                )

        if n_eval >= 5 and sigma_within > 0:
            r6_indices = []
            for i in range(n_eval - 4):
                window = eval_data[i:i+5]
                high_count = sum(1 for v in window if v > (cl + 1.0 * sigma_within))
                low_count = sum(1 for v in window if v < (cl - 1.0 * sigma_within))
                if high_count >= 4 or low_count >= 4:
                    r6_indices.extend(list(range(i, i+5)))
            if r6_indices:
                violations.append(
                    NelsonRuleViolation(
                        rule_number=6,
                        rule_name="Zone B Shift (4 of 5 beyond 1-sigma)",
                        description="4 out of 5 consecutive points fall beyond 1-sigma on the same side of center line.",
                        sample_indices=sorted(list(set(r6_indices))),
                        severity="Medium"
                    )
                )

        rule_desc_list = [f"Rule {v.rule_number}: {v.rule_name}" for v in violations]
        cap_res = capability_engine.calculate_capability(
            values=clean_vals,
            usl=usl,
            lsl=lsl,
            target=nominal,
            subgroup_size=subgroup_size,
            is_in_control=(len(violations) == 0),
            out_of_control_violations=rule_desc_list
        )

        cp = cap_res.get("cp")
        cpk = cap_res.get("cpk")
        pp = cap_res.get("pp")
        ppk = cap_res.get("ppk")
        cap_assessment = cap_res.get("assessment") or "Capability assessment unavailable"

        chart_data = []
        for i, val in enumerate(data):
            val_f = float(round(float(val), 4))
            chart_data.append({
                "sample_index": i + 1,
                "sample_id": f"P{i+1:03d}",
                "value": val_f,
                "ucl": float(ucl),
                "lcl": float(lcl),
                "cl": float(cl),
                "usl": float(usl) if usl is not None else None,
                "lsl": float(lsl) if lsl is not None else None,
                "is_out_of_control": bool(val_f > ucl or val_f < lcl),
                "is_out_of_spec": bool((usl is not None and val_f > usl) or (lsl is not None and val_f < lsl))
            })

        warning_note = ""
        if cap_res.get("warnings"):
            warning_note = " | ".join(cap_res.get("warnings", []))

        report = SPCReport(
            batch_id=batch_id,
            sample_size=n,
            mean=round(mean, 4),
            std_dev=round(std_dev, 4),
            ucl=ucl,
            lcl=lcl,
            cl=cl,
            min_value=round(min_val, 4),
            max_value=round(max_val, 4),
            range_value=round(range_val, 4),
            chart_type=chart_type,
            review_status="HUMAN_REVIEW_REQUIRED",
            autonomous_actions_prohibited=True,
            usl=usl,
            lsl=lsl,
            cp=cp,
            cpk=cpk,
            pp=pp,
            ppk=ppk,
            capability_assessment=cap_assessment,
            chart_data=chart_data,
            nelson_violations=violations,
            distinction_warning=(
                (f"{warning_note} | " if warning_note else "") +
                f"SPECIFICATION LIMITS (USL={usl}, LSL={lsl}) represent engineering design tolerance. "
                f"STATISTICAL CONTROL LIMITS (UCL={ucl}, LCL={lcl}) represent actual 3-sigma manufacturing capability."
            ),
            certainty=CertaintyLevel.STATISTICAL_FINDING,
            status=cap_res.get("status", "sufficient"),
            warnings=cap_res.get("warnings", []),
            sigma_within=cap_res.get("sigma_within"),
            sigma_within_method=cap_res.get("sigma_within_method"),
            sigma_overall=cap_res.get("sigma_overall"),
            sigma_overall_method=cap_res.get("sigma_overall_method"),
            cpk_ci_95=cap_res.get("cpk_ci_95"),
            interpretation_band=cap_res.get("interpretation_band"),
            guidance_notice=cap_res.get("guidance_notice"),
            future_guarantee_disclaimer=cap_res.get("future_guarantee_disclaimer")
        )

        duration = int((time.time() - start) * 1000)
        log_entry = self.log_execution(
            step_number=5,
            input_summary=f"Evaluated SPC for n={n} points against USL={usl}, LSL={lsl}",
            tool_calls=tool_calls,
            output_summary=(
                f"SPC Findings: Mean={mean:.4f}mm, StdDev={std_dev:.4f}mm, UCL={ucl}mm, LCL={lcl}mm. "
                f"Cp={cp}, Cpk={cpk}. {len(violations)} Nelson Rule violations detected."
            ),
            duration_ms=duration
        )

        return {
            "report": report,
            "log": log_entry
        }

spc_agent = StatisticalProcessControlAgent()
SPCAgent = StatisticalProcessControlAgent

__all__ = [
    "StatisticalProcessControlAgent",
    "SPCAgent",
    "spc_agent",
]
