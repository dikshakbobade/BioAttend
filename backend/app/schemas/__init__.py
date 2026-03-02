"""Pydantic schemas module."""

from app.schemas.schemas import (
    # Enums
    EmployeeStatusEnum,
    BiometricTypeEnum,
    DeviceTypeEnum,
    AdminRoleEnum,

    # Employee
    EmployeeBase,
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
    EmployeeListResponse,

    # Biometric
    BiometricTemplateCreate,
    BiometricTemplateResponse,
    FaceVerifyRequest,
    FingerprintVerifyRequest,
    VerificationResponse,
    FaceEnrollProfileRequest,
    FaceEnrollProfileResponse,

    # Attendance
    AttendanceLogResponse,
    AttendanceReportRequest,
    AttendanceReportResponse,
    TodayAttendanceResponse,

    # Device
    DeviceCreate,
    DeviceResponse,
    DeviceWithApiKey,
    DeviceListResponse,

    # Admin
    AdminLoginRequest,
    AdminLoginResponse,
    AdminUserCreate,
    AdminUserResponse,
)

__all__ = [
    "EmployeeStatusEnum",
    "BiometricTypeEnum",
    "DeviceTypeEnum",
    "AdminRoleEnum",

    "EmployeeBase",
    "EmployeeCreate",
    "EmployeeUpdate",
    "EmployeeResponse",
    "EmployeeListResponse",

    "BiometricTemplateCreate",
    "BiometricTemplateResponse",
    "FaceVerifyRequest",
    "FingerprintVerifyRequest",
    "VerificationResponse",
    "FaceEnrollProfileRequest",
    "FaceEnrollProfileResponse",

    "AttendanceLogResponse",
    "AttendanceReportRequest",
    "AttendanceReportResponse",
    "TodayAttendanceResponse",

    "DeviceCreate",
    "DeviceResponse",
    "DeviceWithApiKey",
    "DeviceListResponse",

    "AdminLoginRequest",
    "AdminLoginResponse",
    "AdminUserCreate",
    "AdminUserResponse",
]