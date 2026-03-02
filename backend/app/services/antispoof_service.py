"""
Passive Anti-Spoof Service — ONNX CNN + Texture Fallback.
==========================================================
Detects printed photos, screen replays, and flat/2D faces.

Flow:
  1. If ONNX model is available → run CNN inference
  2. Otherwise → fallback to texture analysis (LBP variance + Laplacian)

Must run BEFORE embedding generation. On spoof detection, logs a security event.
"""

import logging
import os
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

ONNX_AVAILABLE = False
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    logger.warning("onnxruntime not installed — anti-spoof will use texture fallback only")


class AntiSpoofService:
    """
    Passive liveness detection to reject spoofing attacks.
    
    Two modes:
      1. ONNX CNN model (if model path is provided and valid)
      2. Texture-based fallback (LBP variance + Laplacian sharpness)
    """

    def __init__(self, model_path: str = "", threshold: float = 0.5):
        """
        Args:
            model_path: Path to the anti-spoof ONNX model file
            threshold: Score threshold — above = real, below = spoof
        """
        self._model_path = model_path
        self._threshold = threshold
        self._session: Optional[ort.InferenceSession] = None
        self._mode = "none"
        self._input_name = None
        self._input_shape = None

        self._try_load_model()

    def _try_load_model(self):
        """Attempt to load the ONNX anti-spoof model."""
        if not self._model_path or not os.path.exists(self._model_path):
            if self._model_path:
                logger.warning(f"Anti-spoof model not found at: {self._model_path}")
            self._mode = "texture"
            logger.info("Anti-spoof: using texture analysis fallback (LBP + Laplacian)")
            return

        if not ONNX_AVAILABLE:
            self._mode = "texture"
            logger.warning("onnxruntime not available — falling back to texture analysis")
            return

        try:
            self._session = ort.InferenceSession(
                self._model_path,
                providers=["CPUExecutionProvider"],
            )
            self._input_name = self._session.get_inputs()[0].name
            self._input_shape = self._session.get_inputs()[0].shape
            self._mode = "onnx"
            logger.info(f"Anti-spoof ONNX model loaded: {self._model_path}")
            logger.info(f"  Input: {self._input_name}, shape: {self._input_shape}")
        except Exception as e:
            logger.error(f"Failed to load anti-spoof model: {e}")
            self._mode = "texture"

    def check(self, face_crop: np.ndarray) -> Tuple[bool, float, str]:
        """
        Check if a face crop is a real face or a spoof.
        
        Args:
            face_crop: BGR OpenCV image of the cropped face region
            
        Returns:
            (is_real, score, reason)
            - is_real: True if the face appears genuine
            - score: Confidence score (0-1, higher = more likely real)
            - reason: Human-readable explanation
        """
        if face_crop is None or face_crop.size == 0:
            return False, 0.0, "No face crop provided"

        if self._mode == "onnx":
            return self._check_onnx(face_crop)
        else:
            return self._check_texture(face_crop)

    def _check_onnx(self, face_crop: np.ndarray) -> Tuple[bool, float, str]:
        """Run the ONNX anti-spoof model."""
        try:
            # Preprocess: resize to model input size
            h, w = self._input_shape[2], self._input_shape[3]
            img = cv2.resize(face_crop, (w, h))
            img = img.astype(np.float32) / 255.0
            # Normalize with ImageNet mean/std
            mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
            std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
            img = (img - mean) / std
            # HWC → NCHW
            img = np.transpose(img, (2, 0, 1))
            img = np.expand_dims(img, axis=0)

            outputs = self._session.run(None, {self._input_name: img})
            # Assume sigmoid output: probability of being real
            score = float(outputs[0][0][0]) if len(outputs[0].shape) > 1 else float(outputs[0][0])

            # Apply softmax if output has 2 classes
            if len(outputs[0].shape) > 1 and outputs[0].shape[1] == 2:
                logits = outputs[0][0]
                exp_logits = np.exp(logits - np.max(logits))
                probs = exp_logits / exp_logits.sum()
                score = float(probs[1])  # Index 1 = real

            is_real = score >= self._threshold
            reason = "passed" if is_real else "Spoof detected by anti-spoof model"
            return is_real, score, reason

        except Exception as e:
            logger.error(f"ONNX anti-spoof inference error: {e}")
            # Fall back to texture on error
            return self._check_texture(face_crop)

    def _check_texture(self, face_crop: np.ndarray) -> Tuple[bool, float, str]:
        """
        Texture-based anti-spoof fallback using:
          1. Laplacian variance (sharpness / focus quality)
          2. LBP (Local Binary Pattern) variance (texture richness)
          3. Color diversity analysis
        
        Printed photos and screen replays tend to have:
          - Lower sharpness (Laplacian)
          - More uniform texture (low LBP variance)
          - Reduced color channel diversity
        """
        try:
            gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape

            # Ensure minimum size
            if h < 30 or w < 30:
                return False, 0.1, "Face crop too small for analysis"

            # 1. Laplacian variance (focus / sharpness)
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            lap_var = float(laplacian.var())

            # 2. LBP-like texture variance
            # Compute local differences (simplified LBP)
            padded = cv2.copyMakeBorder(gray, 1, 1, 1, 1, cv2.BORDER_REFLECT)
            center = padded[1:-1, 1:-1].astype(np.float32)
            neighbors = [
                padded[0:-2, 0:-2], padded[0:-2, 1:-1], padded[0:-2, 2:],
                padded[1:-1, 0:-2],                      padded[1:-1, 2:],
                padded[2:, 0:-2],   padded[2:, 1:-1],    padded[2:, 2:],
            ]
            lbp_code = sum(
                (1 << i) * (n.astype(np.float32) >= center).astype(np.float32)
                for i, n in enumerate(neighbors)
            )
            lbp_var = float(lbp_code.var())

            # 3. Color channel standard deviation
            b_std = float(face_crop[:, :, 0].std())
            g_std = float(face_crop[:, :, 1].std())
            r_std = float(face_crop[:, :, 2].std())
            color_richness = (b_std + g_std + r_std) / 3.0

            # Scoring heuristic
            # Real faces: higher laplacian (>50), higher LBP var (>500), richer color
            lap_score = min(lap_var / 100.0, 1.0)          # Normalize: 100+ → 1.0
            lbp_score = min(lbp_var / 2000.0, 1.0)         # Normalize: 2000+ → 1.0
            color_score = min(color_richness / 50.0, 1.0)   # Normalize: 50+ → 1.0

            # Weighted combination
            score = 0.4 * lap_score + 0.35 * lbp_score + 0.25 * color_score
            score = max(0.0, min(1.0, score))

            is_real = score >= self._threshold
            reason = "passed" if is_real else (
                f"Possible spoof: low texture quality "
                f"(laplacian={lap_var:.1f}, lbp={lbp_var:.1f}, color={color_richness:.1f})"
            )

            logger.info(
                f"Texture anti-spoof: lap={lap_var:.1f} lbp={lbp_var:.1f} "
                f"color={color_richness:.1f} → score={score:.3f} → {'REAL' if is_real else 'SPOOF'}"
            )
            return is_real, score, reason

        except Exception as e:
            logger.error(f"Texture anti-spoof error: {e}")
            # On error, allow through but flag it
            return True, 0.5, f"Anti-spoof analysis error: {e}"

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def info(self) -> dict:
        return {
            "mode": self._mode,
            "model_path": self._model_path or "none",
            "threshold": self._threshold,
            "onnx_available": ONNX_AVAILABLE,
        }


# ============================================================
# Singleton
# ============================================================

_service: Optional[AntiSpoofService] = None


def get_antispoof_service() -> AntiSpoofService:
    """Get or create the singleton anti-spoof service."""
    global _service
    if _service is None:
        from app.core.config import get_settings
        settings = get_settings()
        model_path = getattr(settings, "ANTISPOOF_MODEL_PATH", "")
        threshold = getattr(settings, "ANTISPOOF_THRESHOLD", 0.5)
        _service = AntiSpoofService(model_path=model_path, threshold=threshold)
    return _service
