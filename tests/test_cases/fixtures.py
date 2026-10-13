"""
Deterministic Seeded Fixture Builders for TC-01 to TC-08.
Ensures full repeatability, isolation, and negative control verification.
"""
import random
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Tuple
from decimal import Decimal, ROUND_HALF_UP

RANDOM_SEED = 42

def get_tc01_fixture() -> Dict[str, Any]:
    """
    TC-01: All measurements within specification.
    30 diameters between 49.97 and 50.03 plus one at exactly 50.05 and one at exactly 49.95.
    Total = 32 measurements. All conforming.
    """
    rng = random.Random(RANDOM_SEED)
    measurements = []
    
    # 30 diameters strictly within (49.97 to 50.03)
    for i in range(1, 31):
        val = round(49.97 + rng.random() * (50.03 - 49.97), 3)
        measurements.append({"sample_id": f"P{i:03d}", "measured_value": val, "unit": "mm"})
        
    # Boundary values: exactly 50.05 and exactly 49.95
    measurements.append({"sample_id": "P031", "measured_value": 50.05, "unit": "mm"})
    measurements.append({"sample_id": "P032", "measured_value": 49.95, "unit": "mm"})
    
    # Process readings: nominal normal
    telemetry = []
    for i in range(10):
        telemetry.append({
            "timestamp": f"2026-10-12 0{2 + i//6}:{ (i%6)*10 :02d}:00",
            "spindle_speed": 1200.0,
            "feed_rate": 0.20,
            "vibration": 2.10,
            "coolant_temp": 24.0,
            "tool_usage_cycles": 400 + i * 5,
            "motor_current": 14.5
        })
        
    return {
        "batch_id": "TC01-NORMAL",
        "product_id": "PROD-PS-101",
        "part_number": "PS-2026-101",
        "machine": "CNC-04",
        "quantity": 500,
        "nominal_mm": 50.00,
        "tolerance_mm": 0.05,
        "usl": 50.05,
        "lsl": 49.95,
        "measurements": measurements,
        "telemetry": telemetry
    }

def get_tc01_negative_control() -> Dict[str, Any]:
    """Negative control for TC-01: contains 1 out-of-spec measurement (50.08 mm)."""
    data = get_tc01_fixture()
    data["batch_id"] = "TC01-NEG-FAIL"
    data["measurements"][0]["measured_value"] = 50.08
    return data

def get_tc02_fixture() -> Dict[str, Any]:
    """
    TC-02: Measurement exceeds USL.
    Sample P001..P005 = 50.01, 50.03, 50.06, 50.08, 50.07.
    USL = 50.05, LSL = 49.95.
    P003 (+0.01), P004 (+0.03), P005 (+0.02) nonconforming.
    """
    raw_vals = [50.01, 50.03, 50.06, 50.08, 50.07]
    measurements = [
        {"sample_id": f"P{i+1:03d}", "measured_value": v, "unit": "mm"}
        for i, v in enumerate(raw_vals)
    ]
    return {
        "batch_id": "TC02-EXCEED-USL",
        "part_number": "PS-2026-101",
        "nominal_mm": 50.00,
        "tolerance_mm": 0.05,
        "usl": 50.05,
        "lsl": 49.95,
        "measurements": measurements,
        "raw_values": raw_vals
    }

