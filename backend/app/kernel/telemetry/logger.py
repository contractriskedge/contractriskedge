"""structlog + standard library logging configuration."""

from __future__ import annotations

import logging
import sys

import structlog


def setup_logging(environment: str = "development", log_level: str = "INFO") -> None:
    """Configure structlog and standard library logging.

    In development, logs are human-readable with colors.
    In production, logs are JSON-formatted for log aggregation.

    Standard library ``logging`` is configured with a StreamHandler so that
    all ``logger.info / warning / error`` calls throughout the app actually
    produce visible output (e.g. from middleware, services, and workers).
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # ── Standard library logging ───────────────────────────────────
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove any pre-existing handlers to avoid duplicates on reload
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    if environment == "development":
        fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
    else:
        fmt = logging.Formatter(
            '{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
            datefmt="%Y-%m-%dT%H:%M:%S",
        )

    handler.setFormatter(fmt)
    root_logger.addHandler(handler)

    # ── structlog ──────────────────────────────────────────────────
    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if environment == "development":
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(),
        ]
    else:
        processors = shared_processors + [
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
