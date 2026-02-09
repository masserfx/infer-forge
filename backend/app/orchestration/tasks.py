"""Celery tasks for the document orchestration pipeline.

Each task corresponds to a pipeline stage and produces a serializable dict
stored in Redis. Tasks are chained via Celery chain/chord/group.
"""

from __future__ import annotations

import asyncio
import time
import traceback
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import structlog
from celery import chain
from celery.exceptions import MaxRetriesExceededError

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal

logger = structlog.get_logger(__name__)


def _run_async(coro):
    """Run async coroutine in sync context (Celery worker).

    Each asyncio.run() creates a new event loop, but the module-level
    SQLAlchemy engine pool may hold connections from a previous loop.
    We dispose the pool first; if that fails (stale connections from
    a closed loop), we force-recreate the pool via sync_engine.
    """
    async def _wrapper():
        from app.core.database import engine

        try:
            await engine.dispose()
        except RuntimeError:
            # Stale connections from a previous event loop can't be
            # closed cleanly. Force-recreate the pool synchronously.
            engine.sync_engine.pool.dispose()

        return await coro

    return asyncio.run(_wrapper())


def _make_json_safe(data: dict | None) -> dict | None:
    """Convert UUID objects to strings for JSON serialization."""
    if data is None:
        return None
    return {k: str(v) if isinstance(v, UUID) else v for k, v in data.items()}


def _observe_stage(stage: str, status: str, elapsed_seconds: float, tokens: int = 0, task_name: str = "") -> None:
    """Record Prometheus metrics for a pipeline stage."""
    try:
        from app.core.metrics import (
            claude_api_calls,
            claude_tokens_used,
            pipeline_stage_duration,
            pipeline_stage_total,
        )

        pipeline_stage_total.labels(stage=stage, status=status).inc()
        pipeline_stage_duration.labels(stage=stage).observe(elapsed_seconds)
        if tokens > 0 and task_name:
            claude_tokens_used.labels(task=task_name).inc(tokens)
            claude_api_calls.labels(task=task_name, status=status).inc()
    except Exception:
        pass


def _observe_dlq(stage: str) -> None:
    """Record DLQ entry in Prometheus."""
    try:
        from app.core.metrics import dlq_entries_total
        dlq_entries_total.labels(stage=stage).inc()
    except Exception:
        pass


async def _broadcast_pipeline_progress(
    inbox_message_id: str | None,
    stage: str,
    status: str,
    data: dict | None = None,
) -> None:
    """Broadcast pipeline progress via WebSocket."""
    try:
        from app.core.websocket import manager
        await manager.broadcast({
            "type": "pipeline_progress",
            "inbox_message_id": inbox_message_id,
            "stage": stage,
            "status": status,
            "data": data or {},
            "timestamp": datetime.now(UTC).isoformat(),
        })
    except Exception:
        pass


async def _record_processing_task(
    inbox_message_id: str | None,
    celery_task_id: str | None,
    stage: str,
    status: str,
    input_data: dict | None = None,
    output_data: dict | None = None,
    error_message: str | None = None,
    tokens_used: int | None = None,
    processing_time_ms: int | None = None,
) -> None:
    """Record a processing task in the audit trail."""
    from app.models.processing_task import ProcessingStage, ProcessingStatus, ProcessingTask

    async with AsyncSessionLocal() as session:
        task = ProcessingTask(
            inbox_message_id=UUID(inbox_message_id) if inbox_message_id else None,
            celery_task_id=celery_task_id,
            stage=ProcessingStage(stage),
            status=ProcessingStatus(status),
            input_data=_make_json_safe(input_data),
            output_data=_make_json_safe(output_data),
            error_message=error_message,
            tokens_used=tokens_used,
            processing_time_ms=processing_time_ms,
        )
        session.add(task)
        await session.commit()


async def _send_to_dlq(
    original_task: str,
    stage: str,
    payload: dict,
    error_message: str,
    error_tb: str,
    retry_count: int,
) -> None:
    """Send failed task to dead letter queue."""
    from app.models.dead_letter import DeadLetterEntry

    async with AsyncSessionLocal() as session:
        entry = DeadLetterEntry(
            original_task=original_task,
            stage=stage,
            payload=payload,
            error_message=error_message,
            error_traceback=error_tb,
            retry_count=retry_count,
        )
        session.add(entry)
        await session.commit()

    _observe_dlq(stage)


async def _update_inbox_timestamp(inbox_message_id: str | None, field_name: str) -> None:
    """Update a timestamp field on InboxMessage.

    Args:
        inbox_message_id: InboxMessage UUID string
        field_name: 'processing_started_at' or 'processing_completed_at'
    """
    if not inbox_message_id:
        return
    from sqlalchemy import select

    from app.models.inbox import InboxMessage

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(InboxMessage).where(InboxMessage.id == UUID(inbox_message_id))
        )
        msg = result.scalar_one_or_none()
        if msg:
            setattr(msg, field_name, datetime.now(UTC))
            await session.commit()


# ─── Stage 1: Ingest Email ─────────────────────────────────────


