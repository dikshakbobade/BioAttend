-- Biometric Attendance System - MySQL Schema
-- Copy and execute this in MySQL Workbench

CREATE DATABASE IF NOT EXISTS biometric_attendance;
USE biometric_attendance;

-- 1. Employees Table
CREATE TABLE IF NOT EXISTS employees (
    id CHAR(36) NOT NULL,
    employee_code VARCHAR(50) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    department VARCHAR(100) NOT NULL,
    designation VARCHAR(100),
    status ENUM('ACTIVE', 'INACTIVE', 'ON_LEAVE', 'TERMINATED') NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY ix_employees_employee_code (employee_code),
    UNIQUE KEY ix_employees_email (email)
) ENGINE=InnoDB;

-- 2. Biometric Templates Table
CREATE TABLE IF NOT EXISTS biometric_templates (
    id CHAR(36) NOT NULL,
    employee_id CHAR(36) NOT NULL,
    biometric_type ENUM('FACE', 'FINGERPRINT') NOT NULL,
    template_data LONGBLOB NOT NULL,
    template_version INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    quality_score FLOAT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_biometric_employee FOREIGN KEY (employee_id) REFERENCES employees (id) ON DELETE CASCADE,
    INDEX idx_biometric_employee_type (employee_id, biometric_type),
    INDEX idx_biometric_active (is_active)
) ENGINE=InnoDB;

-- 3. Attendance Logs Table
CREATE TABLE IF NOT EXISTS attendance_logs (
    id CHAR(36) NOT NULL,
    employee_id CHAR(36) NOT NULL,
    date DATE NOT NULL,
    check_in_time DATETIME,
    check_out_time DATETIME,
    check_in_method ENUM('FACE', 'FINGERPRINT'),
    check_out_method ENUM('FACE', 'FINGERPRINT'),
    check_in_device_id VARCHAR(50),
    check_out_device_id VARCHAR(50),
    check_in_confidence FLOAT,
    check_out_confidence FLOAT,
    working_hours FLOAT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT uq_employee_date UNIQUE (employee_id, date),
    CONSTRAINT fk_attendance_employee FOREIGN KEY (employee_id) REFERENCES employees (id) ON DELETE CASCADE,
    INDEX idx_attendance_date (date),
    INDEX idx_attendance_employee_date (employee_id, date)
) ENGINE=InnoDB;

-- 4. Audit Logs Table
CREATE TABLE IF NOT EXISTS audit_logs (
    id CHAR(36) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    employee_id CHAR(36),
    device_id VARCHAR(50),
    ip_address VARCHAR(45),
    user_agent VARCHAR(255),
    request_payload JSON,
    response_status VARCHAR(20),
    confidence_score FLOAT,
    error_message TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_audit_event_type (event_type),
    INDEX idx_audit_created_at (created_at),
    INDEX idx_audit_employee (employee_id)
) ENGINE=InnoDB;

-- 5. Devices Table
CREATE TABLE IF NOT EXISTS devices (
    id CHAR(36) NOT NULL,
    device_id VARCHAR(50) NOT NULL,
    device_name VARCHAR(100) NOT NULL,
    device_type ENUM('FACE_CAMERA', 'FINGERPRINT_SCANNER') NOT NULL,
    api_key_hash VARCHAR(64) NOT NULL,
    location VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_seen DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY ix_devices_device_id (device_id)
) ENGINE=InnoDB;

-- 6. Admin Users Table
CREATE TABLE IF NOT EXISTS admin_users (
    id CHAR(36) NOT NULL,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role ENUM('SUPER_ADMIN', 'ADMIN', 'VIEWER') NOT NULL DEFAULT 'ADMIN',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY ix_admin_users_username (username),
    UNIQUE KEY ix_admin_users_email (email)
) ENGINE=InnoDB;

-- Initial Admin (admin / admin123)
-- Hash generated via bcrypt
INSERT INTO admin_users (id, username, email, password_hash, full_name, role, is_active, created_at, updated_at)
VALUES (
    '550e8400-e29b-41d4-a716-446655440000', 
    'admin', 
    'admin@company.com', 
    '$2b$12$LQv3c1yqBWVHxkd0LqCFaeU0L/X.uS3yE.fUnj8r6eH0oK./W.mSy', 
    'System Administrator', 
    'SUPER_ADMIN', 
    1, 
    NOW(), 
    NOW()
) ON DUPLICATE KEY UPDATE username=username;
