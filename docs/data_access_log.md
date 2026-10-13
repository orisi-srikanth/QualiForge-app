# MVTec AD Dataset Access Log

**Date of Verification:** 2026-10-11  
**Source Path Verified:** `D:\Projects Local\BV-DATASETS\mvtec_anomaly_detection`  
**Access Scope:** Read-only verification of strictly 4 approved categories (`metal_nut`, `screw`, `transistor`, `cable`).  
**Compliance Confirmation:**  
- Zero access to the other 11 categories (`bottle`, `capsule`, `carpet`, `grid`, `hazelnut`, `leather`, `pill`, `tile`, `toothbrush`, `wood`, `zipper`).
- Zero modifications, renames, writes, or deletions inside `MVTEC_SOURCE_PATH`.
- Zero scanning outside `MVTEC_SOURCE_PATH` and this repository.
- Zero network uploads of dataset images.

---

## 1. Verified Directory Structure & Image Counts

### Category 1: `metal_nut`
- `train/good`: 220 images
- `test/good`: 22 images
- `test/bent`: 25 images | `ground_truth/bent`: 25 masks
- `test/color`: 22 images | `ground_truth/color`: 22 masks
- `test/flip`: 23 images | `ground_truth/flip`: 23 masks
- `test/scratch`: 23 images | `ground_truth/scratch`: 23 masks
- **Subtotal:** 242 normal images, 93 defective images, 93 ground truth masks

### Category 2: `screw`
- `train/good`: 320 images
- `test/good`: 41 images
- `test/manipulated_front`: 24 images | `ground_truth/manipulated_front`: 24 masks
- `test/scratch_head`: 24 images | `ground_truth/scratch_head`: 24 masks
- `test/scratch_neck`: 25 images | `ground_truth/scratch_neck`: 25 masks
- `test/thread_side`: 23 images | `ground_truth/thread_side`: 23 masks
- `test/thread_top`: 23 images | `ground_truth/thread_top`: 23 masks
- **Subtotal:** 361 normal images, 119 defective images, 119 ground truth masks

### Category 3: `transistor`
- `train/good`: 213 images
- `test/good`: 60 images
- `test/bent_lead`: 10 images | `ground_truth/bent_lead`: 10 masks
- `test/cut_lead`: 10 images | `ground_truth/cut_lead`: 10 masks
- `test/damaged_case`: 10 images | `ground_truth/damaged_case`: 10 masks
- `test/misplaced`: 10 images | `ground_truth/misplaced`: 10 masks
- **Subtotal:** 273 normal images, 40 defective images, 40 ground truth masks

### Category 4: `cable`
- `train/good`: 224 images
- `test/good`: 58 images
- `test/bent_wire`: 13 images | `ground_truth/bent_wire`: 13 masks
- `test/cable_swap`: 12 images | `ground_truth/cable_swap`: 12 masks
- `test/combined`: 11 images | `ground_truth/combined`: 11 masks
- `test/cut_inner_insulation`: 14 images | `ground_truth/cut_inner_insulation`: 14 masks
- `test/cut_outer_insulation`: 10 images | `ground_truth/cut_outer_insulation`: 10 masks
- `test/missing_cable`: 12 images | `ground_truth/missing_cable`: 12 masks
- `test/missing_wire`: 10 images | `ground_truth/missing_wire`: 10 masks
- `test/poke_insulation`: 10 images | `ground_truth/poke_insulation`: 10 masks
- **Subtotal:** 282 normal images, 92 defective images, 92 ground truth masks

---

## 2. Totals Across 4 Categories
- **Train Normal (good):** 977 images
- **Test Normal (good):** 181 images
- **Defective Test Images:** 344 images across 21 defect subfolders
- **Ground Truth Mask Files:** 344 mask PNGs
- **Grand Total Evaluated:** 1,502 image files + 344 mask files

All required directories and mask pairs exist with complete integrity.
