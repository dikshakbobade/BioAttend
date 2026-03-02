CREATE DATABASE IF NOT EXISTS biometric_attendance;
USE biometric_attendance;

CREATE TABLE employees (
	id CHAR(36) NOT NULL, 
	employee_code VARCHAR(50) NOT NULL, 
	full_name VARCHAR(100) NOT NULL, 
	email VARCHAR(100) NOT NULL, 
	department VARCHAR(100) NOT NULL, 
	designation VARCHAR(100), 
	status ENUM('ACTIVE','INACTIVE','ON_LEAVE','TERMINATED') NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
)


CREATE UNIQUE INDEX ix_employees_employee_code ON employees (employee_code)
CREATE UNIQUE INDEX ix_employees_email ON employees (email)

CREATE TABLE audit_logs (
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
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
)


CREATE INDEX idx_audit_created_at ON audit_logs (created_at)
CREATE INDEX idx_audit_employee ON audit_logs (employee_id)
CREATE INDEX idx_audit_event_type ON audit_logs (event_type)
CREATE INDEX ix_audit_logs_event_type ON audit_logs (event_type)

CREATE TABLE devices (
	id CHAR(36) NOT NULL, 
	device_id VARCHAR(50) NOT NULL, 
	device_name VARCHAR(100) NOT NULL, 
	device_type ENUM('FACE_CAMERA','FINGERPRINT_SCANNER') NOT NULL, 
	api_key_hash VARCHAR(64) NOT NULL, 
	location VARCHAR(100), 
	is_active BOOL NOT NULL, 
	last_seen DATETIME, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
)


CREATE UNIQUE INDEX ix_devices_device_id ON devices (device_id)

CREATE TABLE admin_users (
	id CHAR(36) NOT NULL, 
	username VARCHAR(50) NOT NULL, 
	email VARCHAR(100) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	full_name VARCHAR(100) NOT NULL, 
	`role` ENUM('SUPER_ADMIN','ADMIN','VIEWER') NOT NULL, 
	is_active BOOL NOT NULL, 
	last_login DATETIME, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email)
)


CREATE UNIQUE INDEX ix_admin_users_username ON admin_users (username)

CREATE TABLE biometric_templates (
	id CHAR(36) NOT NULL, 
	employee_id CHAR(36) NOT NULL, 
	biometric_type ENUM('FACE','FINGERPRINT') NOT NULL, 
	template_data BLOB NOT NULL, 
	template_version INTEGER NOT NULL, 
	is_active BOOL NOT NULL, 
	quality_score FLOAT, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(employee_id) REFERENCES employees (id) ON DELETE CASCADE
)


CREATE INDEX idx_biometric_employee_type ON biometric_templates (employee_id, biometric_type)
CREATE INDEX idx_biometric_active ON biometric_templates (is_active)

CREATE TABLE attendance_logs (
	id CHAR(36) NOT NULL, 
	employee_id CHAR(36) NOT NULL, 
	date DATE NOT NULL, 
	check_in_time DATETIME, 
	check_out_time DATETIME, 
	check_in_method ENUM('FACE','FINGERPRINT'), 
	check_out_method ENUM('FACE','FINGERPRINT'), 
	check_in_device_id VARCHAR(50), 
	check_out_device_id VARCHAR(50), 
	check_in_confidence FLOAT, 
	check_out_confidence FLOAT, 
	working_hours FLOAT, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_employee_date UNIQUE (employee_id, date), 
	FOREIGN KEY(employee_id) REFERENCES employees (id) ON DELETE CASCADE
)


CREATE INDEX idx_attendance_date ON attendance_logs (date)
CREATE INDEX idx_attendance_employee_date ON attendance_logs (employee_id, date)
CREATE INDEX ix_attendance_logs_date ON attendance_logs (date)

