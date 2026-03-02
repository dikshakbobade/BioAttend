"""
Admin service for user authentication and management.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdminUser, AdminRole
from app.core.security import (
    verify_password, 
    get_password_hash, 
    create_access_token
)
from app.core.config import get_settings
from app.schemas import AdminUserCreate

settings = get_settings()


class AdminService:
    """Service for admin user management and authentication."""
    
    async def get_by_id(self, db: AsyncSession, admin_id: UUID) -> Optional[AdminUser]:
        """Get admin user by ID."""
        result = await db.execute(
            select(AdminUser).where(AdminUser.id == admin_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[AdminUser]:
        """Get admin user by username."""
        result = await db.execute(
            select(AdminUser).where(AdminUser.username == username)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[AdminUser]:
        """Get admin user by email."""
        result = await db.execute(
            select(AdminUser).where(AdminUser.email == email)
        )
        return result.scalar_one_or_none()
    
    async def authenticate(
        self, 
        db: AsyncSession, 
        username: str, 
        password: str
    ) -> Optional[AdminUser]:
        """Authenticate admin user."""
        user = await self.get_by_username(db, username)
        if not user:
            return None
        
        if not user.is_active:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        # Update last login
        user.last_login = datetime.now(timezone.utc)
        await db.commit()
        
        return user
    
    async def create_access_token_for_user(
        self, 
        user: AdminUser
    ) -> tuple[str, int]:
        """Create JWT access token for admin user."""
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token = create_access_token(
            data={
                "sub": str(user.id),
                "username": user.username,
                "role": user.role.value
            },
            expires_delta=expires_delta
        )
        return token, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    async def create(
        self, 
        db: AsyncSession, 
        user_data: AdminUserCreate
    ) -> AdminUser:
        """Create a new admin user."""
        # Check if username or email already exists
        existing = await self.get_by_username(db, user_data.username)
        if existing:
            raise ValueError("Username already exists")
        
        existing = await self.get_by_email(db, user_data.email)
        if existing:
            raise ValueError("Email already exists")
        
        user = AdminUser(
            username=user_data.username,
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            role=AdminRole(user_data.role.value),
            is_active=True
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        return user
    
    async def update_password(
        self, 
        db: AsyncSession, 
        admin_id: UUID, 
        new_password: str
    ) -> bool:
        """Update admin user password."""
        user = await self.get_by_id(db, admin_id)
        if not user:
            return False
        
        user.password_hash = get_password_hash(new_password)
        await db.commit()
        return True
    
    async def deactivate(self, db: AsyncSession, admin_id: UUID) -> bool:
        """Deactivate admin user."""
        user = await self.get_by_id(db, admin_id)
        if not user:
            return False
        
        user.is_active = False
        await db.commit()
        return True
    
    async def create_initial_admin(
        self, 
        db: AsyncSession,
        username: str = "admin",
        email: str = "admin@company.com",
        password: str = "admin123",
        full_name: str = "System Administrator"
    ) -> Optional[AdminUser]:
        """Create initial admin user if none exists."""
        # Check if any admin exists
        result = await db.execute(select(AdminUser).limit(1))
        if result.scalar_one_or_none():
            return None
        
        user = AdminUser(
            username=username,
            email=email,
            password_hash=get_password_hash(password),
            full_name=full_name,
            role=AdminRole.SUPER_ADMIN,
            is_active=True
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        return user


# Singleton instance
admin_service = AdminService()
