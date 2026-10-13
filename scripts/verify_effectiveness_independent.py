"""
Independent verification script for Functional Requirement 15 (Effectiveness Monitoring).
Directly queries SQLite database with sqlite3 (zero imports from app codebase)
and performs statistical verification using scipy.stats.
"""
import sqlite3
import math
from scipy import stats

def run_independent_verification():
    db_path = "backend/data/quality_system.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Query baseline (before) batch
    cursor.execute("""
        SELECT b.id, b.batch_number, b.machine_id, b.product_id, b.scenario_label,
               COUNT(m.id) as inspected,
               SUM(CASE WHEN m.status = 'nonconforming' THEN 1 ELSE 0 END) as nonconforming
        FROM batches b
        JOIN measurements m ON b.id = m.batch_id
        WHERE b.scenario_label = 'PRE_CORRECTIVE_BASELINE'
        GROUP BY b.id
    """)
    pre_row = cursor.fetchone()

    # 2. Query verified (after) batch
    cursor.execute("""
        SELECT b.id, b.batch_number, b.machine_id, b.product_id, b.scenario_label,
               COUNT(m.id) as inspected,
               SUM(CASE WHEN m.status = 'nonconforming' THEN 1 ELSE 0 END) as nonconforming
        FROM batches b
        JOIN measurements m ON b.id = m.batch_id
        WHERE b.scenario_label = 'POST_CORRECTIVE_VERIFIED'
        GROUP BY b.id
    """)
    post_row = cursor.fetchone()

    print("=== RAW SQL QUERY RESULTS ===")
    print(f"Pre-intervention:  batch={pre_row[1]}, machine={pre_row[2]}, product={pre_row[3]}, inspected={pre_row[5]}, nonconforming={pre_row[6]}")
    print(f"Post-intervention: batch={post_row[1]}, machine={post_row[2]}, product={post_row[3]}, inspected={post_row[5]}, nonconforming={post_row[6]}")

    n1 = pre_row[5]
    d1 = pre_row[6]
    n2 = post_row[5]
    d2 = post_row[6]

    rate1 = (d1 / n1) * 100.0
    rate2 = (d2 / n2) * 100.0
    p1 = d1 / n1
    p2 = d2 / n2

    print(f"\nPre-intervention rejection rate:  {d1} / {n1} * 100 = {rate1:.2f}%")
    print(f"Post-intervention rejection rate: {d2} / {n2} * 100 = {rate2:.2f}%")

    # 3. Two-proportion z-test (pooled p-bar)
    p_pool = (d1 + d2) / (n1 + n2)
    se_pool = math.sqrt(p_pool * (1.0 - p_pool) * (1.0 / n1 + 1.0 / n2))
    z_stat = (p1 - p2) / se_pool
    p_value = 2.0 * (1.0 - stats.norm.cdf(abs(z_stat)))

    # 95% Confidence Interval for difference
    se_diff = math.sqrt((p1 * (1.0 - p1) / n1) + (p2 * (1.0 - p2) / n2))
    z_crit = stats.norm.ppf(0.975)
    diff = p1 - p2
    ci_lower = (diff - z_crit * se_diff) * 100.0
    ci_upper = (diff + z_crit * se_diff) * 100.0

    print("\n=== INDEPENDENT STATISTICAL CALCULATIONS ===")
    print(f"Pooled p-bar: {p_pool:.4f}")
    print(f"Standard Error (pooled): {se_pool:.6f}")
    print(f"Z-statistic: {z_stat:.3f}")
    print(f"P-value: {p_value:.4e}")
    print(f"95% Confidence Interval for Difference: [{ci_lower:.2f}%, {ci_upper:.2f}%]")

    # Check CAPAAction and EffectivenessCheck in DB
    cursor.execute("""
        SELECT a.action_code, a.type, a.status, a.completion_date, a.effectiveness_result,
               e.rejection_rate_before, e.rejection_rate_after, e.test_used, e.p_value, e.conclusion_label
        FROM capa_actions a
        LEFT JOIN effectiveness_checks e ON a.id = e.capa_id
        WHERE a.action_code = 'CAPA-2026-001'
    """)
    capa_row = cursor.fetchone()
    print("\n=== CAPA & EFFECTIVENESS_CHECKS DB RECORD ===")
    if capa_row:
        print(f"CAPA Action: {capa_row[0]}, status={capa_row[2]}, completion_date={capa_row[3]}")
        print(f"CAPA effectiveness_result field: {capa_row[4]}")
        print(f"EffectivenessCheck record: before={capa_row[5]}%, after={capa_row[6]}%, test={capa_row[7]}, p={capa_row[8]}")
        print(f"Conclusion: {capa_row[9]}")
    else:
        print("CAPA-2026-001 not found.")

    conn.close()

if __name__ == "__main__":
    run_independent_verification()
