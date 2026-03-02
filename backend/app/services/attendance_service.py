"""
Attendance service for tracking employee check-ins and check-outs.
"""
from datetime import datetime, date, timedelta, timezone
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AttendanceLog, Employee, BiometricType, EmployeeStatus
from app.core.config import get_settings

settings = get_settings()

# IST timezone
IST = timezone(timedelta(hours=5, minutes=30))

def now_ist() -> datetime:
    """Get current IST time as naive datetime (for DB storage)."""
    return datetime.now(IST).replace(tzinfo=None)


class AttendanceService:
    """Service for attendance operations."""

    def __init__(self):
        self.cooldown_minutes = settings.COOLDOWN_MINUTES
        self.workday_start = settings.WORKDAY_START_HOUR
        self.workday_end = settings.WORKDAY_END_HOUR

    async def get_today_attendance(
        self,
        db: AsyncSession,
        employee_id: UUID
    ) -> Optional[AttendanceLog]:
        today = date.today()
        result = await db.execute(
            select(AttendanceLog).where(
                AttendanceLog.employee_id == employee_id,
                AttendanceLog.date == today
            )
        )
        return result.scalar_one_or_none()

    async def check_cooldown(
        self,
        db: AsyncSession,
        employee_id: UUID
    ) -> Tuple[bool, Optional[datetime]]:
        attendance = await self.get_today_attendance(db, employee_id)
        if not attendance:
            return False, None

        last_action = attendance.check_out_time or attendance.check_in_time
        if not last_action:
            return False, None

        cooldown_end = last_action + timedelta(minutes=self.cooldown_minutes)
        now = now_ist()

        if now < cooldown_end:
            return True, last_action

        return False, last_action

    def is_within_working_hours(self) -> bool:
        now = now_ist()
        return self.workday_start <= now.hour < self.workday_end

    async def mark_attendance(
        self,
        db: AsyncSession,
        employee_id: UUID,
        biometric_type: BiometricType,
        device_id: str,
        confidence_score: float
    ) -> Tuple[AttendanceLog, str]:
        today = date.today()
        now = now_ist()

        attendance = await self.get_today_attendance(db, employee_id)

        if attendance is None:
            attendance = AttendanceLog(
                employee_id=employee_id,
                date=today,
                check_in_time=now,
                check_in_method=biometric_type,
                check_in_device_id=device_id,
                check_in_confidence=confidence_score
            )
            db.add(attendance)
            action = "CHECK_IN"
        else:
            attendance.check_out_time = now
            attendance.check_out_method = biometric_type
            attendance.check_out_device_id = device_id
            attendance.check_out_confidence = confidence_score
            action = "CHECK_OUT"

        await db.commit()
        await db.refresh(attendance)

        return attendance, action

    async def get_attendance_by_date_range(
        self,
        db: AsyncSession,
        start_date: date,
        end_date: date,
        employee_id: Optional[UUID] = None,
        department: Optional[str] = None
    ) -> List[AttendanceLog]:
        query = (
            select(AttendanceLog)
            .join(Employee)
            .where(
                AttendanceLog.date >= start_date,
                AttendanceLog.date <= end_date
            )
        )

        if employee_id:
            query = query.where(AttendanceLog.employee_id == employee_id)

        if department:
            query = query.where(Employee.department == department)

        query = query.order_by(AttendanceLog.date.desc(), AttendanceLog.check_in_time.desc())

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_today_summary(
        self,
        db: AsyncSession
    ) -> dict:
        today = date.today()

        total_result = await db.execute(
            select(func.count(Employee.id))
            .where(Employee.status == EmployeeStatus.ACTIVE)
        )
        total_employees = total_result.scalar()

        attendance_result = await db.execute(
            select(AttendanceLog)
            .join(Employee)
            .where(
                AttendanceLog.date == today,
                Employee.status == EmployeeStatus.ACTIVE
            )
        )
        today_logs = list(attendance_result.scalars().all())

        checked_in = len(today_logs)
        checked_out = sum(1 for log in today_logs if log.check_out_time is not None)
        absent = total_employees - checked_in

        return {
            "date": today,
            "total_employees": total_employees,
            "checked_in": checked_in,
            "checked_out": checked_out,
            "absent": absent,
            "logs": today_logs
        }

    async def calculate_working_hours(
        self,
        attendance: AttendanceLog
    ) -> Optional[float]:
        if not attendance.check_in_time or not attendance.check_out_time:
            return None

        duration = attendance.check_out_time - attendance.check_in_time
        hours = duration.total_seconds() / 3600
        return round(hours, 2)

    async def get_monthly_report(
        self,
        db: AsyncSession,
        employee_id: UUID,
        year: int,
        month: int
    ) -> dict:
        from calendar import monthrange

        start_date = date(year, month, 1)
        _, last_day = monthrange(year, month)
        end_date = date(year, month, last_day)

        logs = await self.get_attendance_by_date_range(
            db, start_date, end_date, employee_id
        )

        total_days = 0
        total_hours = 0.0
        late_days = 0

        for log in logs:
            total_days += 1
            hours = await self.calculate_working_hours(log)
            if hours:
                total_hours += hours

            if log.check_in_time and log.check_in_time.hour >= 9:
                late_days += 1

        return {
            "employee_id": str(employee_id),
            "year": year,
            "month": month,
            "total_present_days": total_days,
            "total_working_hours": round(total_hours, 2),
            "late_days": late_days,
            "average_hours_per_day": round(total_hours / total_days, 2) if total_days > 0 else 0
        }


# Singleton instance
attendance_service = AttendanceService()