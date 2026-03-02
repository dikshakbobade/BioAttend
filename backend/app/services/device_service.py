"""
Device service for managing biometric devices.
"""
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Device, DeviceType
from app.core.security import generate_api_key, hash_api_key, verify_api_key
from app.schemas import DeviceCreate


class DeviceService:
    """Service for device management."""
    
    async def get_by_id(self, db: AsyncSession, device_id: str) -> Optional[Device]:
        """Get device by device_id."""
        result = await db.execute(
            select(Device).where(Device.device_id == device_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_uuid(self, db: AsyncSession, uuid: UUID) -> Optional[Device]:
        """Get device by UUID."""
        result = await db.execute(
            select(Device).where(Device.id == uuid)
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        db: AsyncSession,
        device_type: Optional[DeviceType] = None,
        is_active: Optional[bool] = None
    ) -> Tuple[List[Device], int]:
        """Get all devices with optional filters."""
        query = select(Device)
        count_query = select(func.count(Device.id))
        
        if device_type:
            query = query.where(Device.device_type == device_type)
            count_query = count_query.where(Device.device_type == device_type)
        
        if is_active is not None:
            query = query.where(Device.is_active == is_active)
            count_query = count_query.where(Device.is_active == is_active)
        
        query = query.order_by(Device.created_at.desc())
        
        result = await db.execute(query)
        devices = list(result.scalars().all())
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        return devices, total
    
    async def create(
        self, 
        db: AsyncSession, 
        device_data: DeviceCreate
    ) -> Tuple[Device, str]:
        """
        Create a new device and generate API key.
        Returns (device, plain_api_key)
        """
        # Check if device_id already exists
        existing = await self.get_by_id(db, device_data.device_id)
        if existing:
            raise ValueError(f"Device with ID {device_data.device_id} already exists")
        
        # Generate API key
        api_key = generate_api_key()
        api_key_hash = hash_api_key(api_key)
        
        device = Device(
            device_id=device_data.device_id,
            device_name=device_data.device_name,
            device_type=DeviceType(device_data.device_type.value),
            api_key_hash=api_key_hash,
            location=device_data.location,
            is_active=True
        )
        
        db.add(device)
        await db.commit()
        await db.refresh(device)
        
        return device, api_key
    
    async def verify_device_api_key(
        self, 
        db: AsyncSession, 
        device_id: str, 
        api_key: str
    ) -> Optional[Device]:
        """Verify device API key and return device if valid."""
        device = await self.get_by_id(db, device_id)
        if not device:
            return None
        
        if not device.is_active:
            return None
        
        if not verify_api_key(api_key, device.api_key_hash):
            return None
        
        # Update last seen
        device.last_seen = datetime.now(timezone.utc)
        await db.commit()
        
        return device
    
    async def deactivate(self, db: AsyncSession, device_id: str) -> bool:
        """Deactivate a device."""
        device = await self.get_by_id(db, device_id)
        if not device:
            return False
        
        device.is_active = False
        await db.commit()
        return True
    
    async def activate(self, db: AsyncSession, device_id: str) -> bool:
        """Activate a device."""
        device = await self.get_by_id(db, device_id)
        if not device:
            return False
        
        device.is_active = True
        await db.commit()
        return True
    
    async def regenerate_api_key(
        self, 
        db: AsyncSession, 
        device_id: str
    ) -> Optional[str]:
        """Regenerate API key for a device."""
        device = await self.get_by_id(db, device_id)
        if not device:
            return None
        
        api_key = generate_api_key()
        device.api_key_hash = hash_api_key(api_key)
        await db.commit()
        
        return api_key
    
    async def delete(self, db: AsyncSession, device_id: str) -> bool:
        """Delete a device."""
        device = await self.get_by_id(db, device_id)
        if not device:
            return False
        
        await db.delete(device)
        await db.commit()
        return True
    
    async def get_active_device_count(self, db: AsyncSession) -> int:
        """Get count of active devices."""
        result = await db.execute(
            select(func.count(Device.id)).where(Device.is_active == True)
        )
        return result.scalar()


# Singleton instance
device_service = DeviceService()