@celery_app.task(bind=True, max_retries=3, queue="orchestration", name="orchestration.ingest_email")
def ingest_email(self, raw_email_data: dict) -> dict:
    """Ingest a raw email: save to DB + attachments to disk.

    Args:
        raw_email_data: Serialized email data from IMAP fetch

    Returns:
        dict with inbox_message_id, attachment_ids, etc.
    """
    settings = get_settings()
    if not settings.ORCHESTRATION_ENABLED:
        return {"status": "skipped", "reason": "orchestration disabled"}

    start = time.monotonic()
    try:
        result = _run_async(_ingest_email_async(raw_email_data))
        elapsed = time.monotonic() - start
        elapsed_ms = int(elapsed * 1000)

        _run_async(_record_processing_task(
            inbox_message_id=result.get("inbox_message_id"),
            celery_task_id=self.request.id,
            stage="ingest",
            status="success",
            input_data={"message_id": raw_email_data.get("message_id")},
            output_data=result,
            processing_time_ms=elapsed_ms,
        ))

        # M1: Mark processing started
        _run_async(_update_inbox_timestamp(result.get("inbox_message_id"), "processing_started_at"))

        # EMAIL_NEW notification
        _run_async(_notify_email_new(
            subject=raw_email_data.get("subject", ""),
            from_email=raw_email_data.get("from_email", ""),
        ))

        # M3: WebSocket progress
        _run_async(_broadcast_pipeline_progress(
            result.get("inbox_message_id"), "ingest", "success",
            {"attachments": len(result.get("attachment_ids", []))},
        ))

        # M4: Prometheus
        _observe_stage("ingest", "success", elapsed)

        return result

    except Exception as exc:
        elapsed = time.monotonic() - start
        elapsed_ms = int(elapsed * 1000)
        logger.exception("orchestration.ingest_failed", error=str(exc))

        _run_async(_record_processing_task(
            inbox_message_id=None,
            celery_task_id=self.request.id,
            stage="ingest",
            status="failed",
            input_data={"message_id": raw_email_data.get("message_id")},
            error_message=str(exc),
            processing_time_ms=elapsed_ms,
        ))
        _observe_stage("ingest", "failed", elapsed)

        try:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        except MaxRetriesExceededError:
            _run_async(_send_to_dlq(
                "orchestration.ingest_email", "ingest",
                raw_email_data, str(exc), traceback.format_exc(),
                self.request.retries,
            ))
            return {"status": "failed", "error": str(exc)}


async def _ingest_email_async(raw_email_data: dict) -> dict:
    from app.orchestration.agents.email_ingestion import EmailIngestionAgent
    agent = EmailIngestionAgent()
    return await agent.process_from_dict(raw_email_data)


# ─── Stage 2: Classify Email ───────────────────────────────────


@celery_app.task(bind=True, max_retries=2, queue="orchestration", name="orchestration.classify_email")
def classify_email(self, ingest_result: dict) -> dict:
    """Classify an ingested email using heuristics → Claude fallback.

    Args:
        ingest_result: Output from ingest_email task

    Returns:
        dict with classification, confidence, method, stages
    """
    settings = get_settings()
    if not settings.ORCHESTRATION_ENABLED:
        return {**ingest_result, "status": "skipped"}

    start = time.monotonic()
    try:
        result = _run_async(_classify_email_async(ingest_result))
        elapsed = time.monotonic() - start
        elapsed_ms = int(elapsed * 1000)

        _run_async(_record_processing_task(
            inbox_message_id=ingest_result.get("inbox_message_id"),
            celery_task_id=self.request.id,
            stage="classify",
            status="success",
            output_data=result,
            tokens_used=result.get("tokens_used", 0),
            processing_time_ms=elapsed_ms,
        ))

        # M3: WebSocket progress
        _run_async(_broadcast_pipeline_progress(
            ingest_result.get("inbox_message_id"), "classify", "success",
            {"classification": result.get("classification"), "confidence": result.get("confidence"), "method": result.get("method")},
        ))

        # M4: Prometheus
        _observe_stage("classify", "success", elapsed, result.get("tokens_used", 0), "classify")
        try:
            from app.core.metrics import pipeline_emails_total
            pipeline_emails_total.labels(classification=result.get("classification", "unknown")).inc()
        except Exception:
            pass

        return result

    except Exception as exc:
        elapsed = time.monotonic() - start
        elapsed_ms = int(elapsed * 1000)
        logger.exception("orchestration.classify_failed", error=str(exc))

        _run_async(_record_processing_task(
            inbox_message_id=ingest_result.get("inbox_message_id"),
            celery_task_id=self.request.id,
            stage="classify",
            status="failed",
            error_message=str(exc),
            processing_time_ms=elapsed_ms,
        ))
        _observe_stage("classify", "failed", elapsed)

        try:
            raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
        except MaxRetriesExceededError:
            _run_async(_send_to_dlq(
                "orchestration.classify_email", "classify",
                ingest_result, str(exc), traceback.format_exc(),
                self.request.retries,
            ))
            return {**ingest_result, "status": "failed", "error": str(exc)}


