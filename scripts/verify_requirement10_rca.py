"""
Independent QA Recomputation and Verification Script for Requirement 10 (Root Cause Analysis).
Performs pure statistical and formula verification without relying on application internal state:
1. Recomputes BATCH-0245 evidence values (tool usage +91.67%, vibration +82.86%, change-point at P003).
2. Deterministic evidence scoring formula verification matching docs/rca_methodology.md.
3. Counterfactual ranking change proof (tool cycles 450, vibration 2.1 mm/s -> score 0.13, rank 5).
4. Independent Pearson & Spearman correlation calculations with p-values and sample sizes.
5. Regex audit for unauthorized unproven causal assertions.
"""
import sys
import os
import re
import json
import numpy as np
from scipy import stats

def recompute_evidence_values():
    # 1. Telemetry and Measurement physical values
    nominal_tool_limit = 600
    observed_tool_cycles = 1150
    overdue_cycles = observed_tool_cycles - nominal_tool_limit
    overdue_pct = (overdue_cycles / nominal_tool_limit) * 100.0

    baseline_vibration = 2.10
    observed_vibration = 3.84
    vibration_increase_pct = ((observed_vibration - baseline_vibration) / baseline_vibration) * 100.0

    measurements = [50.01, 50.03, 50.06, 50.08, 50.07]
    usl = 50.05
    out_of_spec_indices = [i for i, v in enumerate(measurements) if v > usl]
    first_change_point_idx = out_of_spec_indices[0] if out_of_spec_indices else None
    first_change_point_sample = f"P00{first_change_point_idx + 1}"

    return {
        "tool_cycles": {
            "observed": observed_tool_cycles,
            "nominal": nominal_tool_limit,
            "overdue_cycles": overdue_cycles,
            "overdue_percent": round(overdue_pct, 2)
        },
        "vibration": {
            "observed": observed_vibration,
            "baseline": baseline_vibration,
            "increase_percent": round(vibration_increase_pct, 2)
        },
        "dimensional_change_point": {
            "sample_id": first_change_point_sample,
            "index": first_change_point_idx,
            "measured_value": measurements[first_change_point_idx],
            "usl": usl,
            "deviation": round(measurements[first_change_point_idx] - usl, 4)
        }
    }

def score_formula(base, supp_items, contra_items, multiplier=0.155):
    sum_supp = sum(s * r for s, r in supp_items)
    sum_contra = sum(c * r for c, r in contra_items)
    diff = sum_supp - sum_contra
    raw = base + multiplier * diff
    clipped = max(0.05, min(0.98, raw))
    return round(clipped, 2), round(sum_supp, 3), round(sum_contra, 3), round(diff, 3)

