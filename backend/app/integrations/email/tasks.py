"""Celery tasks for email polling and inbox management.

Provides background tasks for fetching emails from IMAP server,
classifying them with AI, and cleaning up old processed messages.

When ORCHESTRATION_ENABLED=true, emails are dispatched to the
orchestration pipeline (HeuristicClassifier → Claude fallback)
instead of using the old EmailClassifier directly.
"""

import asyncio
import base64
import smtplib
from datetime import UTC, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import structlog
from celery.exceptions import MaxRetriesExceededError
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.integrations.email.imap_client import IMAPClient, RawEmail
from app.models.inbox import InboxClassification, InboxMessage, InboxStatus

logger = structlog.get_logger(__name__)

# Cleanup retention period for processed messages (90 days)
_CLEANUP_RETENTION_DAYS = 90

# Template directory for emails
_TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates"


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

    # Skip if IMAP polling is disabled (safety switch)
    if not settings.IMAP_POLLING_ENABLED:
        logger.info("poll_inbox.skipped", reason="IMAP_POLLING_ENABLED=false")
        return {
            "status": "skipped",
            "reason": "IMAP polling disabled (set IMAP_POLLING_ENABLED=true to enable)",
            "processed": 0,
            "errors": 0,
        }

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


def _serialize_raw_email(raw_email: RawEmail) -> dict:
    """Serialize RawEmail to dict for Celery task dispatch.

    Attachments are base64-encoded for JSON serialization.

    Args:
        raw_email: Parsed email from IMAP

    Returns:
        dict compatible with EmailIngestionAgent.process_from_dict()
    """
    return {
        "message_id": raw_email.message_id,
        "from_email": raw_email.from_email,
        "subject": raw_email.subject,
        "body_text": raw_email.body_text,
        "received_at": raw_email.received_at.isoformat(),
        "attachments": [
            {
                "filename": att.filename,
                "content_type": att.content_type,
                "data_b64": base64.b64encode(att.data).decode("ascii"),
            }
            for att in raw_email.attachments
        ],
        "references_header": raw_email.references_header,
        "in_reply_to_header": raw_email.in_reply_to_header,
    }


async def _poll_inbox_async(settings: object) -> dict[str, object]:
    """Async implementation of inbox polling logic.

    When ORCHESTRATION_ENABLED=true, dispatches each email to the
    orchestration pipeline (ingest → classify → route → parse → orchestrate).
    Otherwise falls back to legacy EmailClassifier flow.

    Args:
        settings: Application settings with IMAP and Anthropic config.

    Returns:
        dict: Execution summary with processed/skipped/error counts.
    """
    # Dispose stale connections from previous event loop
    # (asyncio.run() creates a new loop each time in Celery workers)
    from app.core.database import engine

    try:
        await engine.dispose()
    except RuntimeError:
        # Stale connections from previous event loop can't be closed cleanly
        engine.sync_engine.pool.dispose()

    # Type-safe access to settings
    imap_host = str(settings.IMAP_HOST)  # type: ignore[attr-defined]
    imap_port = int(settings.IMAP_PORT)  # type: ignore[attr-defined]
    imap_user = str(settings.IMAP_USER)  # type: ignore[attr-defined]
    imap_password = str(settings.IMAP_PASSWORD)  # type: ignore[attr-defined]
    orchestration_enabled = getattr(settings, "ORCHESTRATION_ENABLED", False)

    processed_count = 0
    skipped_count = 0
    error_count = 0

    # Initialize IMAP client
    imap_client = IMAPClient(
        host=imap_host,
        port=imap_port,
        user=imap_user,
        password=imap_password,
    )

    try:
        # Connect to IMAP server
        await imap_client.connect()

        # Fetch new messages
        raw_emails = await imap_client.fetch_new_messages(mailbox="INBOX")

        logger.info("poll_inbox.fetched", count=len(raw_emails))

        # Process each email
        for raw_email in raw_emails:
            try:
                # Generate a unique message_id if missing
                if not raw_email.message_id or not raw_email.message_id.strip():
                    import hashlib
                    from uuid import uuid4

                    # Create deterministic ID from content, fallback to uuid
                    content_hash = hashlib.sha256(
                        f"{raw_email.subject}|{raw_email.from_email}|{raw_email.date}".encode()
                    ).hexdigest()[:16]
                    raw_email.message_id = f"<gen-{content_hash}-{uuid4().hex[:8]}@infer-forge>"
                    logger.info(
                        "poll_inbox.generated_message_id",
                        generated_id=raw_email.message_id,
                        subject=raw_email.subject,
                    )

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

                if orchestration_enabled:
                    # ── New orchestration pipeline ──
                    # Dispatch to run_pipeline task (async Celery chain)
                    # Pipeline handles: ingest → classify → route → parse → orchestrate
                    from app.orchestration.tasks import run_pipeline

                    raw_email_data = _serialize_raw_email(raw_email)
                    run_pipeline.delay(raw_email_data)

                    processed_count += 1
                    logger.info(
                        "poll_inbox.dispatched_to_pipeline",
                        message_id=raw_email.message_id,
                        subject=raw_email.subject,
                        attachment_count=len(raw_email.attachments),
                    )
                else:
                    # ── Legacy flow (EmailClassifier) ──
                    processed, skipped = await _process_email_legacy(
                        settings, raw_email
                    )
                    processed_count += processed
                    skipped_count += skipped

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
        "mode": "orchestration" if orchestration_enabled else "legacy",
        "timestamp": datetime.utcnow().isoformat(),
    }


