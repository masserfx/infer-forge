"""Celery tasks for email polling and inbox management.

Provides background tasks for fetching emails from IMAP server,
classifying them with AI, and cleaning up old processed messages.
"""

import asyncio
from datetime import datetime, timedelta

import structlog
from celery.exceptions import MaxRetriesExceededError
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.agents.email_classifier import EmailClassifier
from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.integrations.email.imap_client import IMAPClient
from app.models.inbox import InboxClassification, InboxMessage, InboxStatus

logger = structlog.get_logger(__name__)

# Cleanup retention period for processed messages (90 days)
_CLEANUP_RETENTION_DAYS = 90


@celery_app.task(bind=True, max_retries=3)
def poll_inbox(self) -> dict[str, object]:  # type: ignore[no-untyped-def]
    """Poll IMAP inbox for new emails and classify them.

    This task:
    1. Connects to the IMAP server
    2. Fetches new (unseen) messages
    3. Classifies each message using AI
    4. Creates InboxMessage records in the database
    5. Handles deduplication (skips already processed message_ids)

    The task is scheduled to run every 60 seconds via Celery Beat.
    Skips execution if IMAP is not configured.

    Returns:
        dict: Task execution summary with counts and errors.

    Raises:
        Exception: On transient failures, retries up to 3 times.
    """
    settings = get_settings()

    # Skip if IMAP is not configured
    if not settings.IMAP_HOST:
        logger.info("poll_inbox.skipped", reason="IMAP_HOST not configured")
        return {
            "status": "skipped",
            "reason": "IMAP not configured",
            "processed": 0,
            "errors": 0,
        }

    logger.info(
        "poll_inbox.started",
        task_id=self.request.id,
        host=settings.IMAP_HOST,
        user=settings.IMAP_USER,
    )

    try:
        # Run async polling logic
        result = asyncio.run(_poll_inbox_async(settings))

        logger.info(
            "poll_inbox.completed",
            task_id=self.request.id,
            processed=result["processed"],
            skipped=result["skipped"],
            errors=result["errors"],
        )

        return result

    except Exception as exc:
        logger.exception(
            "poll_inbox.failed",
            task_id=self.request.id,
            error=str(exc),
            retry_count=self.request.retries,
        )

        # Retry on transient failures (network, IMAP, DB connection issues)
        try:
            raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))
        except MaxRetriesExceededError:
            logger.error(
                "poll_inbox.max_retries_exceeded",
                task_id=self.request.id,
                error=str(exc),
            )
            return {
                "status": "failed",
                "error": str(exc),
                "processed": 0,
                "errors": 1,
            }


