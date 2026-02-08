"""Orchestration API endpoints for DLQ management and pipeline monitoring."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models.dead_letter import DeadLetterEntry
from app.models.processing_task import ProcessingStage, ProcessingStatus, ProcessingTask

router = APIRouter(prefix="/orchestrace", tags=["orchestrace"])


# ─── Schemas ───────────────────────────────────────────────────

class TestEmailAttachment(BaseModel):
    filename: str
    content_type: str = "application/octet-stream"
    data_base64: str = Field(description="Base64-encoded file content")


class TestEmailRequest(BaseModel):
    from_email: str = Field(description="Sender email address")
    subject: str = Field(description="Email subject")
    body_text: str = Field(description="Email body text")
    attachments: list[TestEmailAttachment] = Field(default_factory=list)
    references_header: str | None = None
    in_reply_to_header: str | None = None


class TestEmailResponse(BaseModel):
    pipeline_stages: list[dict]
    inbox_message_id: str | None = None
    classification: str | None = None
    classification_confidence: float | None = None
    classification_method: str | None = None
    routed_stages: list[str] = Field(default_factory=list)
    customer_id: str | None = None
    order_id: str | None = None
    order_number: str | None = None
    attachment_count: int = 0
    total_time_ms: int = 0
    errors: list[str] = Field(default_factory=list)


class DLQEntryResponse(BaseModel):
    id: str
    original_task: str
    stage: str
    error_message: str | None
    retry_count: int
    resolved: bool
    resolved_at: str | None
    created_at: str

    class Config:
        from_attributes = True


class DLQListResponse(BaseModel):
    items: list[DLQEntryResponse]
    total: int
    unresolved: int


class ProcessingTaskResponse(BaseModel):
    id: str
    inbox_message_id: str | None
    celery_task_id: str | None
    stage: str
    status: str
    tokens_used: int | None
    processing_time_ms: int | None
    retry_count: int
    error_message: str | None
    created_at: str

    class Config:
        from_attributes = True


class PipelineStatsResponse(BaseModel):
    total_tasks: int
    by_stage: dict[str, int]
    by_status: dict[str, int]
    total_tokens_used: int
    avg_processing_time_ms: float
    error_rate: float
    dlq_unresolved: int


class DLQResolveRequest(BaseModel):
    resolved_by: str | None = None


# ─── DLQ Endpoints ────────────────────────────────────────────

@router.get("/dlq", response_model=DLQListResponse)
async def list_dlq_entries(
    resolved: bool | None = Query(None),
    stage: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List dead letter queue entries."""
    async with AsyncSessionLocal() as session:
        query = select(DeadLetterEntry).order_by(DeadLetterEntry.created_at.desc())
        count_query = select(func.count(DeadLetterEntry.id))
        unresolved_query = select(func.count(DeadLetterEntry.id)).where(
            DeadLetterEntry.resolved == False  # noqa: E712
        )

        if resolved is not None:
            query = query.where(DeadLetterEntry.resolved == resolved)
            count_query = count_query.where(DeadLetterEntry.resolved == resolved)
        if stage:
            query = query.where(DeadLetterEntry.stage == stage)
            count_query = count_query.where(DeadLetterEntry.stage == stage)

        query = query.limit(limit).offset(offset)

        result = await session.execute(query)
        entries = result.scalars().all()

        total = (await session.execute(count_query)).scalar() or 0
        unresolved = (await session.execute(unresolved_query)).scalar() or 0

        return DLQListResponse(
            items=[
                DLQEntryResponse(
                    id=str(e.id),
                    original_task=e.original_task,
                    stage=e.stage,
                    error_message=e.error_message,
                    retry_count=e.retry_count,
                    resolved=e.resolved,
                    resolved_at=e.resolved_at.isoformat() if e.resolved_at else None,
                    created_at=e.created_at.isoformat(),
                )
                for e in entries
            ],
            total=total,
            unresolved=unresolved,
        )


