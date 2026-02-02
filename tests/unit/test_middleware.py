"""
Unit tests for the request logging middleware.

Tests cover:
- Request/response logging
- Trace ID extraction
- Duration calculation
- Log level based on status code
- Skipping health check paths
"""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.responses import Response

from api.middleware import RequestLoggingMiddleware
from core.logging import setup_logging


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI application."""
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/test")
    async def test_endpoint() -> dict:
        return {"status": "ok"}

    @app.get("/health")
    async def health_endpoint() -> dict:
        return {"status": "healthy"}

    @app.get("/error")
    async def error_endpoint() -> None:
        raise ValueError("Test error")

    @app.get("/not-found")
    async def not_found_endpoint() -> Response:
        return Response(status_code=404)

    @app.get("/server-error")
    async def server_error_endpoint() -> Response:
        return Response(status_code=500)

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app, raise_server_exceptions=False)


class TestRequestLoggingMiddleware:
    """Tests for the RequestLoggingMiddleware."""

    @pytest.fixture(autouse=True)
    def setup_logging_for_test(self) -> None:
        """Setup logging before each test."""
        setup_logging("test")

    def test_logs_successful_request(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that successful requests are logged at INFO level."""
        with caplog.at_level(logging.INFO):
            response = client.get("/test")

        assert response.status_code == 200

        # Check that the request was logged
        log_messages = [r.message for r in caplog.records]
        assert any("GET /test - 200" in msg for msg in log_messages)

    def test_logs_404_at_warning_level(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that 404 responses are logged at WARNING level."""
        with caplog.at_level(logging.WARNING):
            response = client.get("/not-found")

        assert response.status_code == 404

        # Check that a warning was logged
        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert any("GET /not-found - 404" in r.message for r in warning_records)

    def test_logs_500_at_error_level(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that 500 responses are logged at ERROR level."""
        with caplog.at_level(logging.ERROR):
            response = client.get("/server-error")

        assert response.status_code == 500

        # Check that an error was logged
        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert any("GET /server-error - 500" in r.message for r in error_records)

    def test_skips_health_endpoint(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that health check requests are not logged."""
        with caplog.at_level(logging.INFO):
            response = client.get("/health")

        assert response.status_code == 200

        # Check that the health endpoint was NOT logged
        log_messages = [r.message for r in caplog.records]
        assert not any("/health" in msg for msg in log_messages)

    def test_includes_request_id_in_log(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that request ID is included in log extra fields."""
        with caplog.at_level(logging.INFO):
            response = client.get("/test")

        assert response.status_code == 200

        # Find the log record for our request
        relevant_records = [
            r for r in caplog.records if hasattr(r, "extra_fields")
        ]
        assert len(relevant_records) > 0

        record = relevant_records[0]
        assert "request_id" in record.extra_fields

    def test_includes_http_request_info_in_log(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that HTTP request info is included in log extra fields."""
        with caplog.at_level(logging.INFO):
            response = client.get("/test")

        assert response.status_code == 200

        # Find the log record for our request
        relevant_records = [
            r for r in caplog.records if hasattr(r, "extra_fields")
        ]
        assert len(relevant_records) > 0

        record = relevant_records[0]
        http_request = record.extra_fields.get("httpRequest", {})
        assert http_request.get("requestMethod") == "GET"
        assert http_request.get("requestUrl") == "/test"
        assert http_request.get("status") == 200
        assert "latency" in http_request

    def test_uses_custom_request_id_from_header(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that X-Request-ID header is used if provided."""
        with caplog.at_level(logging.INFO):
            response = client.get("/test", headers={"X-Request-ID": "custom-id-123"})

        assert response.status_code == 200

        # Find the log record for our request
        relevant_records = [
            r for r in caplog.records if hasattr(r, "extra_fields")
        ]
        assert len(relevant_records) > 0

        record = relevant_records[0]
        assert record.extra_fields["request_id"] == "custom-id-123"


class TestTraceIdExtraction:
    """Tests for Cloud Trace ID extraction."""

    def test_extracts_trace_id_from_header(self) -> None:
        """Test that trace ID is extracted from X-Cloud-Trace-Context header."""
        middleware = RequestLoggingMiddleware(MagicMock())

        # Create a mock request with trace header
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {
            "X-Cloud-Trace-Context": "abc123def456/1;o=1"
        }

        with patch("api.middleware.settings") as mock_settings:
            mock_settings.GCP_PROJECT = "my-project"
            trace_id = middleware._extract_trace_id(mock_request)

        assert trace_id == "projects/my-project/traces/abc123def456"

    def test_returns_none_when_no_trace_header(self) -> None:
        """Test that None is returned when no trace header is present."""
        middleware = RequestLoggingMiddleware(MagicMock())

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}

        with patch("api.middleware.settings") as mock_settings:
            mock_settings.GCP_PROJECT = "my-project"
            trace_id = middleware._extract_trace_id(mock_request)

        assert trace_id is None

    def test_returns_none_when_no_gcp_project(self) -> None:
        """Test that None is returned when GCP_PROJECT is not set."""
        middleware = RequestLoggingMiddleware(MagicMock())

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {
            "X-Cloud-Trace-Context": "abc123def456/1;o=1"
        }

        with patch("api.middleware.settings") as mock_settings:
            mock_settings.GCP_PROJECT = ""
            trace_id = middleware._extract_trace_id(mock_request)

        assert trace_id is None


class TestSkipPaths:
    """Tests for path skipping functionality."""

    def test_skip_paths_includes_health(self) -> None:
        """Test that /health is in skip paths."""
        assert "/health" in RequestLoggingMiddleware.SKIP_PATHS

    def test_skip_paths_includes_docs(self) -> None:
        """Test that /docs is in skip paths."""
        assert "/docs" in RequestLoggingMiddleware.SKIP_PATHS

    def test_skip_paths_includes_openapi(self) -> None:
        """Test that /openapi.json is in skip paths."""
        assert "/openapi.json" in RequestLoggingMiddleware.SKIP_PATHS
