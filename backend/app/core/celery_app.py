"""Celery application configuration for background tasks.

Handles async task processing, scheduled jobs (beat), and email polling integration.
"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

# Initialize Celery app
celery_app = Celery(
    "inferbox",
    broker=str(settings.REDIS_URL),
    backend=str(settings.REDIS_URL),
    include=[
        "app.integrations.email.tasks",
        "app.integrations.pohoda.tasks",
        "app.agents.tasks",
        "app.services.embedding_tasks",
        "app.services.deadline_tasks",
        "app.orchestration.tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Prague",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max per task
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    result_expires=3600,  # Results expire after 1 hour
    broker_connection_retry_on_startup=True,
)

# Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "poll-email-inbox": {
        "task": "app.integrations.email.tasks.poll_inbox",
        "schedule": 60.0,  # Every 60 seconds
        "options": {
            "expires": 55.0,  # Expire if not executed within 55 seconds
        },
    },
    "cleanup-old-tasks": {
        "task": "app.integrations.email.tasks.cleanup_processed_emails",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    "sync-pohoda-daily": {
        "task": "app.integrations.pohoda.tasks.sync_daily_exports",
        "schedule": crontab(hour=6, minute=0),  # Daily at 6 AM
    },
    "check-operation-deadlines": {
        "task": "app.services.deadline_tasks.check_operation_deadlines",
        "schedule": crontab(hour="7,11,15", minute=0),  # 3x daily
    },
}


@celery_app.task(bind=True, max_retries=3)
def debug_task(self) -> str:  # type: ignore[no-untyped-def]
    """Debug task to verify Celery is working correctly.

    Returns:
        str: Debug information about the task request.
    """
    return f"Request: {self.request!r}"
