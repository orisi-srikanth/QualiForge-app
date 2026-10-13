"""
Stage A: PatchCore Anomaly Detection and Localization for MVTec AD
Builds a patch memory bank per category ONLY from train/good images.
Calibrates image and pixel thresholds using held-out validation normal and defect samples.
Saves memory bank to backend/models/patchcore_banks.pt and thresholds to backend/models/thresholds.json.
"""
import os
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
from sklearn.metrics import roc_auc_score, precision_recall_curve

CATEGORIES = ["metal_nut", "screw", "transistor", "cable"]

class FeatureExtractor(nn.Module):
    """Extracts multiscale patch feature representations from intermediate ResNet18 layers."""
    def __init__(self):
        super().__init__()
        resnet = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
        self.conv1 = resnet.conv1
        self.bn1 = resnet.bn1
        self.relu = resnet.relu
        self.maxpool = resnet.maxpool
        self.layer1 = resnet.layer1
        self.layer2 = resnet.layer2  # (B, 128, H/8, W/8)
        self.layer3 = resnet.layer3  # (B, 256, H/16, W/16)
        self.eval()
        for p in self.parameters():
            p.requires_grad = False

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        x = self.layer1(x)
        f1 = self.layer2(x) # 128 channels
        f2 = self.layer3(f1) # 256 channels

        # Resize f2 to match f1 spatial dimensions
        f2_up = F.interpolate(f2, size=f1.shape[-2:], mode="bilinear", align_corners=False)
        # Concatenate patch features -> 384 channels
        feats = torch.cat([f1, f2_up], dim=1)
        # Neighborhood smoothing via average pooling (3x3)
        feats = F.avg_pool2d(feats, kernel_size=3, stride=1, padding=1)
        return feats