@router.get("/dlq/{entry_id}")
async def get_dlq_entry(entry_id: UUID):
    """Get DLQ entry detail including payload and traceback."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DeadLetterEntry).where(DeadLetterEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise HTTPException(status_code=404, detail="DLQ entry not found")

        return {
            "id": str(entry.id),
            "original_task": entry.original_task,
            "stage": entry.stage,
            "payload": entry.payload,
            "error_message": entry.error_message,
            "error_traceback": entry.error_traceback,
            "retry_count": entry.retry_count,
            "resolved": entry.resolved,
            "resolved_at": entry.resolved_at.isoformat() if entry.resolved_at else None,
            "resolved_by": str(entry.resolved_by) if entry.resolved_by else None,
            "created_at": entry.created_at.isoformat(),
        }


@router.post("/dlq/{entry_id}/resolve")
async def resolve_dlq_entry(entry_id: UUID, body: DLQResolveRequest):
    """Mark a DLQ entry as resolved."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DeadLetterEntry).where(DeadLetterEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise HTTPException(status_code=404, detail="DLQ entry not found")

        entry.resolved = True
        entry.resolved_at = datetime.now(UTC)
        if body.resolved_by:
            try:
                entry.resolved_by = UUID(body.resolved_by)
            except ValueError:
                pass

        await session.commit()
        return {"status": "resolved", "id": str(entry_id)}


@router.post("/dlq/{entry_id}/retry")
async def retry_dlq_entry(entry_id: UUID):
    """Retry a failed DLQ entry by re-dispatching the task."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DeadLetterEntry).where(DeadLetterEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise HTTPException(status_code=404, detail="DLQ entry not found")

        if entry.resolved:
            raise HTTPException(status_code=400, detail="Entry already resolved")

        # Re-dispatch based on original task
        from app.orchestration import tasks as orch_tasks

        task_map = {
            "orchestration.ingest_email": orch_tasks.ingest_email,
            "orchestration.classify_email": orch_tasks.classify_email,
            "orchestration.parse_email": orch_tasks.parse_email,
            "orchestration.process_attachment": orch_tasks.process_attachment,
            "orchestration.analyze_drawing": orch_tasks.analyze_drawing,
            "orchestration.orchestrate_order": orch_tasks.orchestrate_order,
            "orchestration.auto_calculate": orch_tasks.auto_calculate,
            "orchestration.generate_offer": orch_tasks.generate_offer,
        }

        task_func = task_map.get(entry.original_task)
        if not task_func:
            raise HTTPException(status_code=400, detail=f"Unknown task: {entry.original_task}")

        # Re-dispatch with task-specific argument unpacking
        if entry.payload:
            if entry.original_task == "orchestration.process_attachment":
                p = entry.payload
                task_func.delay(
                    p.get("attachment_id", ""),
                    p.get("file_path", ""),
                    p.get("content_type", ""),
                    p.get("filename", ""),
                )
            elif entry.original_task == "orchestration.analyze_drawing":
                p = entry.payload
                task_func.delay(
                    p.get("document_id", ""),
                    p.get("ocr_text", ""),
                    p.get("ocr_confidence", 0.0),
                )
            elif isinstance(entry.payload, dict):
                task_func.delay(entry.payload)
            elif isinstance(entry.payload, list):
                task_func.delay(*entry.payload)

        entry.retry_count += 1
        await session.commit()

        return {"status": "retried", "id": str(entry_id), "retry_count": entry.retry_count}


# ─── Processing Tasks Endpoints ───────────────────────────────

@router.get("/tasks", response_model=list[ProcessingTaskResponse])
async def list_processing_tasks(
    stage: str | None = Query(None),
    status: str | None = Query(None),
    inbox_message_id: UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List processing tasks (audit trail)."""
    async with AsyncSessionLocal() as session:
        query = select(ProcessingTask).order_by(ProcessingTask.created_at.desc())

        if stage:
            query = query.where(ProcessingTask.stage == ProcessingStage(stage))
        if status:
            query = query.where(ProcessingTask.status == ProcessingStatus(status))
        if inbox_message_id:
            query = query.where(ProcessingTask.inbox_message_id == inbox_message_id)

        query = query.limit(limit).offset(offset)

        result = await session.execute(query)
        tasks = result.scalars().all()

        return [
            ProcessingTaskResponse(
                id=str(t.id),
                inbox_message_id=str(t.inbox_message_id) if t.inbox_message_id else None,
                celery_task_id=t.celery_task_id,
                stage=t.stage.value,
                status=t.status.value,
                tokens_used=t.tokens_used,
                processing_time_ms=t.processing_time_ms,
                retry_count=t.retry_count,
                error_message=t.error_message,
                created_at=t.created_at.isoformat(),
            )
            for t in tasks
        ]