async def _classify_email_async(ingest_result: dict) -> dict:
    """Classify email: try heuristics first, fall back to Claude."""
    from app.orchestration.agents.heuristic_classifier import HeuristicClassifier
    from app.orchestration.router import route_classification

    inbox_message_id = ingest_result["inbox_message_id"]
    subject = ingest_result.get("subject", "")
    body_text = ingest_result.get("body_text", "")
    has_attachments = bool(ingest_result.get("attachment_ids"))

    heuristic = HeuristicClassifier()
    heuristic_result = heuristic.classify(
        subject=subject,
        body=body_text,
        has_attachments=has_attachments,
        body_length=len(body_text),
    )

    tokens_used = 0
    method = "heuristic"

    if heuristic_result is not None:
        classification = heuristic_result.category
        confidence = heuristic_result.confidence
    else:
        # Fall back to Claude classifier with rate limiting
        from app.agents.email_classifier import EmailClassifier
        from app.core.config import get_settings

        settings = get_settings()

        if not settings.ANTHROPIC_API_KEY:
            classification = "dotaz"
            confidence = 0.5
            method = "default_fallback"
        else:
            # H4: Rate limiter
            try:
                from app.core.rate_limiter import RateLimitExceeded, get_rate_limiter
                limiter = get_rate_limiter()
                limiter.acquire(estimated_tokens=900)
            except RateLimitExceeded:
                raise
            except Exception:
                pass  # Redis unavailable — proceed without limiting

            try:
                classifier = EmailClassifier(api_key=settings.ANTHROPIC_API_KEY)
                result = await classifier.classify(subject=subject, body=body_text)
                classification = result.category
                confidence = result.confidence
                tokens_used = 900
                method = "claude"
            finally:
                try:
                    limiter = get_rate_limiter()
                    limiter.release()
                    limiter.record_usage(tokens_used)
                except Exception:
                    pass

    # Determine processing stages
    stages = route_classification(
        classification=classification or "dotaz",
        confidence=confidence,
        has_attachments=has_attachments,
    )

    # Update InboxMessage with classification
    from sqlalchemy import select

    from app.models.inbox import InboxClassification, InboxMessage, InboxStatus

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(InboxMessage).where(InboxMessage.id == UUID(inbox_message_id))
        )
        msg = result.scalar_one_or_none()
        if msg:
            try:
                msg.classification = InboxClassification(classification) if classification else None
            except ValueError:
                msg.classification = None
            msg.confidence = confidence
            msg.status = InboxStatus.CLASSIFIED if classification else InboxStatus.NEW
            await session.commit()

        # WebSocket notification
        try:
            from app.models.notification import NotificationType
            from app.models.user import UserRole
            from app.services.notification import NotificationService

            notif_service = NotificationService(session)
            await notif_service.create_for_roles(
                notification_type=NotificationType.EMAIL_CLASSIFIED,
                title="Email klasifikován",
                message=f"'{ingest_result.get('subject', '')}' → {classification or 'neznámé'} ({method})",
                roles=[UserRole.ADMIN, UserRole.OBCHODNIK],
                link="/inbox",
            )
            await session.commit()
        except Exception:
            pass

        # Prometheus metric
        try:
            from app.core.metrics import emails_processed_total

            emails_processed_total.labels(
                classification=classification or "unknown"
            ).inc()
        except Exception:
            pass

    return {
        **ingest_result,
        "classification": classification,
        "confidence": confidence,
        "method": method,
        "tokens_used": tokens_used,
        "stages": stages,
    }


# ─── Stage 3: Process Attachments ─────────────────────────────


@celery_app.task(bind=True, max_retries=2, queue="ocr", name="orchestration.process_attachment")
def process_attachment(self, attachment_id: str, file_path: str, content_type: str, filename: str) -> dict:
    """Process a single attachment: OCR + type detection.

    After processing, if the detected category is a drawing, triggers
    analyze_drawing as a follow-up task.

    Args:
        attachment_id: UUID of EmailAttachment
        file_path: Path to file on disk
        content_type: MIME type
        filename: Original filename

    Returns:
        dict with document_id, ocr_confidence, detected_category
    """
    start = time.monotonic()
    try:
        result = _run_async(_process_attachment_async(attachment_id, file_path, content_type, filename))
        elapsed = time.monotonic() - start
        elapsed_ms = int(elapsed * 1000)

        _run_async(_record_processing_task(
            inbox_message_id=None,
            celery_task_id=self.request.id,
            stage="ocr",
            status="success",
            input_data={"attachment_id": attachment_id, "filename": filename},
            output_data=result,
            processing_time_ms=elapsed_ms,
        ))
        _observe_stage("ocr", "success", elapsed)

        # H2: Trigger drawing analysis for technical drawings
        detected_category = result.get("detected_category", "")
        if detected_category in ("vykres", "technical_drawing") and result.get("document_id"):
            analyze_drawing.delay(
                result["document_id"],
                result.get("ocr_text", ""),
                result.get("ocr_confidence", 0.0),
            )
            logger.info(
                "orchestration.drawing_analysis_triggered",
                document_id=result["document_id"],
                category=detected_category,
            )

        return result

    except Exception as exc:
        elapsed = time.monotonic() - start
        elapsed_ms = int(elapsed * 1000)
        logger.exception("orchestration.process_attachment_failed", attachment_id=attachment_id, error=str(exc))
        _observe_stage("ocr", "failed", elapsed)

        try:
            raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
        except MaxRetriesExceededError:
            _run_async(_send_to_dlq(
                "orchestration.process_attachment", "ocr",
                {"attachment_id": attachment_id, "file_path": file_path, "content_type": content_type, "filename": filename},
                str(exc), traceback.format_exc(), self.request.retries,
            ))
            return {"status": "failed", "attachment_id": attachment_id, "error": str(exc)}


async def _process_attachment_async(attachment_id: str, file_path: str, content_type: str, filename: str) -> dict:
    from app.orchestration.agents.attachment_processor import AttachmentProcessor
    processor = AttachmentProcessor()
    return await processor.process(
        attachment_id=UUID(attachment_id),
        file_path=file_path,
        content_type=content_type,
        filename=filename,
    )


# ─── Stage 4: Parse Email ─────────────────────────────────────


@celery_app.task(bind=True, max_retries=2, queue="ai_agents", name="orchestration.parse_email")
def parse_email(self, classify_result: dict) -> dict:
    """Parse email content with Claude to extract structured data.

    Args:
        classify_result: Output from classify_email task

    Returns:
        dict with parsed_data merged into classify_result
    """
    start = time.monotonic()
    try:
        result = _run_async(_parse_email_async(classify_result))
        elapsed = time.monotonic() - start
        elapsed_ms = int(elapsed * 1000)

        _run_async(_record_processing_task(
            inbox_message_id=classify_result.get("inbox_message_id"),
            celery_task_id=self.request.id,
            stage="parse",
            status="success",
            output_data={"parsed_keys": list(result.get("parsed_data", {}).keys())},
            tokens_used=result.get("parse_tokens_used", 0),
            processing_time_ms=elapsed_ms,
        ))

        # M3: WebSocket progress
        _run_async(_broadcast_pipeline_progress(
            classify_result.get("inbox_message_id"), "parse", "success",
            {"parsed_keys": list(result.get("parsed_data", {}).keys())},
        ))

        # M4: Prometheus
        _observe_stage("parse", "success", elapsed, result.get("parse_tokens_used", 0), "parse")

        return result

    except Exception as exc:
        elapsed = time.monotonic() - start
        elapsed_ms = int(elapsed * 1000)
        logger.exception("orchestration.parse_failed", error=str(exc))
        _observe_stage("parse", "failed", elapsed)

        try:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        except MaxRetriesExceededError:
            _run_async(_send_to_dlq(
                "orchestration.parse_email", "parse",
                classify_result, str(exc), traceback.format_exc(),
                self.request.retries,
            ))
            return {**classify_result, "parsed_data": None, "status": "failed"}


