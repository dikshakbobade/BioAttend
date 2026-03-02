"""
Attendance API endpoints.
"""
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy import select

from app.db import get_db
from app.models import AdminUser, AttendanceLog, Employee
from app.schemas import (
    AttendanceLogResponse,
    AttendanceReportRequest,
    AttendanceReportResponse,
    TodayAttendanceResponse,
)
from app.services import attendance_service
from app.api.v1.dependencies import get_current_admin

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.get("/today", response_model=TodayAttendanceResponse)
async def get_today_attendance(
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin)
):
    """Get today's attendance summary."""
    summary = await attendance_service.get_today_summary(db)
    
    logs = []
    for log in summary["logs"]:
        # Get employee info
        result = await db.execute(
            select(Employee).where(Employee.id == log.employee_id)
        )
        employee = result.scalar_one_or_none()
        
        working_hours = await attendance_service.calculate_working_hours(log)
        
        logs.append(AttendanceLogResponse(
            id=log.id,
            employee_id=log.employee_id,
            employee_name=employee.full_name if employee else None,
            employee_code=employee.employee_code if employee else None,
            date=log.date,
            check_in_time=log.check_in_time,
            check_out_time=log.check_out_time,
            check_in_method=log.check_in_method,
            check_out_method=log.check_out_method,
            working_hours=working_hours
        ))
    
    return TodayAttendanceResponse(
        date=summary["date"],
        total_employees=summary["total_employees"],
        checked_in=summary["checked_in"],
        checked_out=summary["checked_out"],
        absent=summary["absent"],
        logs=logs
    )


@router.get("/report", response_model=AttendanceReportResponse)
async def get_attendance_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    employee_id: Optional[UUID] = None,
    department: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin)
):
    """Get attendance report for date range."""
    attendance_logs = await attendance_service.get_attendance_by_date_range(
        db=db,
        start_date=start_date,
        end_date=end_date,
        employee_id=employee_id,
        department=department
    )
    
    logs = []
    for log in attendance_logs:
        # Get employee info
        result = await db.execute(
            select(Employee).where(Employee.id == log.employee_id)
        )
        employee = result.scalar_one_or_none()
        
        working_hours = await attendance_service.calculate_working_hours(log)
        
        logs.append(AttendanceLogResponse(
            id=log.id,
            employee_id=log.employee_id,
            employee_name=employee.full_name if employee else None,
            employee_code=employee.employee_code if employee else None,
            date=log.date,
            check_in_time=log.check_in_time,
            check_out_time=log.check_out_time,
            check_in_method=log.check_in_method,
            check_out_method=log.check_out_method,
            working_hours=working_hours
        ))
    
    return AttendanceReportResponse(
        records=logs,
        total_records=len(logs),
        start_date=start_date,
        end_date=end_date
    )


@router.get("/employee/{employee_id}", response_model=list[AttendanceLogResponse])
async def get_employee_attendance(
    employee_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin)
):
    """Get attendance history for a specific employee."""
    if not start_date:
        start_date = date.today().replace(day=1)  # First of current month
    if not end_date:
        end_date = date.today()
    
    logs = await attendance_service.get_attendance_by_date_range(
        db=db,
        start_date=start_date,
        end_date=end_date,
        employee_id=employee_id
    )
    
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )
    employee = result.scalar_one_or_none()
    
    response = []
    for log in logs:
        working_hours = await attendance_service.calculate_working_hours(log)
        response.append(AttendanceLogResponse(
            id=log.id,
            employee_id=log.employee_id,
            employee_name=employee.full_name if employee else None,
            employee_code=employee.employee_code if employee else None,
            date=log.date,
            check_in_time=log.check_in_time,
            check_out_time=log.check_out_time,
            check_in_method=log.check_in_method,
            check_out_method=log.check_out_method,
            working_hours=working_hours
        ))
    
    return response


@router.get("/monthly/{employee_id}")
async def get_monthly_report(
    employee_id: UUID,
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin)
):
    """Get monthly attendance report for an employee."""
    return await attendance_service.get_monthly_report(
        db=db,
        employee_id=employee_id,
        year=year,
        month=month
    )
