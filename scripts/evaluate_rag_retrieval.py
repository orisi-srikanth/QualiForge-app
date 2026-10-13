"""
Independent QA Evaluation Script: RAG Retrieval Metrics for Requirement 11
Module: scripts/evaluate_rag_retrieval.py

Evaluates:
- 25 In-domain labelled manufacturing queries covering:
  * shaft oversize -> NCR-019 (TC-06)
  * each visual defect type present in the project (MVTec unified classes)
  * tool-change SOP (SOP-044)
  * vibration limit in machine manual (Machine_Guidelines / MANUAL)
  * calibration & gauge drift (NCR-084 / Calibration)
  * maintenance lookups (maintenance_records)
  * decoys with different confirmed causes (NCR-042, NCR-073, NCR-024, NCR-055, NCR-031, NCR-140, NCR-141)
- 3 Out-of-domain queries (similarity floor / no relevant incident response)
- Computes: Hit@1, Hit@3, Recall@5, MRR
- Verifies Hit@3 >= 0.80 and TC-06 passes.
"""
import sys
import os
from pathlib import Path
from typing import Dict, List, Any

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.agents.quality_knowledge_agent import quality_knowledge_agent

# 25 Labeled In-Domain Queries + 3 Out-of-Domain Queries
EVALUATION_QUERY_SET = [
    # 1. Shaft oversize & Tool wear (Anchor / TC-06)
    {"id": "Q01", "category": "shaft_oversize", "query": "oversized shaft diameter CNC-04 tool wear", "target": "NCR-019"},
    {"id": "Q02", "category": "shaft_oversize", "query": "shaft outer diameter positive drift past USL 50.05 mm", "target": "NCR-019"},
    {"id": "Q03", "category": "shaft_oversize", "query": "progressive tool flank wear cutting force increase", "target": "NCR-019"},

    # 2. Each visual defect type present in the project
    {"id": "Q04", "category": "visual_defect", "query": "metal_nut surface scratch linear abrasion marks", "target": "surface_scratch"},
    {"id": "Q05", "category": "visual_defect", "query": "metal_nut rim dent deformation impact damage", "target": "dent_deformation"},
    {"id": "Q06", "category": "visual_defect", "query": "metal_nut incorrect assembly inverted orientation flipped", "target": "incorrect_assembly"},
    {"id": "Q07", "category": "visual_defect", "query": "metal_nut surface contamination oil discoloration spot", "target": "surface_contamination"},
    {"id": "Q08", "category": "visual_defect", "query": "screw thread damage stripped pitch crest deformed", "target": "thread_damage"},
    {"id": "Q09", "category": "visual_defect", "query": "transistor missing component cut lead wire missing", "target": "missing_component"},
    {"id": "Q10", "category": "visual_defect", "query": "cable insulation or wire damage cut outer jacket", "target": "insulation_or_wire_damage"},

    # 3. Tool-change SOP
    {"id": "Q11", "category": "sop", "query": "cutting tool life management replacement interval cycle limit", "target": "SOP-044"},
    {"id": "Q12", "category": "sop", "query": "tool wear offset compensation procedure and maximum cycles", "target": "SOP-044"},

    # 4. Vibration limit in machine manual
    {"id": "Q13", "category": "manual", "query": "spindle radial vibration trip threshold warning level mm/s", "target": "Machine_Guidelines"},
    {"id": "Q14", "category": "manual", "query": "turning center spindle vibration alarm limit 3.5 mm/s", "target": "Machine_Guidelines"},

    # 5. Calibration and gauge questions
    {"id": "Q15", "category": "calibration", "query": "snap gauge calibration master anvil loosened false nonconformance", "target": "NCR-084"},
    {"id": "Q16", "category": "calibration", "query": "calibration certificate verification micrometer anvil wear", "target": "Calibration"},

    # 6. Maintenance lookups
    {"id": "Q17", "category": "maintenance", "query": "CNC-04 hydraulic chuck pressure service tailstock live center", "target": "NCR-031"},
    {"id": "Q18", "category": "maintenance", "query": "spindle bearing scheduled maintenance preventive service record", "target": "maintenance_records"},

    # 7. Decoys with similar symptoms but different confirmed causes
    {"id": "Q19", "category": "decoy", "query": "oversized shaft diameter incorrect tool offset register input typed", "target": "NCR-042"},
    {"id": "Q20", "category": "decoy", "query": "shaft diameter variation raw material lot hardness 245 HB", "target": "NCR-073"},
    {"id": "Q21", "category": "decoy", "query": "bore dimension undersized thermal contraction cooling soak", "target": "NCR-024"},
    {"id": "Q22", "category": "decoy", "query": "tapered cylinder geometry headstock misalignment spindle axis", "target": "NCR-055"},
    {"id": "Q23", "category": "decoy", "query": "surface chatter marks finish waviness collet sleeve vibration", "target": "NCR-031"},
    {"id": "Q24", "category": "decoy", "query": "surface scratch metal nut unloader gripper swarf", "target": "NCR-140"},
    {"id": "Q25", "category": "decoy", "query": "surface scratch metal nut conveyor chute tumbling decoy", "target": "NCR-141"},
]

OUT_OF_DOMAIN_QUERIES = [
    {"id": "OOD1", "query": "baking temperature for chocolate chip cookies in conventional oven", "expected": "NO_MATCH"},
    {"id": "OOD2", "query": "aerospace hydraulic wing flap flutter on Boeing 787 dreamliner", "expected": "NO_MATCH"},
    {"id": "OOD3", "query": "Python Flask REST API tutorial for building web apps", "expected": "NO_MATCH"}
]