class PatchCoreModel:
    def __init__(self, device: str = "cpu"):
        self.device = torch.device(device)
        self.extractor = FeatureExtractor().to(self.device)
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        self.memory_banks: Dict[str, torch.Tensor] = {}
        self.thresholds: Dict[str, Dict[str, float]] = {}

    def extract_patch_features(self, img_path: str) -> torch.Tensor:
        """Returns patch features shaped (H*W, D) where D=384."""
        img = Image.open(img_path).convert("RGB")
        tensor = self.transform(img).unsqueeze(0).to(self.device)
        with torch.no_grad():
            feat_map = self.extractor(tensor) # (1, D, H_f, W_f)
            B, D, H_f, W_f = feat_map.shape
            patches = feat_map.permute(0, 2, 3, 1).reshape(-1, D)
            # L2 normalize patches
            patches = F.normalize(patches, p=2, dim=1)
        return patches.cpu()

    def build_memory_bank(self, image_paths: List[str], subsample_rate: float = 0.05, max_patches: int = 1500) -> torch.Tensor:
        """Collects patch embeddings from normal images and extracts representative coreset."""
        all_patches = []
        for p in image_paths:
            patches = self.extract_patch_features(p)
            # Sample subset per image to conserve memory
            n_sample = max(10, int(len(patches) * subsample_rate))
            idx = torch.randperm(len(patches))[:n_sample]
            all_patches.append(patches[idx])

        bank = torch.cat(all_patches, dim=0)
        # Further downsample if larger than max_patches
        if len(bank) > max_patches:
            idx = torch.randperm(len(bank))[:max_patches]
            bank = bank[idx]
        return bank

    def compute_anomaly_map(self, img_path: str, category: str) -> Tuple[float, np.ndarray, List[Dict[str, int]]]:
        """
        Computes anomaly score, smoothed heatmap (224x224), and bounding boxes for an image.
        """
        if category not in self.memory_banks:
            raise ValueError(f"Category '{category}' has no memory bank.")

        bank = self.memory_banks[category].to(self.device)
        img = Image.open(img_path).convert("RGB")
        w_orig, h_orig = img.size
        tensor = self.transform(img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            feat_map = self.extractor(tensor) # (1, D, 28, 28)
            B, D, H_f, W_f = feat_map.shape
            patches = feat_map.permute(0, 2, 3, 1).reshape(-1, D)
            patches = F.normalize(patches, p=2, dim=1)

            # Compute pairwise Euclidean distance to nearest neighbor in bank
            # ||p - m||^2 = ||p||^2 + ||m||^2 - 2 p.m = 2 - 2 p.m (for normalized vectors)
            sim = torch.mm(patches, bank.t()) # (H_f*W_f, N_bank)
            max_sim, _ = sim.max(dim=1)
            dist = torch.sqrt(torch.clamp(2.0 - 2.0 * max_sim, min=0.0))

            dist_map = dist.reshape(H_f, W_f).cpu().numpy()

        # Gaussian smoothing
        dist_map_smooth = cv2.GaussianBlur(dist_map, (5, 5), sigmaX=2.0)
        # Upsample to 224x224
        heatmap_224 = cv2.resize(dist_map_smooth, (224, 224), interpolation=cv2.INTER_LINEAR)

        # Image anomaly score: top 1% mean anomaly score
        top_k = max(1, int(len(dist) * 0.01))
        top_scores, _ = torch.topk(dist, top_k)
        image_score = float(top_scores.mean().item())

        # Extract bounding boxes based on category pixel threshold
        thresh = self.thresholds.get(category, {}).get("pixel_threshold", 0.55)
        binary_mask = (heatmap_224 >= thresh).astype(np.uint8) * 255
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        bboxes = []
        scale_x = w_orig / 224.0
        scale_y = h_orig / 224.0

        for c in contours:
            if cv2.contourArea(c) >= 15: # Filter tiny pixel noise
                x, y, w, h = cv2.boundingRect(c)
                # Map bbox back to original image dimensions
                bx = int(max(0, x * scale_x))
                by = int(max(0, y * scale_y))
                bw = int(min(w_orig - bx, w * scale_x))
                bh = int(min(h_orig - by, h * scale_y))
                bboxes.append({"x": bx, "y": by, "width": bw, "height": bh})

        # Resize heatmap to original image dimensions for visualization/overlay
        heatmap_orig = cv2.resize(heatmap_224, (w_orig, h_orig), interpolation=cv2.INTER_LINEAR)
        return image_score, heatmap_orig, bboxes

def train_patchcore(splits_path: Path = None, output_dir: Path = None) -> PatchCoreModel:
    project_root = Path(__file__).resolve().parent.parent.parent
    if splits_path is None:
        splits_path = project_root / "data" / "splits.json"
    if output_dir is None:
        output_dir = project_root / "backend" / "models"

    output_dir.mkdir(parents=True, exist_ok=True)
    alt_models_dir = project_root / "models"
    alt_models_dir.mkdir(parents=True, exist_ok=True)

    with open(splits_path, "r", encoding="utf-8") as f:
        splits_data = json.load(f)

    train_records = splits_data["train"]
    val_records = splits_data["val"]

    model = PatchCoreModel(device="cpu")
    print("\n" + "=" * 65)
    print("STAGE A: Training PatchCore Anomaly Detector on Real MVTec AD")
    print("=" * 65)

    # 1. Build Memory Bank per Category from train/good ONLY
    for cat in CATEGORIES:
        normal_train = [r["path"] for r in train_records if r["category"] == cat and r["unified_type"] == "no_defect"]
        print(f"[{cat}] Building patch memory bank from {len(normal_train)} train/good images...")
        t0 = time.time()
        bank = model.build_memory_bank(normal_train, subsample_rate=0.08, max_patches=1600)
        model.memory_banks[cat] = bank
        elapsed = time.time() - t0
        print(f"[{cat}] Memory bank shape: {list(bank.shape)} constructed in {elapsed:.2f}s")

    # 2. Calibrate Thresholds using Val Split
    print("\nCalibrating Image and Pixel Thresholds on Held-out Validation Split...")
    thresholds_dict = {}

    for cat in CATEGORIES:
        val_cat = [r for r in val_records if r["category"] == cat]
        scores = []
        labels = [] # 0 = normal, 1 = defect

        for r in val_cat:
            is_defect = 0 if r["unified_type"] == "no_defect" else 1
            labels.append(is_defect)
            score, _, _ = model.compute_anomaly_map(r["path"], cat)
            scores.append(score)

        scores = np.array(scores)
        labels = np.array(labels)

        # Calibrate optimal threshold: maximize F1 on validation
        precisions, recalls, candidate_thresholds = precision_recall_curve(labels, scores)
        f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-8)
        best_idx = np.argmax(f1_scores)
        
        # If perfect or boundary, select high-precision threshold
        if best_idx < len(candidate_thresholds):
            best_thresh = float(candidate_thresholds[best_idx])
        else:
            best_thresh = float(np.percentile(scores[labels == 0], 95) + 0.05)

        normal_scores = scores[labels == 0]
        mean_normal = float(np.mean(normal_scores))
        std_normal = float(np.std(normal_scores))

        # Safe image threshold: at least mean + 2.5 * std of normal scores
        calibrated_img_thresh = max(best_thresh, mean_normal + 2.5 * std_normal)
        pixel_thresh = calibrated_img_thresh * 0.90

        thresholds_dict[cat] = {
            "image_threshold": round(calibrated_img_thresh, 4),
            "pixel_threshold": round(pixel_thresh, 4),
            "mean_normal_score": round(mean_normal, 4),
            "std_normal_score": round(std_normal, 4),
            "val_auroc": round(float(roc_auc_score(labels, scores)), 4) if len(np.unique(labels)) > 1 else 1.0,
            "best_val_f1": round(float(f1_scores[best_idx]), 4)
        }
        print(f"  [{cat:<12}] Img Thresh: {calibrated_img_thresh:.4f} | Pixel Thresh: {pixel_thresh:.4f} | Val AUROC: {thresholds_dict[cat]['val_auroc']:.4f}")

    model.thresholds = thresholds_dict

    # 3. Save Artifacts
    banks_save_path = output_dir / "patchcore_banks.pt"
    torch.save(model.memory_banks, banks_save_path)

    thresh_save_path = output_dir / "thresholds.json"
    with open(thresh_save_path, "w", encoding="utf-8") as f:
        json.dump(thresholds_dict, f, indent=2)

    # Mirror to models/thresholds.json
    with open(alt_models_dir / "thresholds.json", "w", encoding="utf-8") as f:
        json.dump(thresholds_dict, f, indent=2)

    print(f"\nSaved PatchCore memory banks to: {banks_save_path}")
    print(f"Saved calibrated thresholds to:  {thresh_save_path}")
    print("Stage A PatchCore Training Complete!")

    return model

if __name__ == "__main__":
    train_patchcore()
