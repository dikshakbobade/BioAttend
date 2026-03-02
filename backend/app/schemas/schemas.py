"""
Pydantic schemas for request/response validation.
Compatible with FastAPI + Pydantic v2
"""

from datetime import datetime, date
from typing import Optional, List
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ============================================================
# ENUMS
# ============================================================

class EmployeeStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ON_LEAVE = "ON_LEAVE"
    TERMINATED = "TERMINATED"


class BiometricTypeEnum(str, Enum):
    FACE = "FACE"
    FINGERPRINT = "FINGERPRINT"


class DeviceTypeEnum(str, Enum):
    FACE_CAMERA = "FACE_CAMERA"
    FINGERPRINT_SCANNER = "FINGERPRINT_SCANNER"


class AdminRoleEnum(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    VIEWER = "VIEWER"


# ============================================================
# EMPLOYEE SCHEMAS
# ============================================================

class EmployeeBase(BaseModel):
    employee_code: str = Field(..., min_length=1, max_length=50)
    full_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    department: str = Field(..., min_length=1, max_length=100)
    designation: Optional[str] = Field(None, max_length=100)


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    department: Optional[str] = Field(None, min_length=1, max_length=100)
    designation: Optional[str] = Field(None, max_length=100)
    status: Optional[EmployeeStatusEnum] = None


class EmployeeResponse(EmployeeBase):
    id: UUID
    status: EmployeeStatusEnum
    created_at: datetime
    updated_at: datetime
    has_face_template: bool = False
    has_fingerprint_template: bool = False

    model_config = ConfigDict(from_attributes=True)


class FaceDetectionResult(BaseModel):
    """Result of fast face detection with real-time quality metrics."""
    detected: bool
    faces: List[dict] = []
    message: str = ""
    brightness: float = 0.0
    is_centered: bool = False
    quality_label: str = "Poor"  # "Good" or "Poor"


class EmployeeListResponse(BaseModel):
    items: List[EmployeeResponse]
    total: int
    page: int
    page_size: int


# ============================================================
# BIOMETRIC REGISTRATION
# ============================================================

class BiometricTemplateCreate(BaseModel):
    biometric_type: BiometricTypeEnum
    template_data: str = Field(..., min_length=100)
    quality_score: float = Field(default=80, ge=0, le=100)


class FaceEnrollProfileRequest(BaseModel):
    front_image: str = Field(..., min_length=100)
    left_image: str = Field(..., min_length=100)
    right_image: str = Field(..., min_length=100)


class FaceEnrollProfileResponse(BaseModel):
    success: bool
    message: str
    quality_scores: dict  # {"front": 85.0, "left": 78.0, "right": 82.0}
    average_quality: float


class BiometricTemplateResponse(BaseModel):
    id: UUID
    employee_id: UUID
    biometric_type: BiometricTypeEnum
    template_version: int
    is_active: bool
    quality_score: Optional[float]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# BIOMETRIC VERIFICATION (FACE + FINGERPRINT)
# ============================================================

class FaceVerifyRequest(BaseModel):
    image_base64: str = Field(..., min_length=100)
    device_id: Optional[str] = None


class FingerprintVerifyRequest(BaseModel):
    fingerprint_template: str = Field(..., min_length=50)
    device_id: Optional[str] = None


class VerificationResponse(BaseModel):
    success: bool
    employee_id: Optional[UUID] = None
    employee_name: Optional[str] = None
    employee_code: Optional[str] = None
    confidence_score: Optional[float] = None
    attendance_action: Optional[str] = None
    message: str


# ============================================================
# ATTENDANCE SCHEMAS
# ============================================================

class AttendanceLogResponse(BaseModel):
    id: UUID
    employee_id: UUID
    employee_name: Optional[str]
    employee_code: Optional[str]
    date: date
    check_in_time: Optional[datetime]
    check_out_time: Optional[datetime]
    check_in_method: Optional[BiometricTypeEnum]
    check_out_method: Optional[BiometricTypeEnum]
    working_hours: Optional[float]

    model_config = ConfigDict(from_attributes=True)


class TodayAttendanceResponse(BaseModel):
    date: date
    total_employees: int
    checked_in: int
    checked_out: int
    absent: int
    logs: List[AttendanceLogResponse]


class AttendanceReportRequest(BaseModel):
    start_date: date
    end_date: date
    employee_id: Optional[UUID] = None
    department: Optional[str] = None

class AttendanceReportResponse(BaseModel):
    start_date: date
    end_date: date
    total_records: int
    records: List[AttendanceLogResponse]



# ============================================================
# DEVICE SCHEMAS
# ============================================================

class DeviceCreate(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=50)
    device_name: str = Field(..., min_length=1, max_length=100)
    device_type: DeviceTypeEnum
    location: Optional[str] = None


class DeviceResponse(BaseModel):
    id: UUID
    device_id: str
    device_name: str
    device_type: DeviceTypeEnum
    location: Optional[str]
    is_active: bool
    last_seen: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeviceWithApiKey(DeviceResponse):
    """Device response with API key (only shown on creation)."""
    api_key: str


class DeviceListResponse(BaseModel):
    """Device list response."""
    items: List[DeviceResponse]
    total: int


# ============================================================
# ADMIN SCHEMAS

class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminUserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str
    role: AdminRoleEnum = AdminRoleEnum.ADMIN


class AdminUserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    full_name: str
    role: AdminRoleEnum
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AdminUserResponse


AdminLoginResponse.model_rebuild()
