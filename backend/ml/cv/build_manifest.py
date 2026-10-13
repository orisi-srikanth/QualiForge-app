"""
MVTec AD Dataset Manifest Builder for QualityMind
Builds data/mvtec_manifest.csv containing image paths, categories, splits, raw defect types,
unified defect types, and ground truth mask paths for the 4 approved categories only.
"""
import os
import csv
import yaml
from pathlib import Path

ALLOWED_CATEGORIES = ["metal_nut", "screw", "transistor", "cable"]

def get_mvtec_root() -> Path:
    env_path = os.getenv("MVTEC_ROOT")
    if env_path:
        return Path(env_path)
    
    # Check .env file
    project_root = Path(__file__).resolve().parent.parent.parent
    dotenv_file = project_root / ".env"
    if dotenv_file.exists():
        with open(dotenv_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MVTEC_ROOT="):
                    val = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
                    return Path(val)
                    
    return Path(r"D:\Projects Local\BV-DATASETS\mvtec_anomaly_detection")

def load_label_map() -> dict:
    project_root = Path(__file__).resolve().parent.parent.parent
    label_map_path = project_root / "data" / "mvtec_label_map.yaml"
    if not label_map_path.exists():
        label_map_path = project_root / "backend" / "data" / "mvtec_label_map.yaml"
    with open(label_map_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def build_manifest(output_csv_path: Path = None):
    mvtec_root = get_mvtec_root()
    if not mvtec_root.exists():
        raise FileNotFoundError(f"MVTec AD dataset directory not found at: {mvtec_root}")

    label_map = load_label_map()
    categories_cfg = label_map.get("categories", {})

    project_root = Path(__file__).resolve().parent.parent.parent
    if output_csv_path is None:
        output_csv_path = project_root / "data" / "mvtec_manifest.csv"

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)

    records = []

    for cat in ALLOWED_CATEGORIES:
        cat_dir = mvtec_root / cat
        if not cat_dir.exists():
            raise FileNotFoundError(f"Required category folder missing: {cat_dir}")

        cat_cfg = categories_cfg.get(cat, {}).get("defects", {})

        # 1. Train Good
        train_good_dir = cat_dir / "train" / "good"
        if train_good_dir.exists():
            for img_file in sorted(train_good_dir.glob("*.png")):
                records.append({
                    "path": str(img_file),
                    "category": cat,
                    "split": "train",
                    "defect_type": "good",
                    "unified_type": "no_defect",
                    "mask_path": ""
                })

        # 2. Test Good
        test_good_dir = cat_dir / "test" / "good"
        if test_good_dir.exists():
            for img_file in sorted(test_good_dir.glob("*.png")):
                records.append({
                    "path": str(img_file),
                    "category": cat,
                    "split": "test",
                    "defect_type": "good",
                    "unified_type": "no_defect",
                    "mask_path": ""
                })

        # 3. Test Defects
        test_dir = cat_dir / "test"
        if test_dir.exists():
            for defect_dir in sorted(test_dir.iterdir()):
                if not defect_dir.is_dir() or defect_dir.name == "good":
                    continue
                raw_defect = defect_dir.name
                unified = cat_cfg.get(raw_defect, {}).get("unified_defect_type", raw_defect)

                gt_dir = cat_dir / "ground_truth" / raw_defect

                for img_file in sorted(defect_dir.glob("*.png")):
                    mask_file = gt_dir / f"{img_file.stem}_mask.png"
                    mask_str = str(mask_file) if mask_file.exists() else ""
                    records.append({
                        "path": str(img_file),
                        "category": cat,
                        "split": "test",
                        "defect_type": raw_defect,
                        "unified_type": unified,
                        "mask_path": mask_str
                    })

    # Write CSV
    fieldnames = ["path", "category", "split", "defect_type", "unified_type", "mask_path"]
    with open(output_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    # Mirror to backend/data/mvtec_manifest.csv as well
    backend_csv = project_root / "backend" / "data" / "mvtec_manifest.csv"
    backend_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(backend_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"Manifest written to {output_csv_path} ({len(records)} total records).")
    print(f"Mirrored to {backend_csv}.")

    # Summary
    summary = {}
    for r in records:
        key = (r["category"], r["split"], r["unified_type"])
        summary[key] = summary.get(key, 0) + 1

    print("\nSummary by Category, Split, and Unified Defect Type:")
    for (cat, sp, ut), count in sorted(summary.items()):
        print(f"  {cat:<12} | {sp:<6} | {ut:<28} : {count} images")

    return output_csv_path

if __name__ == "__main__":
    build_manifest()
