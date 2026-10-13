"""
Independent Raw SQL / Pandas Pareto Analysis Verifier
Strictly independent verification: does NOT import application code or services.
Connects directly to backend/data/quality_system.db via raw sqlite3.
Compares independent calculation side-by-side with live FastAPI endpoint.
"""
import sqlite3
import json
import requests
from typing import Dict, Any, List

DB_PATH = "backend/data/quality_system.db"
API_URL = "http://127.0.0.1:8000/api/pareto"

def compute_independent_pareto(
    dimension: str,
    start_date: str = None,
    end_date: str = None
) -> Dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Build date clause for quality_incidents created_at
    date_clauses = []
    params = []
    if start_date:
        if len(start_date) == 10:
            s_val = f"{start_date} 00:00:00"
        else:
            s_val = start_date.replace("T", " ").replace("Z", "")
        date_clauses.append("qi.created_at >= ?")
        params.append(s_val)

    if end_date:
        if len(end_date) == 10:
            e_val = f"{end_date} 23:59:59.999999"
        else:
            e_val = end_date.replace("T", " ").replace("Z", "")
        date_clauses.append("qi.created_at <= ?")
        params.append(e_val)

    where_str = f"WHERE {' AND '.join(date_clauses)}" if date_clauses else ""

    if dimension == "defect_type":
        sql = f"""
            SELECT COALESCE(qi.defect_type, 'Unspecified') as cat, COUNT(*) as cnt
            FROM quality_incidents qi
            {where_str}
            GROUP BY cat
        """
    elif dimension == "machine":
        sql = f"""
            SELECT COALESCE(m.code, 'Unspecified') as cat, COUNT(*) as cnt
            FROM quality_incidents qi
            LEFT JOIN batches b ON qi.batch_id = b.id
            LEFT JOIN machines m ON b.machine_id = m.id
            {where_str}
            GROUP BY cat
        """
    elif dimension == "product_family":
        sql = f"""
            SELECT COALESCE(p.family, 'Unspecified') as cat, COUNT(*) as cnt
            FROM quality_incidents qi
            LEFT JOIN batches b ON qi.batch_id = b.id
            LEFT JOIN products p ON b.product_id = p.id
            {where_str}
            GROUP BY cat
        """
    elif dimension == "rejection_reason":
        sql = f"""
            SELECT COALESCE(qi.rejection_reason, 'Unspecified') as cat, COUNT(*) as cnt
            FROM quality_incidents qi
            {where_str}
            GROUP BY cat
        """
    elif dimension == "root_cause":
        # Strictly confirmed root causes only
        rc_where = ["(rh.label = 'CONFIRMED_ROOT_CAUSE' OR rh.status = 'confirmed')"]
        if date_clauses:
            rc_where.extend(date_clauses)
        where_rc = f"WHERE {' AND '.join(rc_where)}"

        sql = f"""
            SELECT COALESCE(rh.title, 'Unspecified') as cat, COUNT(*) as cnt
            FROM rca_hypotheses rh
            JOIN quality_incidents qi ON rh.incident_id = qi.id
            {where_rc}
            GROUP BY cat
        """
    else:
        raise ValueError(f"Unknown dimension: {dimension}")

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    total = sum(r[1] for r in rows)
    if total == 0:
        return {
            "dimension": dimension,
            "total": 0,
            "items": [],
            "vital_few": []
        }

    # Deterministic sorting: count descending, then category name ascending
    sorted_rows = sorted(rows, key=lambda x: (-x[1], str(x[0])))

    items = []
    cum_sum = 0
    vital_few = []
    vital_reached = False

    for idx, (cat, cnt) in enumerate(sorted_rows):
        cum_sum += cnt
        pct = round((cnt / total) * 100.0, 1)
        if idx == len(sorted_rows) - 1:
            cum_pct = 100.0
        else:
            cum_pct = round((cum_sum / total) * 100.0, 1)

        if not vital_reached:
            vital_few.append(cat)
            is_vital = True
            if cum_pct >= 80.0:
                vital_reached = True
        else:
            is_vital = False

        items.append({
            "category": cat,
            "count": cnt,
            "percentage": pct,
            "cumulative_percentage": cum_pct,
            "is_vital_few": is_vital
        })

    return {
        "dimension": dimension,
        "total": total,
        "items": items,
        "vital_few": vital_few
    }

