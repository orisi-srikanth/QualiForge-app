"""
Independent Statistical Verification Script for Functional Requirement 9 (Process Capability Analysis)
Standards: AIAG SPC Reference Manual (2nd Ed), ISO 21747, IATF 16949:2016 Section 8.5.1
CRITICAL RULE: Calculations in this script use PURE NUMPY ONLY (no imports of app code for formulas).
"""
import os
import sys
sys.path.insert(0, os.path.abspath("."))
import numpy as np

def independent_calc(values, usl=None, lsl=None, subgroup_size=1):
    vals = np.array(values, dtype=float)
    n = len(vals)
    mean = float(np.mean(vals))
    s = float(np.std(vals, ddof=1)) if n > 1 else 0.0

    if subgroup_size > 1 and n >= subgroup_size:
        d2_map = {2: 1.128, 3: 1.693, 4: 2.059, 5: 2.326}
        d2 = d2_map.get(subgroup_size, 1.128)
        num_sg = n // subgroup_size
        reshaped = vals[:num_sg * subgroup_size].reshape(num_sg, subgroup_size)
        ranges = np.ptp(reshaped, axis=1)
        r_bar = float(np.mean(ranges))
        sigma_w = r_bar / d2
    else:
        mr = np.abs(np.diff(vals))
        mr_bar = float(np.mean(mr)) if len(mr) > 0 else s
        sigma_w = mr_bar / 1.128

    cp, cpk, pp, ppk = None, None, None, None
    if usl is not None and lsl is not None:
        tol = usl - lsl
        cp = tol / (6.0 * sigma_w)
        cpu = (usl - mean) / (3.0 * sigma_w)
        cpl = (mean - lsl) / (3.0 * sigma_w)
        cpk = min(cpu, cpl)
        pp = tol / (6.0 * s)
        ppu = (usl - mean) / (3.0 * s)
        ppl = (mean - lsl) / (3.0 * s)
        ppk = min(ppu, ppl)
    elif usl is not None:
        cpu = (usl - mean) / (3.0 * sigma_w)
        cpk = cpu
        ppu = (usl - mean) / (3.0 * s)
        ppk = ppu
    elif lsl is not None:
        cpl = (mean - lsl) / (3.0 * sigma_w)
        cpk = cpl
        ppl = (mean - lsl) / (3.0 * s)
        ppk = ppl

    return {
        "n": n,
        "mean": mean,
        "s_overall": s,
        "sigma_within": sigma_w,
        "cp": cp,
        "cpk": cpk,
        "pp": pp,
        "ppk": ppk
    }

if __name__ == "__main__":
    from backend.app.services.capability import capability_engine

    print("=" * 80)
    print("  REQUIREMENT 9 PROCESS CAPABILITY VERIFICATION — INDEPENDENT RECALCULATION")
    print("=" * 80)

    # 1. BATCH-0245 Anchor Case
    anchor_vals = [50.01, 50.03, 50.06, 50.08, 50.07]
    usl, lsl = 50.05, 49.95
    app_res = capability_engine.calculate_capability(anchor_vals, usl=usl, lsl=lsl)
    indep_res = independent_calc(anchor_vals, usl=usl, lsl=lsl)

    print("\n--- 1. GOLDEN DATASET (BATCH-0245) SIDE-BY-SIDE VERIFICATION ---")
    print(f"{'Metric':<20} | {'Expected / Hand':<18} | {'App Actual':<18} | {'Independent NumPy':<18} | {'Discrepancy':<12}")
    print("-" * 92)
    metrics = [
        ("Mean", 50.05, app_res["mean"], indep_res["mean"]),
        ("Sample SD (s)", 0.029155, app_res["std_dev"], indep_res["s_overall"]),
        ("Within Sigma", 0.017730, app_res["sigma_within"], indep_res["sigma_within"]),
        ("Pp", 0.5717, app_res["pp"], indep_res["pp"]),
        ("Ppk", 0.0, app_res["ppk"], indep_res["ppk"]),
        ("Cp", 0.9400, app_res["cp"], indep_res["cp"]),
        ("Cpk", 0.0, app_res["cpk"], indep_res["cpk"]),
    ]
    for m, exp, app_val, ind_val in metrics:
        delta = abs(app_val - ind_val)
        print(f"{m:<20} | {exp:<18.6f} | {app_val:<18.6f} | {ind_val:<18.6f} | {delta:<12.6f}")

    print("\nWarnings Active on Anchor (n=5):")
    for w in app_res["warnings"]:
        print(f"  • {w}")

    # 2. Centred in-control 100 points
    rng = np.random.RandomState(42)
    vals_100 = [round(float(x), 4) for x in rng.normal(50.00, 0.01, 100)]
    app_100 = capability_engine.calculate_capability(vals_100, usl=usl, lsl=lsl)
    ind_100 = independent_calc(vals_100, usl=usl, lsl=lsl)

    print("\n--- 2. CENTRED IN-CONTROL (n=100) SIDE-BY-SIDE VERIFICATION ---")
    print(f"{'Metric':<20} | {'App Actual':<18} | {'Independent NumPy':<18} | {'Discrepancy':<12}")
    print("-" * 72)
    metrics_100 = [
        ("Mean", app_100["mean"], ind_100["mean"]),
        ("Sample SD (s)", app_100["std_dev"], ind_100["s_overall"]),
        ("Within Sigma", app_100["sigma_within"], ind_100["sigma_within"]),
        ("Pp", app_100["pp"], ind_100["pp"]),
        ("Ppk", app_100["ppk"], ind_100["ppk"]),
        ("Cp", app_100["cp"], ind_100["cp"]),
        ("Cpk", app_100["cpk"], ind_100["cpk"]),
    ]
    for m, app_val, ind_val in metrics_100:
        delta = abs(app_val - ind_val)
        print(f"{m:<20} | {app_val:<18.6f} | {ind_val:<18.6f} | {delta:<12.6f}")

    print("\n--- 3. SUFFICIENCY THRESHOLDS (n=1, 2, 4, 5, 29, 30) ---")
    for test_n in [1, 2, 4, 5, 29, 30]:
        t_vals = [50.00 + 0.002 * i for i in range(test_n)]
        r = capability_engine.calculate_capability(t_vals, usl=usl, lsl=lsl)
        print(f"n={test_n:<2} -> status={r['status']:<18} | Cp={str(r['cp']):<8} | Warnings count={len(r['warnings'])}")

    print("\nVerification complete.")
