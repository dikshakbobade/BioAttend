"""
Main FastAPI application.
"""
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.db import init_db, get_db, check_db_connection, AsyncSessionLocal
from app.api.v1 import api_router
from app.services import template_cache, device_service, admin_service
from app.services.scheduler import start_scheduler, stop_scheduler
import logging

logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting up Biometric Attendance System...")

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # In production, you might want to exit here
        raise

    # Create initial admin user if needed and pre-load templates
    try:
        async with AsyncSessionLocal() as db:
            admin = await admin_service.create_initial_admin(db)
            if admin:
                logger.info(f"Initial admin user created: {admin.username}")
                logger.warning("WARNING: Change the default password immediately!")

            # Pre-load biometric templates for faster matching
            try:
                from app.services.matching_service import matching_service
                from app.models import BiometricType
                count = await matching_service.load_templates(db, BiometricType.FACE)
                logger.info(f"Pre-loaded {count} face templates.")
            except Exception as e:
                logger.warning(f"Failed to pre-load templates: {e}")
    except Exception as e:
        logger.error(f"Failed to create initial admin or pre-load templates: {e}")

    # Start email notification scheduler
    try:
        start_scheduler()
        logger.info("Email notification scheduler started.")
    except Exception as e:
        logger.error(f"Warning: Scheduler failed to start: {e}")

    # Pre-initialize Face Engine (Avoids timeout on first enrollment/match)
    try:
        from app.services.face_engine import get_face_engine
        engine = get_face_engine()
        # This will trigger model download/loading if not already done
        logger.info("Pre-initializing InsightFace engine (this may take a minute first time)...")
        engine._ensure_initialized()
        logger.info("Face engine pre-initialization complete.")
    except Exception as e:
        logger.error(f"Failed to pre-initialize face engine: {e}")

    yield

    # Shutdown
    logger.info("Shutting down...")
    stop_scheduler()
    template_cache.clear()


app = FastAPI(
    title="Biometric Attendance System",
    description="Production-ready biometric attendance system with face and fingerprint recognition",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "name": "Biometric Attendance System",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    async with AsyncSessionLocal() as db:
        db_healthy = await check_db_connection(db)
        active_devices = await device_service.get_active_device_count(db)

    checks = {
        "database": db_healthy,
        "face_templates_loaded": template_cache.is_loaded("FACE"),
        "fingerprint_templates_loaded": template_cache.is_loaded("FINGERPRINT"),
        "active_devices": active_devices
    }

    status = "healthy" if db_healthy else "degraded"

    return {
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred",
            "error_code": "INTERNAL_ERROR"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )