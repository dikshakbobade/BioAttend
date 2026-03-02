"""
Security utilities for authentication and encryption.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
import secrets

from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
import base64

from app.core.config import get_settings

settings = get_settings()

# Password hashing using bcrypt directly (bypassing passlib due to version conflicts on Python 3.14)
import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash using bcrypt."""
    try:
        if isinstance(plain_password, str):
            plain_password = plain_password.encode("utf-8")
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode("utf-8")
        return bcrypt.checkpw(plain_password, hashed_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Generate password hash using bcrypt."""
    if isinstance(password, str):
        password = password.encode("utf-8")
    return bcrypt.hashpw(password, bcrypt.gensalt()).decode("utf-8")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:

    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_api_key() -> str:
    """Generate a secure random API key."""
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """Hash API key using SHA-256."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verify API key against its hash."""
    return hash_api_key(plain_key) == hashed_key


class EncryptionService:
    """Service for encrypting/decrypting biometric templates."""
    
    def __init__(self):
        # Ensure encryption key is 32 bytes, base64 encoded
        key = settings.ENCRYPTION_KEY.encode()
        if len(key) < 32:
            key = key.ljust(32, b'0')
        elif len(key) > 32:
            key = key[:32]
        self._fernet = Fernet(base64.urlsafe_b64encode(key))
    
    def encrypt(self, data: bytes) -> bytes:
        """Encrypt data using Fernet (AES-256)."""
        return self._fernet.encrypt(data)
    
    def decrypt(self, encrypted_data: bytes) -> bytes:
        """Decrypt data using Fernet."""
        return self._fernet.decrypt(encrypted_data)
    
    def encrypt_template(self, template_data: bytes) -> bytes:
        """Encrypt a biometric template."""
        return self.encrypt(template_data)
    
    def decrypt_template(self, encrypted_template: bytes) -> bytes:
        """Decrypt a biometric template."""
        return self.decrypt(encrypted_template)


# Singleton encryption service
encryption_service = EncryptionService()
