"""Pipeline router — maps email classification to processing stages."""

from __future__ import annotations

import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


def route_classification(
    classification: str,
    confidence: float,
    has_attachments: bool,
    needs_review: bool = False,
) -> list[str]:
    """Determine processing stages based on email classification.

    Args:
        classification: Email classification category
        confidence: Classification confidence (0-1)
        has_attachments: Whether email has attachments
        needs_review: Whether email needs human review

    Returns:
        List of stage names to execute in order
    """
    settings = get_settings()
    review_threshold = settings.ORCHESTRATION_REVIEW_THRESHOLD

    stages: list[str] = []

    if needs_review or confidence < review_threshold:
        return ["review"]

    # Always process attachments if present
    if has_attachments:
        stages.append("process_attachments")

    # Route based on classification
    if classification in ("poptavka", "objednavka", "faktura"):
        stages.append("parse_email")
        stages.append("orchestrate_order")
        if classification == "poptavka":
            stages.append("auto_calculate")
            stages.append("generate_offer")
    elif classification == "informace_zakazka":
        stages.append("parse_email")
        stages.append("orchestrate_order")
    elif classification == "reklamace":
        stages.append("parse_email")
        stages.append("escalate")
    elif classification == "obchodni_sdeleni":
        stages.append("archive")
    elif classification == "dotaz":
        stages.append("orchestrate_order")
        stages.append("notify")
    elif classification == "priloha":
        # Attachments already added above
        if not has_attachments:
            stages.append("review")

    logger.info(
        "pipeline.routed",
        classification=classification,
        confidence=confidence,
        has_attachments=has_attachments,
        stages=stages,
    )

    return stages
