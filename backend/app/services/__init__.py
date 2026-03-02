"""Services module containing business logic."""
from app.services.employee_service import employee_service
from app.services.matching_service import matching_service, template_cache
from app.services.attendance_service import attendance_service
from app.services.audit_service import audit_service
from app.services.device_service import device_service
from app.services.admin_service import admin_service
from app.services.email_service import email_service

__all__ = [
    "employee_service",
    "matching_service",
    "template_cache",
    "attendance_service",
    "audit_service",
    "device_service",
    "admin_service",
    "email_service",
]