from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "aivisoor",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=300,
    task_time_limit=600,
    beat_schedule={
        # Reset monthly usage counters on 1st of each month
        "reset-monthly-usage": {
            "task": "app.tasks.reset_monthly_usage",
            "schedule": crontab(day_of_month=1, hour=0, minute=0),
        },
        # Send weekly digest emails to active users
        "weekly-digest": {
            "task": "app.tasks.send_weekly_digest",
            "schedule": crontab(day_of_week="monday", hour=9, minute=0),
        },
    },
)
