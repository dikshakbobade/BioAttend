"""
Biometric matching service for face and fingerprint verification.
"""
import asyncio
import base64
import os
import time
from logging.handlers import TimedRotatingFileHandler
from typing import Optional, List, Tuple
from uuid import UUID

import numpy as np
import cv2
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    faiss = None
    FAISS_AVAILABLE = False
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from cachetools import TTLCache
import logging

logger = logging.getLogger(__name__)

from app.models import Employee, BiometricTemplate, BiometricType, EmployeeStatus
from app.core.security import encryption_service
from app.core.config import get_settings

settings = get_settings()

# ---------------------------------------------------------------------------
# Rotating match log
# ---------------------------------------------------------------------------
_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
os.makedirs(_LOG_DIR, exist_ok=True)

_match_logger = logging.getLogger("bioattend.matching")
if not _match_logger.handlers:
    _fh = TimedRotatingFileHandler(
        os.path.join(_LOG_DIR, "matching.log"),
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )
    _fh.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S"))
    _match_logger.addHandler(_fh)
    _match_logger.setLevel(logging.INFO)
    _match_logger.propagate = False

FACE_MATCH_TIMEOUT = 2.0


class TemplateCache:
    def __init__(self, ttl: int = 300):
        self._face_cache: TTLCache = TTLCache(maxsize=1000, ttl=ttl)
        self._fingerprint_cache: TTLCache = TTLCache(maxsize=1000, ttl=ttl)
        self._loaded = {"FACE": False, "FINGERPRINT": False}
        self._face_index = None
        self._face_id_map: List[Employee] = []

    def get_face_templates(self) -> dict:
        return dict(self._face_cache)

    def get_fingerprint_templates(self) -> dict:
        return dict(self._fingerprint_cache)

    def set_face_template(self, employee_id: UUID, embedding: np.ndarray, employee: Employee):
        eid_str = str(employee_id)
        if eid_str not in self._face_cache:
            self._face_cache[eid_str] = {"embeddings": [], "employee": employee}
        self._face_cache[eid_str]["embeddings"].append(embedding)

    def rebuild_face_index(self):
        all_embeddings = []
        self._face_id_map = []

        for eid, data in self._face_cache.items():
            for emb in data["embeddings"]:
                all_embeddings.append(emb)
                self._face_id_map.append(data["employee"])

        if not all_embeddings:
            self._face_index = None
            return

        embeddings_arr = np.array(all_embeddings).astype('float32')

        if FAISS_AVAILABLE:
            faiss.normalize_L2(embeddings_arr)
            dim = embeddings_arr.shape[1]
            self._face_index = faiss.IndexFlatIP(dim)
            self._face_index.add(embeddings_arr)
            logger.info(f"Faiss index built with {len(all_embeddings)} vectors (dim={dim})")
        else:
            norms = np.linalg.norm(embeddings_arr, axis=1, keepdims=True)
            self._face_index = embeddings_arr / np.where(norms == 0, 1, norms)
            dim = embeddings_arr.shape[1]
            logger.info(f"Numpy fallback index built with {len(all_embeddings)} vectors (dim={dim})")

    def search_face(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Tuple[Employee, float]]:
        if not self._face_cache or not self._face_id_map:
            return []
        try:
            query = query_embedding.astype('float32').reshape(1, -1)
            query_norm = np.linalg.norm(query)
            if query_norm == 0:
                return []
            query = query / query_norm

            if FAISS_AVAILABLE and self._face_index is not None and isinstance(self._face_index, faiss.IndexFlatIP):
                scores, indices = self._face_index.search(query, min(top_k, self._face_index.ntotal))
                results = []
                for i, idx in enumerate(indices[0]):
                    if idx < 0 or idx >= len(self._face_id_map):
                        continue
                    results.append((self._face_id_map[idx], float(scores[0][i])))
                return results
            else:
                all_embs, all_emps = [], []
                for eid, data in self._face_cache.items():
                    for emb in data["embeddings"]:
                        all_embs.append(emb)
                        all_emps.append(data["employee"])
                if not all_embs:
                    return []
                matrix = np.array(all_embs, dtype=np.float32)
                norms = np.linalg.norm(matrix, axis=1, keepdims=True)
                matrix_norm = matrix / np.where(norms == 0, 1, norms)
                similarities = np.dot(matrix_norm, query.flatten())
                indices = np.argsort(similarities)[-top_k:][::-1]
                return [(all_emps[idx], float(similarities[idx])) for idx in indices]
        except Exception as e:
            logger.error(f"Face search error: {e}")
            return []

    def set_fingerprint_template(self, employee_id: UUID, template: bytes, employee: Employee):
        self._fingerprint_cache[str(employee_id)] = {"template": template, "employee": employee}

    def clear(self):
        self._face_cache.clear()
        self._fingerprint_cache.clear()
        self._loaded = {"FACE": False, "FINGERPRINT": False}
        self._face_index = None
        self._face_id_map = []

    def is_loaded(self, biometric_type: str) -> bool:
        return self._loaded.get(biometric_type, False)

    def set_loaded(self, biometric_type: str, loaded: bool = True):
        self._loaded[biometric_type] = loaded


