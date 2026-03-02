"""
Application configuration settings.
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings
from pydantic import field_validator
import json


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ENCRYPTION_KEY: str

    # Biometric Thresholds
    FACE_SIMILARITY_THRESHOLD: float = 0.60
    FINGERPRINT_MATCH_THRESHOLD: int = 70
    LIVENESS_THRESHOLD: float = 0.70

    # Anti-Spoof / Liveness
    ANTISPOOF_THRESHOLD: float = 0.5
    ANTISPOOF_MODEL_PATH: str = ""
    ACTIVE_LIVENESS_MIN_CHECKS: int = 2  # out of 3 (blink, nod, smile)
    INSIGHTFACE_CTX_ID: int = -1  # -1 = CPU, 0 = GPU

    # Attendance Settings
    COOLDOWN_MINUTES: int = 5
    WORKDAY_START_HOUR: int = 6
    WORKDAY_END_HOUR: int = 22

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # Rate Limiting
    RATE_LIMIT_PER_DEVICE: int = 30
    RATE_LIMIT_PER_IP: int = 100

    # Email Settings
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    ADMIN_EMAIL: str = ""
    OFFICE_START_HOUR: int = 11
    OFFICE_START_MINUTE: int = 0
    OFFICE_END_HOUR: int = 18
    ABSENT_ALERT_MINUTES: int = 30
    DAILY_SUMMARY_HOUR: int = 19

    # Debug
    DEBUG: bool = False

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()