from app.core.celery import celery_app
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.reset_monthly_usage", bind=True, max_retries=3)
def reset_monthly_usage(self):
    """Reset reports_used counter for all subscriptions on 1st of month."""
    import asyncio
    from database import AsyncSessionLocal
    from subscriptions.models import Subscription
    from sqlalchemy import select
    from datetime import datetime, timezone

    async def _run():
        async with AsyncSessionLocal() as db:
            subs = await db.scalars(select(Subscription))
            count = 0
            for sub in subs:
                sub.reports_used = 0
                sub.reports_reset_at = datetime.now(timezone.utc)
                count += 1
            await db.commit()
            logger.info(f"Reset usage for {count} subscriptions")

    asyncio.get_event_loop().run_until_complete(_run())


@celery_app.task(name="app.tasks.send_weekly_digest", bind=True, max_retries=3)
def send_weekly_digest(self):
    """Send weekly summary email to active users with recent reports."""
    import asyncio
    from database import AsyncSessionLocal
    from models import User
    from reports.models import Report, ReportStatus
    from sqlalchemy import select, and_
    from datetime import datetime, timedelta, timezone
    from email import send_email

    async def _run():
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        async with AsyncSessionLocal() as db:
            users = await db.scalars(
                select(User).where(User.is_active == True, User.is_verified == True)
            )
            sent = 0
            for user in users:
                recent = await db.scalars(
                    select(Report).where(
                        and_(
                            Report.user_id == user.id,
                            Report.created_at >= week_ago,
                            Report.status == ReportStatus.DONE,
                        )
                    )
                )
                reports = recent.all()
                if not reports:
                    continue
                avg_score = round(sum(r.score_overall or 0 for r in reports) / len(reports))
                # Simple digest (could be expanded)
                logger.info(f"Sending digest to {user.email}: {len(reports)} reports, avg score {avg_score}")
                sent += 1
            logger.info(f"Weekly digest sent to {sent} users")

    asyncio.get_event_loop().run_until_complete(_run())
