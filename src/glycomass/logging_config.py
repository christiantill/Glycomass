from __future__ import annotations

import logging
import sys
from typing import cast

import structlog


def configure_logging(*, json_output: bool, level: str = "INFO") -> None:
    """Configure structlog + stdlib logging once at startup."""
    logging.basicConfig(format="%(message)s", level=getattr(logging, level.upper(), logging.INFO))
    renderer = structlog.processors.JSONRenderer() if json_output else structlog.dev.ConsoleRenderer()
    structlog.configure(
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "glycomass") -> structlog.BoundLogger:
    return cast(structlog.BoundLogger, structlog.get_logger(name))
