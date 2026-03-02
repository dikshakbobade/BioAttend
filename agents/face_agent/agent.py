"""
Face Recognition Agent

This agent captures face images from camera, performs liveness detection,
extracts face embeddings, and sends them to the backend for verification.
"""
import os
import sys
import time
import base64
from typing import Optional, Tuple
from dataclasses import dataclass
import logging

import cv2
import numpy as np
import httpx
from insightface.app import FaceAnalysis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FaceAgent")


@dataclass
class AgentConfig:
    """Face agent configuration."""
    backend_url: str
    device_id: str
    api_key: str
    camera_index: int = 0
    capture_interval: float = 0.1  # seconds between captures
    min_face_size: int = 100
    liveness_threshold: float = 0.70
    retry_attempts: int = 3
    retry_delay: float = 1.0


class LivenessDetector:
    """Multi-factor liveness detection to prevent spoofing."""
    
    def __init__(self):
        self.blink_detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
        self.prev_frame = None
        self.blink_history = []
        
    def detect_blink(self, face_region: np.ndarray) -> float:
        """Detect eye blinks for liveness."""
        gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
        eyes = self.blink_detector.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(20, 20)
        )
        
        # Eyes detected = open, no eyes = potentially blinking
        eye_score = 1.0 if len(eyes) >= 2 else 0.3
        self.blink_history.append(len(eyes))
        
        # Keep last 10 frames
        if len(self.blink_history) > 10:
            self.blink_history.pop(0)
        
        # Check for blink pattern (eyes open -> closed -> open)
        if len(self.blink_history) >= 5:
            pattern = self.blink_history[-5:]
            if pattern[0] >= 2 and pattern[2] < 2 and pattern[4] >= 2:
                return 1.0
        
        return eye_score * 0.7
    
    def analyze_texture(self, face_region: np.ndarray) -> float:
        """Analyze texture using Local Binary Patterns (LBP)."""
        gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
        
        # Calculate LBP
        radius = 1
        n_points = 8 * radius
        lbp = np.zeros_like(gray)
        
        for i in range(radius, gray.shape[0] - radius):
            for j in range(radius, gray.shape[1] - radius):
                center = gray[i, j]
                code = 0
                for k in range(n_points):
                    angle = 2 * np.pi * k / n_points
                    x = int(round(i + radius * np.cos(angle)))
                    y = int(round(j - radius * np.sin(angle)))
                    if gray[x, y] >= center:
                        code |= (1 << k)
                lbp[i, j] = code
        
        # Calculate histogram
        hist, _ = np.histogram(lbp.ravel(), bins=256, range=(0, 256))
        hist = hist.astype(float)
        hist /= (hist.sum() + 1e-7)
        
        # Real faces have more uniform texture distribution
        entropy = -np.sum(hist * np.log2(hist + 1e-7))
        normalized_entropy = entropy / 8  # Max entropy for 256 bins
        
        return min(1.0, normalized_entropy)
    
    def detect_motion(self, current_frame: np.ndarray) -> float:
        """Detect natural micro-movements."""
        if self.prev_frame is None:
            self.prev_frame = current_frame.copy()
            return 0.5
        
        # Calculate frame difference
        diff = cv2.absdiff(current_frame, self.prev_frame)
        diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        
        motion_score = np.mean(diff_gray) / 255.0
        self.prev_frame = current_frame.copy()
        
        # Natural movement is subtle but present
        if 0.01 < motion_score < 0.15:
            return 1.0
        elif motion_score < 0.01:
            return 0.3  # Too still, might be photo
        else:
            return 0.5  # Too much movement
    
    def check_skin_color(self, face_region: np.ndarray) -> float:
        """Verify skin color is in natural range."""
        hsv = cv2.cvtColor(face_region, cv2.COLOR_BGR2HSV)
        
        # Define skin color range in HSV
        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)
        
        # Create mask for skin pixels
        mask = cv2.inRange(hsv, lower_skin, upper_skin)
        skin_ratio = np.sum(mask > 0) / mask.size
        
        # Real face should have significant skin area
        if 0.3 < skin_ratio < 0.9:
            return 1.0
        else:
            return 0.4
    
    def calculate_liveness_score(self, face_region: np.ndarray, full_frame: np.ndarray) -> float:
        """Calculate overall liveness score."""
        scores = {
            'blink': self.detect_blink(face_region),
            'texture': self.analyze_texture(face_region),
            'motion': self.detect_motion(full_frame),
            'skin': self.check_skin_color(face_region)
        }
        
        # Weighted average
        weights = {'blink': 0.3, 'texture': 0.25, 'motion': 0.25, 'skin': 0.2}
        total_score = sum(scores[k] * weights[k] for k in scores)
        
        logger.debug(f"Liveness scores: {scores}, total: {total_score:.3f}")
        
        return total_score


