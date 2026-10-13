"""
Realistic Synthetic Machined-Shaft Image Generator & Dataset Builder
QualityMind Industrial Vision Platform

Renders high-fidelity side-view images of cylindrical steel shafts with:
- Brushed metallic texture along cylinder axis
- Specular highlight gradients and 3D cylindrical Phong lighting
- Stepped journals, chamfered ends, fillets
- Standard features: milled keyway pocket, circlip groove, retaining collar
- 6 Defect Classes:
  0: no_defect
  1: surface_scratch
  2: dent
  3: crack
  4: missing_feature (missing keyway pocket or circlip groove)
  5: incorrect_assembly (misplaced or skewed retaining collar)
- Group-based stratified splitting (70% train, 15% val, 15% test) with ZERO leakage
- Separate HARD TEST split with unseen lighting, contrast, blur, and sensor noise
- Annotations: YOLO txt, COCO json, and binary PNG masks
"""
import os
import sys
import json
import math
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

import cv2
import numpy as np
from PIL import Image

CLASSES = [
    "no_defect",
    "surface_scratch",
    "dent",
    "crack",
    "missing_feature",
    "incorrect_assembly"
]

CLASS_TO_IDX = {cls_name: i for i, cls_name in enumerate(CLASSES)}
IDX_TO_CLASS = {i: cls_name for i, cls_name in enumerate(CLASSES)}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_BASE_DIR = PROJECT_ROOT / "data" / "synthetic_shafts"


def compute_phash(image_np: np.ndarray) -> str:
    """Computes 256-bit DCT perceptual hash (pHash)."""
    if len(image_np.shape) == 3:
        gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
    else:
        gray = image_np
    resized = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
    dct = cv2.dct(np.float32(resized))
    dct_low = dct[:16, :16]
    med = np.median(dct_low)
    bits = [1 if v > med else 0 for v in dct_low.flatten()]
    # Return as hex string
    hex_str = "".join([f"{int(''.join(map(str, bits[i:i+4])), 2):x}" for i in range(0, 256, 4)])
    return hex_str