async def _parse_email_async(classify_result: dict) -> dict:
    """Parse email using EmailParser and persist results."""
    from sqlalchemy import select

    from app.agents.email_parser import EmailParser
    from app.core.config import get_settings
    from app.models.inbox import InboxMessage

    settings = get_settings()

    # H4: Rate limiter
    try:
        from app.core.rate_limiter import RateLimitExceeded, get_rate_limiter
        limiter = get_rate_limiter()
        limiter.acquire(estimated_tokens=1200)
    except RateLimitExceeded:
        raise
    except Exception:
        pass

    try:
        parser = EmailParser(api_key=settings.ANTHROPIC_API_KEY)
        parsed = await parser.parse(
            subject=classify_result.get("subject", ""),
            body=classify_result.get("body_text", ""),
        )
    finally:
        try:
            limiter = get_rate_limiter()
            limiter.release()
            limiter.record_usage(1200)
        except Exception:
            pass

    # Convert to serializable dict
    parsed_data = {
        "company_name": parsed.company_name,
        "contact_name": parsed.contact_name,
        "email": parsed.email,
        "phone": parsed.phone,
        "items": [
            {
                "name": item.name,
                "material": item.material,
                "quantity": item.quantity,
                "unit": item.unit,
                "dimensions": item.dimensions,
            }
            for item in parsed.items
        ],
        "deadline": parsed.deadline,
        "note": parsed.note,
    }

    # Persist parsed_data to InboxMessage
    inbox_message_id = classify_result.get("inbox_message_id")
    if inbox_message_id:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(InboxMessage).where(InboxMessage.id == UUID(inbox_message_id))
            )
            msg = result.scalar_one_or_none()
            if msg:
                msg.parsed_data = parsed_data
                await session.commit()

    return {
        **classify_result,
        "parsed_data": parsed_data,
        "parse_tokens_used": 1200,  # Approximate
    }


# ─── Stage 5: Analyze Drawing ─────────────────────────────────


@celery_app.task(bind=True, max_retries=2, queue="ai_agents", name="orchestration.analyze_drawing")
def analyze_drawing(self, document_id: str, ocr_text: str, ocr_confidence: float) -> dict:
    """Analyze a drawing with Claude if OCR confidence > 30.

    Args:
        document_id: UUID of Document
        ocr_text: OCR extracted text
        ocr_confidence: OCR confidence score

    Returns:
        dict with analysis results
    """
    if ocr_confidence < 30:
        return {"status": "skipped", "reason": "low_ocr_confidence", "document_id": document_id}

    start = time.monotonic()
    try:
        # H4: Rate limiter
        try:
            from app.core.rate_limiter import RateLimitExceeded, get_rate_limiter
            limiter = get_rate_limiter()
            limiter.acquire(estimated_tokens=2500)
        except RateLimitExceeded:
            raise
        except Exception:
            pass

        result = _run_async(_analyze_drawing_async(document_id, ocr_text))
        elapsed = time.monotonic() - start
        elapsed_ms = int(elapsed * 1000)

        # Release rate limiter
        try:
            limiter = get_rate_limiter()
            limiter.release()
            limiter.record_usage(result.get("tokens_used", 2500))
        except Exception:
            pass

        _run_async(_record_processing_task(
            inbox_message_id=None,
            celery_task_id=self.request.id,
            stage="analyze",
            status="success",
            input_data={"document_id": document_id},
            output_data={"dimensions_count": len(result.get("dimensions", []))},
            tokens_used=result.get("tokens_used", 0),
            processing_time_ms=elapsed_ms,
        ))

        # M3: WebSocket progress
        _run_async(_broadcast_pipeline_progress(
            None, "analyze", "success",
            {"document_id": document_id, "dimensions_count": len(result.get("dimensions", []))},
        ))

        # M4: Prometheus
        _observe_stage("analyze", "success", elapsed, result.get("tokens_used", 0), "analyze_drawing")

        return result

    except Exception as exc:
        elapsed = time.monotonic() - start
        logger.exception("orchestration.analyze_drawing_failed", document_id=document_id)
        _observe_stage("analyze", "failed", elapsed)
        try:
            limiter = get_rate_limiter()
            limiter.release()
        except Exception:
            pass
        try:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        except MaxRetriesExceededError:
            _run_async(_send_to_dlq(
                "orchestration.analyze_drawing", "analyze",
                {"document_id": document_id}, str(exc), traceback.format_exc(),
                self.request.retries,
            ))
            return {"status": "failed", "document_id": document_id}


async def _analyze_drawing_async(document_id: str, ocr_text: str) -> dict:
    """Run drawing analysis and persist results."""
    from app.core.config import get_settings
    from app.integrations.ocr.drawing_analyzer import DrawingAnalyzer
    from app.models.drawing_analysis import DrawingAnalysis as DrawingAnalysisModel

    settings = get_settings()
    analyzer = DrawingAnalyzer(api_key=settings.ANTHROPIC_API_KEY)
    analysis = await analyzer.analyze(ocr_text=ocr_text)

    # Persist to DB
    async with AsyncSessionLocal() as session:
        db_analysis = DrawingAnalysisModel(
            document_id=UUID(document_id),
            dimensions=[{"type": d.type, "value": d.value, "unit": d.unit, "tolerance": d.tolerance} for d in analysis.dimensions],
            materials=[{"grade": m.grade, "standard": m.standard, "type": m.type} for m in analysis.materials],
            tolerances=[{"type": t.type, "value": t.value, "standard": t.standard} for t in analysis.tolerances],
            surface_treatments=analysis.surface_treatments,
            welding_requirements={
                "wps": analysis.welding_requirements.wps,
                "wpqr": analysis.welding_requirements.wpqr,
                "ndt_methods": analysis.welding_requirements.ndt_methods,
                "acceptance_criteria": analysis.welding_requirements.acceptance_criteria,
            },
            notes=analysis.notes,
            analysis_model="claude-sonnet-4-20250514",
            tokens_used=2500,
        )
        session.add(db_analysis)
        await session.commit()

    return {
        "document_id": document_id,
        "dimensions_count": len(analysis.dimensions),
        "materials_count": len(analysis.materials),
        "tokens_used": 2500,
    }