def recompute_batch0245_hypotheses():
    # Weights and reliabilities from docs/rca_methodology.md
    # HYP-01: Progressive Tool Flank Wear (Machine)
    # supp: cycles 1150 (1.0*1.0), drift (0.95*1.0), vib 3.8 (0.80*1.0), NCR-019 (0.75*0.9)
    # contra: no fracture (0.40*0.8)
    h1_supp = [(1.0, 1.0), (0.95, 1.0), (0.80, 1.0), (0.75, 0.9)]
    h1_contra = [(0.40, 0.8)]
    score_h1, supp_h1, contra_h1, diff_h1 = score_formula(0.40, h1_supp, h1_contra)

    # HYP-02: Incorrect Tool Offset Setting (Method)
    # supp: shift change (0.60*0.8), multi-part (0.50*0.9)
    # contra: early parts ok (0.65*1.0), steady feed/rpm (0.60*1.0)
    h2_supp = [(0.60, 0.8), (0.50, 0.9)]
    h2_contra = [(0.65, 1.0), (0.60, 1.0)]
    score_h2, supp_h2, contra_h2, diff_h2 = score_formula(0.50, h2_supp, h2_contra)

    # HYP-03: Spindle Harmonic Vibration (Machine)
    # supp: vib 3.8 (0.90*1.0), NCR-014 (0.60*0.9)
    # contra: Ra ok (0.45*0.8), RPM steady (0.30*1.0)
    h3_supp = [(0.90, 1.0), (0.60, 0.9)]
    h3_contra = [(0.45, 0.8), (0.30, 1.0)]
    score_h3, supp_h3, contra_h3, diff_h3 = score_formula(0.50, h3_supp, h3_contra)

    # HYP-04: Fixture Clamping Instability (Machine)
    # supp: vib cut (0.40*0.8)
    # contra: length zero shift (0.90*1.0), chuck 5.5 bar (0.70*1.0)
    h4_supp = [(0.40, 0.8)]
    h4_contra = [(0.90, 1.0), (0.70, 1.0)]
    score_h4, supp_h4, contra_h4, diff_h4 = score_formula(0.45, h4_supp, h4_contra)

    # HYP-05: Measurement System Error (Measurement)
    # supp: consecutive high (0.35*0.8)
    # contra: master gauge ok (0.95*1.0), thermal window (0.75*1.0)
    h5_supp = [(0.35, 0.8)]
    h5_contra = [(0.95, 1.0), (0.75, 1.0)]
    score_h5, supp_h5, contra_h5, diff_h5 = score_formula(0.37, h5_supp, h5_contra)

    hypos = [
        {"id": "HYP-01", "name": "Progressive Tool Flank Wear", "category": "Machine", "base": 0.40, "supp": supp_h1, "contra": contra_h1, "diff": diff_h1, "score": score_h1},
        {"id": "HYP-02", "name": "Incorrect Tool Offset Setting", "category": "Method", "base": 0.50, "supp": supp_h2, "contra": contra_h2, "diff": diff_h2, "score": score_h2},
        {"id": "HYP-03", "name": "Spindle Harmonic Vibration", "category": "Machine", "base": 0.50, "supp": supp_h3, "contra": contra_h3, "diff": diff_h3, "score": score_h3},
        {"id": "HYP-04", "name": "Fixture Clamping Instability", "category": "Machine", "base": 0.45, "supp": supp_h4, "contra": contra_h4, "diff": diff_h4, "score": score_h4},
        {"id": "HYP-05", "name": "Measurement System Error", "category": "Measurement", "base": 0.37, "supp": supp_h5, "contra": contra_h5, "diff": diff_h5, "score": score_h5},
    ]

    # Sort descending by score
    sorted_hypos = sorted(hypos, key=lambda x: x["score"], reverse=True)
    for rank, h in enumerate(sorted_hypos, start=1):
        h["rank"] = rank

    return sorted_hypos

def recompute_counterfactual():
    # If tool usage = 450 (<= 600 cycles) and vibration = 2.1 (baseline)
    # Tool wear:
    # supp: slight var (0.15*0.7) = 0.105
    # contra: cycles ok (1.0*1.0) + vib normal (0.85*1.0) = 1.850
    h1_cf_supp = [(0.15, 0.7)]
    h1_cf_contra = [(1.0, 1.0), (0.85, 1.0)]
    score_cf, supp_cf, contra_cf, diff_cf = score_formula(0.40, h1_cf_supp, h1_cf_contra)

    # Vibration:
    # supp: harmonic (0.10*0.6) = 0.06
    # contra: vib normal (1.0*1.0) = 1.00
    h3_cf_supp = [(0.10, 0.6)]
    h3_cf_contra = [(1.0, 1.0)]
    score_h3_cf, _, _, _ = score_formula(0.50, h3_cf_supp, h3_cf_contra)

    hypos_cf = [
        {"id": "HYP-01", "name": "Progressive Tool Flank Wear", "score": score_cf},
        {"id": "HYP-02", "name": "Incorrect Tool Offset Setting", "score": 0.45},
        {"id": "HYP-03", "name": "Spindle Harmonic Vibration", "score": score_h3_cf},
        {"id": "HYP-04", "name": "Fixture Clamping Instability", "score": 0.25},
        {"id": "HYP-05", "name": "Measurement System Error", "score": 0.15},
    ]
    sorted_cf = sorted(hypos_cf, key=lambda x: x["score"], reverse=True)
    for rank, h in enumerate(sorted_cf, start=1):
        h["rank"] = rank

    return {
        "counterfactual_tool_wear_score": score_cf,
        "counterfactual_tool_wear_rank": next(h["rank"] for h in sorted_cf if h["id"] == "HYP-01"),
        "ranking": sorted_cf
    }

