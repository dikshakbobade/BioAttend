"""
Email notification service for attendance alerts.
Uses Gmail SMTP with App Password.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Employee, AttendanceLog, EmployeeStatus
from app.core.config import get_settings

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))

def now_ist() -> datetime:
    return datetime.now(IST)


class EmailService:
    """Service for sending email notifications."""

    def __init__(self):
        self.settings = get_settings()

    def _send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        """Send an email via Gmail SMTP."""
        if not self.settings.SMTP_USER or not self.settings.SMTP_PASSWORD:
            logger.warning("SMTP credentials not configured. Skipping email.")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = f"BioAttend <{self.settings.SMTP_USER}>"
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT) as server:
                server.starttls()
                server.login(self.settings.SMTP_USER, self.settings.SMTP_PASSWORD)
                server.send_message(msg)

            logger.info(f"Email sent: '{subject}' -> {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def send_to_admin(self, subject: str, html_body: str) -> bool:
        """Send email to admin."""
        return self._send_email(self.settings.ADMIN_EMAIL, subject, html_body)
    
    async def send_email(self, subject: str, html_body: str, to_email: str) -> bool:
        """Send a generic email to any recipient."""
        return self._send_email(to_email, subject, html_body)

    # ==========================================
    # LATE ARRIVAL ALERT (real-time)
    # ==========================================
    def send_late_arrival_alert(
        self,
        employee_name: str,
        employee_code: str,
        check_in_time: datetime,
        late_by_minutes: int
    ) -> bool:
        """Send real-time alert when employee arrives late."""
        time_str = check_in_time.strftime("%I:%M %p")
        office_start = f"{self.settings.OFFICE_START_HOUR}:{self.settings.OFFICE_START_MINUTE:02d} AM" \
            if self.settings.OFFICE_START_HOUR < 12 \
            else f"{self.settings.OFFICE_START_HOUR - 12}:{self.settings.OFFICE_START_MINUTE:02d} PM"

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto;">
            <div style="background: #FEF3C7; border-left: 4px solid #F59E0B; padding: 16px; border-radius: 8px;">
                <h2 style="color: #92400E; margin: 0 0 8px 0;">⚠️ Late Arrival Alert</h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr><td style="padding: 4px 0; color: #666;">Employee:</td>
                        <td style="padding: 4px 0; font-weight: bold;">{employee_name} ({employee_code})</td></tr>
                    <tr><td style="padding: 4px 0; color: #666;">Check-in Time:</td>
                        <td style="padding: 4px 0; font-weight: bold;">{time_str}</td></tr>
                    <tr><td style="padding: 4px 0; color: #666;">Office Start:</td>
                        <td style="padding: 4px 0;">{office_start}</td></tr>
                    <tr><td style="padding: 4px 0; color: #666;">Late By:</td>
                        <td style="padding: 4px 0; color: #DC2626; font-weight: bold;">{late_by_minutes} minutes</td></tr>
                </table>
            </div>
            <p style="color: #999; font-size: 12px; margin-top: 12px;">— BioAttend Notification System</p>
        </div>
        """
        return self.send_to_admin(
            f"⚠️ Late Arrival: {employee_name} ({late_by_minutes} min late)",
            html
        )

    # ==========================================
    # ABSENT EMPLOYEE ALERT
    # ==========================================
    async def send_absent_alert(self, db: AsyncSession) -> bool:
        """Send alert for employees who haven't checked in by cutoff time."""
        today = date.today()

        # Get all active employees
        emp_result = await db.execute(
            select(Employee).where(Employee.status == EmployeeStatus.ACTIVE)
        )
        all_employees = list(emp_result.scalars().all())

        # Get today's check-ins
        att_result = await db.execute(
            select(AttendanceLog.employee_id).where(AttendanceLog.date == today)
        )
        checked_in_ids = {row[0] for row in att_result.all()}

        absent_employees = [e for e in all_employees if e.id not in checked_in_ids]

        if not absent_employees:
            logger.info("No absent employees to alert about.")
            return True

        cutoff_time = f"{self.settings.OFFICE_START_HOUR}:{self.settings.OFFICE_START_MINUTE:02d}"
        alert_time = now_ist().strftime("%I:%M %p")

        rows = ""
        for emp in absent_employees:
            rows += f"""
            <tr>
                <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{emp.full_name}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{emp.employee_code}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{emp.department}</td>
            </tr>"""

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #FEE2E2; border-left: 4px solid #EF4444; padding: 16px; border-radius: 8px;">
                <h2 style="color: #991B1B; margin: 0 0 4px 0;">🚫 Absent Employee Alert</h2>
                <p style="color: #666; margin: 0;">{len(absent_employees)} employee(s) have not checked in as of {alert_time}</p>
            </div>
            <table style="width: 100%; border-collapse: collapse; margin-top: 16px; background: white; border-radius: 8px; overflow: hidden; border: 1px solid #eee;">
                <thead>
                    <tr style="background: #F9FAFB;">
                        <th style="padding: 10px 12px; text-align: left; font-size: 12px; color: #666; text-transform: uppercase;">Name</th>
                        <th style="padding: 10px 12px; text-align: left; font-size: 12px; color: #666; text-transform: uppercase;">Code</th>
                        <th style="padding: 10px 12px; text-align: left; font-size: 12px; color: #666; text-transform: uppercase;">Department</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
            <p style="color: #999; font-size: 12px; margin-top: 12px;">— BioAttend Notification System</p>
        </div>
        """
        return self.send_to_admin(
            f"🚫 {len(absent_employees)} Absent Employees — {today.strftime('%b %d, %Y')}",
            html
        )

    # ==========================================
    # DAILY SUMMARY
    # ==========================================
    async def send_daily_summary(self, db: AsyncSession) -> bool:
        """Send end-of-day attendance summary to admin."""
        today = date.today()

        # Total active employees
        total_result = await db.execute(
            select(func.count(Employee.id)).where(Employee.status == EmployeeStatus.ACTIVE)
        )
        total_employees = total_result.scalar()

        # Today's logs
        att_result = await db.execute(
            select(AttendanceLog, Employee)
            .join(Employee)
            .where(AttendanceLog.date == today, Employee.status == EmployeeStatus.ACTIVE)
            .order_by(Employee.full_name)
        )
        logs = att_result.all()

        present = len(logs)
        absent = total_employees - present
        checked_out = sum(1 for log, _ in logs if log.check_out_time)
        late_count = 0

        rows = ""
        for log, emp in logs:
            in_time = log.check_in_time.strftime("%I:%M %p") if log.check_in_time else "-"
            out_time = log.check_out_time.strftime("%I:%M %p") if log.check_out_time else "-"

            # Calculate hours
            hours = "-"
            if log.check_in_time and log.check_out_time:
                delta = (log.check_out_time - log.check_in_time).total_seconds() / 3600
                hours = f"{delta:.1f} hrs"

            # Check if late
            is_late = False
            if log.check_in_time:
                start_minutes = self.settings.OFFICE_START_HOUR * 60 + self.settings.OFFICE_START_MINUTE
                checkin_minutes = log.check_in_time.hour * 60 + log.check_in_time.minute
                if checkin_minutes > start_minutes:
                    is_late = True
                    late_count += 1

            late_badge = '<span style="color: #DC2626; font-size: 11px;"> (LATE)</span>' if is_late else ""

            rows += f"""
            <tr>
                <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{emp.full_name}{late_badge}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{emp.employee_code}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #eee; color: #059669;">{in_time}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #eee; color: #DC2626;">{out_time}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{hours}</td>
            </tr>"""

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto;">
            <div style="background: #EFF6FF; border-left: 4px solid #3B82F6; padding: 16px; border-radius: 8px;">
                <h2 style="color: #1E40AF; margin: 0 0 4px 0;">📊 Daily Attendance Summary</h2>
                <p style="color: #666; margin: 0;">{today.strftime('%A, %B %d, %Y')}</p>
            </div>

            <div style="display: flex; gap: 12px; margin: 16px 0;">
                <div style="flex: 1; background: #F0FDF4; padding: 12px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #16A34A;">{present}</div>
                    <div style="font-size: 12px; color: #666;">Present</div>
                </div>
                <div style="flex: 1; background: #FEF2F2; padding: 12px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #DC2626;">{absent}</div>
                    <div style="font-size: 12px; color: #666;">Absent</div>
                </div>
                <div style="flex: 1; background: #FEF3C7; padding: 12px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #D97706;">{late_count}</div>
                    <div style="font-size: 12px; color: #666;">Late</div>
                </div>
                <div style="flex: 1; background: #EFF6FF; padding: 12px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #2563EB;">{total_employees}</div>
                    <div style="font-size: 12px; color: #666;">Total</div>
                </div>
            </div>

            <table style="width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; border: 1px solid #eee;">
                <thead>
                    <tr style="background: #F9FAFB;">
                        <th style="padding: 10px 12px; text-align: left; font-size: 12px; color: #666;">NAME</th>
                        <th style="padding: 10px 12px; text-align: left; font-size: 12px; color: #666;">CODE</th>
                        <th style="padding: 10px 12px; text-align: left; font-size: 12px; color: #666;">CHECK IN</th>
                        <th style="padding: 10px 12px; text-align: left; font-size: 12px; color: #666;">CHECK OUT</th>
                        <th style="padding: 10px 12px; text-align: left; font-size: 12px; color: #666;">HOURS</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
            <p style="color: #999; font-size: 12px; margin-top: 12px;">— BioAttend Notification System</p>
        </div>
        """
        return self.send_to_admin(
            f"📊 Daily Summary: {present} Present, {absent} Absent — {today.strftime('%b %d')}",
            html
        )

    # ==========================================
    # WEEKLY REPORT
    # ==========================================
    async def send_weekly_report(self, db: AsyncSession) -> bool:
        """Send weekly attendance report."""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())  # Monday
        week_end = week_start + timedelta(days=6)  # Sunday

        # Get all employees
        emp_result = await db.execute(
            select(Employee).where(Employee.status == EmployeeStatus.ACTIVE).order_by(Employee.full_name)
        )
        employees = list(emp_result.scalars().all())

        # Get week's attendance
        att_result = await db.execute(
            select(AttendanceLog).where(
                AttendanceLog.date >= week_start,
                AttendanceLog.date <= week_end
            )
        )
        all_logs = list(att_result.scalars().all())

        # Build per-employee summary
        emp_logs = {}
        for log in all_logs:
            emp_logs.setdefault(log.employee_id, []).append(log)

        rows = ""
        for emp in employees:
            logs = emp_logs.get(emp.id, [])
            days_present = len(logs)
            total_hours = 0
            late_days = 0

            for log in logs:
                if log.check_in_time and log.check_out_time:
                    total_hours += (log.check_out_time - log.check_in_time).total_seconds() / 3600
                if log.check_in_time:
                    start_min = self.settings.OFFICE_START_HOUR * 60 + self.settings.OFFICE_START_MINUTE
                    checkin_min = log.check_in_time.hour * 60 + log.check_in_time.minute
                    if checkin_min > start_min:
                        late_days += 1

            color = "#16A34A" if days_present >= 5 else ("#D97706" if days_present >= 3 else "#DC2626")
            rows += f"""
            <tr>
                <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{emp.full_name}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{emp.employee_code}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #eee; color: {color}; font-weight: bold;">{days_present}/6</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{total_hours:.1f} hrs</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #eee; color: #DC2626;">{late_days}</td>
            </tr>"""

        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto;">
            <div style="background: #F0FDF4; border-left: 4px solid #16A34A; padding: 16px; border-radius: 8px;">
                <h2 style="color: #166534; margin: 0 0 4px 0;">📅 Weekly Attendance Report</h2>
                <p style="color: #666; margin: 0;">{week_start.strftime('%b %d')} — {week_end.strftime('%b %d, %Y')}</p>
            </div>
            <table style="width: 100%; border-collapse: collapse; margin-top: 16px; background: white; border-radius: 8px; border: 1px solid #eee;">
                <thead>
                    <tr style="background: #F9FAFB;">
                        <th style="padding: 10px 12px; text-align: left; font-size: 12px; color: #666;">NAME</th>
                        <th style="padding: 10px 12px; text-align: left; font-size: 12px; color: #666;">CODE</th>
                        <th style="padding: 10px 12px; text-align: left; font-size: 12px; color: #666;">DAYS</th>
                        <th style="padding: 10px 12px; text-align: left; font-size: 12px; color: #666;">HOURS</th>
                        <th style="padding: 10px 12px; text-align: left; font-size: 12px; color: #666;">LATE</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
            <p style="color: #999; font-size: 12px; margin-top: 12px;">— BioAttend Notification System</p>
        </div>
        """
        return self.send_to_admin(
            f"📅 Weekly Report: {week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}",
            html
        )


# Singleton
email_service = EmailService()