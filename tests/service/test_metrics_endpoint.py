import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_403_FORBIDDEN
from litestar.testing import AsyncTestClient

from pylon_client.service.settings import settings


class TestMetricsEndpoint:
    @pytest.mark.asyncio
    async def test_metrics_without_token_config_returns_403(self, test_client: AsyncTestClient, monkeypatch):
        monkeypatch.setattr(settings, "metrics_token", None)

        response = await test_client.get("/metrics")

        assert response.status_code == HTTP_403_FORBIDDEN
        assert response.json() == {"detail": "Metrics endpoint is not configured", "status_code": 403}

    @pytest.mark.asyncio
    async def test_metrics_without_authorization_header_returns_403(self, test_client: AsyncTestClient, monkeypatch):
        monkeypatch.setattr(settings, "metrics_token", "test-metrics-token")

        response = await test_client.get("/metrics")

        assert response.status_code == HTTP_403_FORBIDDEN
        assert response.json() == {"detail": "Authorization header is required", "status_code": 403}

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "auth_header",
        [
            pytest.param("invalid-format", id="invalid_format"),
            pytest.param("Bearer", id="bearer_without_token"),
            pytest.param("Basic dGVzdDp0ZXN0", id="basic_auth_scheme"),
            pytest.param("Bearer token with spaces", id="bearer_with_spaces"),
            pytest.param("", id="empty_string"),
        ],
    )
    async def test_metrics_with_invalid_authorization_format_returns_403(
        self, test_client: AsyncTestClient, monkeypatch, auth_header: str
    ):
        monkeypatch.setattr(settings, "metrics_token", "test-metrics-token")

        response = await test_client.get("/metrics", headers={"Authorization": auth_header})

        assert response.status_code == HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_metrics_with_wrong_token_returns_403(self, test_client: AsyncTestClient, monkeypatch):
        monkeypatch.setattr(settings, "metrics_token", "correct-token")

        response = await test_client.get("/metrics", headers={"Authorization": "Bearer wrong-token"})

        assert response.status_code == HTTP_403_FORBIDDEN
        assert response.json() == {"detail": "Invalid authorization token", "status_code": 403}

    @pytest.mark.asyncio
    async def test_metrics_with_correct_token_returns_200(self, test_client: AsyncTestClient, monkeypatch):
        test_token = "correct-metrics-token"
        monkeypatch.setattr(settings, "metrics_token", test_token)

        response = await test_client.get("/metrics", headers={"Authorization": f"Bearer {test_token}"})

        assert response.status_code == HTTP_200_OK

        # Should contain Prometheus metrics
        content = response.text
        assert "# HELP" in content or "# TYPE" in content

    @pytest.mark.asyncio
    async def test_metrics_endpoint_includes_pylon_metrics(self, test_client: AsyncTestClient, monkeypatch):
        test_token = "metrics-content-test"
        monkeypatch.setattr(settings, "metrics_token", test_token)

        response = await test_client.get("/metrics", headers={"Authorization": f"Bearer {test_token}"})

        assert response.status_code == HTTP_200_OK
        content = response.text

        expected_metrics = [
            "pylon_bittensor_operation_duration_seconds",
            "pylon_bittensor_fallback_total",
        ]

        for metric in expected_metrics:
            assert metric in content, f"Expected metric {metric} not found in response"