async def _process_email_legacy(
    settings: object, raw_email: RawEmail
) -> tuple[int, int]:
    """Process email using legacy EmailClassifier flow.

    Args:
        settings: Application settings
        raw_email: Parsed email from IMAP

    Returns:
        (processed_count, skipped_count) tuple
    """
    from app.agents.email_classifier import EmailClassifier

    anthropic_key = str(settings.ANTHROPIC_API_KEY)  # type: ignore[attr-defined]
    classifier = EmailClassifier(api_key=anthropic_key)

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
        auto_reply_sent=False,
    )

    # Save to database
    async with AsyncSessionLocal() as session:
        session.add(inbox_message)
        try:
            await session.commit()

            # Emit notifications for new email and classification
            try:
                from app.models.notification import NotificationType
                from app.models.user import UserRole
                from app.services.notification import NotificationService

                notif_service = NotificationService(session)

                # EMAIL_NEW notification
                await notif_service.create_for_roles(
                    notification_type=NotificationType.EMAIL_NEW,
                    title="Nový email",
                    message=f"Od: {raw_email.from_email} — '{raw_email.subject}'",
                    roles=[UserRole.ADMIN, UserRole.OBCHODNIK],
                    link="/inbox",
                )

                # EMAIL_CLASSIFIED notification
                await notif_service.create_for_roles(
                    notification_type=NotificationType.EMAIL_CLASSIFIED,
                    title="Email klasifikován",
                    message=f"'{raw_email.subject}' → {classification_result.category or 'neznámé'}",
                    roles=[UserRole.ADMIN, UserRole.OBCHODNIK],
                    link="/inbox",
                )
                await session.commit()
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

            # Match email to order
            order_number_for_reply = None
            try:
                from app.services.inbox import match_email_to_order

                matched_order_id = await match_email_to_order(session, inbox_message)
                if matched_order_id:
                    inbox_message.order_id = matched_order_id
                    await session.commit()

                    # Fetch order number for auto-reply
                    from app.models.order import Order

                    order_result = await session.execute(
                        select(Order).where(Order.id == matched_order_id)
                    )
                    order = order_result.scalar_one_or_none()
                    if order:
                        order_number_for_reply = order.number

                    logger.info(
                        "poll_inbox.order_matched",
                        message_id=raw_email.message_id,
                        order_id=str(matched_order_id),
                        order_number=order_number_for_reply,
                    )
            except Exception:
                logger.warning(
                    "poll_inbox.order_matching_failed",
                    message_id=raw_email.message_id,
                )

            # Send auto-reply (async task)
            try:
                reply_subject = f"Re: {raw_email.subject}"
                send_auto_reply_task.delay(
                    to_email=raw_email.from_email,
                    subject=reply_subject,
                    order_number=order_number_for_reply,
                    classification=classification_result.category,
                    message_preview=raw_email.body_text[:200],
                    original_message_id=raw_email.message_id,
                )

                # Mark as auto-reply sent
                inbox_message.auto_reply_sent = True
                await session.commit()

            except Exception:
                logger.warning(
                    "poll_inbox.auto_reply_failed",
                    message_id=raw_email.message_id,
                )

            logger.info(
                "poll_inbox.message_processed",
                message_id=raw_email.message_id,
                classification=classification_result.category,
                confidence=classification_result.confidence,
                status=status.value,
                auto_reply_sent=inbox_message.auto_reply_sent,
            )

            return 1, 0

        except IntegrityError:
            # Handle race condition if message was inserted between check and insert
            await session.rollback()
            logger.warning(
                "poll_inbox.duplicate_insert",
                message_id=raw_email.message_id,
            )
            return 0, 1


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


