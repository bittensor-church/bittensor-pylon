from __future__ import annotations

import asyncio
import logging

from litestar.logging import LoggingConfig

from pylon_service.request_id import current_request_id


def _get_current_coroutine_name() -> str:
    try:
        task = asyncio.current_task()
    except RuntimeError:
        return "no-event-loop"

    try:
        return "main" if task is None else task.get_name()
    except Exception as e:
        logging.getLogger("pylon_service.raw_logger").error(
            "Exception when getting coroutine name: %s", e, exc_info=True
        )
        return "unknown-task"


class PylonLogFilter(logging.Filter):
    """Injects request-local fields into records so formatters can reference them safely."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "coro_name"):
            record.coro_name = _get_current_coroutine_name()
        if not hasattr(record, "pylon_request_id"):
            record.pylon_request_id = current_request_id() or "-"
        return True


def litestar_logging_config():
    return LoggingConfig(
        root={"level": "INFO", "handlers": ["console"]},
        loggers={
            "pylon_service": {"level": "DEBUG", "handlers": ["console"], "propagate": False},
            "litestar": {"level": "INFO", "handlers": ["console"], "propagate": False},
            "pylon_service.raw_logger": {
                "level": "DEBUG",
                "handlers": ["raw_console"],
                "propagate": False,
            },
            "uvicorn": {"level": "INFO", "handlers": ["console"], "propagate": False},
            "uvicorn.error": {"level": "INFO", "handlers": ["console"], "propagate": False},
            "uvicorn.access": {"level": "INFO", "handlers": ["console"], "propagate": False},
        },
        handlers={
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "filters": ["pylon_filter"],
            },
            "raw_console": {
                "class": "logging.StreamHandler",
                "formatter": "raw",
            },
        },
        formatters={
            "standard": {
                "format": "%(asctime)s - [req=%(pylon_request_id)s] - %(levelname)s - [%(coro_name)s] - %(name)s - %(message)s - %(filename)s:%(lineno)d",
            },
            "raw": {
                "format": "%(asctime)s - %(levelname)s - %(name)s - %(message)s - %(filename)s:%(lineno)d",
            },
        },
        filters={
            "pylon_filter": {"()": PylonLogFilter},
        },
        log_exceptions="always",
    )
