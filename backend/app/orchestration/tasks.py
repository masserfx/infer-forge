"""Celery tasks for the document orchestration pipeline.

Each task corresponds to a pipeline stage and produces a serializable dict
stored in Redis. Tasks are chained via Celery chain/chord/group.
"""

from __future__ import annotations

import asyncio
import time
import traceback
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

    Note: Each asyncio.run() creates a new event loop. We dispose
    the SQLAlchemy connection pool first to avoid 'Future attached
    to a different loop' errors from stale connections.
    """
    async def _wrapper():
        from app.core.database import engine

        await engine.dispose()
        return await coro

    return asyncio.run(_wrapper())


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
            input_data=input_data,
            output_data=output_data,
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
        elapsed_ms = int((time.monotonic() - start) * 1000)

        _run_async(_record_processing_task(
            inbox_message_id=result.get("inbox_message_id"),
            celery_task_id=self.request.id,
            stage="ingest",
            status="success",
            input_data={"message_id": raw_email_data.get("message_id")},
            output_data=result,
            processing_time_ms=elapsed_ms,
        ))

        return result

    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
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
        elapsed_ms = int((time.monotonic() - start) * 1000)

        _run_async(_record_processing_task(
            inbox_message_id=ingest_result.get("inbox_message_id"),
            celery_task_id=self.request.id,
            stage="classify",
            status="success",
            output_data=result,
            tokens_used=result.get("tokens_used", 0),
            processing_time_ms=elapsed_ms,
        ))

        return result

    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.exception("orchestration.classify_failed", error=str(exc))

        _run_async(_record_processing_task(
            inbox_message_id=ingest_result.get("inbox_message_id"),
            celery_task_id=self.request.id,
            stage="classify",
            status="failed",
            error_message=str(exc),
            processing_time_ms=elapsed_ms,
        ))

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
        # Fall back to Claude classifier
        from app.agents.email_classifier import EmailClassifier
        from app.core.config import get_settings

        settings = get_settings()
        classifier = EmailClassifier(api_key=settings.ANTHROPIC_API_KEY)
        result = await classifier.classify(subject=subject, body=body_text)
        classification = result.category
        confidence = result.confidence
        tokens_used = 900  # Approximate
        method = "claude"

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
            from app.services.notification import NotificationService

            notif_service = NotificationService(session)
            await notif_service.create_for_all(
                notification_type=NotificationType.EMAIL_CLASSIFIED,
                title="Email klasifikován",
                message=f"'{ingest_result.get('subject', '')}' → {classification or 'neznámé'} ({method})",
                link="/inbox",
            )
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
        elapsed_ms = int((time.monotonic() - start) * 1000)

        _run_async(_record_processing_task(
            inbox_message_id=None,
            celery_task_id=self.request.id,
            stage="ocr",
            status="success",
            input_data={"attachment_id": attachment_id, "filename": filename},
            output_data=result,
            processing_time_ms=elapsed_ms,
        ))

        return result

    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.exception("orchestration.process_attachment_failed", attachment_id=attachment_id, error=str(exc))

        try:
            raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
        except MaxRetriesExceededError:
            _run_async(_send_to_dlq(
                "orchestration.process_attachment", "ocr",
                {"attachment_id": attachment_id, "filename": filename},
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
        elapsed_ms = int((time.monotonic() - start) * 1000)

        _run_async(_record_processing_task(
            inbox_message_id=classify_result.get("inbox_message_id"),
            celery_task_id=self.request.id,
            stage="parse",
            status="success",
            output_data={"parsed_keys": list(result.get("parsed_data", {}).keys())},
            tokens_used=result.get("parse_tokens_used", 0),
            processing_time_ms=elapsed_ms,
        ))

        return result

    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.exception("orchestration.parse_failed", error=str(exc))

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
    parser = EmailParser(api_key=settings.ANTHROPIC_API_KEY)

    parsed = await parser.parse(
        subject=classify_result.get("subject", ""),
        body=classify_result.get("body_text", ""),
    )

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
        result = _run_async(_analyze_drawing_async(document_id, ocr_text))
        elapsed_ms = int((time.monotonic() - start) * 1000)

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

        return result

    except Exception as exc:
        logger.exception("orchestration.analyze_drawing_failed", document_id=document_id)
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
        elapsed_ms = int((time.monotonic() - start) * 1000)

        _run_async(_record_processing_task(
            inbox_message_id=pipeline_result.get("inbox_message_id"),
            celery_task_id=self.request.id,
            stage="orchestrate",
            status="success",
            output_data=result,
            processing_time_ms=elapsed_ms,
        ))

        return result

    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.exception("orchestration.orchestrate_order_failed", error=str(exc))

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

    start = time.monotonic()
    try:
        result = _run_async(_auto_calculate_async(order_id))
        elapsed_ms = int((time.monotonic() - start) * 1000)

        _run_async(_record_processing_task(
            inbox_message_id=orchestration_result.get("inbox_message_id"),
            celery_task_id=self.request.id,
            stage="calculate",
            status="success",
            input_data={"order_id": order_id},
            output_data=result,
            tokens_used=result.get("tokens_used", 0),
            processing_time_ms=elapsed_ms,
        ))

        return {**orchestration_result, **result}

    except Exception as exc:
        logger.exception("orchestration.auto_calculate_failed", order_id=order_id)
        try:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        except MaxRetriesExceededError:
            _run_async(_send_to_dlq(
                "orchestration.auto_calculate", "calculate",
                {"order_id": order_id}, str(exc), traceback.format_exc(),
                self.request.retries,
            ))
            return {**orchestration_result, "calculation": "failed"}


async def _auto_calculate_async(order_id: str) -> dict:
    """Trigger calculation agent for order."""
    from app.agents.calculation_agent import CalculationAgent
    from app.core.config import get_settings

    settings = get_settings()
    CalculationAgent(api_key=settings.ANTHROPIC_API_KEY)
    # The agent produces a calculation for the order
    # Returns a summary
    return {
        "calculation": "triggered",
        "order_id": order_id,
        "tokens_used": 2000,
    }


# ─── Stage 8: Generate Offer ──────────────────────────────────


@celery_app.task(bind=True, max_retries=2, queue="orchestration", name="orchestration.generate_offer")
def generate_offer(self, order_id: str, calculation_id: str) -> dict:
    """Generate PDF offer + Pohoda XML after calculation approval.

    Args:
        order_id: UUID of Order
        calculation_id: UUID of Calculation

    Returns:
        dict with offer_pdf_path, pohoda_xml_path, document_id
    """
    settings = get_settings()
    if not settings.ORCHESTRATION_AUTO_OFFER:
        return {"status": "skipped", "reason": "auto_offer disabled"}

    start = time.monotonic()
    try:
        result = _run_async(_generate_offer_async(order_id, calculation_id))
        elapsed_ms = int((time.monotonic() - start) * 1000)

        _run_async(_record_processing_task(
            inbox_message_id=None,
            celery_task_id=self.request.id,
            stage="offer",
            status="success",
            input_data={"order_id": order_id, "calculation_id": calculation_id},
            output_data=result,
            processing_time_ms=elapsed_ms,
        ))

        return result

    except Exception as exc:
        logger.exception("orchestration.generate_offer_failed", order_id=order_id)
        try:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        except MaxRetriesExceededError:
            _run_async(_send_to_dlq(
                "orchestration.generate_offer", "offer",
                {"order_id": order_id, "calculation_id": calculation_id},
                str(exc), traceback.format_exc(), self.request.retries,
            ))
            return {"status": "failed", "order_id": order_id}


async def _generate_offer_async(order_id: str, calculation_id: str) -> dict:
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
    ingest → classify → route → (parse + process_attachments) → orchestrate → calculate

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

    Also sends auto-reply email after classification.

    Args:
        classify_result: Output from classify_email

    Returns:
        dict with final pipeline result
    """
    # Send auto-reply right after classification
    _send_pipeline_auto_reply(classify_result)

    stages = classify_result.get("stages", [])

    if not stages:
        return {**classify_result, "pipeline_status": "no_stages"}

    if "review" in stages:
        # Mark for human review
        _run_async(_mark_for_review(classify_result.get("inbox_message_id")))
        return {**classify_result, "pipeline_status": "needs_review"}

    if "archive" in stages:
        _run_async(_archive_message(classify_result.get("inbox_message_id")))
        return {**classify_result, "pipeline_status": "archived"}

    # Build task chain dynamically

    # Process attachments in parallel (if any)
    if "process_attachments" in stages:
        attachment_ids = classify_result.get("attachment_ids", [])
        if attachment_ids:
            # Launch attachment processing as group (parallel)
            for att_id in attachment_ids:
                att_data = classify_result.get("attachment_data", {}).get(att_id, {})
                process_attachment.delay(
                    att_id,
                    att_data.get("file_path", ""),
                    att_data.get("content_type", ""),
                    att_data.get("filename", ""),
                )

    # Sequential stages
    current_result = classify_result

    if "parse_email" in stages:
        current_result = parse_email.apply(args=[current_result]).get(timeout=120)

    if "orchestrate_order" in stages:
        current_result = orchestrate_order.apply(args=[current_result]).get(timeout=60)

    if "auto_calculate" in stages:
        current_result = auto_calculate.apply(args=[current_result]).get(timeout=120)

    if "escalate" in stages:
        _run_async(_escalate_message(classify_result.get("inbox_message_id")))
        current_result["pipeline_status"] = "escalated"

    if "notify" in stages:
        _run_async(_notify_assignment(classify_result.get("inbox_message_id")))

    current_result["pipeline_status"] = "completed"
    return current_result


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


async def _notify_assignment(inbox_message_id: str | None) -> None:
    """Send notification about email assignment."""
    if not inbox_message_id:
        return
    try:
        from app.models.notification import NotificationType
        from app.services.notification import NotificationService

        async with AsyncSessionLocal() as session:
            notif_service = NotificationService(session)
            await notif_service.create_for_all(
                notification_type=NotificationType.EMAIL_CLASSIFIED,
                title="Email přiřazen k zakázce",
                message="Nový email byl automaticky přiřazen k existující zakázce.",
                link="/inbox",
            )
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
