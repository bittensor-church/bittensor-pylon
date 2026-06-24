from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import structlog
from litestar.logging import LoggingConfig

from pylon_service.middleware.request_id import current_request_id
from pylon_service.settings import otel_settings, settings

if TYPE_CHECKING:
    from structlog.typing import EventDict, WrappedLogger


def _get_current_coroutine_name() -> str:
    try:
        task = asyncio.current_task()
    except RuntimeError:
        return "no-event-loop"

    try:
        return "main" if task is None else task.get_name()
    except Exception:
        return "unknown-task"


# Resource attributes are static for the process lifetime, so they are computed once at import.
_OTEL_RESOURCE_ATTRS = otel_settings.resource_attributes()


def add_otel_resource_to_structlog(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Structlog processor injecting OTEL resource attributes into every log line."""
    return {**_OTEL_RESOURCE_ATTRS, **event_dict}


def add_request_id_to_structlog(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Structlog processor injecting the current request id into the log event."""
    event_dict["pylon_request_id"] = current_request_id() or "-"
    return event_dict


def add_coro_name_to_structlog(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Structlog processor injecting the current coroutine name into the log event."""
    event_dict["coro_name"] = _get_current_coroutine_name()
    return event_dict


_CALLSITE_PARAMETER_ADDER = structlog.processors.CallsiteParameterAdder(
    {
        structlog.processors.CallsiteParameter.FILENAME,
        structlog.processors.CallsiteParameter.FUNC_NAME,
        structlog.processors.CallsiteParameter.LINENO,
    }
)

# Base processors applied to every log line. coro_name and OTEL attributes are layered on top per formatter:
# OTEL resource attributes are only injected into the json (production) output to keep dev console clean.
_BASE_FOREIGN_PRE_CHAIN = (
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    _CALLSITE_PARAMETER_ADDER,
    add_request_id_to_structlog,
)

_CONSOLE_FOREIGN_PRE_CHAIN = (*_BASE_FOREIGN_PRE_CHAIN, add_coro_name_to_structlog)
_JSON_FOREIGN_PRE_CHAIN = (*_BASE_FOREIGN_PRE_CHAIN, add_coro_name_to_structlog, add_otel_resource_to_structlog)

_JSON_RENDER_PROCESSORS = [
    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
    structlog.processors.format_exc_info,
    structlog.processors.JSONRenderer(),
]


def _console_formatter(foreign_pre_chain) -> dict:
    return {
        "()": structlog.stdlib.ProcessorFormatter,
        "processor": structlog.dev.ConsoleRenderer(),
        "foreign_pre_chain": list(foreign_pre_chain),
    }


def _json_formatter(foreign_pre_chain) -> dict:
    return {
        "()": structlog.stdlib.ProcessorFormatter,
        "processors": _JSON_RENDER_PROCESSORS,
        "foreign_pre_chain": list(foreign_pre_chain),
    }


def litestar_logging_config() -> LoggingConfig:
    return LoggingConfig(
        root={"level": "INFO", "handlers": ["console"]},
        loggers={
            "pylon_service": {"level": "DEBUG", "handlers": ["console"], "propagate": False},
            "litestar": {"level": "INFO", "handlers": ["console"], "propagate": False},
            "uvicorn": {"level": "INFO", "handlers": ["console"], "propagate": False},
            "uvicorn.error": {"level": "INFO", "handlers": ["console"], "propagate": False},
            "uvicorn.access": {"level": "INFO", "handlers": ["console"], "propagate": False},
        },
        handlers={
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console" if settings.debug else "json",
            },
        },
        formatters={
            "console": _console_formatter(_CONSOLE_FOREIGN_PRE_CHAIN),
            "json": _json_formatter(_JSON_FOREIGN_PRE_CHAIN),
        },
        log_exceptions="always",
        disable_stack_trace=set(range(400, 500)),
    )