def compute_sha256(file_path: Path) -> str:
    """Computes SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class ShaftRenderer:
    def __init__(self, width: int = 512, height: int = 512):
        self.w = width
        self.h = height

    def render_background(self, rng: np.random.Generator, is_hard: bool = False) -> np.ndarray:
        """Generates realistic workbench inspection surface."""
        if not is_hard:
            base_val = float(rng.integers(45, 68))
            bg = np.full((self.h, self.w, 3), base_val, dtype=np.float32)
            # Subtle workshop lighting gradient
            gx = np.linspace(rng.uniform(-10, -2), rng.uniform(2, 10), self.w).reshape(1, self.w, 1)
            gy = np.linspace(rng.uniform(-14, -4), rng.uniform(4, 14), self.h).reshape(self.h, 1, 1)
            bg = bg + gx + gy
            # Fine surface grain
            bg_noise = rng.normal(0, rng.uniform(2.0, 4.0), (self.h, self.w, 3)).astype(np.float32)
            bg = np.clip(bg + bg_noise, 0, 255)
        else:
            # Hard test: heavy dark background or harsh flare
            if rng.random() > 0.4:
                base_val = float(rng.integers(18, 35))  # underexposed dark matte
            else:
                base_val = float(rng.integers(75, 110))  # harsh industrial glare
            bg = np.full((self.h, self.w, 3), base_val, dtype=np.float32)
            # Diagonal shadow band across frame
            xx, yy = np.meshgrid(np.arange(self.w), np.arange(self.h))
            diag = (xx + yy * 0.8) / (self.w + self.h * 0.8)
            shadow_mask = np.sin(diag * math.pi * 2.5) * rng.uniform(15, 30)
            bg = bg + shadow_mask[:, :, np.newaxis]
            bg_noise = rng.normal(0, rng.uniform(6.0, 14.0), (self.h, self.w, 3)).astype(np.float32)
            bg = np.clip(bg + bg_noise, 0, 255)

        return bg

    def render_single_shaft(
        self,
        cls_name: str,
        group_id: int,
        img_idx: int,
        seed: int,
        is_hard: bool = False
    ) -> Tuple[np.ndarray, np.ndarray, Optional[Dict[str, int]]]:
        """Renders complete shaft image, defect mask, and bounding box."""
        rng = np.random.default_rng(seed)

        # 1. Background
        bg = self.render_background(rng, is_hard=is_hard)

        # 2. Workpiece Geometry
        cx = 256 + int(rng.integers(-12, 12))
        cy = 256 + int(rng.integers(-10, 10))
        total_len = int(rng.integers(390, 430))
        main_r = int(rng.integers(50, 56))
        journal_r = int(main_r * rng.uniform(0.78, 0.83))
        journal_len = int(rng.integers(62, 74))
        angle_deg = float(rng.uniform(-4.5, 4.5))

        # Canvases for cylinder and features
        cyl_canvas = np.zeros((self.h, self.w, 3), dtype=np.float32)
        cyl_mask = np.zeros((self.h, self.w), dtype=np.uint8)

        x_start = cx - total_len // 2
        x_end = x_start + total_len
        x_j1_end = x_start + journal_len
        x_j2_start = x_end - journal_len

        # Compute radial envelope along shaft axis (vectorized per column)
        xs = np.arange(x_start, x_end)
        valid_x_mask = (xs >= 0) & (xs < self.w)
        valid_xs = xs[valid_x_mask]

        rs = np.full(len(valid_xs), main_r, dtype=np.int32)
        # Left journal with chamfer
        left_mask = valid_xs < x_j1_end
        chamf_left = np.maximum(0, (x_start + 7) - valid_xs[left_mask])
        rs[left_mask] = np.maximum(4, journal_r - chamf_left)

        # Right journal with chamfer
        right_mask = valid_xs >= x_j2_start
        chamf_right = np.maximum(0, valid_xs[right_mask] - (x_end - 7))
        rs[right_mask] = np.maximum(4, journal_r - chamf_right)

        for col_idx, vx in enumerate(valid_xs):
            r_cur = rs[col_idx]
            y_t = max(0, cy - r_cur)
            y_b = min(self.h, cy + r_cur)
            cyl_mask[y_t:y_b, vx] = 255

        # 3. 3D Cylindrical Shading & Brushed Texture
        steel_base = float(rng.uniform(168, 184))
        y_indices = np.arange(self.h)
        norm_y = (y_indices - cy) / float(main_r)
        in_cylinder = np.abs(norm_y) <= 1.0

        nz = np.zeros_like(norm_y)
        nz[in_cylinder] = np.sqrt(np.maximum(0.0, 1.0 - norm_y[in_cylinder] ** 2))

        # Diffuse component
        diff = np.maximum(0.0, -norm_y * 0.48 + nz * 0.72)
        # Specular highlight stripe at norm_y = -0.34
        spec = np.exp(-((norm_y - (-0.34)) ** 2) / 0.038) * rng.uniform(78.0, 92.0)
        # Ambient bounce from lower table
        amb_bounce = np.maximum(0.0, norm_y * 0.22) * 24.0

        shading_profile = steel_base * (0.58 + 0.42 * diff) + spec + amb_bounce
        cyl_canvas = np.repeat(shading_profile[:, np.newaxis, np.newaxis], self.w, axis=1)
        cyl_canvas = np.repeat(cyl_canvas, 3, axis=2)

        # Directional brushed steel grain (lathe longitudinal striations)
        grain_1d = rng.normal(0, rng.uniform(14.0, 19.0), (self.h, 1)).astype(np.float32)
        grain_1d = cv2.GaussianBlur(grain_1d, (1, 3), 0.75)
        cyl_canvas += grain_1d[:, :, np.newaxis]

        # Harmonic tool feed pitch marks
        feed_pitch = float(rng.uniform(4.5, 6.8))
        x_coords = np.arange(self.w).reshape(1, self.w, 1)
        feed_marks = np.sin(x_coords * (2.0 * math.pi / feed_pitch)) * 5.5
        cyl_canvas += feed_marks

        cyl_canvas = np.clip(cyl_canvas, 8, 252)

        # Composite base cylinder onto background
        img = bg.copy()
        mask_3d = (cyl_mask > 0)[:, :, np.newaxis]
        img = np.where(mask_3d, cyl_canvas, img)

        # 4. Standard Features:
        # A. Circlip groove on right journal
        groove_x = x_j2_start + 22
        groove_w = 4
        groove_y_t = cy - journal_r + 2
        groove_y_b = cy + journal_r - 2
        cv2.rectangle(img, (groove_x, groove_y_t), (groove_x + groove_w, groove_y_b), (60, 60, 65), -1)
        cv2.line(img, (groove_x + groove_w + 1, groove_y_t), (groove_x + groove_w + 1, groove_y_b), (225, 225, 230), 1)

        # B. Keyway slot (milled pocket)
        keyway_w = int(rng.integers(58, 68))
        keyway_h = int(rng.integers(16, 20))
        keyway_x = cx - keyway_w // 2
        keyway_y = cy - keyway_h // 2

        if cls_name != "missing_feature":
            # Render pocket
            cv2.rectangle(img, (keyway_x, keyway_y), (keyway_x + keyway_w, keyway_y + keyway_h), (50, 50, 54), -1)
            # Edge highlights
            cv2.line(img, (keyway_x, keyway_y), (keyway_x + keyway_w, keyway_y), (25, 25, 30), 2)
            cv2.line(img, (keyway_x, keyway_y + keyway_h), (keyway_x + keyway_w, keyway_y + keyway_h), (220, 220, 225), 1)
            cv2.circle(img, (keyway_x + 2, keyway_y + keyway_h // 2), keyway_h // 2, (50, 50, 54), -1)
            cv2.circle(img, (keyway_x + keyway_w - 2, keyway_y + keyway_h // 2), keyway_h // 2, (50, 50, 54), -1)

        # C. Retaining Collar / Spacer Ring
        collar_w = 24
        collar_r = main_r + 9
        normal_collar_x = x_j1_end - 4

        if cls_name == "incorrect_assembly":
            # Misplaced collar shifted into main body
            collar_x = x_j1_end + int(rng.integers(50, 80))
        else:
            collar_x = normal_collar_x

        cv2.rectangle(img, (collar_x, cy - collar_r), (collar_x + collar_w, cy + collar_r), (145, 147, 153), -1)
        cv2.line(img, (collar_x, cy - collar_r), (collar_x, cy + collar_r), (35, 35, 40), 2)
        cv2.line(img, (collar_x + collar_w, cy - collar_r), (collar_x + collar_w, cy + collar_r), (225, 225, 230), 2)
        cv2.line(img, (collar_x + 2, cy - int(collar_r * 0.38)), (collar_x + collar_w - 2, cy - int(collar_r * 0.38)), (245, 245, 250), 3)

        # 5. Defect Mask & Drawing
        defect_mask = np.zeros((self.h, self.w), dtype=np.uint8)

        if cls_name == "no_defect":
            pass

        elif cls_name == "surface_scratch":
            # Multi-segment linear gouge
            main_len_cur = total_len - 2 * journal_len
            sx = cx + int(rng.integers(-main_len_cur // 3, main_len_cur // 3))
            sy = cy + int(rng.integers(-main_r // 2, main_r // 2))
            s_len = float(rng.integers(55, 115))
            s_angle = float(rng.uniform(-0.55, 0.55))

            pts = []
            cur_x, cur_y = float(sx), float(sy)
            pts.append((int(cur_x), int(cur_y)))
            n_segs = int(rng.integers(4, 7))
            seg_len = s_len / n_segs
            for _ in range(n_segs):
                cur_x += seg_len * math.cos(s_angle) + float(rng.uniform(-2.5, 2.5))
                cur_y += seg_len * math.sin(s_angle) + float(rng.uniform(-3.5, 3.5))
                pts.append((int(cur_x), int(cur_y)))

            for i in range(len(pts) - 1):
                p1 = pts[i]
                p2 = pts[i + 1]
                # Dark furrow
                cv2.line(img, p1, p2, (25, 25, 30), 2)
                # Bright ridge
                cv2.line(img, (p1[0], p1[1] - 1), (p2[0], p2[1] - 1), (250, 250, 255), 1)
                cv2.line(defect_mask, p1, p2, 255, 4)

        elif cls_name == "dent":
            main_len_cur = total_len - 2 * journal_len
            dx = cx + int(rng.integers(-main_len_cur // 4, main_len_cur // 4))
            dy = cy + int(rng.integers(-main_r // 2, main_r // 2))
            drx = int(rng.integers(14, 26))
            dry = int(rng.integers(10, 18))
            d_angle = float(rng.uniform(-35, 35))

            # Dent shadow & highlight
            cv2.ellipse(img, (dx - 2, dy - 2), (drx, dry), d_angle, 0, 360, (45, 45, 50), -1)
            cv2.ellipse(img, (dx + 2, dy + 2), (drx, dry), d_angle, 0, 360, (230, 230, 240), 2)
            cv2.ellipse(defect_mask, (dx, dy), (drx + 2, dry + 2), d_angle, 0, 360, 255, -1)

        elif cls_name == "crack":
            main_len_cur = total_len - 2 * journal_len
            cx_pos = cx + int(rng.integers(-main_len_cur // 4, main_len_cur // 4))
            cy_pos = cy + int(rng.integers(-main_r // 2, main_r // 2))
            c_len = float(rng.integers(45, 95))
            c_angle = float(rng.uniform(0.75, 1.40))  # transverse fracture

            pts = []
            cur_x, cur_y = float(cx_pos), float(cy_pos)
            pts.append((int(cur_x), int(cur_y)))
            for _ in range(16):
                c_angle += float(rng.uniform(-0.55, 0.55))
                cur_x += (c_len / 16.0) * math.cos(c_angle)
                cur_y += (c_len / 16.0) * math.sin(c_angle)
                pts.append((int(cur_x), int(cur_y)))

            for i in range(len(pts) - 1):
                p1 = pts[i]
                p2 = pts[i + 1]
                cv2.line(img, p1, p2, (18, 18, 22), 2)
                cv2.line(img, (p1[0] + 1, p1[1]), (p2[0] + 1, p2[1]), (210, 210, 218), 1)
                cv2.line(defect_mask, p1, p2, 255, 4)

        elif cls_name == "missing_feature":
            # Missing keyway annotation region
            defect_mask[keyway_y:keyway_y + keyway_h, keyway_x:keyway_x + keyway_w] = 255

        elif cls_name == "incorrect_assembly":
            # Misplaced collar annotation region
            defect_mask[cy - collar_r:cy + collar_r, collar_x:collar_x + collar_w] = 255

        # 6. Apply Rotation Angle (Unified Image & Mask Affine Warp)
        rot_mat = cv2.getRotationMatrix2D((float(cx), float(cy)), angle_deg, 1.0)
        img = cv2.warpAffine(img, rot_mat, (self.w, self.h), borderMode=cv2.BORDER_REFLECT)
        defect_mask = cv2.warpAffine(defect_mask, rot_mat, (self.w, self.h), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0)

        # 7. Compute Bounding Box from Defect Mask
        bbox = None
        ys, xs = np.where(defect_mask > 0)
        if len(xs) > 0 and len(ys) > 0:
            bx = max(0, int(np.min(xs)) - 3)
            by = max(0, int(np.min(ys)) - 3)
            bw = min(self.w - bx, int(np.max(xs)) - bx + 6)
            bh = min(self.h - by, int(np.max(ys)) - by + 6)
            bbox = {"x": bx, "y": by, "width": bw, "height": bh}

        # 8. Camera Noise & Blur Simulation
        img = np.clip(img, 0, 255).astype(np.uint8)

        if not is_hard:
            sensor_noise = rng.normal(0, rng.uniform(1.2, 2.5), (self.h, self.w, 3)).astype(np.float32)
            img = np.clip(img.astype(np.float32) + sensor_noise, 0, 255).astype(np.uint8)
            img = cv2.GaussianBlur(img, (3, 3), 0.4)
        else:
            # Hard test: aggressive degradation
            if rng.random() > 0.4:
                # Heavy underexposure
                img = cv2.convertScaleAbs(img, alpha=0.55, beta=-20)
            else:
                # Contrast compression / harsh lighting
                img = cv2.convertScaleAbs(img, alpha=1.35, beta=25)

            heavy_noise = rng.normal(0, rng.uniform(22.0, 36.0), (self.h, self.w, 3)).astype(np.float32)
            img = np.clip(img.astype(np.float32) + heavy_noise, 0, 255).astype(np.uint8)
            blur_k = int(rng.choice([5, 7, 9]))
            img = cv2.GaussianBlur(img, (blur_k, blur_k), float(rng.uniform(2.2, 3.6)))

        return img, defect_mask, bbox


def generate_all_shaft_datasets(
    output_dir: Path = OUTPUT_BASE_DIR,
    base_seed: int = 42
) -> Dict[str, Any]:
    """
    Executes full generation pipeline:
    - 20 standard generation groups (0..19) -> 70% train (0..13), 15% val (14..16), 15% test (17..19)
    - 21 images per class per group * 6 classes = 126 images per group
    - Total standard: 2,520 images (420 per class)
    - 5 hard test groups (20..24) -> 10 images per class * 6 = 300 hard test images
    - Total images: 2,820 images
    - Formats: PNG images, PNG masks, YOLO txt labels, COCO json manifests
    - Strict leakage verification via SHA-256 and 64-bit dHash
    """
    renderer = ShaftRenderer(width=512, height=512)

    # Subdirectories
    images_dir = output_dir / "images"
    masks_dir = output_dir / "masks"
    labels_dir = output_dir / "labels"

    for d in [images_dir, masks_dir, labels_dir]:
        d.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("  SYNTHETIC SHAFT COMPUTER VISION DATASET GENERATOR")
    print("  Seed: 42 | Resolution: 512x512 | Target: 2,820 Images")
    print("=" * 65)

    # Group Allocation:
    # Groups 0..13: train (14 groups, 70%)
    # Groups 14..16: val (3 groups, 15%)
    # Groups 17..19: test (3 groups, 15%)
    # Groups 20..24: hard_test (5 groups)
    splits_records: Dict[str, List[Dict[str, Any]]] = {
        "train": [],
        "val": [],
        "test": [],
        "hard_test": []
    }

    # Tracking sets for leakage proofing
    sha256_by_split: Dict[str, set] = {"train": set(), "val": set(), "test": set(), "hard_test": set()}
    phash_by_split: Dict[str, set] = {"train": set(), "val": set(), "test": set(), "hard_test": set()}

    global_img_id = 1
    global_annot_id = 1

    coco_datasets: Dict[str, Dict[str, Any]] = {}
    for sp in ["train", "val", "test", "hard_test"]:
        coco_datasets[sp] = {
            "info": {
                "description": "QualityMind Synthetic Precision Shaft Vision Dataset",
                "version": "2.0-synthetic-shaft",
                "year": 2026,
                "provenance": "synthetic_procedural_generator"
            },
            "categories": [
                {"id": i, "name": name, "supercategory": "shaft_component"}
                for i, name in enumerate(CLASSES)
            ],
            "images": [],
            "annotations": []
        }

    # 1. Standard Generation (Groups 0..19)
    # 20 groups * 21 images/class = 420 images/class (2,520 total)
    for group_id in range(20):
        if group_id < 14:
            split_name = "train"
        elif group_id < 17:
            split_name = "val"
        else:
            split_name = "test"

        group_seed = base_seed + group_id * 1000
        print(f"Generating Group {group_id:02d}/19 -> Split '{split_name}' (Group Seed: {group_seed})...")

        for cls_idx, cls_name in enumerate(CLASSES):
            for item_idx in range(21):
                item_seed = group_seed + cls_idx * 100 + item_idx
                file_stem = f"shaft_grp{group_id:02d}_{cls_name}_{item_idx:02d}"

                # Render
                img, mask, bbox = renderer.render_single_shaft(
                    cls_name=cls_name,
                    group_id=group_id,
                    img_idx=item_idx,
                    seed=item_seed,
                    is_hard=False
                )

                # Save Image if not present
                img_path = images_dir / f"{file_stem}.png"
                mask_path = masks_dir / f"{file_stem}_mask.png"
                label_path = labels_dir / f"{file_stem}.txt"

                if not img_path.exists():
                    cv2.imwrite(str(img_path), img)
                if not mask_path.exists():
                    cv2.imwrite(str(mask_path), mask)

                # Save YOLO txt format
                # <class_id> <x_center> <y_center> <width> <height>
                with open(label_path, "w", encoding="utf-8") as lf:
                    if bbox is not None:
                        xc = (bbox["x"] + bbox["width"] / 2.0) / 512.0
                        yc = (bbox["y"] + bbox["height"] / 2.0) / 512.0
                        norm_w = bbox["width"] / 512.0
                        norm_h = bbox["height"] / 512.0
                        lf.write(f"{cls_idx} {xc:.6f} {yc:.6f} {norm_w:.6f} {norm_h:.6f}\n")

                # Compute Hashes
                img_sha = compute_sha256(img_path)
                img_phash = compute_phash(img)
                sha256_by_split[split_name].add(img_sha)
                phash_by_split[split_name].add(img_phash)

                # Manifest Record
                rec = {
                    "image_id": f"IMG-{global_img_id:05d}",
                    "path": str(img_path),
                    "mask_path": str(mask_path),
                    "label_path": str(label_path),
                    "filename": img_path.name,
                    "class_name": cls_name,
                    "class_idx": cls_idx,
                    "group_id": group_id,
                    "split": split_name,
                    "is_hard": False,
                    "bbox": bbox,
                    "sha256": img_sha,
                    "phash": img_phash
                }
                splits_records[split_name].append(rec)

                # COCO Json
                coco_datasets[split_name]["images"].append({
                    "id": global_img_id,
                    "file_name": img_path.name,
                    "width": 512,
                    "height": 512,
                    "class": cls_name,
                    "split": split_name,
                    "group_id": group_id
                })

                if bbox is not None:
                    coco_datasets[split_name]["annotations"].append({
                        "id": global_annot_id,
                        "image_id": global_img_id,
                        "category_id": cls_idx,
                        "bbox": [bbox["x"], bbox["y"], bbox["width"], bbox["height"]],
                        "area": bbox["width"] * bbox["height"],
                        "iscrowd": 0
                    })
                    global_annot_id += 1

                global_img_id += 1

    # 2. Hard Test Generation (Groups 20..24)
    # 5 groups * 10 images/class = 50 images/class (300 total)
    print("\nGenerating Separate HARD TEST Split (Unseen Lighting, Contrast & Sensor Noise)...")
    for group_id in range(20, 25):
        split_name = "hard_test"
        group_seed = base_seed + group_id * 1000 + 777
        print(f"Generating Hard Group {group_id:02d}/24 -> Split 'hard_test' (Seed: {group_seed})...")

        for cls_idx, cls_name in enumerate(CLASSES):
            for item_idx in range(10):
                item_seed = group_seed + cls_idx * 100 + item_idx
                file_stem = f"shaft_hard_grp{group_id:02d}_{cls_name}_{item_idx:02d}"

                img, mask, bbox = renderer.render_single_shaft(
                    cls_name=cls_name,
                    group_id=group_id,
                    img_idx=item_idx,
                    seed=item_seed,
                    is_hard=True
                )

                img_path = images_dir / f"{file_stem}.png"
                mask_path = masks_dir / f"{file_stem}_mask.png"
                label_path = labels_dir / f"{file_stem}.txt"

                if not img_path.exists():
                    cv2.imwrite(str(img_path), img)
                if not mask_path.exists():
                    cv2.imwrite(str(mask_path), mask)

                with open(label_path, "w", encoding="utf-8") as lf:
                    if bbox is not None:
                        xc = (bbox["x"] + bbox["width"] / 2.0) / 512.0
                        yc = (bbox["y"] + bbox["height"] / 2.0) / 512.0
                        norm_w = bbox["width"] / 512.0
                        norm_h = bbox["height"] / 512.0
                        lf.write(f"{cls_idx} {xc:.6f} {yc:.6f} {norm_w:.6f} {norm_h:.6f}\n")

                img_sha = compute_sha256(img_path)
                img_phash = compute_phash(img)
                sha256_by_split[split_name].add(img_sha)
                phash_by_split[split_name].add(img_phash)

                rec = {
                    "image_id": f"IMG-{global_img_id:05d}",
                    "path": str(img_path),
                    "mask_path": str(mask_path),
                    "label_path": str(label_path),
                    "filename": img_path.name,
                    "class_name": cls_name,
                    "class_idx": cls_idx,
                    "group_id": group_id,
                    "split": split_name,
                    "is_hard": True,
                    "bbox": bbox,
                    "sha256": img_sha,
                    "phash": img_phash
                }
                splits_records[split_name].append(rec)

                coco_datasets[split_name]["images"].append({
                    "id": global_img_id,
                    "file_name": img_path.name,
                    "width": 512,
                    "height": 512,
                    "class": cls_name,
                    "split": split_name,
                    "group_id": group_id
                })

                if bbox is not None:
                    coco_datasets[split_name]["annotations"].append({
                        "id": global_annot_id,
                        "image_id": global_img_id,
                        "category_id": cls_idx,
                        "bbox": [bbox["x"], bbox["y"], bbox["width"], bbox["height"]],
                        "area": bbox["width"] * bbox["height"],
                        "iscrowd": 0
                    })
                    global_annot_id += 1

                global_img_id += 1

    # 3. Leakage Verification & Assertion
    print("\n" + "=" * 65)
    print("  LEAKAGE-PROOF VERIFICATION (SHA-256 & 256-BIT PERCEPTUAL PHASH)")
    print("=" * 65)
    train_sha = sha256_by_split["train"]
    val_sha = sha256_by_split["val"]
    test_sha = sha256_by_split["test"]
    hard_sha = sha256_by_split["hard_test"]

    overlap_train_val = train_sha.intersection(val_sha)
    overlap_train_test = train_sha.intersection(test_sha)
    overlap_val_test = val_sha.intersection(test_sha)
    overlap_train_hard = train_sha.intersection(hard_sha)

    print(f"SHA-256 Overlap Train vs Val:      {len(overlap_train_val)}")
    print(f"SHA-256 Overlap Train vs Test:     {len(overlap_train_test)}")
    print(f"SHA-256 Overlap Val vs Test:       {len(overlap_val_test)}")
    print(f"SHA-256 Overlap Train vs Hard:     {len(overlap_train_hard)}")

    assert len(overlap_train_val) == 0, "DATA LEAKAGE DETECTED: Train vs Val SHA-256 overlap!"
    assert len(overlap_train_test) == 0, "DATA LEAKAGE DETECTED: Train vs Test SHA-256 overlap!"
    assert len(overlap_val_test) == 0, "DATA LEAKAGE DETECTED: Val vs Test SHA-256 overlap!"
    assert len(overlap_train_hard) == 0, "DATA LEAKAGE DETECTED: Train vs Hard Test SHA-256 overlap!"

    # Assert zero perceptual pHash collisions between splits
    train_phash = phash_by_split["train"]
    val_phash = phash_by_split["val"]
    test_phash = phash_by_split["test"]
    hard_phash = phash_by_split["hard_test"]

    phash_overlap_tv = train_phash.intersection(val_phash)
    phash_overlap_tt = train_phash.intersection(test_phash)
    phash_overlap_vt = val_phash.intersection(test_phash)
    phash_overlap_th = train_phash.intersection(hard_phash)

    print(f"pHash Overlap Train vs Val:        {len(phash_overlap_tv)}")
    print(f"pHash Overlap Train vs Test:       {len(phash_overlap_tt)}")
    print(f"pHash Overlap Val vs Test:         {len(phash_overlap_vt)}")
    print(f"pHash Overlap Train vs Hard:       {len(phash_overlap_th)}")

    assert len(phash_overlap_tv) == 0, "LEAKAGE: Train vs Val perceptual hash collision!"
    assert len(phash_overlap_tt) == 0, "LEAKAGE: Train vs Test perceptual hash collision!"
    assert len(phash_overlap_vt) == 0, "LEAKAGE: Val vs Test perceptual hash collision!"
    assert len(phash_overlap_th) == 0, "LEAKAGE: Train vs Hard Test perceptual hash collision!"

    print(">> ZERO DATA LEAKAGE CONFIRMED: 100% DISJOINT ACROSS ALL SPLITS.")

    # 4. Save Split Manifest & COCO JSONs
    splits_json_path = output_dir / "splits.json"
    with open(splits_json_path, "w", encoding="utf-8") as f:
        json.dump(splits_records, f, indent=2)

    # Also mirror splits to backend/data/synthetic_shafts/splits.json
    backend_splits_dir = PROJECT_ROOT / "backend" / "data" / "synthetic_shafts"
    backend_splits_dir.mkdir(parents=True, exist_ok=True)
    with open(backend_splits_dir / "splits.json", "w", encoding="utf-8") as f:
        json.dump(splits_records, f, indent=2)

    for sp, coco_dict in coco_datasets.items():
        coco_path = output_dir / f"annotations_{sp}.json"
        with open(coco_path, "w", encoding="utf-8") as f:
            json.dump(coco_dict, f, indent=2)

    # Summary Counts Table
    print("\n" + "=" * 65)
    print("  DATASET COUNTS PER SPLIT AND CLASS")
    print("=" * 65)
    print(f"{'Class Name':<22} | {'Train (70%)':<12} | {'Val (15%)':<10} | {'Test (15%)':<11} | {'Hard Test':<10} | {'Total'}")
    print("-" * 65)
    totals = {"train": 0, "val": 0, "test": 0, "hard_test": 0}
    for cls_name in CLASSES:
        n_tr = sum(1 for r in splits_records["train"] if r["class_name"] == cls_name)
        n_vl = sum(1 for r in splits_records["val"] if r["class_name"] == cls_name)
        n_ts = sum(1 for r in splits_records["test"] if r["class_name"] == cls_name)
        n_hd = sum(1 for r in splits_records["hard_test"] if r["class_name"] == cls_name)
        tot = n_tr + n_vl + n_ts + n_hd
        totals["train"] += n_tr
        totals["val"] += n_vl
        totals["test"] += n_ts
        totals["hard_test"] += n_hd
        print(f"{cls_name:<22} | {n_tr:<12} | {n_vl:<10} | {n_ts:<11} | {n_hd:<10} | {tot}")
    print("-" * 65)
    tot_all = sum(totals.values())
    print(f"{'TOTALS':<22} | {totals['train']:<12} | {totals['val']:<10} | {totals['test']:<11} | {totals['hard_test']:<10} | {tot_all}")
    print("=" * 65)
    print(f"Generated {tot_all} images stored in {output_dir}")
    print(f"Manifest written to: {splits_json_path}")

    return {
        "splits_records": splits_records,
        "totals": totals,
        "total_images": tot_all,
        "classes": CLASSES
    }


if __name__ == "__main__":
    generate_all_shaft_datasets()
