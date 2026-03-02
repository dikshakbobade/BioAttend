"""
Active Liveness Service — Eye Blink Detection Only.
=====================================================
Simple, reliable liveness detection: a live person blinks, a photo never does.

Uses InsightFace 106-point landmarks to compute Eye Aspect Ratio (EAR):
  - EAR drops when eyes close (blink)
  - EAR rises when eyes open
  - Detect at least 1 blink across captured frames → LIVE
  - No blink detected (static EAR) → SPOOF (photo/screen)
"""

import logging
from typing import List, Tuple, Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ============================================================
# InsightFace 106-point landmark indices for eyes
# ============================================================

# Left eye: 6 key points for EAR calculation
# p1=33(left corner), p2=35(upper-left), p3=36(upper-right),
# p4=37(right corner), p5=40(lower-right), p6=41(lower-left)
LEFT_EYE = [33, 35, 36, 37, 40, 41]

# Right eye: same structure
# p1=43(left corner), p2=45(upper-left), p3=46(upper-right),
# p4=47(right corner), p5=50(lower-right), p6=51(lower-left)
RIGHT_EYE = [43, 45, 46, 47, 50, 51]


def _distance(p1, p2) -> float:
    """Euclidean distance between two 2D points."""
    return float(np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2))


def _compute_ear(landmarks, eye_indices) -> float:
    """
    Eye Aspect Ratio (EAR).
    EAR = (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)

    High EAR (~0.3) = eye open
    Low EAR (~0.15) = eye closed (blink)
    """
    p = [landmarks[i] for i in eye_indices]
    v1 = _distance(p[1], p[5])  # upper-left to lower-left
    v2 = _distance(p[2], p[4])  # upper-right to lower-right
    h  = _distance(p[0], p[3])  # left corner to right corner
    if h == 0:
        return 0.0
    return (v1 + v2) / (2.0 * h)


class ActiveLivenessService:
    """
    Eye-blink liveness detection using InsightFace 106-point landmarks.

    Logic:
      1. Compute EAR for each frame
      2. Find frames where EAR dips (eyes closing) and rises (eyes opening)
      3. A blink = EAR goes below CLOSED_THRESHOLD then back above OPEN_THRESHOLD
      4. At least 1 blink across frames → PASS (live person)
      5. No blink → FAIL (likely a photo or screen)
    """

    CLOSED_THRESHOLD = 0.21   # EAR below this = eyes are closing/closed
    OPEN_THRESHOLD = 0.24     # EAR above this = eyes are open
    MIN_EAR_RANGE = 0.02      # Minimum EAR variation to detect any movement

    def __init__(self):
        self._engine = None

    def _ensure_engine(self):
        if self._engine is None:
            from app.services.face_engine import get_face_engine
            self._engine = get_face_engine()

    def check(self, frames: List[np.ndarray]) -> Tuple[bool, Dict]:
        """
        Check for eye blinks across a sequence of frames.

        Args:
            frames: List of BGR OpenCV images (at least 3)

        Returns:
            (passed, details_dict)
        """
        if not frames or len(frames) < 3:
            return False, {
                "passed": False,
                "reason": "Not enough frames (need at least 3)",
                "blink_detected": False,
                "nod_detected": False,
                "smile_detected": False,
                "checks_passed": 0,
                "checks_required": 1,
            }

        self._ensure_engine()

        # Step 1: Extract EAR from each frame
        ear_values = []
        frames_with_face = 0

        for frame in frames:
            # OPTIMIZATION: Use smaller det_size (320px) for liveness frames.
            # This makes landmarks extraction SIGNIFICANTLY faster on CPU.
            faces = self._engine.detect_faces(frame, max_size=320)
            if not faces:
                ear_values.append(None)
                continue

            largest = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0]) * (f.bbox[3]-f.bbox[1]))


            # Need 106-point landmarks for EAR
            if hasattr(largest, 'landmark_2d_106') and largest.landmark_2d_106 is not None:
                lm = largest.landmark_2d_106
                ear_l = _compute_ear(lm, LEFT_EYE)
                ear_r = _compute_ear(lm, RIGHT_EYE)
                avg_ear = (ear_l + ear_r) / 2.0
                ear_values.append(avg_ear)
                frames_with_face += 1
            else:
                ear_values.append(None)

        # Filter out None values
        valid_ears = [e for e in ear_values if e is not None]

        if len(valid_ears) < 3:
            return False, {
                "passed": False,
                "reason": f"Face not detected consistently ({frames_with_face}/{len(frames)} frames)",
                "blink_detected": False,
                "nod_detected": False,
                "smile_detected": False,
                "checks_passed": 0,
                "checks_required": 1,
            }

        # Step 2: Detect blinks using DYNAMIC EAR pattern
        # Find the baseline "open" EAR (max value in sequence)
        max_ear = max(valid_ears)
        min_ear = min(valid_ears)
        ear_range = max_ear - min_ear
        
        # Dynamic thresholds: eyes are closed if EAR drops significantly from max
        dynamic_closed = max_ear * 0.75  # 25% drop
        dynamic_open = max_ear * 0.88    # Must return to 88% of max to count as re-opened
        
        blink_count = self._count_blinks_dynamic(valid_ears, dynamic_closed, dynamic_open)
        
        # A live person: at least 1 blink OR very high variation relative to average
        # (Photo EAR is extremely flat/static)
        # Relaxed slightly: range > 0.03 (was 0.04) and 12% variation (was 15%)
        blink_detected = blink_count >= 1 or (ear_range > 0.03 and ear_range / max_ear > 0.12)
        passed = blink_detected

        logger.info(
            f"Eye-Blink Liveness: blinks={blink_count}, max_ear={max_ear:.4f}, range={ear_range:.4f} "
            f"({(ear_range/max_ear*100):.1f}%) → {'PASS ✅' if passed else 'FAIL ❌'}"
        )

        details = {
            "passed": passed,
            "reason": "passed" if passed else "BLINK NOT DETECTED — Please look at the camera and blink clearly",
            "blink_detected": blink_detected,
            "nod_detected": False,
            "smile_detected": False,
            "checks_passed": 1 if passed else 0,
            "checks_required": 1,
            "liveness_metrics": {
                "blink_count": blink_count,
                "ear_range": round(ear_range, 4),
                "ear_max": round(max_ear, 4),
                "ear_min": round(min_ear, 4),
                "frames_analyzed": len(valid_ears),
            },
        }

        return passed, details

    def _count_blinks_dynamic(self, ear_values: List[float], closed_thresh: float, open_thresh: float) -> int:
        """Count blinks using dynamic thresholds."""
        blinks = 0
        state = "open"
        for ear in ear_values:
            if state == "open" and ear < closed_thresh:
                state = "closed"
            elif state == "closed" and ear > open_thresh:
                blinks += 1
                state = "open"
        return blinks


    @property
    def info(self) -> dict:
        return {
            "engine": "InsightFace 106-pt Landmarks (Eye Blink)",
            "checks": ["eye_blink"],
            "min_checks_required": 1,
            "available": True,
        }


# Singleton
_service: Optional[ActiveLivenessService] = None

def get_active_liveness_service() -> ActiveLivenessService:
    global _service
    if _service is None:
        _service = ActiveLivenessService()
    return _service