# ─── Pipeline Stats ──────────────────────────────────────────

@router.get("/stats", response_model=PipelineStatsResponse)
async def get_pipeline_stats():
    """Get pipeline processing statistics."""
    async with AsyncSessionLocal() as session:
        # Total tasks
        total = (await session.execute(
            select(func.count(ProcessingTask.id))
        )).scalar() or 0

        # By stage
        stage_result = await session.execute(
            select(ProcessingTask.stage, func.count(ProcessingTask.id))
            .group_by(ProcessingTask.stage)
        )
        by_stage = {row[0].value: row[1] for row in stage_result}

        # By status
        status_result = await session.execute(
            select(ProcessingTask.status, func.count(ProcessingTask.id))
            .group_by(ProcessingTask.status)
        )
        by_status = {row[0].value: row[1] for row in status_result}

        # Tokens
        tokens = (await session.execute(
            select(func.coalesce(func.sum(ProcessingTask.tokens_used), 0))
        )).scalar() or 0

        # Average processing time
        avg_time = (await session.execute(
            select(func.coalesce(func.avg(ProcessingTask.processing_time_ms), 0))
        )).scalar() or 0

        # Error rate
        failed = by_status.get("failed", 0) + by_status.get("dlq", 0)
        error_rate = failed / total if total > 0 else 0.0

        # DLQ unresolved
        dlq_unresolved = (await session.execute(
            select(func.count(DeadLetterEntry.id)).where(
                DeadLetterEntry.resolved == False  # noqa: E712
            )
        )).scalar() or 0

        return PipelineStatsResponse(
            total_tasks=total,
            by_stage=by_stage,
            by_status=by_status,
            total_tokens_used=tokens,
            avg_processing_time_ms=float(avg_time),
            error_rate=error_rate,
            dlq_unresolved=dlq_unresolved,
        )


# ─── Test Email Endpoint ─────────────────────────────────────


