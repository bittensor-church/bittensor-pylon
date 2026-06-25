from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import structlog
from litestar.logging import LoggingConfig

from pylon_service.middleware.request_id import current_request_id
from pylon_service.settings import otel_settings, settings
from pylon_service.tracing import get_current_valid_span_context

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
    return {**event_dict, **_OTEL_RESOURCE_ATTRS}


def add_request_id_to_structlog(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Structlog processor injecting the current request id into the log event."""
    event_dict["pylon_request_id"] = current_request_id() or "-"
    return event_dict


def add_otel_context_to_structlog(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Structlog processor injecting the active span's trace_id and span_id into the log event."""
    ctx = get_current_valid_span_context()
    if ctx is not None:
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
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

# Shared enrichment applied to every log line, for both native structlog loggers and foreign
# (litestar/uvicorn) records. OTEL resource attributes stay out of here: they are injected only into
# the json (production) render processors to keep the dev console clean.
_SHARED_PROCESSORS = (
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    _CALLSITE_PARAMETER_ADDER,
    add_request_id_to_structlog,
    add_coro_name_to_structlog,
)

# Pre-chain for foreign records (litestar/uvicorn). ExtraAdder surfaces their `extra={...}` payloads.
_FOREIGN_PRE_CHAIN = (
    structlog.stdlib.ExtraAdder(),
    *_SHARED_PROCESSORS,
)

# Processor chain for native structlog loggers. wrap_for_formatter MUST be last: it packs the event
# dict into the stdlib LogRecord so ProcessorFormatter can render it through the formatter processors.
_STRUCTLOG_PROCESSORS = (
    *_SHARED_PROCESSORS,
    structlog.stdlib.PositionalArgumentsFormatter(),
    structlog.processors.StackInfoRenderer(),
    structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
)

# Render processors run inside ProcessorFormatter for every record (native and foreign).
_JSON_RENDER_PROCESSORS = [
    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
    add_otel_resource_to_structlog,
    add_otel_context_to_structlog,
    structlog.processors.format_exc_info,
    structlog.processors.JSONRenderer(),
]

# ConsoleRenderer renders exc_info itself, so format_exc_info must not appear here.
_CONSOLE_RENDER_PROCESSORS = [
    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
    structlog.dev.ConsoleRenderer(),
]


def _console_formatter() -> dict:
    return {
        "()": structlog.stdlib.ProcessorFormatter,
        "processors": _CONSOLE_RENDER_PROCESSORS,
        "foreign_pre_chain": list(_FOREIGN_PRE_CHAIN),
    }


def _json_formatter() -> dict:
    return {
        "()": structlog.stdlib.ProcessorFormatter,
        "processors": _JSON_RENDER_PROCESSORS,
        "foreign_pre_chain": list(_FOREIGN_PRE_CHAIN),
    }


def configure_structlog() -> None:
    structlog.configure(
        processors=list(_STRUCTLOG_PROCESSORS),
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


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
            "console": _console_formatter(),
            "json": _json_formatter(),
        },
        log_exceptions="always",
        disable_stack_trace=set(range(400, 500)),
    )