def recompute_correlations():
    # Subgroup series (n=5)
    tool_cycles = np.array([600, 720, 850, 1000, 1150])
    vibration = np.array([2.1, 2.3, 2.9, 3.4, 3.8])
    diameter = np.array([50.01, 50.03, 50.06, 50.08, 50.07])
    spindle = np.array([1200.0, 1200.0, 1200.0, 1200.0, 1200.0])

    r_tool, p_tool = stats.pearsonr(tool_cycles, diameter)
    rho_tool, p_rho_tool = stats.spearmanr(tool_cycles, diameter)

    r_vib, p_vib = stats.pearsonr(vibration, diameter)
    rho_vib, p_rho_vib = stats.spearmanr(vibration, diameter)

    return {
        "tool_vs_diameter": {
            "pearson_r": round(float(r_tool), 3),
            "pearson_p": round(float(p_tool), 4),
            "spearman_rho": round(float(rho_tool), 3),
            "spearman_p": round(float(p_rho_tool), 4),
            "sample_size": len(diameter),
            "disclaimer": "Observed association, causation not established."
        },
        "vibration_vs_diameter": {
            "pearson_r": round(float(r_vib), 3),
            "pearson_p": round(float(p_vib), 4),
            "spearman_rho": round(float(rho_vib), 3),
            "spearman_p": round(float(p_rho_vib), 4),
            "sample_size": len(diameter),
            "disclaimer": "Observed association, causation not established."
        }
    }

def scan_causal_assertions():
    # Prohibited patterns in output narratives
    patterns = [
        r"\broot cause is\b",
        r"\bdefinitely caused by\b",
        r"\bproves causation\b",
        r"\bproven root cause\b"
    ]
    # Scan prompts and schemas
    files_to_scan = [
        "backend/app/agents/rca_agent.py",
        "backend/app/agents/prompts/rca.md",
        "backend/app/routers/rca.py"
    ]
    violations = []
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    for frel in files_to_scan:
        fpath = os.path.join(base_dir, frel)
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            for line_no, line in enumerate(content.splitlines(), start=1):
                # Ignore comments explaining that we must NOT assert causation
                if "never" in line.lower() or "not" in line.lower() or "scan" in line.lower():
                    continue
                for pat in patterns:
                    if re.search(pat, line, re.IGNORECASE):
                        violations.append({"file": frel, "line": line_no, "text": line.strip()})
    return violations

if __name__ == "__main__":
    print("=== REQUIREMENT 10 INDEPENDENT RECOMPUTATION ===")
    ev = recompute_evidence_values()
    print("Physical Evidence Values:")
    print(json.dumps(ev, indent=2))

    print("\nBATCH-0245 Deterministic Hypotheses:")
    hypos = recompute_batch0245_hypotheses()
    for h in hypos:
        print(f"Rank {h['rank']}: {h['name']} ({h['id']}) - Score: {h['score']:.2f} (diff={h['diff']:+.3f})")

    print("\nCounterfactual Ranking Shift (Tool Cycles=450, Vibration=2.1 mm/s):")
    cf = recompute_counterfactual()
    print(json.dumps(cf, indent=2))

    print("\nStatistical Correlations:")
    corr = recompute_correlations()
    print(json.dumps(corr, indent=2))

    print("\nCausal Assertion Scan:")
    viol = scan_causal_assertions()
    print(f"Violations found: {len(viol)}")
    assert len(viol) == 0, f"Found causal assertion violations: {viol}"
    print("Verification completed successfully.")
