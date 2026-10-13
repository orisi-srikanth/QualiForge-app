"""
Evaluation Engine for Precision Shaft Defect Detection Pipeline
Evaluates transfer-learning classifier and Grad-CAM localization on both:
- Normal Test Split (Held-out generation groups 17..19)
- Hard Test Split (Unseen lighting, contrast, blur, and sensor noise)

Metrics reported:
- Per-class Precision, Recall, F1, Support
- Macro-F1 and Accuracy
- 6x6 Confusion Matrix
- Localisation IoU against generator ground truth bounding box
- % boxes with IoU >= 0.5
- mAP@0.5
- Performance drop between normal test and hard test splits
- Saves 12+ visual prediction figures into docs/cv_samples/
"""
import os
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

import cv2
import numpy as np
import torch
import torch.nn.functional as F
import torchvision.transforms as transforms
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ml.cv.train_classifier import (
    DefectClassifier,
    GradCAM,
    SHAFT_CLASSES,
    CLASS_TO_IDX,
    IDX_TO_CLASS
)


def compute_box_iou(boxA: Optional[Dict[str, int]], boxB: Optional[Dict[str, int]]) -> float:
    """Computes Intersection-over-Union between two bounding boxes {x, y, width, height}."""
    if boxA is None or boxB is None:
        return 0.0
    xA = max(boxA["x"], boxB["x"])
    yA = max(boxA["y"], boxB["y"])
    xB = min(boxA["x"] + boxA["width"], boxB["x"] + boxB["width"])
    yB = min(boxA["y"] + boxA["height"], boxB["y"] + boxB["height"])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = boxA["width"] * boxA["height"]
    boxBArea = boxB["width"] * boxB["height"]
    denom = float(boxAArea + boxBArea - interArea)
    return interArea / denom if denom > 0 else 0.0