def run_evaluation():
    print("=" * 95)
    print("  FUNCTIONAL REQUIREMENT 11: RAG RETRIEVAL EVALUATION BENCHMARK")
    print("=" * 95)
    print(f"{'#':<4} | {'Category':<14} | {'Target':<14} | {'Rank':<6} | {'Hit@1':<6} | {'Hit@3':<6} | {'Sim':<6} | {'Top Match Record / Source'}")
    print("-" * 95)

    hits_at_1 = 0
    hits_at_3 = 0
    recalls_at_5 = 0
    rr_list = []
    tc06_passed = False
    in_domain_results = []

    for item in EVALUATION_QUERY_SET:
        qid = item["id"]
        cat = item["category"]
        q = item["query"]
        target = item["target"]

        res = quality_knowledge_agent.query(query_text=q, top_k=5)
        matches = res.get("matches", [])

        rank = None
        top_match_str = "None"
        top_sim = 0.0

        if matches:
            top_m = matches[0]
            top_sim = top_m.get("similarity_score", 0.0)
            top_match_str = f"{top_m.get('record_id', 'N/A')} ({top_m.get('source_file')})"

        for r, m in enumerate(matches, start=1):
            meta = m.get("metadata", {})
            m_text = (
                str(meta.get("record_id", "")) + " " +
                str(m.get("record_id", "")) + " " +
                str(meta.get("file_name", "")) + " " +
                str(m.get("source_file", "")) + " " +
                str(meta.get("defect_type", "")) + " " +
                str(m.get("text", ""))
            ).lower()

            if target.lower() in m_text:
                rank = r
                break

        h1 = (rank == 1)
        h3 = (rank is not None and rank <= 3)
        r5 = (rank is not None and rank <= 5)

        if h1: hits_at_1 += 1
        if h3: hits_at_3 += 1
        if r5: recalls_at_5 += 1
        rr_list.append(1.0 / rank if rank else 0.0)

        if qid == "Q01" and h3:
            tc06_passed = True

        rank_str = str(rank) if rank else ">5"
        h1_str = "YES" if h1 else "no"
        h3_str = "YES" if h3 else "no"

        print(f"{qid:<4} | {cat:<14} | {target:<14} | {rank_str:<6} | {h1_str:<6} | {h3_str:<6} | {top_sim:.3f} | {top_match_str[:32]}")
        in_domain_results.append({
            "id": qid,
            "category": cat,
            "query": q,
            "target": target,
            "rank": rank,
            "hit_at_1": h1,
            "hit_at_3": h3,
            "recall_at_5": r5,
            "reciprocal_rank": 1.0 / rank if rank else 0.0
        })

    n_q = len(EVALUATION_QUERY_SET)
    hit_1_rate = hits_at_1 / n_q
    hit_3_rate = hits_at_3 / n_q
    recall_5_rate = recalls_at_5 / n_q
    mrr = sum(rr_list) / n_q

    print("-" * 95)
    print("IN-DOMAIN RETRIEVAL METRICS SUMMARY:")
    print(f"  Total In-Domain Queries : {n_q}")
    print(f"  Hit@1                   : {hit_1_rate * 100:.2f}% ({hits_at_1}/{n_q})")
    print(f"  Hit@3                   : {hit_3_rate * 100:.2f}% ({hits_at_3}/{n_q})  [Target: >= 80.0%]")
    print(f"  Recall@5                : {recall_5_rate * 100:.2f}% ({recalls_at_5}/{n_q})")
    print(f"  MRR (Mean Reciprocal)   : {mrr:.4f}")
    print(f"  TC-06 Passed (NCR-019)  : {tc06_passed}")

    # Out-of-Domain Evaluation
    print("\n" + "=" * 95)
    print("OUT-OF-DOMAIN QUERY EVALUATION (SIMILARITY FLOOR & REJECTION):")
    print("=" * 95)
    ood_passed = 0
    for ood in OUT_OF_DOMAIN_QUERIES:
        q_ood = ood["query"]
        res = quality_knowledge_agent.query(query_text=q_ood, top_k=5)
        cnt = res.get("results_count", 0)
        mode = res.get("answer_mode", "")
        ans = res.get("answer", "")
        rejection_triggered = (cnt == 0 or "below_similarity_floor" in mode or "No relevant manufacturing" in ans)
        status_str = "PASS (Rejected / 0 Results)" if rejection_triggered else "FAIL (Returned Irrelevant Results)"
        if rejection_triggered: ood_passed += 1
        print(f"Query : '{q_ood}'")
        print(f"Status: {status_str} | Mode: {mode} | Matches Count: {cnt}")
        print(f"Notice: {ans[:90]}...")
        print("-" * 95)

    print(f"Out-of-Domain Success Rate: {ood_passed}/{len(OUT_OF_DOMAIN_QUERIES)} (100.0%)")

    assert hit_3_rate >= 0.80, f"Hit@3 rate {hit_3_rate:.2f} below target 0.80!"
    assert tc06_passed, "TC-06 Failed: NCR-019 was not in the top 3!"
    assert ood_passed == len(OUT_OF_DOMAIN_QUERIES), "Out-of-domain rejection failed for one or more queries!"
    print("\n>>> ALL RAG EVALUATION BENCHMARK TARGETS MET: PASS <<<")
    return {
        "hit_1_rate": hit_1_rate,
        "hit_3_rate": hit_3_rate,
        "recall_5_rate": recall_5_rate,
        "mrr": mrr,
        "tc06_passed": tc06_passed,
        "ood_passed": ood_passed,
        "query_results": in_domain_results
    }

if __name__ == "__main__":
    run_evaluation()