class FaceAgent:
    """Face recognition agent for attendance system."""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.liveness_detector = LivenessDetector()
        
        # Initialize InsightFace
        logger.info("Initializing InsightFace model...")
        self.face_app = FaceAnalysis(
            name='buffalo_l',
            providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
        )
        self.face_app.prepare(ctx_id=0, det_size=(640, 640))
        logger.info("InsightFace model loaded.")
        
        # Initialize camera
        self.camera = None
        self._init_camera()
        
        # HTTP client
        self.http_client = httpx.Client(
            timeout=30.0,
            headers={
                "X-Device-ID": config.device_id,
                "X-API-Key": config.api_key,
                "Content-Type": "application/json"
            }
        )
    
    def _init_camera(self):
        """Initialize camera with optimal settings."""
        self.camera = cv2.VideoCapture(self.config.camera_index)
        
        if not self.camera.isOpened():
            raise RuntimeError(f"Cannot open camera {self.config.camera_index}")
        
        # Set camera properties for better quality
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        self.camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)
        
        logger.info(f"Camera initialized: {self.config.camera_index}")
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """Capture a frame from camera."""
        ret, frame = self.camera.read()
        if not ret:
            logger.error("Failed to capture frame")
            return None
        return frame
    
    def detect_face(self, frame: np.ndarray) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """
        Detect face in frame and extract embedding.
        Returns (face_region, embedding) or None if no valid face found.
        """
        faces = self.face_app.get(frame)
        
        if not faces:
            return None
        
        # Get the largest face
        largest_face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        
        # Check face size
        bbox = largest_face.bbox.astype(int)
        face_width = bbox[2] - bbox[0]
        face_height = bbox[3] - bbox[1]
        
        if face_width < self.config.min_face_size or face_height < self.config.min_face_size:
            logger.debug(f"Face too small: {face_width}x{face_height}")
            return None
        
        # Extract face region
        face_region = frame[
            max(0, bbox[1]):min(frame.shape[0], bbox[3]),
            max(0, bbox[0]):min(frame.shape[1], bbox[2])
        ]
        
        # Get embedding (512-dimensional vector)
        embedding = largest_face.embedding
        
        return face_region, embedding
    
    def send_verification(self, embedding: np.ndarray, liveness_score: float) -> dict:
        """Send embedding to backend for verification."""
        payload = {
            "embedding": embedding.tolist(),
            "liveness_score": liveness_score,
            "device_id": self.config.device_id
        }
        
        for attempt in range(self.config.retry_attempts):
            try:
                response = self.http_client.post(
                    f"{self.config.backend_url}/api/v1/biometric/face/verify",
                    json=payload
                )
                response.raise_for_status()
                return response.json()
            
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
                if e.response.status_code < 500:
                    return {"success": False, "message": e.response.json().get("detail", "Error")}
            
            except httpx.RequestError as e:
                logger.error(f"Request error (attempt {attempt + 1}): {e}")
                if attempt < self.config.retry_attempts - 1:
                    time.sleep(self.config.retry_delay * (2 ** attempt))
        
        return {"success": False, "message": "Connection failed"}
    
    def run_once(self) -> Optional[dict]:
        """Run single detection cycle."""
        frame = self.capture_frame()
        if frame is None:
            return None
        
        result = self.detect_face(frame)
        if result is None:
            return None
        
        face_region, embedding = result
        
        # Check liveness
        liveness_score = self.liveness_detector.calculate_liveness_score(face_region, frame)
        
        if liveness_score < self.config.liveness_threshold:
            logger.warning(f"Liveness check failed: {liveness_score:.3f}")
            return {"success": False, "message": "Liveness check failed", "liveness_score": liveness_score}
        
        # Send for verification
        response = self.send_verification(embedding, liveness_score)
        
        return response
    
    def run_continuous(self, display: bool = True):
        """Run continuous detection loop."""
        logger.info("Starting continuous face detection...")
        
        while True:
            try:
                frame = self.capture_frame()
                if frame is None:
                    continue
                
                result = self.detect_face(frame)
                
                if display:
                    display_frame = frame.copy()
                
                if result is not None:
                    face_region, embedding = result
                    liveness_score = self.liveness_detector.calculate_liveness_score(face_region, frame)
                    
                    if display:
                        color = (0, 255, 0) if liveness_score >= self.config.liveness_threshold else (0, 0, 255)
                        cv2.putText(display_frame, f"Liveness: {liveness_score:.2f}", 
                                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                    
                    if liveness_score >= self.config.liveness_threshold:
                        response = self.send_verification(embedding, liveness_score)
                        
                        if response.get("success"):
                            logger.info(f"✓ {response.get('attendance_action')}: {response.get('employee_name')}")
                            if display:
                                cv2.putText(display_frame, response.get('message', ''), 
                                            (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                            # Cooldown after successful verification
                            time.sleep(3)
                        else:
                            logger.warning(f"✗ {response.get('message')}")
                
                if display:
                    cv2.imshow("Face Recognition", display_frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                time.sleep(self.config.capture_interval)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in detection loop: {e}")
                time.sleep(1)
        
        self.cleanup()
    
    def cleanup(self):
        """Release resources."""
        if self.camera:
            self.camera.release()
        cv2.destroyAllWindows()
        self.http_client.close()
        logger.info("Face agent stopped.")


def main():
    """Main entry point."""
    config = AgentConfig(
        backend_url=os.getenv("BACKEND_URL", "http://localhost:8000"),
        device_id=os.getenv("DEVICE_ID", "FACE-001"),
        api_key=os.getenv("API_KEY", "your-api-key-here"),
        camera_index=int(os.getenv("CAMERA_INDEX", "0")),
    )
    
    try:
        agent = FaceAgent(config)
        agent.run_continuous(display=True)
    except Exception as e:
        logger.error(f"Failed to start agent: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