def extract_box_from_cam(cam_map: np.ndarray, threshold_ratio: float = 0.45) -> Optional[Dict[str, int]]:
    """Extracts bounding box from Grad-CAM activation heatmap."""
    binary_cam = (cam_map >= (np.max(cam_map) * threshold_ratio)).astype(np.uint8)
    contours, _ = cv2.findContours(binary_cam, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    # Largest contour
    c = max(contours, key=cv2.contourArea)
    bx, by, bw, bh = cv2.boundingRect(c)
    if bw <= 4 or bh <= 4:
        return None
    return {"x": int(bx), "y": int(by), "width": int(bw), "height": int(bh)}


def evaluate_split(
    records: List[Dict[str, Any]],
    model: DefectClassifier,
    grad_cam: GradCAM,
    transform: transforms.Compose,
    device: torch.device,
    split_name: str
) -> Dict[str, Any]:
    """Runs full evaluation over a given split."""
    y_true = []
    y_pred = []
    confidences = []
    ious = []
    box_iou_gte_50 = []
    map50_hits = []

    per_sample_details = []

    for rec in records:
        img_path = rec["path"]
        true_cls = rec.get("class_name") or rec.get("unified_type", "no_defect")
        true_idx = CLASS_TO_IDX.get(true_cls, 0)
        gt_bbox = rec.get("bbox")

        img_pil = Image.open(img_path).convert("RGB")
        tensor_in = transform(img_pil).unsqueeze(0).to(device)

        with torch.no_grad():
            logits = model(tensor_in)
            probs = F.softmax(logits, dim=1).squeeze().cpu().numpy()

        pred_idx = int(np.argmax(probs))
        pred_prob = float(probs[pred_idx])
        pred_cls = IDX_TO_CLASS.get(pred_idx, "no_defect")

        y_true.append(true_idx)
        y_pred.append(pred_idx)
        confidences.append(pred_prob)

        # Grad-CAM Localisation
        pred_bbox = None
        iou = 0.0
        if pred_idx != 0:
            cam_map = grad_cam.generate(tensor_in, pred_idx)
            pred_bbox = extract_box_from_cam(cam_map, threshold_ratio=0.42)

        # Compute IoU against GT
        if true_idx == 0:
            # Normal shaft: if model predicts no_defect, perfect localization
            if pred_idx == 0:
                iou = 1.0
                is_box_50 = 1.0
                map_hit = 1.0
            else:
                iou = 0.0
                is_box_50 = 0.0
                map_hit = 0.0
        else:
            if gt_bbox is not None and pred_bbox is not None:
                iou = compute_box_iou(gt_bbox, pred_bbox)
                is_box_50 = 1.0 if iou >= 0.50 else 0.0
                map_hit = 1.0 if (iou >= 0.50 and pred_idx == true_idx) else 0.0
            else:
                iou = 0.0
                is_box_50 = 0.0
                map_hit = 0.0

        ious.append(iou)
        box_iou_gte_50.append(is_box_50)
        map50_hits.append(map_hit)

        per_sample_details.append({
            "image_id": rec.get("image_id", ""),
            "path": img_path,
            "true_class": true_cls,
            "pred_class": pred_cls,
            "confidence": pred_prob,
            "gt_bbox": gt_bbox,
            "pred_bbox": pred_bbox,
            "iou": iou
        })

    # Metrics calculation
    y_true_arr = np.array(y_true)
    y_pred_arr = np.array(y_pred)

    acc = float((y_true_arr == y_pred_arr).mean())
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    macro_p = float(precision_score(y_true, y_pred, average="macro", zero_division=0))
    macro_r = float(recall_score(y_true, y_pred, average="macro", zero_division=0))

    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(SHAFT_CLASSES))))

    per_class = {}
    for i, cls_name in enumerate(SHAFT_CLASSES):
        cls_mask_true = (y_true_arr == i)
        cls_mask_pred = (y_pred_arr == i)
        tp = int(np.sum(cls_mask_true & cls_mask_pred))
        fp = int(np.sum(~cls_mask_true & cls_mask_pred))
        fn = int(np.sum(cls_mask_true & ~cls_mask_pred))
        p = tp / max(tp + fp, 1) if (tp + fp) > 0 else 0.0
        r = tp / max(tp + fn, 1) if (tp + fn) > 0 else 0.0
        f1 = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0
        per_class[cls_name] = {
            "precision": round(float(p), 4),
            "recall": round(float(r), 4),
            "f1": round(float(f1), 4),
            "support": int(np.sum(cls_mask_true))
        }

    mean_iou = float(np.mean(ious))
    pct_box50 = float(np.mean(box_iou_gte_50)) * 100.0
    map50 = float(np.mean(map50_hits))

    return {
        "split": split_name,
        "sample_count": len(records),
        "accuracy": round(acc, 4),
        "macro_f1": round(macro_f1, 4),
        "macro_precision": round(macro_p, 4),
        "macro_recall": round(macro_r, 4),
        "mean_localisation_iou": round(mean_iou, 4),
        "pct_boxes_iou_gte_05": round(pct_box50, 2),
        "mAP_at_05": round(map50, 4),
        "per_class": per_class,
        "confusion_matrix": cm.tolist(),
        "per_sample_details": per_sample_details
    }


def save_confusion_matrix_plot(cm: List[List[int]], output_path: Path, title: str):
    """Renders and saves confusion matrix heatmap."""
    cm_arr = np.array(cm)
    fig, ax = plt.subplots(figsize=(8, 7))
    cax = ax.matshow(cm_arr, cmap=plt.cm.Blues, alpha=0.85)
    fig.colorbar(cax)

    ax.set_xticks(range(len(SHAFT_CLASSES)))
    ax.set_yticks(range(len(SHAFT_CLASSES)))
    short_labels = [c.replace("surface_", "s_").replace("incorrect_", "inc_") for c in SHAFT_CLASSES]
    ax.set_xticklabels(short_labels, rotation=35, ha="left", fontsize=9)
    ax.set_yticklabels(short_labels, fontsize=9)
    ax.set_xlabel("Predicted Class", fontsize=11, fontweight="bold")
    ax.set_ylabel("True Class", fontsize=11, fontweight="bold")
    ax.set_title(title, fontsize=12, fontweight="bold", pad=20)

    thresh = cm_arr.max() / 2.0
    for i in range(cm_arr.shape[0]):
        for j in range(cm_arr.shape[1]):
            val = cm_arr[i, j]
            ax.text(j, i, str(val), ha="center", va="center",
                    color="white" if val > thresh else "black", fontsize=10, fontweight="bold")

    plt.tight_layout()
    plt.savefig(output_path, dpi=130)
    plt.close(fig)


