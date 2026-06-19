from unittest.mock import MagicMock, patch

import pytest

from pylon_service.otel_config import init_otel
from pylon_service.settings import OtelSettings


@pytest.mark.parametrize(
    ("endpoint", "expected"),
    [
        pytest.param("", False, id="empty_endpoint_disabled"),
        pytest.param("   ", False, id="whitespace_only_disabled"),
        pytest.param("http://alloy:4318", True, id="set_endpoint_enabled"),
    ],
)
def test_traces_enabled_reflects_endpoint(endpoint, expected):
    assert OtelSettings(collector_endpoint=endpoint).traces_enabled is expected


def test_init_otel_is_noop_when_disabled():
    with (
        patch("pylon_service.otel_config.otel_settings", OtelSettings(collector_endpoint="")),
        patch("pylon_service.otel_config.trace.set_tracer_provider") as set_provider,
        patch("pylon_service.otel_config.HTTPXClientInstrumentor") as httpx_instrumentor,
        patch("pylon_service.otel_config.AioHttpClientInstrumentor") as aiohttp_instrumentor,
        patch("pylon_service.otel_config.SQLAlchemyInstrumentor") as sqlalchemy_instrumentor,
    ):
        init_otel()

    set_provider.assert_not_called()
    httpx_instrumentor.assert_not_called()
    aiohttp_instrumentor.assert_not_called()
    sqlalchemy_instrumentor.assert_not_called()


def test_init_otel_installs_provider_and_instruments_when_enabled():
    sync_engine = MagicMock()
    db_engine = MagicMock(sync_engine=sync_engine)

    with (
        patch("pylon_service.otel_config.otel_settings", OtelSettings(collector_endpoint="http://alloy:4318")),
        patch("pylon_service.otel_config.db_engine", db_engine),
        patch("pylon_service.otel_config.trace.set_tracer_provider") as set_provider,
        patch("pylon_service.otel_config.TracerProvider"),
        patch("pylon_service.otel_config.BatchSpanProcessor"),
        patch("pylon_service.otel_config.OTLPSpanExporter") as exporter,
        patch("pylon_service.otel_config.HTTPXClientInstrumentor") as httpx_instrumentor,
        patch("pylon_service.otel_config.AioHttpClientInstrumentor") as aiohttp_instrumentor,
        patch("pylon_service.otel_config.SQLAlchemyInstrumentor") as sqlalchemy_instrumentor,
    ):
        init_otel()

    set_provider.assert_called_once()
    exporter.assert_called_once_with(endpoint="http://alloy:4318/v1/traces")
    httpx_instrumentor.return_value.instrument.assert_called_once_with()
    aiohttp_instrumentor.return_value.instrument.assert_called_once_with()
    sqlalchemy_instrumentor.return_value.instrument.assert_called_once_with(engine=sync_engine)


@pytest.mark.parametrize(
    ("collector_endpoint", "expected_exporter_endpoint"),
    [
        pytest.param("http://alloy:4318", "http://alloy:4318/v1/traces", id="bare_endpoint"),
        pytest.param("http://alloy:4318/", "http://alloy:4318/v1/traces", id="trailing_slash"),
        pytest.param("  http://alloy:4318/  ", "http://alloy:4318/v1/traces", id="whitespace_and_slash"),
    ],
)
def test_init_otel_normalizes_collector_endpoint(collector_endpoint, expected_exporter_endpoint):
    with (
        patch("pylon_service.otel_config.otel_settings", OtelSettings(collector_endpoint=collector_endpoint)),
        patch("pylon_service.otel_config.db_engine", MagicMock()),
        patch("pylon_service.otel_config.trace.set_tracer_provider"),
        patch("pylon_service.otel_config.TracerProvider"),
        patch("pylon_service.otel_config.BatchSpanProcessor"),
        patch("pylon_service.otel_config.OTLPSpanExporter") as exporter,
        patch("pylon_service.otel_config.HTTPXClientInstrumentor"),
        patch("pylon_service.otel_config.AioHttpClientInstrumentor"),
        patch("pylon_service.otel_config.SQLAlchemyInstrumentor"),
    ):
        init_otel()

    exporter.assert_called_once_with(endpoint=expected_exporter_endpoint)


@pytest.mark.parametrize(
    ("traces_enabled", "expected_present"),
    [
        pytest.param(True, True, id="enabled_plugin_present"),
        pytest.param(False, False, id="disabled_plugin_absent"),
    ],
)
def test_create_app_registers_otel_plugin_only_when_enabled(traces_enabled, expected_present):
    from litestar.contrib.opentelemetry import OpenTelemetryPlugin

    from pylon_service.main import create_app

    with patch("pylon_service.main.otel_settings") as otel_settings_mock:
        otel_settings_mock.traces_enabled = traces_enabled
        app = create_app()

    has_plugin = any(isinstance(plugin, OpenTelemetryPlugin) for plugin in app.plugins)
    assert has_plugin is expected_present
