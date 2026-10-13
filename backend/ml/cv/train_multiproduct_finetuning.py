"""
Multi-Product Defect Classifier and Visual Domain Recognition Engine
Fine-tuning transfer learning across 5 industrial product categories:
- precision_shaft (Primary manufactured part PS-2026-101)
- screw (MVTec AD fastener benchmark)
- metal_nut (MVTec AD hex fastener benchmark)
- cable (MVTec AD wiring harness benchmark)
- transistor (MVTec AD semiconductor benchmark)

Architecture: MobileNetV3-Small Backbone + Multi-Head Architecture:
1. Product Recognition Head: Visually classifies category (screw, nut, cable, etc.) directly from image pixels
2. Domain-Specific Defect Classification Heads: Predicts defect vs. conforming for each product
"""
import os
import sys
import json
import random
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, TensorDataset
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score

SEED = 42
torch.manual_seed(SEED)
random.seed(SEED)
np.random.seed(SEED)

PRODUCT_CATEGORIES = [
    "screw",
    "metal_nut",
    "cable",
    "transistor",
    "precision_shaft"
]

CATEGORY_TO_IDX = {cat: i for i, cat in enumerate(PRODUCT_CATEGORIES)}
IDX_TO_CATEGORY = {i: cat for i, cat in enumerate(PRODUCT_CATEGORIES)}

CATEGORY_CLASSES = {
    "screw": ["no_defect", "scratch_head", "thread_damage", "neck_dent"],
    "metal_nut": ["no_defect", "scratch", "bent", "color", "flip"],
    "cable": ["no_defect", "cut_inner_insulation", "bent_wire", "missing_wire", "cable_swap"],
    "transistor": ["no_defect", "damaged_case", "misplaced", "cut_lead", "bent_lead"],
    "precision_shaft": ["no_defect", "surface_scratch", "dent", "crack", "missing_feature", "incorrect_assembly"]
}

SCREW_DEFECT_MAP = {
    "good": "no_defect",
    "scratch_head": "scratch_head",
    "thread_side": "thread_damage",
    "thread_top": "thread_damage",
    "manipulated_front": "neck_dent",
    "scratch_neck": "neck_dent"
}

NUT_DEFECT_MAP = {
    "good": "no_defect",
    "scratch": "scratch",
    "bent": "bent",
    "color": "color",
    "flip": "flip"
}

CABLE_DEFECT_MAP = {
    "good": "no_defect",
    "cut_inner_insulation": "cut_inner_insulation",
    "cut_outer_insulation": "cut_inner_insulation",
    "poke_insulation": "cut_inner_insulation",
    "bent_wire": "bent_wire",
    "missing_wire": "missing_wire",
    "missing_cable": "missing_wire",
    "cable_swap": "cable_swap",
    "combined": "cut_inner_insulation"
}

TRANSISTOR_DEFECT_MAP = {
    "good": "no_defect",
    "damaged_case": "damaged_case",
    "misplaced": "misplaced",
    "cut_lead": "cut_lead",
    "bent_lead": "bent_lead"
}


def collect_dataset(mvtec_dir: Path, shaft_dir: Path) -> List[Dict[str, Any]]:
    records = []

    # 1. Collect MVTec categories
    for cat in ["screw", "metal_nut", "cable", "transistor"]:
        cat_path = mvtec_dir / cat
        if not cat_path.exists():
            continue

        # Train good
        train_good_dir = cat_path / "train" / "good"
        if train_good_dir.exists():
            for f in sorted(os.listdir(train_good_dir)):
                if f.endswith((".png", ".jpg")):
                    records.append({
                        "path": str(train_good_dir / f),
                        "product_category": cat,
                        "raw_defect": "good",
                        "defect_class": "no_defect"
                    })

        # Test good and defects
        test_dir = cat_path / "test"
        if test_dir.exists():
            for defect_folder in sorted(os.listdir(test_dir)):
                sub_p = test_dir / defect_folder
                if sub_p.is_dir() and defect_folder != "ground_truth":
                    if cat == "screw":
                        d_class = SCREW_DEFECT_MAP.get(defect_folder, "scratch_head")
                    elif cat == "metal_nut":
                        d_class = NUT_DEFECT_MAP.get(defect_folder, "scratch")
                    elif cat == "cable":
                        d_class = CABLE_DEFECT_MAP.get(defect_folder, "cut_inner_insulation")
                    elif cat == "transistor":
                        d_class = TRANSISTOR_DEFECT_MAP.get(defect_folder, "damaged_case")
                    else:
                        d_class = "no_defect"

                    for f in sorted(os.listdir(sub_p)):
                        if f.endswith((".png", ".jpg")):
                            records.append({
                                "path": str(sub_p / f),
                                "product_category": cat,
                                "raw_defect": defect_folder,
                                "defect_class": d_class
                            })

    # 2. Collect Synthetic Shafts
    shaft_sub = shaft_dir / "images"
    if shaft_sub.exists():
        shaft_files = sorted(os.listdir(shaft_sub))
        class_samples: Dict[str, List[str]] = {}
        for f in shaft_files:
            if not f.endswith(".png"):
                continue
            cls = "no_defect"
            for c in CATEGORY_CLASSES["precision_shaft"]:
                if c != "no_defect" and c in f:
                    cls = c
                    break
            class_samples.setdefault(cls, []).append(f)

        for cls, flist in class_samples.items():
            for f in flist[:80]:
                records.append({
                    "path": str(shaft_sub / f),
                    "product_category": "precision_shaft",
                    "raw_defect": cls,
                    "defect_class": cls
                })

    return records


