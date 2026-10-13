import sqlite3
import json
import math
import numpy as np

conn = sqlite3.connect('backend/data/quality_system.db')
c = conn.cursor()

print("="*60)
print("INDEPENDENT RECOMPUTATION OF REPORT VALUES (BATCH-0245)")
print("="*60)

# 1. Product & Batch metadata
c.execute("SELECT p.part_number, p.name, ic.nominal, ic.tol_plus, ic.tol_minus, ic.lsl, ic.usl FROM products p JOIN inspection_characteristics ic ON p.id = ic.product_id WHERE p.part_number='PS-2026-101'")
prod = c.fetchone()
print(f"Product: {prod[1]} ({prod[0]})")
nominal = float(prod[2])
tol_plus = float(prod[3])
tol_minus = float(prod[4])
lsl = float(prod[5])
usl = float(prod[6])
print(f"Configured Spec Limits: Nominal={nominal:.2f} mm, USL={usl:.2f} mm, LSL={lsl:.2f} mm")


c.execute("SELECT id, batch_number, machine_id, shift, quantity, status FROM batches WHERE batch_number='BATCH-0245'")
batch = c.fetchone()
batch_id = batch[1]
machine = batch[2]
shift = batch[3]
quantity = batch[4]
print(f"Batch: {batch_id}, Machine: {machine}, Shift: {shift}, Total Quantity: {quantity}")

# 2. Inspection Measurements & Rejection Rate
c.execute("SELECT component_id, value FROM measurements WHERE batch_id=? ORDER BY component_id", (batch[0],))
meas = c.fetchall()
values = [float(r[1]) for r in meas]
total_inspected = len(values)
conforming = sum(1 for v in values if lsl <= v <= usl)
nonconforming = sum(1 for v in values if v < lsl or v > usl)
rejection_rate = (nonconforming / total_inspected * 100.0) if total_inspected > 0 else 0.0
acceptance_rate = (conforming / total_inspected * 100.0) if total_inspected > 0 else 0.0

print(f"\nInspection Counts Recomputation:")
print(f"  Total Inspected: {total_inspected}")
print(f"  Conforming: {conforming}")
print(f"  Nonconforming: {nonconforming}")
print(f"  Sum check: conforming + nonconforming = {conforming + nonconforming} == {total_inspected}")
print(f"  Rejection Rate: {rejection_rate:.2f}% (Formula: {nonconforming}/{total_inspected} * 100)")
print(f"  Acceptance Rate: {acceptance_rate:.2f}% (Formula: {conforming}/{total_inspected} * 100)")
print(f"  Percentage Sum check: {rejection_rate + acceptance_rate:.2f}% == 100.00%")

# 3. Dimensional Deviations
print(f"\nIndividual Dimensional Deviations:")
for r in meas:
    val = float(r[1])
    dev_nom = val - nominal
    dev_lim = val - usl if val > usl else (lsl - val if val < lsl else 0.0)
    status = "NONCONFORMING" if val > usl or val < lsl else "CONFORMING"
    print(f"  {r[0]}: {val:.4f} mm | Dev from Nominal: {dev_nom:+.4f} mm | Dev from Limit: {dev_lim:+.4f} mm | {status}")

# 4. SPC Recomputations (Individuals Chart / I-MR)
mean_val = float(np.mean(values))
std_overall = float(np.std(values, ddof=1)) # sample standard deviation s

# Moving range MR between consecutive points
moving_ranges = [abs(values[i] - values[i-1]) for i in range(1, len(values))]
mr_bar = float(np.mean(moving_ranges))
d2 = 1.128 # for subgroup size 2
sigma_within = mr_bar / d2

# Control limits for Individuals (I) chart: Mean +/- 3 * (MR_bar / d2)
ucl = mean_val + 3.0 * sigma_within
lcl = mean_val - 3.0 * sigma_within

# Capability indices
cp = (usl - lsl) / (6.0 * sigma_within) if sigma_within > 0 else None
cpu = (usl - mean_val) / (3.0 * sigma_within) if sigma_within > 0 else None
cpl = (mean_val - lsl) / (3.0 * sigma_within) if sigma_within > 0 else None
cpk = min(cpu, cpl) if cpu is not None and cpl is not None else None

# Performance indices (overall variation)
pp = (usl - lsl) / (6.0 * std_overall) if std_overall > 0 else None
ppu = (usl - mean_val) / (3.0 * std_overall) if std_overall > 0 else None
ppl = (mean_val - lsl) / (3.0 * std_overall) if std_overall > 0 else None
ppk = min(ppu, ppl) if ppu is not None and ppl is not None else None

print(f"\nSPC Statistical Recomputation:")
print(f"  Sample Size n = {total_inspected}")
print(f"  Process Mean (Center Line): {mean_val:.4f} mm")
print(f"  MR-bar: {mr_bar:.4f} mm")
print(f"  Sigma Within (MR_bar / 1.128): {sigma_within:.4f} mm")
print(f"  Sigma Overall (s): {std_overall:.4f} mm")
print(f"  UCL (Mean + 3*sigma_within): {ucl:.4f} mm")
print(f"  LCL (Mean - 3*sigma_within): {lcl:.4f} mm")
print(f"  Cp: {cp:.4f}")
print(f"  Cpk: {cpk:.4f}")
print(f"  Pp: {pp:.4f}")
print(f"  Ppk: {ppk:.4f}")

# 5. Effectiveness Monitoring Recomputation (TC-08)
n1 = 1000
d1 = 82
p1 = d1 / n1
n2 = 1000
d2 = 11
p2 = d2 / n2

# Pooled proportion
p_pool = (d1 + d2) / (n1 + n2)
se_pool = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
z_stat = (p1 - p2) / se_pool
from scipy import stats
p_val = 2 * (1 - stats.norm.cdf(abs(z_stat)))
diff = p1 - p2
se_unpooled = math.sqrt(p1*(1-p1)/n1 + p2*(1-p2)/n2)
ci_low = (diff - 1.96 * se_unpooled) * 100.0
ci_high = (diff + 1.96 * se_unpooled) * 100.0
rel_red = ((p1 - p2) / p1) * 100.0

print(f"\nEffectiveness Monitoring (TC-08) Recomputation:")
print(f"  Pre-intervention Rejection Rate: {p1*100:.1f}% ({d1}/{n1})")
print(f"  Post-intervention Rejection Rate: {p2*100:.1f}% ({d2}/{n2})")
print(f"  Relative Reduction: {rel_red:.1f}%")
print(f"  Z-Statistic: {z_stat:.4f}")
print(f"  P-Value: {p_val:.4e}")
print(f"  95% Confidence Interval of Difference: [{ci_low:.2f}%, {ci_high:.2f}%]")
print(f"  Statistical Significance: {'Significant (p < 0.05)' if p_val < 0.05 else 'Not Significant'}")
