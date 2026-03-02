"""
InsightFace Engine — RetinaFace Detection + ArcFace Recognition.
================================================================
Uses InsightFace FaceAnalysis with buffalo_l model for:
  - Face Detection (RetinaFace)
  - 512-d Face Embedding (ArcFace)
  - CPU-optimized (GPU optional via ctx_id=0)
"""

import logging
from typing import Optional, List, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

INSIGHTFACE_AVAILABLE = False
try:
    import insightface
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
    logger.info("InsightFace loaded successfully")
except ImportError:
    logger.error("InsightFace NOT installed! Run: pip install insightface")


class InsightFaceEngine:
    """
    Face detection + recognition engine using InsightFace (buffalo_l).
    
    - detect_faces(): RetinaFace detection → bounding boxes + landmarks
    - extract_embedding(): ArcFace 512-d normalized embedding
    - extract_embedding_from_b64(): convenience wrapper for base64 images
    """

    def __init__(self, ctx_id: int = -1, det_size: Tuple[int, int] = (640, 640)):
        """
        Initialize the engine.
        
        Args:
            ctx_id: -1 for CPU, 0 for GPU
            det_size: Detection input size (width, height)
        """
        self._ctx_id = ctx_id
        self._det_size = det_size
        self._app: Optional[FaceAnalysis] = None
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy-load the model on first use."""
        if self._initialized:
            return
        if not INSIGHTFACE_AVAILABLE:
            raise RuntimeError("InsightFace is required but not installed. Run: pip install insightface")

        logger.info(f"Loading InsightFace buffalo_l (ctx_id={self._ctx_id}, det_size={self._det_size})...")
        self._app = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"] if self._ctx_id < 0 else ["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        self._app.prepare(ctx_id=self._ctx_id, det_size=self._det_size)
        self._initialized = True
        logger.info("InsightFace engine ready ✅")

    def detect_faces(self, image: np.ndarray, max_size: Optional[int] = None) -> list:
        """
        Detect faces using RetinaFace.
        
        Args:
            image: BGR OpenCV image
            max_size: Optional. If provided, resize image to this max dimension before detection.
            
        Returns:
            List of InsightFace Face objects with bbox, landmarks, embedding, etc.
        """
        self._ensure_initialized()
        
        # Speed optimization: resize for liveness/passive checks
        if max_size and max_size > 0:
            h, w = image.shape[:2]
            if max(h, w) > max_size:
                scale = max_size / max(h, w)
                resized = cv2.resize(image, (int(w * scale), int(h * scale)))
                faces = self._app.get(resized)
                # Rescale bboxes and landmarks back to original
                for face in faces:
                    face.bbox /= scale
                    if face.kps is not None:
                        face.kps /= scale
                    if hasattr(face, 'landmark_2d_106') and face.landmark_2d_106 is not None:
                        face.landmark_2d_106 /= scale
                    if hasattr(face, 'landmark_3d_68') and face.landmark_3d_68 is not None:
                        face.landmark_3d_68 /= scale
                return faces

        faces = self._app.get(image)
        return faces


    def extract_embedding(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract a 512-d ArcFace embedding from an image.
        Returns the embedding for the largest detected face, or None if no face found.
        
        Args:
            image: BGR OpenCV image
            
        Returns:
            Normalized 512-d float32 numpy array, or None
        """
        faces = self.detect_faces(image)
        if not faces:
            logger.warning("No face detected in image")
            return None

        # Pick the largest face by bounding box area
        largest = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        embedding = largest.normed_embedding  # Already L2-normalized by InsightFace

        if embedding is None or len(embedding) == 0:
            logger.warning("Face detected but no embedding extracted")
            return None

        embedding = np.array(embedding, dtype=np.float32)
        logger.info(f"Embedding extracted: {len(embedding)}-d, norm={np.linalg.norm(embedding):.4f}")
        return embedding

    def get_face_crop(self, image: np.ndarray, face) -> np.ndarray:
        """
        Crop a face region from the image with margin.
        
        Args:
            image: BGR OpenCV image
            face: InsightFace Face object
            
        Returns:
            Cropped face region as BGR image
        """
        bbox = face.bbox.astype(int)
        h, w = image.shape[:2]
        # Add 20% margin
        margin_x = int((bbox[2] - bbox[0]) * 0.2)
        margin_y = int((bbox[3] - bbox[1]) * 0.2)
        x1 = max(0, bbox[0] - margin_x)
        y1 = max(0, bbox[1] - margin_y)
        x2 = min(w, bbox[2] + margin_x)
        y2 = min(h, bbox[3] + margin_y)
        return image[y1:y2, x1:x2]

    def extract_embedding_from_b64(self, b64_image: str) -> Optional[np.ndarray]:
        """
        Extract embedding from a base64-encoded image.
        
        Args:
            b64_image: Base64 encoded JPEG/PNG image
            
        Returns:
            512-d embedding or None
        """
        import base64
        try:
            img_bytes = base64.b64decode(b64_image)
            img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                logger.error("Could not decode base64 image")
                return None
            return self.extract_embedding(img)
        except Exception as e:
            logger.error(f"Error extracting embedding from base64: {e}")
            return None

    def b64_to_cv2(self, b64_str: str) -> Optional[np.ndarray]:
        """Convert a base64 image string to an OpenCV BGR image."""
        import base64
        try:
            return cv2.imdecode(
                np.frombuffer(base64.b64decode(b64_str), np.uint8),
                cv2.IMREAD_COLOR,
            )
        except Exception:
            return None

    @property
    def is_available(self) -> bool:
        return INSIGHTFACE_AVAILABLE

    @property
    def model_info(self) -> dict:
        return {
            "engine": "InsightFace (RetinaFace + ArcFace)",
            "model": "buffalo_l",
            "embedding_dim": 512,
            "ctx_id": self._ctx_id,
            "initialized": self._initialized,
            "available": INSIGHTFACE_AVAILABLE,
        }


# ============================================================
# Singleton
# ============================================================

_engine: Optional[InsightFaceEngine] = None


def get_face_engine() -> InsightFaceEngine:
    """Get or create the singleton InsightFace engine."""
    global _engine
    if _engine is None:
        from app.core.config import get_settings
        settings = get_settings()
        ctx_id = getattr(settings, "INSIGHTFACE_CTX_ID", -1)
        _engine = InsightFaceEngine(ctx_id=ctx_id)
    return _engine


# Convenience alias
face_engine = None  # Will be lazy-initialized on first import via get_face_engine()