# Global template cache
template_cache = TemplateCache()


class MatchingService:

    def __init__(self):
        self.face_threshold = max(settings.FACE_SIMILARITY_THRESHOLD, 0.75)
        self.fingerprint_threshold = settings.FINGERPRINT_MATCH_THRESHOLD

    @staticmethod
    def cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(embedding1, embedding2) / (norm1 * norm2))

    async def load_templates(self, db: AsyncSession, biometric_type: BiometricType) -> int:
        result = await db.execute(
            select(BiometricTemplate, Employee)
            .join(Employee)
            .where(
                BiometricTemplate.biometric_type == biometric_type,
                BiometricTemplate.is_active == True,
                Employee.status == EmployeeStatus.ACTIVE
            )
        )
        rows = result.all()
        count = 0
        for template, employee in rows:
            try:
                decrypted = encryption_service.decrypt_template(template.template_data)
                if biometric_type == BiometricType.FACE:
                    if len(decrypted) % 4 != 0:
                        logger.warning(f"Invalid face template size for employee {employee.id}: {len(decrypted)} bytes.")
                        continue
                    embedding = np.frombuffer(decrypted, dtype=np.float32)
                    template_cache.set_face_template(employee.id, embedding, employee)
                else:
                    template_cache.set_fingerprint_template(employee.id, decrypted, employee)
                count += 1
            except Exception as e:
                logger.error(f"Error loading template for employee {employee.id}: {e}")

        template_cache.set_loaded(biometric_type.value)
        if biometric_type == BiometricType.FACE:
            template_cache.rebuild_face_index()
        return count

    async def match_face(
        self, db: AsyncSession, query_embedding: List[float], liveness_score: float,
    ) -> Optional[Tuple[Employee, float]]:
        if liveness_score < settings.LIVENESS_THRESHOLD:
            return None
        if not template_cache.is_loaded("FACE"):
            await self.load_templates(db, BiometricType.FACE)
            template_cache.rebuild_face_index()

        t0 = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, self._sync_search, query_embedding),
                timeout=FACE_MATCH_TIMEOUT,
            )
        except asyncio.TimeoutError:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            _match_logger.warning(f"TIMEOUT | elapsed={elapsed_ms:.1f}ms")
            return None

        elapsed_ms = (time.perf_counter() - t0) * 1000
        if result is None:
            _match_logger.info(f"NO_MATCH | elapsed={elapsed_ms:.1f}ms")
            return None

        best_match, similarity = result
        _match_logger.info(f"MATCH | employee={best_match.full_name!r} | score={similarity:.4f} | elapsed={elapsed_ms:.1f}ms")
        return (best_match, similarity)

    def _sync_search(self, query_embedding: List[float]) -> Optional[Tuple["Employee", float]]:
        query_array = np.array(query_embedding, dtype=np.float32)
        matches = template_cache.search_face(query_array, top_k=1)
        if not matches:
            return None
        best_match, similarity = matches[0]
        if similarity >= self.face_threshold:
            return (best_match, similarity)
        return None

    async def match_fingerprint(self, db: AsyncSession, query_template: bytes, quality_score: float) -> Optional[Tuple[Employee, float]]:
        if quality_score < 40:
            return None
        if not template_cache.is_loaded("FINGERPRINT"):
            await self.load_templates(db, BiometricType.FINGERPRINT)

        best_match: Optional[Tuple[Employee, float]] = None
        best_score = 0.0
        for employee_id, data in template_cache.get_fingerprint_templates().items():
            score = self._compare_fingerprint_templates(query_template, data["template"])
            if score > best_score and score >= self.fingerprint_threshold:
                best_score = score
                best_match = (data["employee"], score)
        return best_match

    def _compare_fingerprint_templates(self, template1: bytes, template2: bytes) -> float:
        if len(template1) == 0 or len(template2) == 0:
            return 0.0
        min_len = min(len(template1), len(template2))
        matches = sum(1 for a, b in zip(template1[:min_len], template2[:min_len]) if a == b)
        return (matches / min_len) * 100

    async def register_template(
        self, db: AsyncSession, employee_id: UUID, biometric_type: BiometricType,
        template_data: str, quality_score: Optional[float] = None
    ) -> BiometricTemplate:
        if biometric_type == BiometricType.FACE:
            img_bytes = base64.b64decode(template_data)
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Could not decode face image.")

            from .face_engine import get_face_engine
            from .face_quality import get_face_quality_service
            engine = get_face_engine()
            quality_service = get_face_quality_service()

            try:
                passed, q_details = quality_service.analyze_quality(img)
                if not passed:
                    logger.warning(f"Quality warning (proceeding anyway): {q_details.get('errors', '')}")
                if quality_score is None:
                    quality_score = q_details.get("sharpness", 50.0)
            except Exception as qe:
                logger.warning(f"Quality check skipped: {qe}")
                if quality_score is None:
                    quality_score = 50.0

            embedding = engine.extract_embedding(img)
            if embedding is None:
                raise ValueError("Could not detect face. Please try again with better lighting.")

            raw_template = embedding.tobytes()
            logger.info(f"Face embedding extracted: {len(raw_template)} bytes")
        else:
            raw_template = base64.b64decode(template_data)

        encrypted_template = encryption_service.encrypt_template(raw_template)

        existing_result = await db.execute(
            select(BiometricTemplate).where(
                BiometricTemplate.employee_id == employee_id,
                BiometricTemplate.biometric_type == biometric_type,
                BiometricTemplate.is_active == True
            )
        )
        existing_active = existing_result.scalars().all()
        if len(existing_active) >= 3:
            existing_active.sort(key=lambda x: x.created_at)
            existing_active[0].is_active = False

        template = BiometricTemplate(
            employee_id=employee_id,
            biometric_type=biometric_type,
            template_data=encrypted_template,
            quality_score=quality_score,
            is_active=True
        )
        db.add(template)
        await db.commit()
        await db.refresh(template)

        # ✅ FIX: AsyncSessionLocal — not db.__class__(bind=...)
        try:
            from app.db import AsyncSessionLocal
            template_cache.clear()
            async with AsyncSessionLocal() as reload_db:
                await self.load_templates(reload_db, BiometricType.FACE)
        except Exception as e:
            logger.warning(f"FAISS hot-reload failed (lazy-reload on next match): {e}")

        return template

    async def get_employee_templates(self, db: AsyncSession, employee_id: UUID) -> List[BiometricTemplate]:
        result = await db.execute(
            select(BiometricTemplate)
            .where(BiometricTemplate.employee_id == employee_id)
            .order_by(BiometricTemplate.created_at.desc())
        )
        return list(result.scalars().all())

    async def register_face_profile(
        self, db: AsyncSession, employee_id: UUID,
        front_image: str, left_image: str, right_image: str
    ) -> dict:
        """
        3-image guided enrollment:
        1. Decode all 3 images
        2. Extract & normalize embeddings using extract_embedding()
        3. Consistency check (lowered threshold = 0.45 for poor lighting)
        4. Store canonical averaged template (ACTIVE)
        5. Store 3 raw templates (INACTIVE fallback)
        6. Rebuild FAISS index
        """
        images_b64 = [front_image, left_image, right_image]
        images_cv2 = []
        for b64 in images_b64:
            raw = base64.b64decode(b64)
            img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Could not decode one of the face images.")
            images_cv2.append(img)

        from .face_engine import get_face_engine
        from .face_quality import get_face_quality_service
        engine = get_face_engine()
        quality_service = get_face_quality_service()

        embeddings = []
        quality_scores = {}
        angles = ["front", "left", "right"]

        for i, img in enumerate(images_cv2):
            # ✅ FIX: extract_embedding() — extract_face_object() does NOT exist
            embedding = engine.extract_embedding(img)
            if embedding is None:
                raise ValueError(
                    f"Could not detect face in the {angles[i]} image. "
                    "Please ensure your face is visible and lighting is adequate."
                )

            # Normalize
            norm = np.linalg.norm(embedding)
            if norm > 1e-6:
                embedding = embedding / norm
            embeddings.append(embedding)

            # Quality score — wrapped in try/except so it never crashes enrollment
            try:
                _, q_details = quality_service.analyze_quality(img)
                q_val = min(100, (q_details.get("brightness", 50) * 0.4) + (q_details.get("sharpness", 20) * 1.5))
            except Exception as qe:
                logger.warning(f"Quality analysis skipped for {angles[i]}: {qe}")
                q_val = 50.0
            quality_scores[angles[i]] = round(q_val, 1)

        # ✅ Same-person consistency check
        # Threshold LOWERED to 0.45 (was 0.6) — handles poor lighting & dark rooms
        sim_fl = self.cosine_similarity(embeddings[0], embeddings[1])
        sim_fr = self.cosine_similarity(embeddings[0], embeddings[2])
        sim_lr = self.cosine_similarity(embeddings[1], embeddings[2])

        logger.info(f"Enroll similarities — FL={sim_fl:.3f}, FR={sim_fr:.3f}, LR={sim_lr:.3f}")

        # ✅ LOWERED from 0.6 → 0.45 to handle dark/angled shots
        CONSISTENCY_THRESHOLD = 0.45
        if sim_fl < CONSISTENCY_THRESHOLD or sim_fr < CONSISTENCY_THRESHOLD or sim_lr < CONSISTENCY_THRESHOLD:
            raise ValueError(
                f"The 3 photos appear to be different people "
                f"(similarity scores: FL={sim_fl:.2f}, FR={sim_fr:.2f}, LR={sim_lr:.2f}). "
                f"Please retake all 3 shots of the same person in consistent lighting."
            )

        # Deactivate old templates for this employee
        await db.execute(
            update(BiometricTemplate)
            .where(
                BiometricTemplate.employee_id == employee_id,
                BiometricTemplate.biometric_type == BiometricType.FACE
            )
            .values(is_active=False)
        )

        # Average + normalize canonical embedding
        avg_emb = np.mean(embeddings, axis=0)
        norm = np.linalg.norm(avg_emb)
        if norm > 1e-6:
            avg_emb = avg_emb / norm

        canonical_enc = encryption_service.encrypt_template(avg_emb.astype(np.float32).tobytes())
        avg_quality = float(np.mean(list(quality_scores.values())))

        # Store canonical template (ACTIVE — used for matching)
        canonical_template = BiometricTemplate(
            employee_id=employee_id,
            biometric_type=BiometricType.FACE,
            template_data=canonical_enc,
            quality_score=avg_quality,
            is_active=True,
            template_version=100  # 100 = canonical average
        )
        db.add(canonical_template)

        # Store 3 raw component templates (INACTIVE — fallback metadata)
        for i, emb in enumerate(embeddings):
            enc = encryption_service.encrypt_template(emb.astype(np.float32).tobytes())
            comp = BiometricTemplate(
                employee_id=employee_id,
                biometric_type=BiometricType.FACE,
                template_data=enc,
                quality_score=quality_scores[angles[i]],
                is_active=False,
                template_version=i + 1  # 1=front, 2=left, 3=right
            )
            db.add(comp)

        await db.commit()
        await db.refresh(canonical_template)

        # ✅ FIX: AsyncSessionLocal — not db.__class__(bind=...)
        try:
            from app.db import AsyncSessionLocal
            template_cache.clear()
            async with AsyncSessionLocal() as reload_db:
                await self.load_templates(reload_db, BiometricType.FACE)
            logger.info("FAISS index rebuilt successfully after enrollment.")
        except Exception as e:
            logger.warning(f"FAISS index rebuild failed (lazy-reload on next match): {e}")

        return {
            "success": True,
            "quality_scores": quality_scores,
            "average_quality": round(avg_quality, 1),
            "similarity_scores": {
                "front_left": round(sim_fl, 3),
                "front_right": round(sim_fr, 3),
                "left_right": round(sim_lr, 3),
            },
            "message": "Face profile enrolled successfully."
        }


# Singleton instance
matching_service = MatchingService()