def recompute_tc02_decimal(raw_vals: List[float], usl: float, lsl: float) -> Dict[str, Any]:
    """Independent exact Decimal recomputation for TC-02."""
    usl_d = Decimal(str(usl))
    lsl_d = Decimal(str(lsl))
    
    nonconforming = []
    accepted = []
    
    for i, v in enumerate(raw_vals):
        sid = f"P{i+1:03d}"
        val_d = Decimal(str(v))
        if val_d > usl_d:
            dev_d = val_d - usl_d
            nonconforming.append({"sample_id": sid, "value": float(val_d), "deviation": float(dev_d), "status": "FAIL_HIGH"})
        elif val_d < lsl_d:
            dev_d = lsl_d - val_d
            nonconforming.append({"sample_id": sid, "value": float(val_d), "deviation": float(dev_d), "status": "FAIL_LOW"})
        else:
            accepted.append(sid)
            
    total = len(raw_vals)
    rej_rate = (Decimal(len(nonconforming)) / Decimal(total) * Decimal("100.0")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    
    return {
        "total": total,
        "accepted_count": len(accepted),
        "nonconforming_count": len(nonconforming),
        "rejection_rate_percent": float(rej_rate),
        "nonconforming_items": nonconforming
    }

def get_tc03_fixture() -> Dict[str, Any]:
    """
    TC-03: Defect image supplied.
    One held-out defect image (never used in training) and one good image.
    Returns file paths, hashes, and ground truth metadata.
    """
    base_samples = Path("backend/app/static/uploads/samples")
    defect_path = base_samples / "IMG-001.png"
    good_path = base_samples / "shaft_normal.png"
    
    if not defect_path.exists():
        defect_path = base_samples / "metal_nut_scratch.png"
    if not good_path.exists():
        good_path = base_samples / "metal_nut_normal.png"
        
    def hash_file(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()
        
    return {
        "batch_id": "TC03-VISION-DEFECT",
        "defect_image_path": str(defect_path.resolve()),
        "defect_image_hash": hash_file(defect_path),
        "good_image_path": str(good_path.resolve()),
        "good_image_hash": hash_file(good_path),
        "expected_defect_type": "surface_scratch",
        "category": "precision_shaft"
    }

def get_tc04_fixture() -> Dict[str, Any]:
    """
    TC-04: Machine vibration suddenly increases.
    CNC-04 readings with vibration around 2.1 mm/s stepping to around 3.8 mm/s at index 15.
    Spindle speed (1200) and feed rate (0.20) unchanged.
    """
    rng = random.Random(RANDOM_SEED)
    readings = []
    step_index = 15
    total_samples = 25
    
    for i in range(total_samples):
        ts = f"2026-10-12 0{2 + i//6}:{ (i%6)*10 :02d}:00"
        speed = 1200.0 + rng.uniform(-2.0, 2.0)
        feed = 0.20 + rng.uniform(-0.001, 0.001)
        temp = 24.0 + rng.uniform(-0.2, 0.2)
        cycles = 600 + i * 10
        current = 14.5 + rng.uniform(-0.1, 0.1)
        
        if i < step_index:
            vib = round(2.10 + rng.uniform(-0.05, 0.05), 2)
        else:
            # Sudden step change
            vib = round(3.80 + rng.uniform(-0.05, 0.05), 2)
            
        readings.append({
            "timestamp": ts,
            "machine": "CNC-04",
            "vibration": vib,
            "machine_vibration_mms": vib,
            "spindle_speed": round(speed, 1),
            "spindle_speed_rpm": round(speed, 1),
            "feed_rate": round(feed, 3),
            "feed_rate_mmrev": round(feed, 3),
            "coolant_temp": round(temp, 1),
            "coolant_temperature_c": round(temp, 1),
            "tool_usage_cycles": cycles,
            "motor_current": round(current, 1)
        })
        
    return {
        "batch_id": "TC04-VIB-STEP",
        "machine": "CNC-04",
        "step_index": step_index,
        "readings": readings,
        "baseline_mean": 2.10,
        "baseline_trip_limit": 3.50,
        "step_value": 3.80
    }

def get_tc04_negative_control() -> Dict[str, Any]:
    """Negative control for TC-04: flat vibration series at 2.10 mm/s without step change."""
    data = get_tc04_fixture()
    data["batch_id"] = "TC04-NEG-FLAT"
    rng = random.Random(RANDOM_SEED)
    for r in data["readings"]:
        v = round(2.10 + rng.uniform(-0.04, 0.04), 2)
        r["vibration"] = v
        r["machine_vibration_mms"] = v
    return data

def get_tc05_fixture() -> Dict[str, Any]:
    """
    TC-05: Measurements gradually move toward USL.
    60 diameters rising by about 0.001 to 0.002 mm per part, starting from 50.000 mm,
    with tool usage rising.
    USL = 50.05 mm.
    First point exceeding USL occurs around part 52 (> 50.050 mm).
    Drift alarm must trigger BEFORE the first out-of-spec part.
    """
    values = []
    out_of_spec_idx = None
    
    for i in range(60):
        # Gradual upward drift of ~0.001 mm per piece with minor noise
        val = round(50.000 + (i * 0.0010) + (0.0002 if i % 2 == 0 else -0.0002), 4)
        values.append(val)
        if val > 50.05 and out_of_spec_idx is None:
            out_of_spec_idx = i
            
    return {
        "batch_id": "TC05-DRIFT-TREND",
        "nominal_mm": 50.00,
        "usl": 50.05,
        "lsl": 49.95,
        "values": values,
        "expected_first_oos_index": out_of_spec_idx
    }

def get_tc06_fixture() -> Dict[str, Any]:
    """
    TC-06: Similar previous NCR exists.
    Query: 'Oversized shaft diameter' for PS-2026-101.
    Expected: NCR-019 retrieved in top 3 with similarity score.
    """
    return {
        "query": "Oversized shaft diameter",
        "part_number": "PS-2026-101",
        "expected_ncr": "NCR-019",
        "expected_confirmed_cause": "Progressive Cutting Tool Flank Wear on CNC-04"
    }

def get_tc02_negative_control() -> Dict[str, Any]:
    """Negative control for TC-02: 5 fully conforming parts within specification."""
    raw_vals = [50.01, 50.02, 50.03, 50.00, 49.98]
    return {
        "batch_id": "TC02-NEG-CONFORMING",
        "part_number": "PS-2026-101",
        "nominal_mm": 50.00,
        "tolerance_mm": 0.05,
        "usl": 50.05,
        "lsl": 49.95,
        "measurements": [
            {"sample_id": f"P{i+1:03d}", "measured_value": v, "unit": "mm"}
            for i, v in enumerate(raw_vals)
        ],
        "raw_values": raw_vals
    }

def get_tc03_negative_control() -> Dict[str, Any]:
    """Negative control for TC-03: confirmed good shaft image."""
    base_samples = Path("backend/app/static/uploads/samples")
    good_path = base_samples / "shaft_normal.png"
    if not good_path.exists():
        good_path = base_samples / "metal_nut_normal.png"
    return {
        "batch_id": "TC03-NEG-GOOD",
        "image_path": str(good_path.resolve()),
        "expected_defect_detected": False
    }

def get_tc05_negative_control() -> Dict[str, Any]:
    """Negative control for TC-05: stable stationary process with no drift."""
    rng = random.Random(RANDOM_SEED)
    values = [round(50.000 + rng.gauss(0, 0.006), 4) for _ in range(60)]
    return {
        "batch_id": "TC05-NEG-STABLE",
        "nominal_mm": 50.00,
        "usl": 50.05,
        "lsl": 49.95,
        "values": values
    }

def get_tc06_negative_control() -> Dict[str, Any]:
    """Negative control for TC-06: query completely unrelated to shaft machining."""
    return {
        "query": "Cardboard outer shipping carton barcode label misalignment",
        "part_number": "PS-2026-101",
        "unexpected_ncr": "NCR-019"
    }

def get_tc07_fixture() -> Dict[str, Any]:
    """
    TC-07: Multiple potential causes exist.
    Incident with tool usage 1,150 cycles (nominal 600), vibration 3.8 mm/s (nominal 2.1),
    spindle speed 1200 unchanged, feed 0.20 unchanged, max diameter 50.08 mm.
    """
    return {
        "incident_id": "INC-TC07",
        "batch_id": "BATCH-0245",
        "defect_type": "Oversized shaft diameter",
        "max_measured_val": 50.08,
        "usl": 50.05,
        "vibration_val": 3.8,
        "tool_cycles": 1150
    }

def get_tc07_negative_control() -> Dict[str, Any]:
    """Negative control for TC-07: process data with strictly normal tool cycles and vibration."""
    return {
        "incident_id": "INC-TC07-NEG",
        "batch_id": "BATCH-0245",
        "defect_type": "Oversized shaft diameter",
        "max_measured_val": 50.08,
        "usl": 50.05,
        "vibration_val": 2.10,
        "tool_cycles": 400
    }

def get_tc08_fixture() -> Dict[str, Any]:
    """
    TC-08: Corrective action completed.
    Pre-intervention window: 82 nonconforming out of 1,000 (8.2%).
    Post-intervention window: 11 nonconforming out of 1,000 (1.1%).
    """
    return {
        "action_code": "CAPA-2026-001",
        "sample_before": 1000,
        "defects_before": 82,
        "sample_after": 1000,
        "defects_after": 11
    }

def get_tc08_negative_control() -> Dict[str, Any]:
    """Negative control for TC-08: small sample size (n=15) where statistical significance cannot be claimed."""
    return {
        "action_code": "CAPA-2026-001",
        "sample_before": 15,
        "defects_before": 1,
        "sample_after": 15,
        "defects_after": 0
    }

def recompute_two_proportion_z(n1: int, x1: int, n2: int, x2: int, conf: float = 0.95) -> Dict[str, Any]:
    """Independent exact mathematical recomputation of two-proportion z-test."""
    import math
    from scipy import stats
    
    p1 = x1 / n1
    p2 = x2 / n2
    p_pool = (x1 + x2) / (n1 + n2)
    se_pool = math.sqrt(p_pool * (1.0 - p_pool) * (1.0 / n1 + 1.0 / n2))
    z = (p1 - p2) / se_pool
    p_val = 2.0 * (1.0 - stats.norm.cdf(abs(z)))
    
    # Standard error of difference for confidence interval
    se_diff = math.sqrt(p1 * (1.0 - p1) / n1 + p2 * (1.0 - p2) / n2)
    z_crit = 1.95996
    ci_low = round((p1 - p2 - z_crit * se_diff) * 100.0, 2)
    ci_high = round((p1 - p2 + z_crit * se_diff) * 100.0, 2)
    
    return {
        "p1_percent": round(p1 * 100.0, 2),
        "p2_percent": round(p2 * 100.0, 2),
        "difference_percent": round((p1 - p2) * 100.0, 2),
        "z_statistic": round(z, 2),
        "p_value": float(p_val),
        "ci_95": [ci_low, ci_high]
    }

def recompute_rca_scores(tool_cycles: int, vibration_val: float, max_val: float, usl: float = 50.05) -> Dict[str, float]:
    """
    Independent exact mathematical recomputation of the 5 RCA hypothesis evidence scores.
    Formula: clip(base + 0.155 * (sum_supp - sum_contra), 0.05, 0.98)
    """
    scores = {}
    
    # HYP-01: Progressive Cutting Tool Flank Wear
    if tool_cycles > 800:
        supp_1 = 1.0 * 1.0 + 0.95 * 1.0 + (0.80 if vibration_val > 3.0 else 0.20) * 1.0 + 0.75 * 0.9
        contra_1 = 0.40 * 0.8
        diff_1 = supp_1 - contra_1
        score_1 = round(max(0.05, min(0.98, 0.40 + 0.155 * diff_1)), 2)
    else:
        supp_1 = 0.15 * 0.7
        contra_1 = 1.0 * 1.0 + 0.85 * 1.0
        diff_1 = supp_1 - contra_1
        score_1 = round(max(0.05, min(0.98, 0.40 + 0.155 * diff_1)), 2)
    scores["HYP-01"] = score_1
    
    # HYP-02: Incorrect Tool Wear Offset Calibration
    diff_2 = (0.60 * 0.8 + 0.50 * 0.9) - (0.65 * 1.0 + 0.60 * 1.0)
    scores["HYP-02"] = round(max(0.05, min(0.98, 0.50 + 0.155 * diff_2)), 2)
    
    # HYP-03: Spindle Harmonic Vibration and Bearing Play
    if vibration_val >= 3.5:
        diff_3 = (0.90 * 1.0 + 0.60 * 0.9) - (0.45 * 0.8 + 0.30 * 1.0)
    else:
        diff_3 = (0.10 * 0.6) - (1.0 * 1.0)
    scores["HYP-03"] = round(max(0.05, min(0.98, 0.50 + 0.155 * diff_3)), 2)
    
    # HYP-04: Hydraulic Fixture Clamping Instability
    diff_4 = (0.40 * 0.8) - (0.90 * 1.0 + 0.70 * 1.0)
    scores["HYP-04"] = round(max(0.05, min(0.98, 0.45 + 0.155 * diff_4)), 2)
    
    # HYP-05: Measurement System Digital Micrometer Gauge Error
    diff_5 = (0.35 * 0.8) - (0.95 * 1.0 + 0.75 * 1.0)
    scores["HYP-05"] = round(max(0.05, min(0.98, 0.37 + 0.155 * diff_5)), 2)
    
    return scores

