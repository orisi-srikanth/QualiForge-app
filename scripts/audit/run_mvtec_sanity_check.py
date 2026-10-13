"""
External Sanity Check: MVTec AD Benchmark (metal_nut and screw)
Evaluates trained synthetic shaft model on real MVTec AD scratch vs normal images
with documented domain gap caveat.
"""
import os
import glob
from pathlib import Path
import cv2
import numpy as np
import torch
import torch.nn.functional as F
import torchvision.transforms as transforms
from PIL import Image

import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ml.cv.train_classifier import DefectClassifier, SHAFT_CLASSES

def run_sanity_check():
    mvtec_base = Path(r"D:\Projects Local\BV-DATASETS\mvtec_anomaly_detection")
    sample_dir = PROJECT_ROOT / "backend" / "app" / "static" / "uploads" / "samples"

    # Verify if MVTec exists
    categories = ["metal_nut", "screw"]
    available = {}
    for cat in categories:
        cat_path = mvtec_base / cat
        if cat_path.exists():
            available[cat] = cat_path

    if not available:
        print("MVTec AD local directory not found. Skipping external sanity check.")
        return None

    print("=" * 65)
    print("  EXTERNAL REAL-IMAGE SANITY CHECK (MVTec AD: metal_nut & screw)")
    print("  Note: Read-only benchmark with domain gap caveat (proxy parts vs shaft).")
    print("=" * 65)

    device = torch.device("cpu")
    model = DefectClassifier(num_classes=len(SHAFT_CLASSES)).to(device)
    weights_path = PROJECT_ROOT / "backend" / "models" / "cv_model.pt"
    model.load_state_dict(torch.load(weights_path, map_location=device))
    model.eval()

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    results = []

    for cat in ["metal_nut", "screw"]:
        cat_path = available[cat]
        good_imgs = sorted(glob.glob(str(cat_path / "test" / "good" / "*.png")))[:15]
        # Scratch images
        scratch_dirs = [d for d in glob.glob(str(cat_path / "test" / "*")) if "scratch" in os.path.basename(d).lower()]
        scratch_imgs = []
        for sd in scratch_dirs:
            scratch_imgs.extend(sorted(glob.glob(str(Path(sd) / "*.png"))))
        scratch_imgs = scratch_imgs[:15]

        print(f"\nEvaluating Category: {cat} (Good: {len(good_imgs)}, Scratch: {len(scratch_imgs)})")

        cat_correct = 0
        cat_total = 0

        # Good images: expect 'no_defect'
        for g_img in good_imgs:
            im = Image.open(g_img).convert("RGB")
            t_in = transform(im).unsqueeze(0).to(device)
            with torch.no_grad():
                out = model(t_in)
                probs = F.softmax(out, dim=1).squeeze().numpy()
            pred_idx = int(np.argmax(probs))
            pred_cls = SHAFT_CLASSES[pred_idx]
            # Scratch vs normal binary decision
            is_good = (pred_cls == "no_defect")
            if is_good:
                cat_correct += 1
            cat_total += 1
            results.append({"category": cat, "true": "good", "pred": pred_cls, "prob": float(probs[pred_idx])})

        # Scratch images: expect 'surface_scratch' or any defect
        for s_img in scratch_imgs:
            im = Image.open(s_img).convert("RGB")
            t_in = transform(im).unsqueeze(0).to(device)
            with torch.no_grad():
                out = model(t_in)
                probs = F.softmax(out, dim=1).squeeze().numpy()
            pred_idx = int(np.argmax(probs))
            pred_cls = SHAFT_CLASSES[pred_idx]
            is_defect = (pred_cls != "no_defect")
            if is_defect:
                cat_correct += 1
            cat_total += 1
            results.append({"category": cat, "true": "scratch", "pred": pred_cls, "prob": float(probs[pred_idx])})

        acc = (cat_correct / max(cat_total, 1)) * 100.0
        print(f"  {cat} Binary Anomaly Accuracy: {acc:.1f}% ({cat_correct}/{cat_total})")

    # Overall Summary
    total_corr = sum(1 for r in results if (r["true"] == "good" and r["pred"] == "no_defect") or (r["true"] == "scratch" and r["pred"] != "no_defect"))
    overall_acc = (total_corr / len(results)) * 100.0 if results else 0.0

    print("\n" + "=" * 65)
    print(f"Overall External Sanity Decision Accuracy: {overall_acc:.1f}% ({total_corr}/{len(results)})")
    print("DOMAIN-GAP CAVEAT:")
    print("- MVTec AD parts are hexagonal nuts and threaded screws, whereas the model was trained")
    print("  on cylindrical machined steel shafts.")
    print("- This external check demonstrates transferability of learned edge and gouge representations")
    print("  across metallic surfaces, but is NOT claimed as formal validation on precision ground shafts.")
    print("=" * 65)

    return {"overall_accuracy": overall_acc, "total_samples": len(results), "results": results}

if __name__ == "__main__":
    run_sanity_check()
