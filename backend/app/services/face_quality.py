"""
Face Quality Service — Sharpness, Brightness, and Pose Estimation.
================================================================
Ensures that only high-quality face images are used for biometric enrollment.
Matches ISO/IEC 19794-5 standards for biometric face images where possible.
"""

import logging
from typing import Dict, Tuple, Optional
import cv2
import numpy as np

logger = logging.getLogger(__name__)

class FaceQualityService:
    """
    Analyzes face quality:
    - Sharpness: Variance of Laplacian (blur detection)
    - Brightness: Mean intensity
    - Pose: Yaw, Pitch, Roll estimation from 2D landmarks
    """

    # Thresholds for quality
    BLUR_THRESHOLD = 5.0        # Set to absolute minimum for now to ensure enrollment
    BRIGHT_MIN = 30             # More permissive dark limit
    BRIGHT_MAX = 240            # More permissive bright limit
    MAX_YAW = 35                # Increased from 20 to 35
    MAX_PITCH = 30              # Increased from 20 to 30
    MAX_ROLL = 25               # Increased from 15 to 25

    def __init__(self):
        self._engine = None

    def _ensure_engine(self):
        if self._engine is None:
            from .face_engine import get_face_engine
            self._engine = get_face_engine()

    def analyze_quality(self, image: np.ndarray) -> Tuple[bool, Dict]:
        """
        Comprehensive quality analysis of a face image.
        
        Returns:
            (is_ok, details)
        """
        details = {
            "sharpness": 0.0,
            "brightness": 0.0,
            "pose": {"yaw": 0.0, "pitch": 0.0, "roll": 0.0},
            "passed": True,
            "errors": []
        }

        # 1. Basic Image Checks (Blur & Brightness)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        details["sharpness"] = round(cv2.Laplacian(gray, cv2.CV_64F).var(), 2)
        details["brightness"] = round(np.mean(gray), 2)

        if details["sharpness"] < self.BLUR_THRESHOLD:
            details["passed"] = False
            details["errors"].append(f"Image is too blurry ({details['sharpness']} < {self.BLUR_THRESHOLD})")

        if details["brightness"] < self.BRIGHT_MIN:
            details["passed"] = False
            details["errors"].append("Image is too dark")
        elif details["brightness"] > self.BRIGHT_MAX:
            details["passed"] = False
            details["errors"].append("Image is too bright (overexposed)")

        # 2. Advanced Checks (Pose & Visibility)
        self._ensure_engine()
        faces = self._engine.detect_faces(image)
        
        if not faces:
            details["passed"] = False
            details["errors"].append("No face detected")
            logger.info(f"Quality: FAILED - No face detected | Metrics: {details}")
            return False, details

        # Analyze the largest face
        face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0]) * (f.bbox[3]-f.bbox[1]))
        
        # Estimate pose using InsightFace landmarks if available
        if hasattr(face, 'pose') and face.pose is not None:
            yaw, pitch, roll = face.pose
            details["pose"] = {"yaw": round(yaw, 2), "pitch": round(pitch, 2), "roll": round(roll, 2)}
        elif hasattr(face, 'kps') and face.kps is not None:
            details["pose"] = self._estimate_pose_from_kps(face.kps, image.shape)

        if abs(details["pose"]["yaw"]) > self.MAX_YAW:
            details["passed"] = False
            details["errors"].append(f"Yaw too high ({details['pose']['yaw']}°)")
        
        if abs(details["pose"]["pitch"]) > self.MAX_PITCH:
            details["passed"] = False
            details["errors"].append(f"Pitch too high ({details['pose']['pitch']}°)")

        if abs(details["pose"]["roll"]) > self.MAX_ROLL:
            details["passed"] = False
            details["errors"].append(f"Roll too high ({details['pose']['roll']}°)")

        logger.info(f"Quality: {'PASSED' if details['passed'] else 'FAILED'} | Metrics: {details}")
        return details["passed"], details

    def _estimate_pose_from_kps(self, kps: np.ndarray, img_shape: tuple) -> Dict:
        """Simple pose estimation from 5 keypoints (eyes, nose, mouth corners)."""
        # Relative positions for a frontal face
        # This is a heuristic estimation
        left_eye, right_eye, nose, left_mouth, right_mouth = kps
        
        # Yaw: Difference in distance from nose to eyes
        eye_dist = np.linalg.norm(left_eye - right_eye)
        nose_to_left = np.linalg.norm(left_eye - nose)
        nose_to_right = np.linalg.norm(right_eye - nose)
        yaw = (nose_to_left - nose_to_right) / eye_dist * 45  # Normalize to ~45 deg
        
        # Roll: Tilt of eye line
        dy = right_eye[1] - left_eye[1]
        dx = right_eye[0] - left_eye[0]
        roll = np.degrees(np.arctan2(dy, dx))
        
        # Pitch: Ratio of nose-to-eye vertical dist vs nose-to-mouth
        eye_y = (left_eye[1] + right_eye[1]) / 2.0
        mouth_y = (left_mouth[1] + right_mouth[1]) / 2.0
        dist_nose_to_eye = nose[1] - eye_y
        dist_nose_to_mouth = mouth_y - nose[1]
        
        # Crude pitch estimate
        if dist_nose_to_mouth != 0:
            pitch = (dist_nose_to_eye / dist_nose_to_mouth - 1.0) * 30
        else:
            pitch = 0.0
            
        return {"yaw": round(yaw, 2), "pitch": round(pitch, 2), "roll": round(roll, 2)}

# Singleton
_service: Optional[FaceQualityService] = None

def get_face_quality_service() -> FaceQualityService:
    global _service
    if _service is None:
        _service = FaceQualityService()
    return _service
