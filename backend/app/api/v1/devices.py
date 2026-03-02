"""
Device management API endpoints.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import AdminUser, DeviceType, AdminRole
from app.schemas import (
    DeviceCreate,
    DeviceResponse,
    DeviceWithApiKey,
    DeviceListResponse,
)
from app.services import device_service
from app.api.v1.dependencies import get_current_admin, require_role

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=DeviceListResponse)
async def list_devices(
    device_type: Optional[DeviceType] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin)
):
    """List all registered devices."""
    devices, total = await device_service.get_all(
        db=db,
        device_type=device_type,
        is_active=is_active
    )
    
    return DeviceListResponse(
        items=[
            DeviceResponse(
                id=d.id,
                device_id=d.device_id,
                device_name=d.device_name,
                device_type=d.device_type,
                location=d.location,
                is_active=d.is_active,
                last_seen=d.last_seen,
                created_at=d.created_at
            )
            for d in devices
        ],
        total=total
    )


@router.post("", response_model=DeviceWithApiKey, status_code=status.HTTP_201_CREATED)
async def register_device(
    device_data: DeviceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_role([AdminRole.SUPER_ADMIN, AdminRole.ADMIN]))
):
    """
    Register a new device.
    Returns the device with its API key (only shown once).
    """
    try:
        device, api_key = await device_service.create(db, device_data)
        
        return DeviceWithApiKey(
            id=device.id,
            device_id=device.device_id,
            device_name=device.device_name,
            device_type=device.device_type,
            location=device.location,
            is_active=device.is_active,
            last_seen=device.last_seen,
            created_at=device.created_at,
            api_key=api_key
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin)
):
    """Get device by device_id."""
    device = await device_service.get_by_id(db, device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    return DeviceResponse(
        id=device.id,
        device_id=device.device_id,
        device_name=device.device_name,
        device_type=device.device_type,
        location=device.location,
        is_active=device.is_active,
        last_seen=device.last_seen,
        created_at=device.created_at
    )


@router.post("/{device_id}/deactivate")
async def deactivate_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_role([AdminRole.SUPER_ADMIN, AdminRole.ADMIN]))
):
    """Deactivate a device."""
    success = await device_service.deactivate(db, device_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    return {"message": f"Device {device_id} deactivated"}


@router.post("/{device_id}/activate")
async def activate_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_role([AdminRole.SUPER_ADMIN, AdminRole.ADMIN]))
):
    """Activate a device."""
    success = await device_service.activate(db, device_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    return {"message": f"Device {device_id} activated"}


@router.post("/{device_id}/regenerate-key")
async def regenerate_api_key(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_role([AdminRole.SUPER_ADMIN]))
):
    """Regenerate API key for a device (Super Admin only)."""
    api_key = await device_service.regenerate_api_key(db, device_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    return {
        "message": f"API key regenerated for device {device_id}",
        "api_key": api_key
    }


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_role([AdminRole.SUPER_ADMIN]))
):
    """Delete a device (Super Admin only)."""
    success = await device_service.delete(db, device_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
