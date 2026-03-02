import logging
import sys
import os

# Configure logging to stdout
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

try:
    print("Testing InsightFace loading...")
    import insightface
    from insightface.app import FaceAnalysis
    print("InsightFace library imported.")
    
    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    print("FaceAnalysis instance created. Preparing (this might download models)...")
    app.prepare(ctx_id=-1, det_size=(640, 640))
    print("InsightFace ready ✅")
    
    import numpy as np
    dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)
    print("Running detection on dummy image...")
    faces = app.get(dummy_img)
    print(f"Detection successful. Found {len(faces)} faces.")
    
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
