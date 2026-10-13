"""
MVTec AD Dataset Manifest Builder for QualityMind
Alias module pointing to root ml/cv/build_manifest.py
"""
from ml.cv.build_manifest import build_manifest, get_mvtec_root, load_label_map, ALLOWED_CATEGORIES

if __name__ == "__main__":
    build_manifest()