@router.post("/test-email", response_model=TestEmailResponse)
async def test_email_pipeline(body: TestEmailRequest):
    """Simulate email arrival and run the full orchestration pipeline.

    Runs all stages synchronously (no Celery) so the result is immediate.
    Useful for testing the pipeline without IMAP configuration.
    """
    from uuid import uuid4

    start = time.time()
    stages: list[dict] = []
    errors: list[str] = []
    result = TestEmailResponse(pipeline_stages=[], attachment_count=len(body.attachments))

    # ── Stage 1: Ingestion ──────────────────────────────────
    try:
        t0 = time.time()
        from app.orchestration.agents.email_ingestion import EmailIngestionAgent

        agent = EmailIngestionAgent()
        raw_email_data = {
            "message_id": f"<test-{uuid4()}@infer-forge-test>",
            "from_email": body.from_email,
            "subject": body.subject,
            "body_text": body.body_text,
            "received_at": datetime.now(UTC).isoformat(),
            "attachments": [
                {
                    "filename": att.filename,
                    "content_type": att.content_type,
                    "data_b64": att.data_base64,
                }
                for att in body.attachments
            ],
            "references_header": body.references_header,
            "in_reply_to_header": body.in_reply_to_header,
        }

        ingest_result = await agent.process_from_dict(raw_email_data)
        elapsed = int((time.time() - t0) * 1000)
        stages.append({
            "stage": "ingest",
            "status": "success",
            "time_ms": elapsed,
            "inbox_message_id": ingest_result["inbox_message_id"],
            "attachments": len(ingest_result.get("attachment_ids", [])),
            "thread_id": ingest_result.get("thread_id"),
        })
        result.inbox_message_id = ingest_result["inbox_message_id"]

    except Exception as e:
        errors.append(f"Ingestion failed: {e}")
        stages.append({"stage": "ingest", "status": "failed", "error": str(e)})
        result.pipeline_stages = stages
        result.errors = errors
        result.total_time_ms = int((time.time() - start) * 1000)
        return result

    # ── Stage 2: Classification ─────────────────────────────
    try:
        t0 = time.time()
        from app.orchestration.agents.heuristic_classifier import HeuristicClassifier

        hc = HeuristicClassifier()
        hc_result = hc.classify(
            subject=body.subject,
            body=body.body_text,
            has_attachments=len(body.attachments) > 0,
            body_length=len(body.body_text),
        )

        if hc_result:
            classification = hc_result.category
            confidence = hc_result.confidence
            method = "heuristic"
        else:
            # Fallback: try AI classifier if available
            try:
                from app.core.config import get_settings

                settings = get_settings()
                if settings.ANTHROPIC_API_KEY:
                    from app.agents.email_classifier import EmailClassifier

                    classifier = EmailClassifier(api_key=settings.ANTHROPIC_API_KEY)
                    ai_result = await classifier.classify(
                        subject=body.subject,
                        body=body.body_text,
                    )
                    classification = ai_result.category
                    confidence = ai_result.confidence
                    method = "ai_claude"
                else:
                    classification = "dotaz"
                    confidence = 0.5
                    method = "default_fallback"
            except Exception:
                classification = "dotaz"
                confidence = 0.5
                method = "default_fallback"

        elapsed = int((time.time() - t0) * 1000)
        stages.append({
            "stage": "classify",
            "status": "success",
            "time_ms": elapsed,
            "category": classification,
            "confidence": confidence,
            "method": method,
        })
        result.classification = classification
        result.classification_confidence = confidence
        result.classification_method = method

    except Exception as e:
        errors.append(f"Classification failed: {e}")
        stages.append({"stage": "classify", "status": "failed", "error": str(e)})
        result.pipeline_stages = stages
        result.errors = errors
        result.total_time_ms = int((time.time() - start) * 1000)
        return result

    # ── Stage 3: Routing ────────────────────────────────────
    try:
        from app.orchestration.router import route_classification

        routed_stages = route_classification(
            classification=classification,
            confidence=confidence,
            has_attachments=len(body.attachments) > 0,
        )
        stages.append({
            "stage": "route",
            "status": "success",
            "routed_to": routed_stages,
        })
        result.routed_stages = routed_stages

    except Exception as e:
        errors.append(f"Routing failed: {e}")
        stages.append({"stage": "route", "status": "failed", "error": str(e)})
        routed_stages = []

    # ── Stage 4: Attachment Processing ──────────────────────
    if "process_attachments" in routed_stages and ingest_result.get("attachment_ids"):
        try:
            t0 = time.time()
            from app.models.email_attachment import EmailAttachment
            from app.orchestration.agents.attachment_processor import AttachmentProcessor

            ap = AttachmentProcessor()
            att_results = []
            for att_id_str in ingest_result["attachment_ids"]:
                async with AsyncSessionLocal() as session:
                    att_row = (await session.execute(
                        select(EmailAttachment).where(
                            EmailAttachment.id == UUID(att_id_str)
                        )
                    )).scalar_one()

                try:
                    att_result = await ap.process(
                        attachment_id=UUID(att_id_str),
                        file_path=att_row.file_path,
                        content_type=att_row.content_type,
                        filename=att_row.filename,
                    )
                    att_results.append(att_result)
                except Exception as att_err:
                    att_results.append({"error": str(att_err), "filename": att_row.filename})

            elapsed = int((time.time() - t0) * 1000)
            stages.append({
                "stage": "process_attachments",
                "status": "success",
                "time_ms": elapsed,
                "results": att_results,
            })
        except Exception as e:
            errors.append(f"Attachment processing failed: {e}")
            stages.append({"stage": "process_attachments", "status": "failed", "error": str(e)})

    # ── Stage 5: Order Orchestration ────────────────────────
    if "orchestrate_order" in routed_stages:
        try:
            t0 = time.time()
            from app.orchestration.agents.order_orchestrator import OrderOrchestrator

            oo = OrderOrchestrator()
            orch_result = await oo.process(
                inbox_message_id=UUID(ingest_result["inbox_message_id"]),
                parsed_data={
                    "classification": classification,
                    "company_name": None,
                    "contact_email": body.from_email,
                    "ico": None,
                },
            )
            elapsed = int((time.time() - t0) * 1000)
            stages.append({
                "stage": "orchestrate_order",
                "status": "success",
                "time_ms": elapsed,
                "customer_id": orch_result.get("customer_id"),
                "order_id": orch_result.get("order_id"),
                "order_number": orch_result.get("order_number"),
                "customer_created": orch_result.get("customer_created"),
                "order_created": orch_result.get("order_created"),
                "next_stage": orch_result.get("next_stage"),
            })
            result.customer_id = orch_result.get("customer_id")
            result.order_id = orch_result.get("order_id")
            result.order_number = orch_result.get("order_number")

        except Exception as e:
            errors.append(f"Order orchestration failed: {e}")
            stages.append({"stage": "orchestrate_order", "status": "failed", "error": str(e)})

    # ── Stage 6: Archive ────────────────────────────────────
    if "archive" in routed_stages:
        try:
            from app.models.inbox import InboxMessage, InboxStatus

            async with AsyncSessionLocal() as session:
                msg = (await session.execute(
                    select(InboxMessage).where(
                        InboxMessage.id == UUID(ingest_result["inbox_message_id"])
                    )
                )).scalar_one()
                msg.status = InboxStatus.ARCHIVED
                await session.commit()

            stages.append({"stage": "archive", "status": "success"})
        except Exception as e:
            errors.append(f"Archive failed: {e}")
            stages.append({"stage": "archive", "status": "failed", "error": str(e)})

    # ── Stage 7: Escalate ───────────────────────────────────
    if "escalate" in routed_stages:
        try:
            from app.models.inbox import InboxMessage, InboxStatus

            async with AsyncSessionLocal() as session:
                msg = (await session.execute(
                    select(InboxMessage).where(
                        InboxMessage.id == UUID(ingest_result["inbox_message_id"])
                    )
                )).scalar_one()
                msg.status = InboxStatus.ESCALATED
                msg.needs_review = True
                await session.commit()

            stages.append({"stage": "escalate", "status": "success"})
        except Exception as e:
            errors.append(f"Escalate failed: {e}")
            stages.append({"stage": "escalate", "status": "failed", "error": str(e)})

    result.pipeline_stages = stages
    result.errors = errors
    result.total_time_ms = int((time.time() - start) * 1000)
    return result


