"""
Employee API endpoints.
"""
import logging

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import AdminUser, EmployeeStatus, BiometricType
from app.schemas import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
    EmployeeListResponse,
    BiometricTemplateCreate,
    BiometricTemplateResponse,
    FaceEnrollProfileRequest,
    FaceEnrollProfileResponse,
)
from app.services import employee_service, matching_service
from app.api.v1.dependencies import get_current_admin

router = APIRouter(prefix="/employees", tags=["employees"])
logger = logging.getLogger(__name__)


# ============================================================
# EMPLOYEE LIST
# ============================================================

@router.get("", response_model=EmployeeListResponse)
async def list_employees(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[EmployeeStatus] = None,
    department: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin),
):
    skip = (page - 1) * page_size

    employees, total = await employee_service.get_all(
        db=db,
        skip=skip,
        limit=page_size,
        status=status,
        department=department,
    )

    items = []
    for emp in employees:
        has_face, has_fp = await employee_service.get_employee_template_status(
            db, emp.id
        )

        items.append(
            EmployeeResponse(
                id=emp.id,
                employee_code=emp.employee_code,
                full_name=emp.full_name,
                email=emp.email,
                department=emp.department,
                designation=emp.designation,
                status=emp.status,
                created_at=emp.created_at,
                updated_at=emp.updated_at,
                has_face_template=has_face,
                has_fingerprint_template=has_fp,
            )
        )

    return EmployeeListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


# ============================================================
# CREATE EMPLOYEE
# ============================================================

@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_employee(
    employee_data: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin),
):
    if await employee_service.get_by_code(db, employee_data.employee_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee code already exists",
        )

    if await employee_service.get_by_email(db, employee_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists",
        )

    employee = await employee_service.create(db, employee_data)

    return EmployeeResponse(
        id=employee.id,
        employee_code=employee.employee_code,
        full_name=employee.full_name,
        email=employee.email,
        department=employee.department,
        designation=employee.designation,
        status=employee.status,
        created_at=employee.created_at,
        updated_at=employee.updated_at,
        has_face_template=False,
        has_fingerprint_template=False,
    )


# ============================================================
# GET EMPLOYEE
# ============================================================

@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin),
):
    employee = await employee_service.get_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    has_face, has_fp = await employee_service.get_employee_template_status(
        db, employee.id
    )

    return EmployeeResponse(
        id=employee.id,
        employee_code=employee.employee_code,
        full_name=employee.full_name,
        email=employee.email,
        department=employee.department,
        designation=employee.designation,
        status=employee.status,
        created_at=employee.created_at,
        updated_at=employee.updated_at,
        has_face_template=has_face,
        has_fingerprint_template=has_fp,
    )


# ============================================================
# UPDATE EMPLOYEE
# ============================================================

@router.put("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: UUID,
    employee_data: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin),
):
    employee = await employee_service.update(db, employee_id, employee_data)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    has_face, has_fp = await employee_service.get_employee_template_status(
        db, employee.id
    )

    return EmployeeResponse(
        id=employee.id,
        employee_code=employee.employee_code,
        full_name=employee.full_name,
        email=employee.email,
        department=employee.department,
        designation=employee.designation,
        status=employee.status,
        created_at=employee.created_at,
        updated_at=employee.updated_at,
        has_face_template=has_face,
        has_fingerprint_template=has_fp,
    )


# ============================================================
# DELETE EMPLOYEE
# ============================================================

@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin),
):
    if not await employee_service.delete(db, employee_id):
        raise HTTPException(status_code=404, detail="Employee not found")


# ============================================================
# REGISTER BIOMETRIC (🔥 FIXED)
# ============================================================

@router.post(
    "/{employee_id}/biometrics",
    response_model=BiometricTemplateResponse,
)
async def register_biometric(
    employee_id: UUID,
    payload: BiometricTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin),
):
    employee = await employee_service.get_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    if not payload.template_data:
        raise HTTPException(
            status_code=400,
            detail="Biometric template data is required",
        )

    biometric_type = BiometricType[payload.biometric_type.name]

    try:
        template = await matching_service.register_template(
            db=db,
            employee_id=employee_id,
            biometric_type=biometric_type,
            template_data=payload.template_data,
            quality_score=payload.quality_score,
        )
    except ValueError as e:
        logger.warning(f"Validation error during biometric registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Internal error during biometric registration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Biometric processing failed: {str(e)}"
        )


    return BiometricTemplateResponse(
        id=template.id,
        employee_id=template.employee_id,
        biometric_type=template.biometric_type,
        template_version=template.template_version,
        is_active=template.is_active,
        quality_score=template.quality_score,
        created_at=template.created_at,
    )


# ============================================================
# ENROLL FACE PROFILE (3 SHOTS)
# ============================================================

@router.post(
    "/{employee_id}/enroll-face-profile",
    response_model=FaceEnrollProfileResponse,
)
async def enroll_face_profile(
    employee_id: UUID,
    payload: FaceEnrollProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin),
):
    """
    Handle guided enrollment with 3 images.
    Extracts embeddings, averages them, and stores the canonical profile.
    """
    employee = await employee_service.get_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    try:
        result = await matching_service.register_face_profile(
            db=db,
            employee_id=employee_id,
            front_image=payload.front_image,
            left_image=payload.left_image,
            right_image=payload.right_image
        )
        return FaceEnrollProfileResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Face profile enrollment failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during enrollment")


# ============================================================
# GET BIOMETRICS
# ============================================================

@router.get(
    "/{employee_id}/biometrics",
    response_model=list[BiometricTemplateResponse],
)
async def get_employee_biometrics(
    employee_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin),
):
    employee = await employee_service.get_by_id(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    templates = await matching_service.get_employee_templates(db, employee_id)

    return [
        BiometricTemplateResponse(
            id=t.id,
            employee_id=t.employee_id,
            biometric_type=t.biometric_type,
            template_version=t.template_version,
            is_active=t.is_active,
            quality_score=t.quality_score,
            created_at=t.created_at,
        )
        for t in templates
    ]
