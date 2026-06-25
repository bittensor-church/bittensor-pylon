from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from pylon_service.db.database import engine as db_engine
from pylon_service.settings import otel_settings


def init_otel() -> None:
    """
    Initialize OpenTelemetry tracing if a traces endpoint is configured.

    Sets up a TracerProvider exporting via OTLP HTTP/protobuf and auto-instruments the httpx,
    aiohttp, and SQLAlchemy libraries. A no-op when no endpoint is set.
    """
    if not otel_settings.traces_enabled:
        return

    resource = Resource.create(otel_settings.resource_attributes())
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{otel_settings.normalized_collector_endpoint}/v1/traces"))
    )
    trace.set_tracer_provider(provider)

    HTTPXClientInstrumentor().instrument()
    AioHttpClientInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument(engine=db_engine.sync_engine)
