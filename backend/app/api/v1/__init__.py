"""
API v1 router aggregation.
"""
from fastapi import APIRouter

from app.api.v1 import employees, verification, attendance, admin, devices

api_router = APIRouter(prefix="/api/v1")

# Include all routers
api_router.include_router(admin.router)
api_router.include_router(employees.router)
api_router.include_router(verification.router)
api_router.include_router(attendance.router)
api_router.include_router(devices.router)

__all__ = ["api_router"]
