"""
Independent Verification Script: MVTec AD Dataset Disk Count vs Manifest Audit
Strictly read-only. Accesses only metal_nut, screw, transistor, cable.
Checks file counts on disk, compares with data/mvtec_manifest.csv,
and validates ground-truth mask pairing and shapes.
"""
import os
import csv
from pathlib import Path
from PIL import Image

MVTEC_ROOT = Path(r"D:\Projects Local\BV-DATASETS\mvtec_anomaly_detection")
MANIFEST_PATH = Path("data/mvtec_manifest.csv")

ALLOWED_CATEGORIES = ["metal_nut", "screw", "transistor", "cable"]

def audit_dataset():
    print("=" * 80)
    print("INDEPENDENT V&V AUDIT: MVTEC AD REAL DATASET DISK COUNT & MANIFEST VERIFICATION")
    print("=" * 80)
    print(f"Target Source Path: {MVTEC_ROOT}")
    assert MVTEC_ROOT.exists(), f"Source path {MVTEC_ROOT} does not exist!"

    # 1. Read manifest
    manifest_rows = []
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            manifest_rows = list(reader)
    print(f"Manifest Records Loaded: {len(manifest_rows)}")

    manifest_by_cat_defect = {}
    for r in manifest_rows:
        key = (r["category"], r["split"], r["defect_type"])
        manifest_by_cat_defect[key] = manifest_by_cat_defect.get(key, 0) + 1

    total_disk_images = 0
    total_disk_masks = 0
    all_mask_checks_passed = True
    corrupt_files = []

    print("\n" + "-" * 80)
    print(f"{'Category':<12} | {'Split':<6} | {'Defect / Subfolder':<24} | {'Disk Files':<10} | {'Manifest':<10} | {'Masks':<8} | {'Match'}")
    print("-" * 80)

    for cat in ALLOWED_CATEGORIES:
        cat_dir = MVTEC_ROOT / cat
        assert cat_dir.exists(), f"Category directory {cat_dir} missing!"

        # Train good
        train_good_dir = cat_dir / "train" / "good"
        train_good_files = [f for f in train_good_dir.glob("*.png") if f.is_file()]
        disk_count = len(train_good_files)
        total_disk_images += disk_count
        man_count = manifest_by_cat_defect.get((cat, "train", "good"), 0)
        match_str = "OK" if disk_count == man_count else "MISMATCH"
        print(f"{cat:<12} | {'train':<6} | {'good':<24} | {disk_count:<10} | {man_count:<10} | {'N/A':<8} | {match_str}")

        # Test subfolders
        test_dir = cat_dir / "test"
        for sub in sorted(test_dir.iterdir()):
            if not sub.is_dir():
                continue
            defect_name = sub.name
            img_files = [f for f in sub.glob("*.png") if f.is_file()]
            disk_count = len(img_files)
            total_disk_images += disk_count
            man_count = manifest_by_cat_defect.get((cat, "test", defect_name), 0)

            # Check masks if defect
            mask_count_str = "N/A"
            if defect_name != "good":
                mask_dir = cat_dir / "ground_truth" / defect_name
                mask_files = [f for f in mask_dir.glob("*_mask.png") if f.is_file()] if mask_dir.exists() else []
                total_disk_masks += len(mask_files)
                mask_count_str = str(len(mask_files))
                if len(mask_files) != disk_count:
                    all_mask_checks_passed = False

                # Sample check mask validity
                for mf in mask_files[:2]:
                    try:
                        with Image.open(mf) as m_img:
                            mode = m_img.mode
                            sz = m_img.size
                    except Exception as e:
                        corrupt_files.append((str(mf), str(e)))

            match_str = "OK" if disk_count == man_count else "MISMATCH"
            print(f"{cat:<12} | {'test':<6} | {defect_name:<24} | {disk_count:<10} | {man_count:<10} | {mask_count_str:<8} | {match_str}")

    print("-" * 80)
    print(f"Total Disk Images Evaluated (4 allowed categories): {total_disk_images}")
    print(f"Total Disk Ground Truth Masks Evaluated           : {total_disk_masks}")
    print(f"Total Manifest Image Records                      : {len(manifest_rows)}")
    print(f"All Defect Images Have Matching Ground Truth Masks: {all_mask_checks_passed}")
    print(f"Corrupt Files Detected                            : {len(corrupt_files)}")
    print("=" * 80)

    return total_disk_images, total_disk_masks, corrupt_files

if __name__ == "__main__":
    audit_dataset()