# ─── Stage 6: Orchestrate Order ───────────────────────────────


@celery_app.task(bind=True, max_retries=3, queue="orchestration", name="orchestration.orchestrate_order")
def orchestrate_order(self, pipeline_result: dict) -> dict:
    """Create/match customer and order from parsed email data.

    Args:
        pipeline_result: Output from parse_email or classify_email task

    Returns:
        dict with customer_id, order_id, next_stage
    """
    settings = get_settings()
    if not settings.ORCHESTRATION_AUTO_CREATE_ORDERS:
        return {**pipeline_result, "orchestration": "skipped", "reason": "auto_create_orders disabled"}

    start = time.monotonic()
    try:
        result = _run_async(_orchestrate_order_async(pipeline_result))
        elapsed = time.monotonic() - start
        elapsed_ms = int(elapsed * 1000)

        _run_async(_record_processing_task(
            inbox_message_id=pipeline_result.get("inbox_message_id"),
            celery_task_id=self.request.id,
            stage="orchestrate",
            status="success",
            output_data=result,
            processing_time_ms=elapsed_ms,
        ))

        # M3: WebSocket progress
        _run_async(_broadcast_pipeline_progress(
            pipeline_result.get("inbox_message_id"), "orchestrate", "success",
            {"order_id": str(result.get("order_id", "")), "customer_created": result.get("customer_created")},
        ))

        # M4: Prometheus
        _observe_stage("orchestrate", "success", elapsed)

        return result

    except Exception as exc:
        elapsed = time.monotonic() - start
        elapsed_ms = int(elapsed * 1000)
        logger.exception("orchestration.orchestrate_order_failed", error=str(exc))
        _observe_stage("orchestrate", "failed", elapsed)

        try:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        except MaxRetriesExceededError:
            _run_async(_send_to_dlq(
                "orchestration.orchestrate_order", "orchestrate",
                pipeline_result, str(exc), traceback.format_exc(),
                self.request.retries,
            ))
            return {**pipeline_result, "status": "failed"}


async def _orchestrate_order_async(pipeline_result: dict) -> dict:
    from app.orchestration.agents.order_orchestrator import OrderOrchestrator

    # Merge classification and email context into parsed_data
    # OrderOrchestrator.process() expects (inbox_message_id, parsed_data)
    parsed_data = dict(pipeline_result.get("parsed_data") or {})
    if "classification" not in parsed_data and pipeline_result.get("classification"):
        parsed_data["classification"] = pipeline_result["classification"]
    if "email" not in parsed_data and pipeline_result.get("from_email"):
        parsed_data["email"] = pipeline_result["from_email"]

    orchestrator = OrderOrchestrator()
    return await orchestrator.process(
        inbox_message_id=UUID(pipeline_result["inbox_message_id"]),
        parsed_data=parsed_data,
    )


# ─── Stage 7: Auto Calculate ──────────────────────────────────


@celery_app.task(bind=True, max_retries=2, queue="ai_agents", name="orchestration.auto_calculate")
def auto_calculate(self, orchestration_result: dict) -> dict:
    """Auto-trigger calculation for poptavky orders.

    Args:
        orchestration_result: Output from orchestrate_order task

    Returns:
        dict with calculation_id
    """
    settings = get_settings()
    if not settings.ORCHESTRATION_AUTO_CALCULATE:
        return {**orchestration_result, "calculation": "skipped"}

    order_id = orchestration_result.get("order_id")
    if not order_id:
        return {**orchestration_result, "calculation": "skipped", "reason": "no_order"}

    if not settings.ANTHROPIC_API_KEY:
        logger.warning("orchestration.auto_calculate_skipped", reason="ANTHROPIC_API_KEY not set")
        return {**orchestration_result, "calculation": "skipped", "reason": "no_api_key"}

    start = time.monotonic()
    try:
        result = _run_async(_auto_calculate_async(str(order_id)))
        elapsed = time.monotonic() - start
        elapsed_ms = int(elapsed * 1000)

        _run_async(_record_processing_task(
            inbox_message_id=orchestration_result.get("inbox_message_id"),
            celery_task_id=self.request.id,
            stage="calculate",
            status="success",
            input_data={"order_id": str(order_id)},
            output_data=result,
            tokens_used=result.get("tokens_used", 0),
            processing_time_ms=elapsed_ms,
        ))

        # M3: WebSocket progress
        _run_async(_broadcast_pipeline_progress(
            orchestration_result.get("inbox_message_id"), "calculate", "success",
            {"calculation_id": result.get("calculation_id"), "total_czk": result.get("total_czk")},
        ))

        # M4: Prometheus
        _observe_stage("calculate", "success", elapsed, result.get("tokens_used", 0), "auto_calculate")

        return {**orchestration_result, **result}

    except Exception as exc:
        elapsed = time.monotonic() - start
        logger.exception("orchestration.auto_calculate_failed", order_id=order_id)
        _observe_stage("calculate", "failed", elapsed)
        try:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        except MaxRetriesExceededError:
            _run_async(_send_to_dlq(
                "orchestration.auto_calculate", "calculate",
                {"order_id": str(order_id)}, str(exc), traceback.format_exc(),
                self.request.retries,
            ))
            return {**orchestration_result, "calculation": "failed"}


