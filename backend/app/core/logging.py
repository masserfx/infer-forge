"""Structured logging configuration using structlog.

Provides JSON-formatted logs for production and human-readable logs for development.
All logs include request context, user info, and timestamps.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from app.core.config import get_settings

settings = get_settings()


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to all log entries.

    Args:
        logger: Logger instance.
        method_name: Method name being logged.
        event_dict: Event dictionary to modify.

    Returns:
        EventDict: Modified event dictionary with app context.
    """
    event_dict["app"] = settings.APP_NAME
    return event_dict


def configure_logging() -> None:
    """Configure structured logging for the application.

    Sets up:
    - JSON formatting for production
    - Console formatting for development
    - Log levels and processors
    - Integration with standard library logging
    """
    # Determine log level
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Shared processors for all environments
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_app_context,
    ]

    if settings.DEBUG:
        # Development: pretty console output
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # Production: JSON output for log aggregation
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,  # type: ignore[arg-type]
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a configured structlog logger instance.

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        structlog.stdlib.BoundLogger: Configured logger instance.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("user_logged_in", user_id=123, email="user@example.com")
    """
    return structlog.get_logger(name)


# Configure logging on module import
configure_logging()
