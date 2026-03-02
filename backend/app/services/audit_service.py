"""
Audit service for security logging and compliance.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


class AuditService:
    """Service for audit logging."""
    
    async def log_event(
        self,
        db: AsyncSession,
        event_type: str,
        employee_id: Optional[UUID] = None,
        device_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_payload: Optional[dict] = None,
        response_status: Optional[str] = None,
        confidence_score: Optional[float] = None,
        error_message: Optional[str] = None
    ) -> AuditLog:
        """Create an audit log entry."""
        # Sanitize payload - remove sensitive data
        if request_payload:
            sanitized_payload = self._sanitize_payload(request_payload)
        else:
            sanitized_payload = None
        
        audit_log = AuditLog(
            event_type=event_type,
            employee_id=employee_id,
            device_id=device_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_payload=sanitized_payload,
            response_status=response_status,
            confidence_score=confidence_score,
            error_message=error_message
        )
        db.add(audit_log)
        await db.commit()
        await db.refresh(audit_log)
        return audit_log
    
    def _sanitize_payload(self, payload: dict) -> dict:
        """Remove sensitive data from payload before logging."""
        sensitive_keys = {
            'password', 'api_key', 'token', 'secret', 
            'embedding', 'template', 'template_data',
            'biometric_data', 'fingerprint', 'face_data'
        }
        
        sanitized = {}
        for key, value in payload.items():
            if key.lower() in sensitive_keys:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_payload(value)
            elif isinstance(value, list) and len(value) > 10:
                sanitized[key] = f"[LIST: {len(value)} items]"
            else:
                sanitized[key] = value
        
        return sanitized
    
    async def get_logs(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        event_type: Optional[str] = None,
        employee_id: Optional[UUID] = None,
        device_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Tuple[List[AuditLog], int]:
        """Get audit logs with filters and pagination."""
        query = select(AuditLog)
        count_query = select(func.count(AuditLog.id))
        
        if event_type:
            query = query.where(AuditLog.event_type == event_type)
            count_query = count_query.where(AuditLog.event_type == event_type)
        
        if employee_id:
            query = query.where(AuditLog.employee_id == employee_id)
            count_query = count_query.where(AuditLog.employee_id == employee_id)
        
        if device_id:
            query = query.where(AuditLog.device_id == device_id)
            count_query = count_query.where(AuditLog.device_id == device_id)
        
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
            count_query = count_query.where(AuditLog.created_at >= start_date)
        
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)
            count_query = count_query.where(AuditLog.created_at <= end_date)
        
        query = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        logs = list(result.scalars().all())
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        return logs, total
    
    async def log_verification_attempt(
        self,
        db: AsyncSession,
        biometric_type: str,
        device_id: str,
        ip_address: Optional[str],
        success: bool,
        employee_id: Optional[UUID] = None,
        confidence_score: Optional[float] = None,
        error_message: Optional[str] = None
    ) -> AuditLog:
        """Log a biometric verification attempt."""
        event_type = f"VERIFICATION_{biometric_type}"
        response_status = "SUCCESS" if success else "FAILED"
        
        return await self.log_event(
            db=db,
            event_type=event_type,
            employee_id=employee_id,
            device_id=device_id,
            ip_address=ip_address,
            response_status=response_status,
            confidence_score=confidence_score,
            error_message=error_message
        )
    
    async def log_admin_action(
        self,
        db: AsyncSession,
        action: str,
        admin_id: UUID,
        ip_address: Optional[str],
        details: Optional[dict] = None
    ) -> AuditLog:
        """Log an admin action."""
        return await self.log_event(
            db=db,
            event_type=f"ADMIN_{action}",
            employee_id=admin_id,
            ip_address=ip_address,
            request_payload=details,
            response_status="SUCCESS"
        )
    
    async def get_failed_verifications_count(
        self,
        db: AsyncSession,
        minutes: int = 5
    ) -> int:
        """Get count of failed verifications in last N minutes."""
        since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        result = await db.execute(
            select(func.count(AuditLog.id))
            .where(
                AuditLog.event_type.like("VERIFICATION_%"),
                AuditLog.response_status == "FAILED",
                AuditLog.created_at >= since
            )
        )
        return result.scalar()



# Singleton instance
audit_service = AuditService()
