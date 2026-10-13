"""
Grad-CAM Explainability & Defect Localisation Module
Computes Class Activation Maps from convolutional layers to produce visual heatmaps
and derive defect bounding boxes for explainable AI decision support.
"""
import cv2
import numpy as np
import torch
import torch.nn.functional as F

class GradCAM:
    def __init__(self, model: torch.nn.Module, target_layer: torch.nn.Module):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None
        self._register_hooks()

    def _register_hooks(self):
        def forward_hook(module, input, output):
            self.activations = output

        def backward_hook(module, grad_in, grad_out):
            self.gradients = grad_out[0]

        self.target_layer.register_forward_hook(forward_hook)
        self.target_layer.register_full_backward_hook(backward_hook)

    def generate_heatmap(self, input_tensor: torch.Tensor, class_idx: int) -> np.ndarray:
        """Generates normalized [0, 1] 2D Grad-CAM heatmap."""
        self.model.eval()
        output = self.model(input_tensor)
        self.model.zero_grad()

        score = output[0, class_idx]
        score.backward(retain_graph=True)

        gradients = self.gradients.cpu().data.numpy()[0]
        activations = self.activations.cpu().data.numpy()[0]

        weights = np.mean(gradients, axis=(1, 2))
        cam = np.zeros(activations.shape[1:], dtype=np.float32)

        for i, w in enumerate(weights):
            cam += w * activations[i]

        cam = np.maximum(cam, 0)
        if np.max(cam) > 0:
            cam = cam / np.max(cam)
        return cam

    @staticmethod
    def overlay_heatmap(image: np.ndarray, heatmap: np.ndarray, alpha: float = 0.4) -> np.ndarray:
        """Overlays Grad-CAM heatmap on original BGR image using COLORMAP_JET."""
        h, w = image.shape[:2]
        resized_heatmap = cv2.resize(heatmap, (w, h))
        colored_heatmap = cv2.applyColorMap(np.uint8(255 * resized_heatmap), cv2.COLORMAP_JET)
        overlay = cv2.addWeighted(colored_heatmap, alpha, image, 1 - alpha, 0)
        return overlay

    @staticmethod
    def derive_bounding_box(heatmap: np.ndarray, threshold: float = 0.45) -> tuple:
        """Derives [x, y, w, h] bounding box from peak activation region in heatmap."""
        binary = (heatmap > threshold).astype(np.uint8) * 255
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        largest_cnt = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_cnt)
        return (x, y, w, h)
