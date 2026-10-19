import os
import torch
import torch.nn as nn

class LightweightYOLOHead(nn.Module):
    def __init__(self, num_classes=6):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 16, kernel_size=3, stride=2, padding=1)
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, stride=2, padding=1)
        self.conv3 = nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1)
        self.pool = nn.AdaptiveAvgPool2d((1, 8400))
        self.head = nn.Conv1d(64, 4 + num_classes, kernel_size=1)

    def forward(self, x):
        feat = self.conv1(x)
        feat = self.conv2(feat)
        feat = self.conv3(feat)
        feat = self.pool(feat).squeeze(2)
        out = self.head(feat)
        return out

class LightweightClassifier(nn.Module):
    def __init__(self, num_classes=5):
        super().__init__()
        self.backbone = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(16, 32, 3, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((4, 4))
        )
        self.fc = nn.Linear(32 * 4 * 4, num_classes)

    def forward(self, x):
        x = self.backbone(x)
        x = torch.flatten(x, 1)
        return self.fc(x)

def main():
    models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "models"))
    os.makedirs(models_dir, exist_ok=True)

    yolo_path = os.path.join(models_dir, "yolo_model.onnx")
    print(f"Exporting YOLO ONNX to {yolo_path}...")
    yolo_model = LightweightYOLOHead(num_classes=6).eval()
    dummy_yolo = torch.randn(1, 3, 512, 512)
    torch.onnx.export(
        yolo_model,
        dummy_yolo,
        yolo_path,
        input_names=["images"],
        output_names=["output0"],
        opset_version=17
    )
    print(f"✓ Created {yolo_path} ({os.path.getsize(yolo_path)} bytes)")

    cv_path = os.path.join(models_dir, "cv_model.onnx")
    print(f"Exporting CV Classifier ONNX to {cv_path}...")
    cv_model = LightweightClassifier(num_classes=5).eval()
    dummy_cv = torch.randn(1, 3, 224, 224)
    torch.onnx.export(
        cv_model,
        dummy_cv,
        cv_path,
        input_names=["input"],
        output_names=["output"],
        opset_version=17
    )
    print(f"✓ Created {cv_path} ({os.path.getsize(cv_path)} bytes)")

if __name__ == "__main__":
    main()
