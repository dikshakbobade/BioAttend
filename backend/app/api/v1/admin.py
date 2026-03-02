from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import AdminUser, AdminRole
from app.schemas import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminUserCreate,
    AdminUserResponse,
)
from app.services import admin_service
from app.api.v1.dependencies import get_current_admin, require_role

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/login", response_model=AdminLoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Admin login endpoint."""
    user = await admin_service.authenticate(
        db=db,
        username=form_data.username,
        password=form_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token, expires_in = await admin_service.create_access_token_for_user(user)
    
    return AdminLoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=AdminUserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            last_login=user.last_login,
            created_at=user.created_at
        )
    )


@router.get("/me", response_model=AdminUserResponse)
async def get_current_user(
    current_user: AdminUser = Depends(get_current_admin)
):
    """Get current authenticated admin user."""
    return AdminUserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        last_login=current_user.last_login,
        created_at=current_user.created_at
    )


@router.post("/users", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_user(
    user_data: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(require_role([AdminRole.SUPER_ADMIN]))
):
    """Create a new admin user (Super Admin only)."""
    try:
        user = await admin_service.create(db, user_data)
        return AdminUserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            last_login=user.last_login,
            created_at=user.created_at
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_admin)
):
    """Change current user's password."""
    from app.core.security import verify_password
    
    if not verify_password(current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters"
        )
    
    await admin_service.update_password(db, current_user.id, new_password)
    
    return {"message": "Password changed successfully"}

import secrets
from datetime import datetime, timedelta, timezone

# In-memory reset tokens (simple approach)
_reset_tokens = {}

@router.post("/forgot-password")
async def forgot_password(
    email: str,
    db: AsyncSession = Depends(get_db)
):
    """Send password reset code to admin email."""
    from sqlalchemy import select
    from app.services.email_service import EmailService

    result = await db.execute(
        select(AdminUser).where(AdminUser.email == email)
    )
    user = result.scalar_one_or_none()

    # Always return success (don't reveal if email exists)
    if not user:
        return {"message": "If the email exists, a reset code has been sent."}

    # Generate 6-digit code
    code = str(secrets.randbelow(900000) + 100000)
    _reset_tokens[email] = {
        "code": code,
        "expires": datetime.now(timezone.utc) + timedelta(minutes=15),
        "user_id": user.id
    }

    # Send email
    email_service = EmailService()
    subject = "BioAttend - Password Reset Code"
    body = f"""
    <div style="font-family:Arial,sans-serif;max-width:500px;margin:0 auto;padding:20px;">
        <h2 style="color:#1e40af;">Password Reset</h2>
        <p>Hi {user.full_name},</p>
        <p>Your password reset code is:</p>
        <div style="background:#f0f4ff;border:2px solid #1e40af;border-radius:8px;padding:20px;text-align:center;margin:20px 0;">
            <span style="font-size:32px;font-weight:bold;letter-spacing:8px;color:#1e40af;">{code}</span>
        </div>
        <p>This code expires in <strong>15 minutes</strong>.</p>
        <p>If you didn't request this, ignore this email.</p>
        <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0;">
        <p style="color:#9ca3af;font-size:12px;">— BioAttend System</p>
    </div>
    """
    try:
        await email_service.send_email(subject, body, email)
    except Exception as e:
        import logging; logging.getLogger(__name__).error(f"Failed to send reset email: {e}")

    return {"message": "If the email exists, a reset code has been sent."}


@router.post("/reset-password")
async def reset_password(
    email: str,
    code: str,
    new_password: str,
    db: AsyncSession = Depends(get_db)
):
    """Reset password using the code sent via email."""
    token_data = _reset_tokens.get(email)

    if not token_data:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")

    if datetime.now(timezone.utc) > token_data["expires"]:
        del _reset_tokens[email]
        raise HTTPException(status_code=400, detail="Reset code has expired")

    if token_data["code"] != code:
        raise HTTPException(status_code=400, detail="Invalid reset code")

    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    await admin_service.update_password(db, token_data["user_id"], new_password)
    del _reset_tokens[email]

    return {"message": "Password reset successfully"}

