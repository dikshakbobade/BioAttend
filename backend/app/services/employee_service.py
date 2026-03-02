"""
Employee service for CRUD operations.
"""
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Employee, BiometricTemplate, EmployeeStatus, BiometricType
from app.schemas import EmployeeCreate, EmployeeUpdate


class EmployeeService:
    """Service for employee operations."""
    
    async def get_by_id(
        self, 
        db: AsyncSession, 
        employee_id: UUID,
        include_templates: bool = False
    ) -> Optional[Employee]:
        """Get employee by ID."""
        query = select(Employee).where(Employee.id == employee_id)
        if include_templates:
            query = query.options(selectinload(Employee.biometric_templates))
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_code(self, db: AsyncSession, employee_code: str) -> Optional[Employee]:
        """Get employee by employee code."""
        result = await db.execute(
            select(Employee).where(Employee.employee_code == employee_code)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[Employee]:
        """Get employee by email."""
        result = await db.execute(
            select(Employee).where(Employee.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self, 
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: Optional[EmployeeStatus] = None,
        department: Optional[str] = None
    ) -> Tuple[List[Employee], int]:
        """Get all employees with pagination and filters."""
        query = select(Employee)
        count_query = select(func.count(Employee.id))
        
        if status:
            query = query.where(Employee.status == status)
            count_query = count_query.where(Employee.status == status)
        
        if department:
            query = query.where(Employee.department == department)
            count_query = count_query.where(Employee.department == department)
        
        query = query.order_by(Employee.full_name).offset(skip).limit(limit)
        
        result = await db.execute(query)
        employees = list(result.scalars().all())
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        return employees, total
    
    async def get_active_employees(self, db: AsyncSession) -> List[Employee]:
        """Get all active employees."""
        result = await db.execute(
            select(Employee)
            .where(Employee.status == EmployeeStatus.ACTIVE)
            .options(selectinload(Employee.biometric_templates))
        )
        return list(result.scalars().all())
    
    async def create(self, db: AsyncSession, employee_data: EmployeeCreate) -> Employee:
        """Create a new employee."""
        employee = Employee(
            employee_code=employee_data.employee_code,
            full_name=employee_data.full_name,
            email=employee_data.email,
            department=employee_data.department,
            designation=employee_data.designation,
            status=EmployeeStatus.ACTIVE
        )
        db.add(employee)
        await db.commit()
        await db.refresh(employee)
        return employee
    
    async def update(
        self, 
        db: AsyncSession, 
        employee_id: UUID, 
        employee_data: EmployeeUpdate
    ) -> Optional[Employee]:
        """Update an employee."""
        employee = await self.get_by_id(db, employee_id)
        if not employee:
            return None
        
        update_data = employee_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(employee, field, value)
        
        await db.commit()
        await db.refresh(employee)
        return employee
    
    async def delete(self, db: AsyncSession, employee_id: UUID) -> bool:
        """Delete an employee."""
        employee = await self.get_by_id(db, employee_id)
        if not employee:
            return False
        
        await db.delete(employee)
        await db.commit()
        return True
    
    async def get_employee_template_status(
        self, 
        db: AsyncSession, 
        employee_id: UUID
    ) -> Tuple[bool, bool]:
        """Get whether employee has face and fingerprint templates."""
        result = await db.execute(
            select(BiometricTemplate)
            .where(
                BiometricTemplate.employee_id == employee_id,
                BiometricTemplate.is_active == True
            )
        )
        templates = list(result.scalars().all())
        
        has_face = any(t.biometric_type == BiometricType.FACE for t in templates)
        has_fingerprint = any(t.biometric_type == BiometricType.FINGERPRINT for t in templates)
        
        return has_face, has_fingerprint
    
    async def get_active_employee_count(self, db: AsyncSession) -> int:
        """Get count of active employees."""
        result = await db.execute(
            select(func.count(Employee.id))
            .where(Employee.status == EmployeeStatus.ACTIVE)
        )
        return result.scalar()


# Singleton instance
employee_service = EmployeeService()
