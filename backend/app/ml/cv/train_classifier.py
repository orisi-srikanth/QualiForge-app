"""
Stage B Defect Classifier training module alias.
"""
from ml.cv.train_classifier import (
    DefectClassifier,
    GradCAM,
    train_classifier,
    UNIFIED_CLASSES,
    CLASS_TO_IDX,
    IDX_TO_CLASS
)

if __name__ == "__main__":
    train_classifier()