async def _auto_calculate_async(order_id: str) -> dict:
    """Trigger calculation agent for order — full implementation.

    Loads the order from DB, builds description/items, calls CalculationAgent.estimate(),
    creates Calculation + CalculationItem records, and returns summary.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.agents.calculation_agent import CalculationAgent
    from app.core.config import get_settings
    from app.models.calculation import Calculation, CalculationItem, CalculationStatus, CostType
    from app.models.order import Order

    settings = get_settings()

    # H4: Rate limiter
    try:
        from app.core.rate_limiter import RateLimitExceeded, get_rate_limiter
        limiter = get_rate_limiter()
        limiter.acquire(estimated_tokens=4000)
    except RateLimitExceeded:
        raise
    except Exception:
        pass

    try:
        async with AsyncSessionLocal() as session:
            # Load order with items and customer
            result = await session.execute(
                select(Order)
                .options(selectinload(Order.customer))
                .where(Order.id == UUID(order_id))
            )
            order = result.scalar_one_or_none()
            if not order:
                raise ValueError(f"Order not found: {order_id}")

            # Build description from order data
            customer_name = order.customer.company_name if order.customer else "Neznámý zákazník"
            description = f"Zakázka {order.number} pro {customer_name}"
            if order.note:
                description += f"\n{order.note}"

            # Build items list from parsed_data (stored on related InboxMessage)
            items: list[dict] = []
            # Try to get items from inbox message parsed_data
            from app.models.inbox import InboxMessage
            inbox_result = await session.execute(
                select(InboxMessage).where(InboxMessage.order_id == UUID(order_id))
            )
            inbox_msg = inbox_result.scalar_one_or_none()
            if inbox_msg and inbox_msg.parsed_data and isinstance(inbox_msg.parsed_data, dict):
                parsed_items = inbox_msg.parsed_data.get("items", [])
                for item in parsed_items:
                    if isinstance(item, dict):
                        items.append({
                            "name": item.get("name", "Položka"),
                            "material": item.get("material", "Nespecifikováno"),
                            "dimension": item.get("dimensions", ""),
                            "quantity": item.get("quantity", 1),
                            "unit": item.get("unit", "ks"),
                        })

            # Fallback if no items
            if not items:
                items = [{
                    "name": f"Zakázka {order.number}",
                    "material": "Nespecifikováno",
                    "dimension": "",
                    "quantity": 1,
                    "unit": "ks",
                }]

            # Call CalculationAgent
            agent = CalculationAgent(api_key=settings.ANTHROPIC_API_KEY, db_session=session)
            estimate = await agent.estimate(description=description, items=items)

            tokens_used = 4000  # Approximate

            # Create Calculation record
            calc = Calculation(
                order_id=UUID(order_id),
                name=f"Auto-kalkulace {order.number}",
                status=CalculationStatus.PENDING_APPROVAL,
                note=estimate.reasoning,
                material_total=Decimal(str(estimate.material_cost_czk)),
                labor_total=Decimal(str(estimate.labor_cost_czk)),
                overhead_total=Decimal(str(estimate.overhead_czk)),
                margin_percent=Decimal(str(estimate.margin_percent)),
                total_price=Decimal(str(estimate.total_czk)),
            )
            # Calculate margin amount
            direct = estimate.material_cost_czk + estimate.labor_cost_czk + estimate.overhead_czk
            calc.margin_amount = Decimal(str(direct * (estimate.margin_percent / 100.0)))

            session.add(calc)
            await session.flush()

            # Create CalculationItem records from breakdown
            for item_est in estimate.breakdown:
                labor_cost = item_est.labor_hours * 850.0  # Default hourly rate
                # Material item
                if item_est.material_cost_czk > 0:
                    mat_item = CalculationItem(
                        calculation_id=calc.id,
                        cost_type=CostType.MATERIAL,
                        name=item_est.name,
                        description=item_est.notes,
                        quantity=Decimal("1"),
                        unit="ks",
                        unit_price=Decimal(str(item_est.material_cost_czk)),
                        total_price=Decimal(str(item_est.material_cost_czk)),
                    )
                    session.add(mat_item)

                # Labor item
                if item_est.labor_hours > 0:
                    lab_item = CalculationItem(
                        calculation_id=calc.id,
                        cost_type=CostType.LABOR,
                        name=f"Práce - {item_est.name}",
                        description=f"{item_est.labor_hours} hodin",
                        quantity=Decimal(str(item_est.labor_hours)),
                        unit="hod",
                        unit_price=Decimal("850"),
                        total_price=Decimal(str(labor_cost)),
                    )
                    session.add(lab_item)

            # Overhead item
            if estimate.overhead_czk > 0:
                overhead_item = CalculationItem(
                    calculation_id=calc.id,
                    cost_type=CostType.OVERHEAD,
                    name="Režijní náklady",
                    description="Energie, spotřební materiál, administrativa",
                    quantity=Decimal("1"),
                    unit="ks",
                    unit_price=Decimal(str(estimate.overhead_czk)),
                    total_price=Decimal(str(estimate.overhead_czk)),
                )
                session.add(overhead_item)

            await session.commit()

            logger.info(
                "orchestration.auto_calculate_complete",
                order_id=order_id,
                calculation_id=str(calc.id),
                total_czk=estimate.total_czk,
            )

            return {
                "calculation_id": str(calc.id),
                "total_czk": estimate.total_czk,
                "margin_percent": estimate.margin_percent,
                "tokens_used": tokens_used,
                "items_count": len(estimate.breakdown),
            }
    finally:
        try:
            limiter = get_rate_limiter()
            limiter.release()
            limiter.record_usage(4000)
        except Exception:
            pass


# ─── Stage 8: Generate Offer ──────────────────────────────────


@celery_app.task(bind=True, max_retries=2, queue="orchestration", name="orchestration.generate_offer")
def generate_offer(self, pipeline_result: dict) -> dict:
    """Generate PDF offer + Pohoda XML after calculation.

    Accepts pipeline_result dict from the chain (auto_calculate output).
    Extracts order_id and calculation_id from the result.

    Args:
        pipeline_result: Output from auto_calculate task (or dict with order_id/calculation_id)

    Returns:
        dict with offer_pdf_path, pohoda_xml_path, document_id
    """
    settings = get_settings()
    if not settings.ORCHESTRATION_AUTO_OFFER:
        return {**pipeline_result, "offer": "skipped", "reason": "auto_offer disabled"}

    # Extract order_id and calculation_id from pipeline result
    order_id = pipeline_result.get("order_id")
    calculation_id = pipeline_result.get("calculation_id")

    if not order_id or not calculation_id:
        logger.info(
            "orchestration.generate_offer_skipped",
            reason="missing order_id or calculation_id",
            order_id=order_id,
            calculation_id=calculation_id,
        )
        return {**pipeline_result, "offer": "skipped", "reason": "no_order_or_calculation"}

    start = time.monotonic()
    try:
        result = _run_async(_generate_offer_async(str(order_id), str(calculation_id)))
        elapsed = time.monotonic() - start
        elapsed_ms = int(elapsed * 1000)

        _run_async(_record_processing_task(
            inbox_message_id=pipeline_result.get("inbox_message_id"),
            celery_task_id=self.request.id,
            stage="offer",
            status="success",
            input_data={"order_id": str(order_id), "calculation_id": str(calculation_id)},
            output_data=result,
            processing_time_ms=elapsed_ms,
        ))

        # M1: Mark processing completed (terminal stage for poptavka)
        _run_async(_update_inbox_timestamp(pipeline_result.get("inbox_message_id"), "processing_completed_at"))

        # M3: WebSocket progress
        _run_async(_broadcast_pipeline_progress(
            pipeline_result.get("inbox_message_id"), "offer", "success",
            {"document_id": result.get("document_id")},
        ))

        # M4: Prometheus
        _observe_stage("offer", "success", elapsed)

        return {**pipeline_result, **result}

    except Exception as exc:
        elapsed = time.monotonic() - start
        logger.exception("orchestration.generate_offer_failed", order_id=order_id)
        _observe_stage("offer", "failed", elapsed)
        try:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        except MaxRetriesExceededError:
            _run_async(_send_to_dlq(
                "orchestration.generate_offer", "offer",
                {"order_id": str(order_id), "calculation_id": str(calculation_id)},
                str(exc), traceback.format_exc(), self.request.retries,
            ))
            return {**pipeline_result, "offer": "failed"}


async def _generate_offer_async(order_id: str, calculation_id: str) -> dict:
    """Generate offer — checks calculation status before proceeding."""
    from sqlalchemy import select

    from app.models.calculation import Calculation, CalculationStatus

    # Check if calculation is approved
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Calculation).where(Calculation.id == UUID(calculation_id))
        )
        calc = result.scalar_one_or_none()
        if not calc:
            return {"offer": "skipped", "reason": f"calculation {calculation_id} not found"}

        if calc.status != CalculationStatus.APPROVED:
            logger.info(
                "orchestration.offer_awaiting_approval",
                calculation_id=calculation_id,
                current_status=calc.status.value,
            )
            return {
                "offer": "awaiting_approval",
                "reason": f"Calculation status is {calc.status.value}, not approved",
                "calculation_id": calculation_id,
            }

    # Calculation is approved — generate offer
    from app.orchestration.agents.offer_generator import OfferGenerator
    generator = OfferGenerator()
    return await generator.generate(
        order_id=UUID(order_id),
        calculation_id=UUID(calculation_id),
    )


# ─── Pipeline Orchestrator ─────────────────────────────────────


@celery_app.task(bind=True, queue="orchestration", name="orchestration.run_pipeline")
def run_pipeline(self, raw_email_data: dict) -> dict:
    """Run the full orchestration pipeline for a single email.

    This is the main entry point. It chains:
    ingest → classify → route → (parse + process_attachments) → orchestrate → calculate → offer

    Args:
        raw_email_data: Serialized email data from IMAP

    Returns:
        dict with pipeline execution summary
    """
    settings = get_settings()
    if not settings.ORCHESTRATION_ENABLED:
        return {"status": "skipped", "reason": "orchestration disabled"}

    # Chain: ingest → classify → dynamic routing
    pipeline = chain(
        ingest_email.s(raw_email_data),
        classify_email.s(),
        route_and_execute.s(),
    )

    result = pipeline.apply_async()

    return {
        "status": "pipeline_started",
        "task_id": result.id,
        "message_id": raw_email_data.get("message_id"),
    }


@celery_app.task(bind=True, queue="orchestration", name="orchestration.route_and_execute")
def route_and_execute(self, classify_result: dict) -> dict:
    """Route classified email to appropriate processing stages.

    Dispatches downstream tasks as a Celery chain so each task runs
    on a fresh worker process with its own event loop (avoids
    asyncio.run() + stale connection pool issues from .apply()).

    Also sends auto-reply email after classification.

    Args:
        classify_result: Output from classify_email

    Returns:
        dict with routing decision
    """
    # Send auto-reply right after classification
    _send_pipeline_auto_reply(classify_result)

    stages = classify_result.get("stages", [])

    if not stages:
        return {**classify_result, "pipeline_status": "no_stages"}

    if "review" in stages:
        _run_async(_mark_for_review(classify_result.get("inbox_message_id")))
        # M1: Mark processing completed (terminal: review)
        _run_async(_update_inbox_timestamp(classify_result.get("inbox_message_id"), "processing_completed_at"))
        return {**classify_result, "pipeline_status": "needs_review"}

    if "archive" in stages:
        _run_async(_archive_message(classify_result.get("inbox_message_id")))
        # M1: Mark processing completed (terminal: archive)
        _run_async(_update_inbox_timestamp(classify_result.get("inbox_message_id"), "processing_completed_at"))
        return {**classify_result, "pipeline_status": "archived"}

    # Process attachments in parallel (fire-and-forget)
    if "process_attachments" in stages:
        attachment_ids = classify_result.get("attachment_ids", [])
        if attachment_ids:
            for att_id in attachment_ids:
                att_data = classify_result.get("attachment_data", {}).get(att_id, {})
                process_attachment.delay(
                    att_id,
                    att_data.get("file_path", ""),
                    att_data.get("content_type", ""),
                    att_data.get("filename", ""),
                )

    # Build sequential chain dynamically — each task runs on its own worker
    chain_tasks = []
    if "parse_email" in stages:
        chain_tasks.append(parse_email.s())
    if "orchestrate_order" in stages:
        chain_tasks.append(orchestrate_order.s())
    if "auto_calculate" in stages:
        chain_tasks.append(auto_calculate.s())
    if "generate_offer" in stages:
        chain_tasks.append(generate_offer.s())

    if chain_tasks:
        # First task in chain gets classify_result as argument
        pipeline = chain(chain_tasks[0].clone(args=[classify_result]), *chain_tasks[1:])
        pipeline.apply_async()

    return {**classify_result, "pipeline_status": "routed", "stages": stages}


async def _mark_for_review(inbox_message_id: str | None) -> None:
    """Mark InboxMessage as needing review."""
    if not inbox_message_id:
        return
    from sqlalchemy import select

    from app.models.inbox import InboxMessage, InboxStatus

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(InboxMessage).where(InboxMessage.id == UUID(inbox_message_id))
        )
        msg = result.scalar_one_or_none()
        if msg:
            msg.status = InboxStatus.REVIEW
            msg.needs_review = True
            await session.commit()


async def _archive_message(inbox_message_id: str | None) -> None:
    """Archive an inbox message (obchodni_sdeleni)."""
    if not inbox_message_id:
        return
    from sqlalchemy import select

    from app.models.inbox import InboxMessage, InboxStatus

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(InboxMessage).where(InboxMessage.id == UUID(inbox_message_id))
        )
        msg = result.scalar_one_or_none()
        if msg:
            msg.status = InboxStatus.ARCHIVED
            await session.commit()


async def _escalate_message(inbox_message_id: str | None) -> None:
    """Escalate an inbox message (reklamace)."""
    if not inbox_message_id:
        return
    from sqlalchemy import select

    from app.models.inbox import InboxMessage, InboxStatus

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(InboxMessage).where(InboxMessage.id == UUID(inbox_message_id))
        )
        msg = result.scalar_one_or_none()
        if msg:
            msg.status = InboxStatus.ESCALATED
            await session.commit()


async def _notify_email_new(subject: str, from_email: str) -> None:
    """Send EMAIL_NEW notification to ADMIN and OBCHODNIK."""
    try:
        from app.models.notification import NotificationType
        from app.models.user import UserRole
        from app.services.notification import NotificationService

        async with AsyncSessionLocal() as session:
            notif_service = NotificationService(session)
            await notif_service.create_for_roles(
                notification_type=NotificationType.EMAIL_NEW,
                title="Nový email",
                message=f"Od: {from_email} — '{subject}'",
                roles=[UserRole.ADMIN, UserRole.OBCHODNIK],
                link="/inbox",
            )
            await session.commit()
    except Exception:
        logger.warning("orchestration.notify_email_new_failed")


async def _notify_assignment(inbox_message_id: str | None) -> None:
    """Send notification about email assignment."""
    if not inbox_message_id:
        return
    try:
        from app.models.notification import NotificationType
        from app.models.user import UserRole
        from app.services.notification import NotificationService

        async with AsyncSessionLocal() as session:
            notif_service = NotificationService(session)
            await notif_service.create_for_roles(
                notification_type=NotificationType.EMAIL_CLASSIFIED,
                title="Email přiřazen k zakázce",
                message="Nový email byl automaticky přiřazen k existující zakázce.",
                roles=[UserRole.ADMIN, UserRole.OBCHODNIK],
                link="/inbox",
            )
            await session.commit()
    except Exception:
        logger.warning("orchestration.notify_failed", inbox_message_id=inbox_message_id)


def _send_pipeline_auto_reply(classify_result: dict) -> None:
    """Send auto-reply email after classification in the orchestration pipeline.

    Dispatches the auto-reply as a Celery task for async SMTP sending.

    Args:
        classify_result: Output from classify_email with from_email, subject, classification
    """
    from_email = classify_result.get("from_email")
    subject = classify_result.get("subject", "")
    classification = classify_result.get("classification")

    if not from_email:
        return

    # Skip auto-reply for commercial messages
    if classification == "obchodni_sdeleni":
        return

    try:
        from app.integrations.email.tasks import send_auto_reply_task

        reply_subject = f"Re: {subject}"
        send_auto_reply_task.delay(
            to_email=from_email,
            subject=reply_subject,
            classification=classification,
            message_preview=classify_result.get("body_text", "")[:200],
            original_message_id=classify_result.get("original_message_id"),
        )

        # Mark auto_reply_sent on InboxMessage
        inbox_message_id = classify_result.get("inbox_message_id")
        if inbox_message_id:
            _run_async(_mark_auto_reply_sent(inbox_message_id))

        logger.info(
            "orchestration.auto_reply_dispatched",
            to_email=from_email,
            classification=classification,
        )
    except Exception:
        logger.warning(
            "orchestration.auto_reply_dispatch_failed",
            from_email=from_email,
        )


async def _mark_auto_reply_sent(inbox_message_id: str) -> None:
    """Mark InboxMessage as auto-reply sent."""
    from sqlalchemy import select

    from app.models.inbox import InboxMessage

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(InboxMessage).where(InboxMessage.id == UUID(inbox_message_id))
        )
        msg = result.scalar_one_or_none()
        if msg:
            msg.auto_reply_sent = True
            await session.commit()
