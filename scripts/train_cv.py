import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.cv.build_manifest import build_manifest
from ml.cv.make_splits import make_splits
from ml.cv.train_patchcore import train_patchcore
from ml.cv.train_classifier import train_classifier
from ml.cv.evaluate import evaluate_pipeline

def main():
    print("=" * 70)
    print("  QUALITYMIND: MVTEC AD COMPUTER VISION TRAINING & EVALUATION PIPELINE")
    print("=" * 70)
    t_start = time.time()

    print("\n[Step 1/5] Building MVTec Manifest (4 Allowed Categories)...")
    build_manifest()

    print("\n[Step 2/5] Creating Stratified Splits with Zero-Leakage Assertion...")
    make_splits()

    print("\n[Step 3/5] Training Stage A PatchCore Anomaly Detector...")
    train_patchcore()

    print("\n[Step 4/5] Training Stage B Defect Classifier & Exporting ONNX...")
    train_classifier()

    print("\n[Step 5/5] Evaluating Honestly on Held-Out Test Split...")
    evaluate_pipeline()

    elapsed = time.time() - t_start
    print("\n" + "=" * 70)
    print(f"PIPELINE COMPLETED SUCCESSFULLY IN {elapsed:.2f} SECONDS.")
    print("=" * 70)

if __name__ == "__main__":
    main()