def run_side_by_side_verification():
    dimensions = ["defect_type", "machine", "product_family", "root_cause", "rejection_reason"]
    print("=" * 80)
    print("  INDEPENDENT RAW SQL VS API PARETO VERIFICATION")
    print("=" * 80)

    all_matched = True

    for dim in dimensions:
        print(f"\n>>> DIMENSION: {dim.upper()} <<<")
        # 1. Independent calculation
        indep = compute_independent_pareto(dim)
        # 2. App API
        resp = requests.get(f"{API_URL}?dimension={dim}")
        assert resp.status_code == 200, f"API failed with {resp.status_code}"
        app_data = resp.json()

        print(f"Independent Total: {indep['total']} | App Total: {app_data['total']}")
        assert indep['total'] == app_data['total'], f"Total mismatch on {dim}"

        print(f"{'Category':<36} | {'Indep Cnt':<9} | {'App Cnt':<7} | {'Indep %':<7} | {'App %':<5} | {'Indep Cum%':<10} | {'App Cum%':<8} | {'Vital Few Match'}")
        print("-" * 115)

        app_items = app_data.get("items", [])
        assert len(indep["items"]) == len(app_items), f"Items length mismatch on {dim}"

        for i_it, a_it in zip(indep["items"], app_items):
            cat_match = i_it["category"] == a_it["category"]
            cnt_match = i_it["count"] == a_it["count"]
            pct_match = abs(i_it["percentage"] - a_it["percentage"]) < 0.01
            cum_match = abs(i_it["cumulative_percentage"] - a_it["cumulative_percentage"]) < 0.01
            vit_match = i_it["is_vital_few"] == a_it["is_vital_few"]

            row_ok = cat_match and cnt_match and pct_match and cum_match and vit_match
            if not row_ok:
                all_matched = False

            vital_str = "MATCH (Vital)" if i_it["is_vital_few"] else "MATCH (Non-vital)"
            if not vit_match:
                vital_str = "MISMATCH"

            print(f"{i_it['category'][:35]:<36} | {i_it['count']:<9} | {a_it['count']:<7} | {i_it['percentage']:<7.1f} | {a_it['percentage']:<5.1f} | {i_it['cumulative_percentage']:<10.1f} | {a_it['cumulative_percentage']:<8.1f} | {vital_str}")

        print(f"Vital Few List Match: {indep['vital_few'] == app_data['vital_few_categories']}")
        assert indep['vital_few'] == app_data['vital_few_categories']

    # Date range independent verification
    print("\n" + "=" * 80)
    print("  DATE RANGE FILTER INDEPENDENT VERIFICATION")
    print("=" * 80)
    test_ranges = [
        ("Exclude Early Incidents (2026-08-01 to 2026-10-31)", "2026-08-01", "2026-10-31"),
        ("Single Day (2026-08-22)", "2026-08-22", "2026-08-22"),
        ("Zero Records Range (2025-01-01 to 2025-01-31)", "2025-01-01", "2025-01-31"),
    ]

    for label, s_date, e_date in test_ranges:
        print(f"\nTesting Range: {label} [{s_date} to {e_date}]")
        indep_range = compute_independent_pareto("defect_type", s_date, e_date)
        app_range = requests.get(f"{API_URL}?dimension=defect_type&start_date={s_date}&end_date={e_date}").json()

        print(f"Indep Total: {indep_range['total']} | App Total: {app_range['total']}")
        assert indep_range['total'] == app_range['total'], f"Count mismatch on range {label}"
        assert len(indep_range['items']) == len(app_range['items'])
        for i_it, a_it in zip(indep_range['items'], app_range['items']):
            print(f"  {i_it['category']}: Indep={i_it['count']} ({i_it['percentage']}%), App={a_it['count']} ({a_it['percentage']}%)")

    print("\n" + "=" * 80)
    print(f"ALL CHECKS PASSED: {all_matched}")
    print("=" * 80)

if __name__ == "__main__":
    run_side_by_side_verification()