def send_auto_reply(
    to_email: str,
    subject: str,
    order_number: str | None = None,
    classification: str | None = None,
    message_preview: str | None = None,
    original_message_id: str | None = None,
) -> dict[str, object]:
    """Send auto-reply email to customer.

    Args:
        to_email: Recipient email address
        subject: Reply subject (typically "Re: {original_subject}")
        order_number: Optional order number for reference
        classification: Email classification (poptavka, objednavka, etc.)
        message_preview: Preview of original message (for context)
        original_message_id: Original message-id for threading

    Returns:
        dict: Execution summary with success status

    Raises:
        Exception: On SMTP failures
    """
    settings = get_settings()

    # Skip if email sending is disabled (safety switch)
    if not settings.EMAIL_SENDING_ENABLED:
        logger.warning(
            "send_auto_reply.blocked",
            reason="EMAIL_SENDING_ENABLED=false",
            to_email=to_email,
            subject=subject,
        )
        return {
            "status": "blocked",
            "reason": "Email sending disabled (set EMAIL_SENDING_ENABLED=true to enable)",
            "to_email": to_email,
        }

    # Skip if SMTP is not configured
    if not settings.SMTP_HOST:
        logger.warning(
            "send_auto_reply.skipped",
            reason="SMTP_HOST not configured",
            to_email=to_email,
        )
        return {"status": "skipped", "reason": "SMTP not configured"}

    logger.info(
        "send_auto_reply.started",
        to_email=to_email,
        subject=subject,
        order_number=order_number,
        classification=classification,
    )

    try:
        # Render email template
        env = Environment(loader=FileSystemLoader(_TEMPLATE_DIR))
        template = env.get_template("email_response.html")

        # Prepare template context
        context = {
            "subject": subject,
            "body": _generate_auto_reply_body(classification, order_number),
            "order_number": order_number,
            "company": {
                "name": "Infer s.r.o.",
                "ico": settings.POHODA_ICO,
                "dic": "CZ04856562",
                "address": "Průmyslová 123, 500 03 Hradec Králové",
                "phone": "+420 123 456 789",
                "email": settings.SMTP_FROM_EMAIL,
            },
            "today": datetime.now(UTC).strftime("%d.%m.%Y"),
            "sender_name": "INFER FORGE",
            "sender_email": settings.SMTP_FROM_EMAIL,
        }

        html_body = template.render(**context)

        # Create MIME message
        msg = MIMEMultipart("alternative")
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject

        # Add threading headers for email clients
        if original_message_id:
            msg["In-Reply-To"] = original_message_id
            msg["References"] = original_message_id

        # Attach HTML body
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # Connect to SMTP server and send
        smtp_class = smtplib.SMTP_SSL if settings.SMTP_PORT == 465 else smtplib.SMTP
        with smtp_class(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
            if settings.SMTP_USE_TLS and smtp_class == smtplib.SMTP:
                server.starttls()

            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

            server.send_message(msg)

        logger.info(
            "send_auto_reply.success",
            to_email=to_email,
            subject=subject,
            order_number=order_number,
        )

        return {
            "status": "sent",
            "to_email": to_email,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as exc:
        logger.exception(
            "send_auto_reply.failed",
            to_email=to_email,
            subject=subject,
            error=str(exc),
        )
        raise


def _generate_auto_reply_body(
    classification: str | None,
    order_number: str | None,
) -> str:
    """Generate auto-reply body based on classification.

    Args:
        classification: Email classification
        order_number: Optional order number

    Returns:
        str: Email body text
    """
    if order_number:
        return (
            f"Děkujeme za Váš email týkající se zakázky {order_number}. "
            "Váš dotaz jsme přijali a pracujeme na jeho zpracování. "
            "V případě potřeby Vás budeme kontaktovat."
        )

    if classification == "poptavka":
        return (
            "Děkujeme za Vaši poptávku. "
            "Váš email jsme přijali a připravíme pro Vás cenovou nabídku. "
            "Ozveme se Vám do 2 pracovních dnů."
        )
    elif classification == "objednavka":
        return (
            "Děkujeme za Vaši objednávku. "
            "Váš email jsme přijali a začneme s přípravou zakázky. "
            "Potvrzení objednávky a harmonogram dodání Vám zašleme v nejbližší době."
        )
    elif classification == "reklamace":
        return (
            "Děkujeme za Váš email týkající se reklamace. "
            "Velmi nás to mrzí a budeme situaci neprodleně řešit. "
            "Náš kolega Vás bude kontaktovat do 24 hodin."
        )
    else:
        return (
            "Děkujeme za Váš email. "
            "Váš dotaz jsme přijali a budeme se mu věnovat. "
            "V případě potřeby Vás budeme kontaktovat."
        )


@celery_app.task(bind=True, max_retries=3)
def send_auto_reply_task(  # type: ignore[no-untyped-def]
    self,
    to_email: str,
    subject: str,
    order_number: str | None = None,
    classification: str | None = None,
    message_preview: str | None = None,
    original_message_id: str | None = None,
) -> dict[str, object]:
    """Celery task wrapper for sending auto-reply emails with retry logic.

    Args:
        to_email: Recipient email address
        subject: Reply subject
        order_number: Optional order number
        classification: Email classification
        message_preview: Preview of original message
        original_message_id: Original message-id for threading

    Returns:
        dict: Task execution summary

    Raises:
        Exception: On transient failures, retries up to 3 times
    """
    logger.info(
        "send_auto_reply_task.started",
        task_id=self.request.id,
        to_email=to_email,
        retry_count=self.request.retries,
    )

    try:
        result = send_auto_reply(
            to_email=to_email,
            subject=subject,
            order_number=order_number,
            classification=classification,
            message_preview=message_preview,
            original_message_id=original_message_id,
        )

        logger.info(
            "send_auto_reply_task.completed",
            task_id=self.request.id,
            to_email=to_email,
            status=result["status"],
        )

        return result

    except Exception as exc:
        logger.exception(
            "send_auto_reply_task.failed",
            task_id=self.request.id,
            to_email=to_email,
            error=str(exc),
            retry_count=self.request.retries,
        )

        # Retry with exponential backoff
        try:
            raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))
        except MaxRetriesExceededError:
            logger.error(
                "send_auto_reply_task.max_retries_exceeded",
                task_id=self.request.id,
                to_email=to_email,
                error=str(exc),
            )
            return {
                "status": "failed",
                "error": str(exc),
                "to_email": to_email,
            }
