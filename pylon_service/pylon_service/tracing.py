import contextvars
from enum import StrEnum, nonmember

from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.trace import SpanContext


class TraceLinkType(StrEnum):
    """
    Kind of span link attached to a retry attempt span, and the attribute key it is stored under.
    """

    ATTRIBUTE_KEY = nonmember("link.type")

    ORIGINATING_REQUEST = "originating_request"
    PREVIOUS_ATTEMPT = "previous_attempt"


def get_current_valid_span_context() -> SpanContext | None:
    """
    Return the active span's context, or None when there is no valid active span.

    The context is invalid when tracing is disabled or when running outside any span.
    """
    ctx = trace.get_current_span().get_span_context()
    return ctx if ctx.is_valid else None


def detached_otel_context() -> contextvars.Context:
    """
    Return a copy of the current contextvars with the active OTEL span cleared.

    Lets a background task keep request-scoped contextvars (e.g. request id) while not
    inheriting the live request span, so its spans and logs do not attach to a request
    trace that has already ended.
    """
    ctx = contextvars.copy_context()
    ctx.run(lambda: otel_context.attach(otel_context.Context()))
    return ctx