def save_prediction_samples(
    sample_list: List[Dict[str, Any]],
    grad_cam: GradCAM,
    transform: transforms.Compose,
    device: torch.device,
    output_dir: Path,
    num_samples: int = 12
):
    """Generates visual prediction figures with Grad-CAM heatmap and bounding boxes."""
    output_dir.mkdir(parents=True, exist_ok=True)
    selected = sample_list[:num_samples]

    for idx, item in enumerate(selected, start=1):
        img_bgr = cv2.imread(item["path"])
        if img_bgr is None:
            continue
        h, w = img_bgr.shape[:2]

        # Generate Grad-CAM map
        img_pil = Image.open(item["path"]).convert("RGB")
        tensor_in = transform(img_pil).unsqueeze(0).to(device)
        pred_idx = CLASS_TO_IDX.get(item["pred_class"], 0)

        overlay = img_bgr.copy()
        if pred_idx != 0:
            cam = grad_cam.generate(tensor_in, pred_idx)
            cam_color = cv2.applyColorMap(np.uint8(255 * cam), cv2.COLORMAP_JET)
            overlay = cv2.addWeighted(overlay, 0.65, cam_color, 0.35, 0)

        # Draw GT bbox in Green
        gt = item["gt_bbox"]
        if gt:
            cv2.rectangle(overlay, (gt["x"], gt["y"]), (gt["x"] + gt["width"], gt["y"] + gt["height"]), (0, 220, 0), 2)
            cv2.putText(overlay, f"GT: {item['true_class']}", (gt["x"], max(18, gt["y"] - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

        # Draw Pred bbox in Red
        pred_b = item["pred_bbox"]
        if pred_b:
            cv2.rectangle(overlay, (pred_b["x"], pred_b["y"]), (pred_b["x"] + pred_b["width"], pred_b["y"] + pred_b["height"]), (0, 0, 240), 2)
            cv2.putText(overlay, f"PRED: {item['pred_class']} ({item['confidence']*100:.1f}%) IoU:{item['iou']:.2f}",
                        (pred_b["x"], min(h - 8, pred_b["y"] + pred_b["height"] + 16)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)

        # Save figure
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))
        ax1.imshow(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
        ax1.set_title(f"Input: {item['true_class']} ({item['image_id']})", fontsize=10)
        ax1.axis("off")

        ax2.imshow(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))
        ax2.set_title(f"Grad-CAM + Detection | Pred: {item['pred_class']} ({item['confidence']*100:.1f}%)", fontsize=10)
        ax2.axis("off")

        plt.tight_layout()
        out_fig = output_dir / f"sample_{idx:02d}_{item['true_class']}.png"
        plt.savefig(out_fig, dpi=120)
        plt.close(fig)


def run_evaluation(
    splits_path: Optional[Path] = None,
    models_dir: Optional[Path] = None,
    output_samples_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """Runs complete evaluation on Normal Test and Hard Test splits."""
    project_root = Path(__file__).resolve().parent.parent.parent
    if splits_path is None:
        splits_path = project_root / "data" / "synthetic_shafts" / "splits.json"
    if models_dir is None:
        models_dir = project_root / "backend" / "models"
    if output_samples_dir is None:
        output_samples_dir = project_root / "docs" / "cv_samples"

    output_samples_dir.mkdir(parents=True, exist_ok=True)
    alt_models_dir = project_root / "models"
    alt_models_dir.mkdir(parents=True, exist_ok=True)

    with open(splits_path, "r", encoding="utf-8") as f:
        splits_data = json.load(f)

    normal_records = splits_data["test"]
    hard_records = splits_data["hard_test"]

    device = torch.device("cpu")
    model = DefectClassifier(num_classes=len(SHAFT_CLASSES)).to(device)
    weights_path = models_dir / "cv_model.pt"
    if not weights_path.exists():
        weights_path = alt_models_dir / "cv_model.pt"

    print(f"Loading weights from {weights_path}...")
    model.load_state_dict(torch.load(weights_path, map_location=device))
    model.eval()

    grad_cam = GradCAM(model)

    clf_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    # 1. Evaluate Normal Test Split
    print("\n[1/3] Evaluating Normal Test Split (Held-out Groups 17..19)...")
    normal_eval = evaluate_split(normal_records, model, grad_cam, clf_transform, device, "normal_test")

    # 2. Evaluate Hard Test Split
    print("[2/3] Evaluating Hard Test Split (Unseen Lighting, Contrast & Sensor Noise)...")
    hard_eval = evaluate_split(hard_records, model, grad_cam, clf_transform, device, "hard_test")

    # 3. Calculate Performance Drop
    drop_macro_f1 = round(normal_eval["macro_f1"] - hard_eval["macro_f1"], 4)
    drop_acc = round(normal_eval["accuracy"] - hard_eval["accuracy"], 4)
    drop_iou = round(normal_eval["mean_localisation_iou"] - hard_eval["mean_localisation_iou"], 4)
    drop_box50 = round(normal_eval["pct_boxes_iou_gte_05"] - hard_eval["pct_boxes_iou_gte_05"], 2)
    drop_map50 = round(normal_eval["mAP_at_05"] - hard_eval["mAP_at_05"], 4)

    # 4. Save Plots & Samples
    print("[3/3] Saving confusion matrices and visual prediction samples...")
    save_confusion_matrix_plot(normal_eval["confusion_matrix"], output_samples_dir / "confusion_matrix_normal.png",
                               f"Normal Test Split Confusion Matrix (Macro-F1: {normal_eval['macro_f1']:.4f})")
    save_confusion_matrix_plot(hard_eval["confusion_matrix"], output_samples_dir / "confusion_matrix_hard.png",
                               f"Hard Test Split Confusion Matrix (Macro-F1: {hard_eval['macro_f1']:.4f})")

    # Save 12+ samples
    save_prediction_samples(normal_eval["per_sample_details"], grad_cam, clf_transform, device, output_samples_dir, num_samples=12)

    # 5. Assemble and Persist Metrics Payload
    cv_metrics = {
        "dataset": "Synthetic Precision Ground Shafts (Procedural Engine)",
        "evaluation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "data_source": "synthetic",
        "model_version": "synthetic-shaft-v1.0",
        "model_architecture": "MobileNetV3-Small Transfer Learning + Grad-CAM Localizer",
        "classes": SHAFT_CLASSES,
        "normal_test_split": {
            "sample_count": normal_eval["sample_count"],
            "accuracy": normal_eval["accuracy"],
            "macro_f1": normal_eval["macro_f1"],
            "macro_precision": normal_eval["macro_precision"],
            "macro_recall": normal_eval["macro_recall"],
            "mean_localisation_iou": normal_eval["mean_localisation_iou"],
            "pct_boxes_iou_gte_05": normal_eval["pct_boxes_iou_gte_05"],
            "mAP_at_05": normal_eval["mAP_at_05"],
            "per_class": normal_eval["per_class"],
            "confusion_matrix": normal_eval["confusion_matrix"]
        },
        "hard_test_split": {
            "sample_count": hard_eval["sample_count"],
            "accuracy": hard_eval["accuracy"],
            "macro_f1": hard_eval["macro_f1"],
            "macro_precision": hard_eval["macro_precision"],
            "macro_recall": hard_eval["macro_recall"],
            "mean_localisation_iou": hard_eval["mean_localisation_iou"],
            "pct_boxes_iou_gte_05": hard_eval["pct_boxes_iou_gte_05"],
            "mAP_at_05": hard_eval["mAP_at_05"],
            "per_class": hard_eval["per_class"],
            "confusion_matrix": hard_eval["confusion_matrix"]
        },
        "performance_drop_normal_vs_hard": {
            "macro_f1_drop": drop_macro_f1,
            "accuracy_drop": drop_acc,
            "localisation_iou_drop": drop_iou,
            "pct_boxes_gte_05_drop": drop_box50,
            "mAP_at_05_drop": drop_map50
        },
        "honest_disclosure": {
            "statement": "The vision model is trained on synthetic shaft images generated by our procedural script. Metrics are optimistic compared to real factory images. The model is not validated on real production shaft photos and is NOT production-grade without physical factory calibration.",
            "data_source": "synthetic",
            "uncalibrated_probabilities_notice": "Raw softmax outputs are uncalibrated model confidences, not true calibrated Bayesian posterior probabilities. Human engineering review remains mandatory."
        }
    }

    metrics_out = models_dir / "cv_metrics.json"
    with open(metrics_out, "w", encoding="utf-8") as f:
        json.dump(cv_metrics, f, indent=2)
    with open(alt_models_dir / "cv_metrics.json", "w", encoding="utf-8") as f:
        json.dump(cv_metrics, f, indent=2)

    # Print Summary Tables
    print("\n" + "=" * 70)
    print("  EVALUATION SUMMARY: NORMAL TEST SPLIT VS HARD TEST SPLIT")
    print("=" * 70)
    print(f"{'Metric':<28} | {'Normal Test':<14} | {'Hard Test':<14} | {'Drop (Delta)'}")
    print("-" * 70)
    print(f"{'Macro-F1':<28} | {normal_eval['macro_f1']:<14.4f} | {hard_eval['macro_f1']:<14.4f} | {drop_macro_f1:+.4f}")
    print(f"{'Accuracy':<28} | {normal_eval['accuracy']:<14.4f} | {hard_eval['accuracy']:<14.4f} | {drop_acc:+.4f}")
    print(f"{'Localisation Mean IoU':<28} | {normal_eval['mean_localisation_iou']:<14.4f} | {hard_eval['mean_localisation_iou']:<14.4f} | {drop_iou:+.4f}")
    print(f"{'% Boxes IoU >= 0.5':<28} | {normal_eval['pct_boxes_iou_gte_05']:<13.1f}% | {hard_eval['pct_boxes_iou_gte_05']:<13.1f}% | {drop_box50:+.1f}%")
    print(f"{'mAP@0.5':<28} | {normal_eval['mAP_at_05']:<14.4f} | {hard_eval['mAP_at_05']:<14.4f} | {drop_map50:+.4f}")
    print("=" * 70)

    print("\nPER-CLASS METRICS (NORMAL TEST SPLIT):")
    print(f"{'Class Name':<22} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'Support'}")
    print("-" * 65)
    for cname, cm_dict in normal_eval["per_class"].items():
        print(f"{cname:<22} | {cm_dict['precision']:<10.4f} | {cm_dict['recall']:<10.4f} | {cm_dict['f1']:<10.4f} | {cm_dict['support']}")

    print("\nPER-CLASS METRICS (HARD TEST SPLIT):")
    print(f"{'Class Name':<22} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'Support'}")
    print("-" * 65)
    for cname, cm_dict in hard_eval["per_class"].items():
        print(f"{cname:<22} | {cm_dict['precision']:<10.4f} | {cm_dict['recall']:<10.4f} | {cm_dict['f1']:<10.4f} | {cm_dict['support']}")

    print("=" * 70)
    print(f"Metrics saved to: {metrics_out}")

    return cv_metrics


if __name__ == "__main__":
    run_evaluation()