@router.post("/batch-upload")
async def batch_upload_eml(
    files: list[UploadFile] = File(...),
):
    """Upload multiple EML files and dispatch them to the orchestration pipeline.

    Each EML file is parsed and dispatched as a run_pipeline task.
    """
    import email as email_module
    from uuid import uuid4

    results = []

    for upload_file in files:
        try:
            content = await upload_file.read()
            msg = email_module.message_from_bytes(content)

            # Extract basic headers
            message_id = msg.get("Message-ID", f"<batch-{uuid4()}@infer-forge>")
            from_email = msg.get("From", "unknown@unknown.com")
            subject = msg.get("Subject", "(bez předmětu)")

            # Extract body
            body_text = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition", "")):
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or "utf-8"
                            body_text = payload.decode(charset, errors="replace")
                            break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or "utf-8"
                    body_text = payload.decode(charset, errors="replace")

            raw_email_data = {
                "message_id": message_id,
                "from_email": from_email,
                "subject": subject,
                "body_text": body_text,
                "received_at": datetime.now(UTC).isoformat(),
                "attachments": [],
                "references_header": msg.get("References"),
                "in_reply_to_header": msg.get("In-Reply-To"),
            }

            from app.orchestration.tasks import run_pipeline
            task = run_pipeline.delay(raw_email_data)

            results.append({
                "filename": upload_file.filename,
                "status": "dispatched",
                "task_id": task.id,
                "message_id": message_id,
                "subject": subject,
            })
        except Exception as e:
            results.append({
                "filename": upload_file.filename,
                "status": "failed",
                "error": str(e),
            })

    return {
        "total": len(files),
        "dispatched": sum(1 for r in results if r["status"] == "dispatched"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "results": results,
    }