class ImageListDataset(Dataset):
    def __init__(self, records: List[Dict[str, Any]], transform):
        self.records = records
        self.transform = transform

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx):
        r = self.records[idx]
        img = Image.open(r["path"]).convert("RGB")
        tensor = self.transform(img)
        return tensor, idx


class MultiProductModel(nn.Module):
    """
    MobileNetV3-Small backbone with two-stage multi-task heads:
    1. Product Recognition Head: classifies visual product domain (screw, nut, etc.)
    2. Category Defect Heads: specialized classifier for each product
    """
    def __init__(self, pretrained: bool = False):
        super().__init__()
        weights = models.MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
        base = models.mobilenet_v3_small(weights=weights)
        self.features = base.features
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        in_features = 576

        # Product Classifier Head
        self.product_head = nn.Sequential(
            nn.Linear(in_features, 256),
            nn.Hardswish(),
            nn.Dropout(p=0.2),
            nn.Linear(256, len(PRODUCT_CATEGORIES))
        )

        # Defect Classifier Heads
        self.defect_heads = nn.ModuleDict({
            cat: nn.Sequential(
                nn.Linear(in_features, 128),
                nn.Hardswish(),
                nn.Dropout(p=0.2),
                nn.Linear(128, len(classes))
            )
            for cat, classes in CATEGORY_CLASSES.items()
        })

    def forward(self, x: torch.Tensor, category: Optional[str] = None) -> Tuple[torch.Tensor, torch.Tensor, str]:
        feat = self.features(x)
        pooled = self.avgpool(feat)
        flat = torch.flatten(pooled, 1)

        product_logits = self.product_head(flat)
        if category is None or category not in self.defect_heads:
            pred_cat_idx = int(torch.argmax(product_logits, dim=1)[0].item())
            category = PRODUCT_CATEGORIES[pred_cat_idx]

        defect_logits = self.defect_heads[category](flat)
        return product_logits, defect_logits, category

    def extract_embedding(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.features(x)
        pooled = self.avgpool(feat)
        return torch.flatten(pooled, 1)


def train_fine_tuned_model():
    print("=" * 70)
    print("Starting Multi-Product Fine-Tuning Pipeline (QualityMind Engine)")
    print("=" * 70)

    mvtec_dir = Path("D:/Projects Local/BV-DATASETS/mvtec_anomaly_detection")
    shaft_dir = Path("d:/Projects Local/QT/data/synthetic_shafts")
    records = collect_dataset(mvtec_dir, shaft_dir)
    print(f"Total collected images: {len(records)}")

    # Split into Train, Val, Test (70/15/15 stratified)
    rng = random.Random(SEED)
    rng.shuffle(records)

    train_recs, val_recs, test_recs = [], [], []
    group_map: Dict[str, List[Dict[str, Any]]] = {}
    for r in records:
        k = f"{r['product_category']}:{r['defect_class']}"
        group_map.setdefault(k, []).append(r)

    for k, items in group_map.items():
        rng.shuffle(items)
        n = len(items)
        n_tr = max(1, int(round(n * 0.70)))
        n_vl = max(1, int(round(n * 0.15))) if n >= 4 else 0
        train_recs.extend(items[:n_tr])
        val_recs.extend(items[n_tr:n_tr + n_vl])
        test_recs.extend(items[n_tr + n_vl:])

    print(f"Dataset Split -> Train: {len(train_recs)} | Val: {len(val_recs)} | Test: {len(test_recs)}")

    device = torch.device("cpu")
    model = MultiProductModel(pretrained=True).to(device)
    model.eval()

    eval_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    print("\n[Phase 1] Extracting MobileNetV3-Small deep feature embeddings (batch extraction)...")
    start_feat = time.time()

    def extract_features_batched(recs, batch_size=32):
        dataset = ImageListDataset(recs, eval_transform)
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)
        feats_list = []
        with torch.no_grad():
            for batch_tensors, _ in loader:
                batch_tensors = batch_tensors.to(device)
                batch_feats = model.extract_embedding(batch_tensors).cpu()
                feats_list.append(batch_feats)
        all_feats = torch.cat(feats_list, dim=0)
        return all_feats

    X_train = extract_features_batched(train_recs, batch_size=32)
    X_val = extract_features_batched(val_recs, batch_size=32)
    X_test = extract_features_batched(test_recs, batch_size=32)
    print(f"Feature Extraction Complete in {time.time() - start_feat:.2f}s! (Tensors: X_train {X_train.shape}, X_test {X_test.shape})")

    # 2. Train Product Classifier Head
    print("\n[Phase 2] Fine-Tuning Visual Product Category Classifier Head...")
    y_train_prod = torch.tensor([CATEGORY_TO_IDX[r["product_category"]] for r in train_recs], dtype=torch.long)
    y_test_prod = torch.tensor([CATEGORY_TO_IDX[r["product_category"]] for r in test_recs], dtype=torch.long)

    prod_dataset = TensorDataset(X_train, y_train_prod)
    prod_loader = DataLoader(prod_dataset, batch_size=32, shuffle=True)

    prod_opt = optim.AdamW(model.product_head.parameters(), lr=2e-3, weight_decay=1e-4)
    criterion_prod = nn.CrossEntropyLoss()

    for epoch in range(25):
        model.product_head.train()
        total_loss = 0.0
        for bx, by in prod_loader:
            prod_opt.zero_grad()
            out = model.product_head(bx)
            loss = criterion_prod(out, by)
            loss.backward()
            prod_opt.step()
            total_loss += loss.item() * len(bx)
        if (epoch + 1) % 5 == 0:
            model.product_head.eval()
            with torch.no_grad():
                train_acc = (model.product_head(X_train).argmax(dim=1) == y_train_prod).float().mean()
                val_acc = (model.product_head(X_test).argmax(dim=1) == y_test_prod).float().mean()
            print(f"  Epoch {epoch+1:02d}/25 | Loss: {total_loss/len(X_train):.4f} | Train Acc: {train_acc*100:.2f}% | Test Acc: {val_acc*100:.2f}%")

    model.product_head.eval()
    with torch.no_grad():
        test_prod_preds = model.product_head(X_test).argmax(dim=1)
        prod_acc = (test_prod_preds == y_test_prod).float().mean().item()
    print(f"\n=> Visual Product Category Recognition Test Accuracy: {prod_acc*100:.2f}%")

    # 3. Train Category-Specific Defect Heads
    print("\n[Phase 3] Fine-Tuning Domain-Specific Defect Classification Heads...")
    defect_metrics = {}

    for cat in PRODUCT_CATEGORIES:
        head = model.defect_heads[cat]
        classes = CATEGORY_CLASSES[cat]
        cls_to_idx = {c: i for i, c in enumerate(classes)}

        train_indices = [i for i, r in enumerate(train_recs) if r["product_category"] == cat]
        test_indices = [i for i, r in enumerate(test_recs) if r["product_category"] == cat]

        if not train_indices or not test_indices:
            continue

        X_cat_train = X_train[train_indices]
        y_cat_train = torch.tensor([cls_to_idx[train_recs[i]["defect_class"]] for i in train_indices], dtype=torch.long)

        X_cat_test = X_test[test_indices]
        y_cat_test = torch.tensor([cls_to_idx[test_recs[i]["defect_class"]] for i in test_indices], dtype=torch.long)

        # Class weights to balance defect vs good
        class_counts = torch.bincount(y_cat_train, minlength=len(classes)).float()
        weights = 1.0 / torch.clamp(class_counts, min=1.0)
        weights = weights / weights.sum()

        optimizer = optim.AdamW(head.parameters(), lr=2e-3, weight_decay=1e-4)
        crit = nn.CrossEntropyLoss(weight=weights)

        cat_dataset = TensorDataset(X_cat_train, y_cat_train)
        cat_loader = DataLoader(cat_dataset, batch_size=16, shuffle=True)

        for epoch in range(30):
            head.train()
            for bx, by in cat_loader:
                optimizer.zero_grad()
                out = head(bx)
                loss = crit(out, by)
                loss.backward()
                optimizer.step()

        # Evaluate on Test Split
        head.eval()
        with torch.no_grad():
            preds = head(X_cat_test).argmax(dim=1).cpu().numpy()
            targets = y_cat_test.cpu().numpy()

        acc = np.mean(preds == targets)
        f1 = f1_score(targets, preds, average="weighted", zero_division=0)
        prec = precision_score(targets, preds, average="weighted", zero_division=0)
        rec = recall_score(targets, preds, average="weighted", zero_division=0)

        defect_metrics[cat] = {
            "accuracy": round(float(acc), 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
            "test_samples": len(test_indices)
        }
        print(f"  [{cat.upper():<15}] Accuracy: {acc*100:6.2f}% | F1: {f1:.4f} | Prec: {prec:.4f} | Rec: {rec:.4f} (Samples: {len(test_indices)})")

    # 4. Save Model Checkpoint
    output_model_path = Path("models/multiproduct_cv_model.pt")
    torch.save(model.state_dict(), output_model_path)
    print(f"\n[Saved] Multi-product model saved to: {output_model_path.resolve()}")

    meta = {
        "model_architecture": "MobileNetV3-Small Multi-Head Transfer Learning",
        "product_categories": PRODUCT_CATEGORIES,
        "category_classes": CATEGORY_CLASSES,
        "category_accuracy": round(float(prod_acc), 4),
        "metrics_by_category": defect_metrics,
        "trained_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    with open("models/multiproduct_classes.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    # 5. Direct Verification on the User's Real Images:
    print("\n" + "=" * 70)
    print("Testing Specifically on User Uploaded Test Cases (007.PNG & 001.PNG):")
    print("=" * 70)

    test_samples = [
        ("D:/Projects Local/BV-DATASETS/mvtec_anomaly_detection/screw/test/scratch_head/007.png", "007.PNG (Screw Defect: scratch_head)"),
        ("D:/Projects Local/BV-DATASETS/mvtec_anomaly_detection/screw/test/good/001.png", "001.PNG (Screw Conforming: good)"),
        ("D:/Projects Local/BV-DATASETS/mvtec_anomaly_detection/screw/test/thread_side/004.png", "004.PNG (Screw Defect: thread_side)"),
        ("D:/Projects Local/BV-DATASETS/mvtec_anomaly_detection/metal_nut/test/scratch/000.png", "000.PNG (Nut Defect: scratch)"),
        ("D:/Projects Local/BV-DATASETS/mvtec_anomaly_detection/metal_nut/test/good/000.png", "000.PNG (Nut Conforming: good)"),
        ("D:/Projects Local/BV-DATASETS/mvtec_anomaly_detection/cable/test/cut_inner_insulation/000.png", "000.PNG (Cable Defect: cut_inner_insulation)"),
        ("D:/Projects Local/BV-DATASETS/mvtec_anomaly_detection/transistor/test/damaged_case/009.png", "009.PNG (Transistor Defect: damaged_case)")
    ]

    model.eval()
    for p, desc in test_samples:
        if not os.path.exists(p):
            continue
        img = Image.open(p).convert("RGB")
        tensor = eval_transform(img).unsqueeze(0).to(device)
        with torch.no_grad():
            prod_logits, def_logits, pred_cat = model(tensor)
            prod_prob = float(torch.softmax(prod_logits, dim=1).max())
            def_probs = torch.softmax(def_logits, dim=1).squeeze(0)
            pred_def_idx = int(torch.argmax(def_probs).item())
            def_prob = float(def_probs[pred_def_idx])
            pred_def_class = CATEGORY_CLASSES[pred_cat][pred_def_idx]

        is_defect = pred_def_class != "no_defect"
        print(f"File: {os.path.basename(p):<10} | Target: {desc:<40} => Category: {pred_cat.upper():<15} ({prod_prob*100:.1f}%) | Defect: {pred_def_class:<20} ({def_prob*100:.1f}%) | Defect Detected: {is_defect}")

    print("\nFine-Tuning pipeline completed successfully.")


if __name__ == "__main__":
    train_fine_tuned_model()
