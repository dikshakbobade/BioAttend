"""
SQLAlchemy database models.
"""
import uuid
import enum
from datetime import datetime, date
from typing import List, Optional

from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, Time, 
    ForeignKey, Enum, Integer, LargeBinary, Text, Float,
    UniqueConstraint, Index, JSON
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import TypeDecorator, CHAR
import uuid

class UUID(TypeDecorator):
    """Platform-independent UUID type.
    Uses PostgreSQL's UUID type, otherwise uses
    CHAR(36), storing as stringified hex values.
    """
    impl = CHAR
    cache_ok = True

    def __init__(self, *args, **kwargs):
        # Consume as_uuid arg if present
        kwargs.pop('as_uuid', None)
        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value
        else:
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value
        else:
            if isinstance(value, uuid.UUID):
                return value
            return uuid.UUID(value)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.database import Base


class EmployeeStatus(str, enum.Enum):
    """Employee status enumeration."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ON_LEAVE = "ON_LEAVE"
    TERMINATED = "TERMINATED"


class BiometricType(str, enum.Enum):
    """Biometric type enumeration."""
    FACE = "FACE"
    FINGERPRINT = "FINGERPRINT"


class DeviceType(str, enum.Enum):
    """Device type enumeration."""
    FACE_CAMERA = "FACE_CAMERA"
    FINGERPRINT_SCANNER = "FINGERPRINT_SCANNER"


class AdminRole(str, enum.Enum):
    """Admin role enumeration."""
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    VIEWER = "VIEWER"


class Employee(Base):
    """Employee model."""
    __tablename__ = "employees"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    designation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[EmployeeStatus] = mapped_column(
        Enum(EmployeeStatus), 
        default=EmployeeStatus.ACTIVE,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    biometric_templates: Mapped[List["BiometricTemplate"]] = relationship(
        "BiometricTemplate", 
        back_populates="employee",
        cascade="all, delete-orphan"
    )
    attendance_logs: Mapped[List["AttendanceLog"]] = relationship(
        "AttendanceLog",
        back_populates="employee",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Employee {self.employee_code}: {self.full_name}>"


class BiometricTemplate(Base):
    """Biometric template storage model."""
    __tablename__ = "biometric_templates"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False
    )
    biometric_type: Mapped[BiometricType] = mapped_column(Enum(BiometricType), nullable=False)
    template_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)  # Encrypted
    template_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    employee: Mapped["Employee"] = relationship("Employee", back_populates="biometric_templates")
    
    # Indexes
    __table_args__ = (
        Index('idx_biometric_employee_type', 'employee_id', 'biometric_type'),
        Index('idx_biometric_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<BiometricTemplate {self.biometric_type.value} for employee {self.employee_id}>"


class AttendanceLog(Base):
    """Attendance log model."""
    __tablename__ = "attendance_logs"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    check_in_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    check_out_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    check_in_method: Mapped[Optional[BiometricType]] = mapped_column(Enum(BiometricType), nullable=True)
    check_out_method: Mapped[Optional[BiometricType]] = mapped_column(Enum(BiometricType), nullable=True)
    check_in_device_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    check_out_device_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    check_in_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    check_out_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    working_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    employee: Mapped["Employee"] = relationship("Employee", back_populates="attendance_logs")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('employee_id', 'date', name='uq_employee_date'),
        Index('idx_attendance_date', 'date'),
        Index('idx_attendance_employee_date', 'employee_id', 'date'),
    )
    
    def __repr__(self):
        return f"<AttendanceLog {self.employee_id} on {self.date}>"


class AuditLog(Base):
    """Audit log for security and compliance."""
    __tablename__ = "audit_logs"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    employee_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    device_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    request_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    response_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_audit_event_type', 'event_type'),
        Index('idx_audit_created_at', 'created_at'),
        Index('idx_audit_employee', 'employee_id'),
    )
    
    def __repr__(self):
        return f"<AuditLog {self.event_type} at {self.created_at}>"


class Device(Base):
    """Device registry model."""
    __tablename__ = "devices"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    device_name: Mapped[str] = mapped_column(String(100), nullable=False)
    device_type: Mapped[DeviceType] = mapped_column(Enum(DeviceType), nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    def __repr__(self):
        return f"<Device {self.device_id}: {self.device_type.value}>"


class AdminUser(Base):
    """Admin user model."""
    __tablename__ = "admin_users"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[AdminRole] = mapped_column(Enum(AdminRole), default=AdminRole.ADMIN, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    def __repr__(self):
        return f"<AdminUser {self.username}: {self.role.value}>"
