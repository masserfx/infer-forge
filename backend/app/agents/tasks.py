"""Celery tasks for AI agents (classification, parsing, calculation).

Background tasks for running AI agents asynchronously via Celery workers.
"""

from __future__ import annotations

import structlog

from app.agents.calculation_agent import CalculationAgent
from app.agents.email_classifier import EmailClassifier
from app.core.celery_app import celery_app
from app.core.config import get_settings

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, max_retries=2)
def run_email_classification(
    self,  # type: ignore[no-untyped-def]
    email_id: str,
    subject: str,
    body: str,
) -> dict[str, object]:
    """Run email classification as background task.

    Args:
        email_id: Database ID of the email being classified.
        subject: Email subject line.
        body: Email body (plain text).

    Returns:
        dict: Classification result with keys:
            - category (str | None): Classified category.
            - confidence (float): Confidence score 0.0-1.0.
            - reasoning (str): Reasoning in Czech.
            - needs_escalation (bool): True if manual review needed.
    """
    log = logger.bind(task_id=self.request.id, email_id=email_id)
    log.info("task.email_classification.started")

    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY:
        log.error("task.email_classification.missing_api_key")
        return {
            "category": None,
            "confidence": 0.0,
            "reasoning": "Chybí Anthropic API klíč v konfiguraci.",
            "needs_escalation": True,
        }

    try:
        classifier = EmailClassifier(api_key=settings.ANTHROPIC_API_KEY)

        # Run classification synchronously within the Celery worker
        # (Celery workers handle their own event loop)
        import asyncio

        result = asyncio.run(classifier.classify(subject=subject, body=body))

        log.info(
            "task.email_classification.completed",
            category=result.category,
            confidence=result.confidence,
            needs_escalation=result.needs_escalation,
        )

        return {
            "category": result.category,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "needs_escalation": result.needs_escalation,
        }

    except Exception as exc:
        log.exception("task.email_classification.failed")
        # Retry on failure (max 2 retries)
        raise self.retry(countdown=60) from exc


@celery_app.task(bind=True, max_retries=2)
def run_calculation_estimate(
    self,  # type: ignore[no-untyped-def]
    order_id: str,
    description: str,
    items: list[dict[str, object]],
) -> dict[str, object]:
    """Run AI calculation estimate as background task.

    Args:
        order_id: Database ID of the order/quote being estimated.
        description: Order description / context.
        items: List of items, each dict with keys:
            - name (str): Item name
            - material (str): Material specification
            - dimension (str): Dimensions
            - quantity (int | float): Quantity
            - unit (str): Unit (ks, m, kg, etc.)

    Returns:
        dict: Calculation result with keys:
            - material_cost_czk (float): Total material cost.
            - labor_hours (float): Total labor hours.
            - labor_cost_czk (float): Total labor cost.
            - overhead_czk (float): Overhead costs.
            - margin_percent (float): Recommended margin.
            - total_czk (float): Total estimated price.
            - breakdown (list[dict]): Per-item breakdown.
            - reasoning (str): Overall reasoning in Czech.
    """
    log = logger.bind(task_id=self.request.id, order_id=order_id, item_count=len(items))
    log.info("task.calculation_estimate.started")

    settings = get_settings()
    if not settings.ANTHROPIC_API_KEY:
        log.error("task.calculation_estimate.missing_api_key")
        return {
            "material_cost_czk": 0.0,
            "labor_hours": 0.0,
            "labor_cost_czk": 0.0,
            "overhead_czk": 0.0,
            "margin_percent": 0.0,
            "total_czk": 0.0,
            "breakdown": [],
            "reasoning": "Chybí Anthropic API klíč v konfiguraci.",
        }

    try:
        agent = CalculationAgent(api_key=settings.ANTHROPIC_API_KEY)

        # Run estimate synchronously within the Celery worker
        import asyncio

        result = asyncio.run(agent.estimate(description=description, items=items))

        log.info(
            "task.calculation_estimate.completed",
            total_czk=result.total_czk,
            labor_hours=result.labor_hours,
            margin_percent=result.margin_percent,
        )

        # Convert breakdown to dict list for JSON serialization
        breakdown_dicts = [
            {
                "name": item.name,
                "material_cost_czk": item.material_cost_czk,
                "labor_hours": item.labor_hours,
                "notes": item.notes,
            }
            for item in result.breakdown
        ]

        # Emit WebSocket notification
        try:
            import asyncio as _asyncio

            from app.core.websocket import manager

            _asyncio.run(
                manager.broadcast(
                    {
                        "type": "CALCULATION_COMPLETE",
                        "title": "Kalkulace dokončena",
                        "message": f"Celková cena: {result.total_czk:,.0f} Kč",
                        "link": "/kalkulace",
                    }
                )
            )
        except Exception:
            log.warning("task.calculation_estimate.notification_failed")

        return {
            "material_cost_czk": result.material_cost_czk,
            "labor_hours": result.labor_hours,
            "labor_cost_czk": result.labor_cost_czk,
            "overhead_czk": result.overhead_czk,
            "margin_percent": result.margin_percent,
            "total_czk": result.total_czk,
            "breakdown": breakdown_dicts,
            "reasoning": result.reasoning,
        }

    except Exception as exc:
        log.exception("task.calculation_estimate.failed")
        # Retry on failure (max 2 retries)
        raise self.retry(countdown=60) from exc
