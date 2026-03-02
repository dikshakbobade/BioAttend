"""Initial database schema

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE employeestatus AS ENUM ('ACTIVE', 'INACTIVE', 'ON_LEAVE', 'TERMINATED')")
    op.execute("CREATE TYPE biometrictype AS ENUM ('FACE', 'FINGERPRINT')")
    op.execute("CREATE TYPE devicetype AS ENUM ('FACE_CAMERA', 'FINGERPRINT_SCANNER')")
    op.execute("CREATE TYPE adminrole AS ENUM ('SUPER_ADMIN', 'ADMIN', 'VIEWER')")
    
    # Create employees table
    op.create_table(
        'employees',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('employee_code', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('full_name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('department', sa.String(100), nullable=False),
        sa.Column('designation', sa.String(100), nullable=True),
        sa.Column('status', postgresql.ENUM('ACTIVE', 'INACTIVE', 'ON_LEAVE', 'TERMINATED', name='employeestatus', create_type=False), nullable=False, default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create biometric_templates table
    op.create_table(
        'biometric_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False),
        sa.Column('biometric_type', postgresql.ENUM('FACE', 'FINGERPRINT', name='biometrictype', create_type=False), nullable=False),
        sa.Column('template_data', sa.LargeBinary(), nullable=False),
        sa.Column('template_version', sa.Integer(), nullable=False, default=1),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('idx_biometric_employee_type', 'biometric_templates', ['employee_id', 'biometric_type'])
    op.create_index('idx_biometric_active', 'biometric_templates', ['is_active'])
    
    # Create attendance_logs table
    op.create_table(
        'attendance_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False, index=True),
        sa.Column('check_in_time', sa.DateTime(), nullable=True),
        sa.Column('check_out_time', sa.DateTime(), nullable=True),
        sa.Column('check_in_method', postgresql.ENUM('FACE', 'FINGERPRINT', name='biometrictype', create_type=False), nullable=True),
        sa.Column('check_out_method', postgresql.ENUM('FACE', 'FINGERPRINT', name='biometrictype', create_type=False), nullable=True),
        sa.Column('check_in_device_id', sa.String(50), nullable=True),
        sa.Column('check_out_device_id', sa.String(50), nullable=True),
        sa.Column('check_in_confidence', sa.Float(), nullable=True),
        sa.Column('check_out_confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('employee_id', 'date', name='uq_employee_date'),
    )
    op.create_index('idx_attendance_date', 'attendance_logs', ['date'])
    op.create_index('idx_attendance_employee_date', 'attendance_logs', ['employee_id', 'date'])
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_type', sa.String(50), nullable=False, index=True),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('device_id', sa.String(50), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(255), nullable=True),
        sa.Column('request_payload', postgresql.JSON(), nullable=True),
        sa.Column('response_status', sa.String(20), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('idx_audit_event_type', 'audit_logs', ['event_type'])
    op.create_index('idx_audit_created_at', 'audit_logs', ['created_at'])
    op.create_index('idx_audit_employee', 'audit_logs', ['employee_id'])
    
    # Create devices table
    op.create_table(
        'devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('device_id', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('device_name', sa.String(100), nullable=False),
        sa.Column('device_type', postgresql.ENUM('FACE_CAMERA', 'FINGERPRINT_SCANNER', name='devicetype', create_type=False), nullable=False),
        sa.Column('api_key_hash', sa.String(64), nullable=False),
        sa.Column('location', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_seen', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create admin_users table
    op.create_table(
        'admin_users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('username', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('email', sa.String(100), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(100), nullable=False),
        sa.Column('role', postgresql.ENUM('SUPER_ADMIN', 'ADMIN', 'VIEWER', name='adminrole', create_type=False), nullable=False, default='ADMIN'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('admin_users')
    op.drop_table('devices')
    op.drop_table('audit_logs')
    op.drop_table('attendance_logs')
    op.drop_table('biometric_templates')
    op.drop_table('employees')
    
    op.execute("DROP TYPE adminrole")
    op.execute("DROP TYPE devicetype")
    op.execute("DROP TYPE biometrictype")
    op.execute("DROP TYPE employeestatus")
