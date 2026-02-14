"""Structured logging configuration using structlog."""

from __future__ import annotations

import logging
import sys

import structlog


def setup_logging(level: str = "INFO") -> None:
    """Configure structlog with JSON output for production, pretty for dev."""

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    is_debug = level.upper() == "DEBUG"

    if is_debug:
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    # Silence noisy third-party loggers
    for name in ("httpx", "httpcore", "openai", "uvicorn.access"):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a bound logger for a module."""
    return structlog.get_logger(name)