async def _poll_inbox_async(settings: object) -> dict[str, object]:
    """Async implementation of inbox polling logic.

    Args:
        settings: Application settings with IMAP and Anthropic config.

    Returns:
        dict: Execution summary with processed/skipped/error counts.
    """
    # Type-safe access to settings
    imap_host = str(settings.IMAP_HOST)  # type: ignore[attr-defined]
    imap_port = int(settings.IMAP_PORT)  # type: ignore[attr-defined]
    imap_user = str(settings.IMAP_USER)  # type: ignore[attr-defined]
    imap_password = str(settings.IMAP_PASSWORD)  # type: ignore[attr-defined]
    anthropic_key = str(settings.ANTHROPIC_API_KEY)  # type: ignore[attr-defined]

    processed_count = 0
    skipped_count = 0
    error_count = 0

    # Initialize IMAP client and email classifier
    imap_client = IMAPClient(
        host=imap_host,
        port=imap_port,
        user=imap_user,
        password=imap_password,
    )

    classifier = EmailClassifier(api_key=anthropic_key)

    try:
        # Connect to IMAP server
        await imap_client.connect()

        # Fetch new messages
        raw_emails = await imap_client.fetch_new_messages(mailbox="INBOX")

        logger.info("poll_inbox.fetched", count=len(raw_emails))

        # Process each email
        for raw_email in raw_emails:
            try:
                # Check if message already exists (deduplication)
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(InboxMessage).where(
                            InboxMessage.message_id == raw_email.message_id
                        )
                    )
                    existing = result.scalar_one_or_none()

                    if existing:
                        logger.info(
                            "poll_inbox.message_exists",
                            message_id=raw_email.message_id,
                        )
                        skipped_count += 1
                        continue

                # Classify email with AI
                classification_result = await classifier.classify(
                    subject=raw_email.subject,
                    body=raw_email.body_text,
                )

                # Determine status based on classification
                status = InboxStatus.NEW
                if classification_result.needs_escalation:
                    status = InboxStatus.ESCALATED

                # Map category to enum (handle None case)
                classification_enum: InboxClassification | None = None
                if classification_result.category:
                    classification_enum = InboxClassification(
                        classification_result.category
                    )

                # Create inbox message record
                inbox_message = InboxMessage(
                    message_id=raw_email.message_id,
                    from_email=raw_email.from_email,
                    subject=raw_email.subject,
                    body_text=raw_email.body_text,
                    received_at=raw_email.received_at,
                    classification=classification_enum,
                    confidence=classification_result.confidence,
                    status=status,
                )

                # Save to database
                async with AsyncSessionLocal() as session:
                    session.add(inbox_message)
                    try:
                        await session.commit()
                        processed_count += 1

                        # Emit WebSocket notification for classified email
                        try:
                            from app.models.notification import NotificationType
                            from app.services.notification import NotificationService

                            notif_service = NotificationService(session)
                            await notif_service.create_for_all(
                                notification_type=NotificationType.EMAIL_CLASSIFIED,
                                title="Email klasifikován",
                                message=f"'{raw_email.subject}' → {classification_result.category or 'neznámé'}",
                                link="/inbox",
                            )
                        except Exception:
                            logger.warning("poll_inbox.notification_failed", message_id=raw_email.message_id)

                        # Prometheus metric
                        try:
                            from app.core.metrics import emails_processed_total

                            emails_processed_total.labels(
                                classification=classification_result.category or "unknown"
                            ).inc()
                        except Exception:
                            pass

                        logger.info(
                            "poll_inbox.message_processed",
                            message_id=raw_email.message_id,
                            classification=classification_result.category,
                            confidence=classification_result.confidence,
                            status=status.value,
                        )

                    except IntegrityError:
                        # Handle race condition if message was inserted between check and insert
                        await session.rollback()
                        logger.warning(
                            "poll_inbox.duplicate_insert",
                            message_id=raw_email.message_id,
                        )
                        skipped_count += 1

            except Exception as exc:
                logger.exception(
                    "poll_inbox.message_processing_failed",
                    message_id=raw_email.message_id,
                    error=str(exc),
                )
                error_count += 1
                continue

    finally:
        # Always disconnect from IMAP server
        await imap_client.disconnect()

    return {
        "status": "completed",
        "processed": processed_count,
        "skipped": skipped_count,
        "errors": error_count,
        "timestamp": datetime.utcnow().isoformat(),
    }


@celery_app.task(bind=True, max_retries=3)
def cleanup_processed_emails(self) -> dict[str, object]:  # type: ignore[no-untyped-def]
    """Clean up old processed inbox messages.

    Deletes messages with status=PROCESSED that are older than 90 days.
    This prevents the inbox table from growing indefinitely.

    Scheduled to run daily at 2 AM via Celery Beat.

    Returns:
        dict: Task execution summary with deleted count.

    Raises:
        Exception: On database failures, retries up to 3 times.
    """
    logger.info(
        "cleanup_processed_emails.started",
        task_id=self.request.id,
        retention_days=_CLEANUP_RETENTION_DAYS,
    )

    try:
        # Run async cleanup logic
        result = asyncio.run(_cleanup_processed_emails_async())

        logger.info(
            "cleanup_processed_emails.completed",
            task_id=self.request.id,
            deleted=result["deleted"],
        )

        return result

    except Exception as exc:
        logger.exception(
            "cleanup_processed_emails.failed",
            task_id=self.request.id,
            error=str(exc),
            retry_count=self.request.retries,
        )

        # Retry on database failures
        try:
            raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))
        except MaxRetriesExceededError:
            logger.error(
                "cleanup_processed_emails.max_retries_exceeded",
                task_id=self.request.id,
                error=str(exc),
            )
            return {
                "status": "failed",
                "error": str(exc),
                "deleted": 0,
            }


async def _cleanup_processed_emails_async() -> dict[str, object]:
    """Async implementation of cleanup logic.

    Returns:
        dict: Execution summary with deleted count.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=_CLEANUP_RETENTION_DAYS)

    logger.info(
        "cleanup_processed_emails.executing",
        cutoff_date=cutoff_date.isoformat(),
    )

    async with AsyncSessionLocal() as session:
        # Delete old processed messages
        stmt = delete(InboxMessage).where(
            InboxMessage.status == InboxStatus.PROCESSED,
            InboxMessage.received_at < cutoff_date,
        )

        result = await session.execute(stmt)
        await session.commit()

        deleted_count = result.rowcount or 0

        logger.info(
            "cleanup_processed_emails.deleted",
            count=deleted_count,
            cutoff_date=cutoff_date.isoformat(),
        )

        return {
            "status": "completed",
            "deleted": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
            "timestamp": datetime.utcnow().isoformat(),
        }
