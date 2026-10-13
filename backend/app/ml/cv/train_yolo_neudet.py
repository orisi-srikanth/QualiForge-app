"""
YOLO26 Surface Defect Training & ONNX Export Script (NEU-DET Dataset)
Designed for free-tier Google Colab (T4 GPU) or Kaggle GPU.
Trains Ultralytics YOLO26 (AGPL-3.0 license) on NEU surface defect benchmarks
and exports an optimized, lightweight ONNX model for CPU deployment on Render (<512 MB RAM).
"""
import os
import sys
import yaml
import argparse
from pathlib import Path

# NEU-DET Defect Classes
NEU_CLASSES = [
    "crazing",
    "inclusion",
    "patches",
    "pitted_surface",
    "rolled-in_scale",
    "scratches"
]

def generate_neu_yaml(output_dir: str = "./data/neu_det") -> str:
    """Generates the Ultralytics dataset configuration file for NEU-DET."""
    os.makedirs(output_dir, exist_ok=True)
    yaml_path = os.path.join(output_dir, "neu_det.yaml")
    
    data_config = {
        "path": os.path.abspath(output_dir),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {i: name for i, name in enumerate(NEU_CLASSES)}
    }
    
    with open(yaml_path, "w") as f:
        yaml.dump(data_config, f, default_flow_style=False)
        
    print(f"[YOLO26 Train] Created dataset config: {yaml_path}")
    return yaml_path

def train_yolo_model(
    data_yaml: str,
    epochs: int = 50,
    imgsz: int = 512,
    batch: int = 16,
    weights: str = "yolo26n.pt",
    output_onnx: str = "./backend/models/yolo_model.onnx"
):
    """
    Trains Ultralytics YOLO26 on NEU-DET and exports to ONNX.
    Note: Requires 'pip install ultralytics' in a GPU environment (Colab/Kaggle).
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[Error] 'ultralytics' is required for training. Please run in Colab/Kaggle:")
        print("        pip install ultralytics")
        return False

    print("=" * 70)
    print(" TRAINING YOLO26 ON NEU SURFACE DEFECT BENCHMARK (AGPL-3.0)")
    print("=" * 70)

    # 1. Load pretrained YOLO26 Nano architecture for lightweight inference
    model = YOLO(weights)

    # 2. Train on dataset
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=0, # GPU
        save=True,
        project="neu_defect_yolo",
        name="yolo26_surface",
        optimizer="AdamW",
        lr0=0.001,
        cos_lr=True
    )

    print("\n[YOLO26 Train] Training complete. Exporting to ONNX for 512 MB Render deployment...")
    
    # 3. Export to ONNX format (dynamic=False, opset=17, simplify=True)
    os.makedirs(os.path.dirname(output_onnx), exist_ok=True)
    onnx_path = model.export(
        format="onnx",
        imgsz=imgsz,
        dynamic=False,
        simplify=True,
        opset=17
    )

    # Copy / rename to target model path
    if os.path.exists(onnx_path):
        import shutil
        shutil.copy(onnx_path, output_onnx)
        print(f"[YOLO26 Train] Successfully saved lightweight ONNX model to: {output_onnx}")
        return True
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train YOLO26 on NEU-DET")
    parser.add_argument("--epochs", type=int, default=50, help="Training epochs")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--imgsz", type=int, default=512, help="Image resolution")
    args = parser.parse_args()

    yaml_file = generate_neu_yaml()
    train_yolo_model(yaml_file, epochs=args.epochs, batch=args.batch, imgsz=args.imgsz)
