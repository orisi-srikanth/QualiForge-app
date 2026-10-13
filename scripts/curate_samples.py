"""
Curate 15-20 Real MVTec AD Demo Samples from Held-Out Test Split
Copies selected test samples to backend/app/static/uploads/samples/
Sets IMG-001.png to a held-out metal_nut/scratch image.
Tags all images with source: "MVTec AD (proxy part)" and associates them with BATCH-0245.
"""
import os
import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPLITS_PATH = PROJECT_ROOT / "data" / "splits.json"
SAMPLES_DIR = PROJECT_ROOT / "backend" / "app" / "static" / "uploads" / "samples"

def curate_samples():
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    with open(SPLITS_PATH, "r", encoding="utf-8") as f:
        splits = json.load(f)

    test_records = splits["test"]

    # Filter held-out test images per category & defect
    curated = []

    # 1. metal_nut
    nut_scratch = next(r for r in test_records if r["category"] == "metal_nut" and r["defect_type"] == "scratch")
    nut_bent = next(r for r in test_records if r["category"] == "metal_nut" and r["defect_type"] == "bent")
    nut_flip = next(r for r in test_records if r["category"] == "metal_nut" and r["defect_type"] == "flip")
    nut_color = next(r for r in test_records if r["category"] == "metal_nut" and r["defect_type"] == "color")
    nut_good = next(r for r in test_records if r["category"] == "metal_nut" and r["unified_type"] == "no_defect")

    # 2. screw
    screw_head = next(r for r in test_records if r["category"] == "screw" and r["defect_type"] == "scratch_head")
    screw_thread = next(r for r in test_records if r["category"] == "screw" and r["defect_type"] == "thread_side")
    screw_front = next(r for r in test_records if r["category"] == "screw" and r["defect_type"] == "manipulated_front")
    screw_good = next(r for r in test_records if r["category"] == "screw" and r["unified_type"] == "no_defect")

    # 3. transistor
    tran_dam = next(r for r in test_records if r["category"] == "transistor" and r["defect_type"] == "damaged_case")
    tran_mis = next(r for r in test_records if r["category"] == "transistor" and r["defect_type"] == "misplaced")
    tran_cut = next(r for r in test_records if r["category"] == "transistor" and r["defect_type"] == "cut_lead")
    tran_good = next(r for r in test_records if r["category"] == "transistor" and r["unified_type"] == "no_defect")

    # 4. cable
    cable_miss = next(r for r in test_records if r["category"] == "cable" and r["defect_type"] == "missing_wire")
    cable_swap = next(r for r in test_records if r["category"] == "cable" and r["defect_type"] == "cable_swap")
    cable_bent = next(r for r in test_records if r["category"] == "cable" and r["defect_type"] == "bent_wire")
    cable_insul = next(r for r in test_records if r["category"] == "cable" and r["defect_type"] == "cut_outer_insulation")
    cable_good = next(r for r in test_records if r["category"] == "cable" and r["unified_type"] == "no_defect")

    selected = [
        ("IMG-001.png", nut_scratch),          # Required Primary Held-Out Test Image
        ("metal_nut_scratch.png", nut_scratch),
        ("metal_nut_bent.png", nut_bent),
        ("metal_nut_flip.png", nut_flip),
        ("metal_nut_color.png", nut_color),
        ("metal_nut_normal.png", nut_good),
        ("screw_scratch_head.png", screw_head),
        ("screw_thread.png", screw_thread),
        ("screw_front_dent.png", screw_front),
        ("screw_normal.png", screw_good),
        ("transistor_damaged.png", tran_dam),
        ("transistor_misplaced.png", tran_mis),
        ("transistor_cut_lead.png", tran_cut),
        ("transistor_normal.png", tran_good),
        ("cable_missing.png", cable_miss),
        ("cable_swap.png", cable_swap),
        ("cable_bent_wire.png", cable_bent),
        ("cable_cut_insul.png", cable_insul),
        ("cable_normal.png", cable_good),
    ]

    manifest_entries = []

    for target_name, rec in selected:
        src_path = Path(rec["path"])
        dest_path = SAMPLES_DIR / target_name
        shutil.copy2(src_path, dest_path)

        manifest_entries.append({
            "sample_id": target_name,
            "filename": target_name,
            "category": rec["category"],
            "defect_type": rec["unified_type"],
            "raw_defect": rec["defect_type"],
            "source": "MVTec AD (proxy part)",
            "batch_association": "BATCH-0245",
            "is_held_out_test": True,
            "original_path": rec["path"]
        })

    # Save manifest
    with open(SAMPLES_DIR / "samples_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest_entries, f, indent=2)

    print(f"Curated {len(selected)} real held-out test images to {SAMPLES_DIR}.")
    print(f"Primary IMG-001.png set to held-out {nut_scratch['category']}/{nut_scratch['defect_type']}.")

if __name__ == "__main__":
    curate_samples()
