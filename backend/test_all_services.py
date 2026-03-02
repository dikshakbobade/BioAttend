import logging
import sys
import os
import time
import asyncio

# Configure logging to stdout
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# Mock settings for testing
os.environ["DATABASE_URL"] = "mysql+aiomysql://root:Password@localhost:3306/biometric_attendance"
os.environ["SECRET_KEY"] = "test"
os.environ["ENCRYPTION_KEY"] = "fiNfV3zhXyjjyclI8EhfRSB13o2wnYYtAYHo2R2kzRo="

async def test_all():
    try:
        print("\n--- Testing FaceEngine ---")
        from app.services.face_engine import get_face_engine
        engine = get_face_engine()
        print("Engine singleton created.")
        import numpy as np
        dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)
        engine.detect_faces(dummy_img)
        print("FaceEngine initialized and tested ✅")

        print("\n--- Testing MatchingService & DB ---")
        from app.services.matching_service import matching_service
        from app.db.database import AsyncSessionLocal
        from app.models.models import BiometricType
        
        async with AsyncSessionLocal() as db:
            print("Database session opened.")
            t1 = time.time()
            count = await matching_service.load_templates(db, BiometricType.FACE)
            print(f"Loaded {count} face templates from DB (took {time.time()-t1:.2f}s).")
            
            t1 = time.time()
            from app.services.matching_service import template_cache
            template_cache.rebuild_face_index()
            print(f"Faiss index rebuilt (took {time.time()-t1:.2f}s).")
            
            # Test match_face
            query_emb = [0.1] * 512
            match = await matching_service.match_face(db, query_emb, liveness_score=1.0)
            print(f"Match test done. Result: {match}")
        
        print("MatchingService initialized and tested ✅")

        print("\nALL SERVICES READY ✅")
        
    except Exception as e:
        print(f"\nFAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_all())
