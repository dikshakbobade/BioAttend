"""
Background scheduler for automated email notifications.
"""
import logging
from datetime import timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db.database import AsyncSessionLocal
from app.services.email_service import email_service
from app.core.config import get_settings

logger = logging.getLogger(__name__)

IST = timezone(timedelta(hours=5, minutes=30))
settings = get_settings()

scheduler = AsyncIOScheduler(timezone=IST)


async def job_absent_alert():
    """Send absent employee alert."""
    logger.info("Running absent alert job...")
    try:
        async with AsyncSessionLocal() as db:
            await email_service.send_absent_alert(db)
    except Exception as e:
        logger.error(f"Absent alert job failed: {e}")


async def job_daily_summary():
    """Send daily attendance summary."""
    logger.info("Running daily summary job...")
    try:
        async with AsyncSessionLocal() as db:
            await email_service.send_daily_summary(db)
    except Exception as e:
        logger.error(f"Daily summary job failed: {e}")


async def job_weekly_report():
    """Send weekly attendance report."""
    logger.info("Running weekly report job...")
    try:
        async with AsyncSessionLocal() as db:
            await email_service.send_weekly_report(db)
    except Exception as e:
        logger.error(f"Weekly report job failed: {e}")


def start_scheduler():
    """Start the background scheduler."""
    absent_hour = settings.OFFICE_START_HOUR
    absent_minute = settings.OFFICE_START_MINUTE + settings.ABSENT_ALERT_MINUTES

    if absent_minute >= 60:
        absent_hour += absent_minute // 60
        absent_minute = absent_minute % 60

    # 1. Absent alert — 11:30 AM Mon-Sat
    scheduler.add_job(
        job_absent_alert,
        CronTrigger(hour=absent_hour, minute=absent_minute, day_of_week="mon-sat"),
        id="absent_alert",
        replace_existing=True,
        name="Absent Employee Alert"
    )

    # 2. Daily summary — 7:00 PM Mon-Sat
    scheduler.add_job(
        job_daily_summary,
        CronTrigger(hour=settings.DAILY_SUMMARY_HOUR, minute=0, day_of_week="mon-sat"),
        id="daily_summary",
        replace_existing=True,
        name="Daily Attendance Summary"
    )

    # 3. Weekly report — Saturday 7:30 PM
    scheduler.add_job(
        job_weekly_report,
        CronTrigger(hour=settings.DAILY_SUMMARY_HOUR, minute=30, day_of_week="sat"),
        id="weekly_report",
        replace_existing=True,
        name="Weekly Attendance Report"
    )

    scheduler.start()
    logger.info(
        f"Scheduler started: absent={absent_hour}:{absent_minute:02d}, "
        f"daily={settings.DAILY_SUMMARY_HOUR}:00, weekly=Sat {settings.DAILY_SUMMARY_HOUR}:30"
    )


def stop_scheduler():
    """Stop the scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped.")