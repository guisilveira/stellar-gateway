"""
Unit tests for the structured logging module.

Tests cover:
- JSON formatter output structure
- Development formatter output
- Trace ID inclusion
- Extra fields handling
- Severity levels
- Exception formatting
"""

import json
import logging
from io import StringIO

import pytest

from core.logging import (
    CloudRunJSONFormatter,
    DevelopmentFormatter,
    get_logger,
    setup_logging,
)


class TestCloudRunJSONFormatter:
    """Tests for the Cloud Run JSON formatter."""

    @pytest.fixture
    def formatter(self) -> CloudRunJSONFormatter:
        """Create a formatter instance."""
        return CloudRunJSONFormatter()

    @pytest.fixture
    def log_record(self) -> logging.LogRecord:
        """Create a basic log record."""
        return logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

    def test_format_basic_log_entry(
        self, formatter: CloudRunJSONFormatter, log_record: logging.LogRecord
    ) -> None:
        """Test that basic log entries are formatted correctly."""
        result = formatter.format(log_record)
        parsed = json.loads(result)

        assert parsed["severity"] == "INFO"
        assert parsed["message"] == "Test message"
        assert parsed["logger"] == "test.logger"
        assert "timestamp" in parsed
        assert "logging.googleapis.com/sourceLocation" in parsed

    def test_format_includes_source_location(
        self, formatter: CloudRunJSONFormatter, log_record: logging.LogRecord
    ) -> None:
        """Test that source location is included."""
        result = formatter.format(log_record)
        parsed = json.loads(result)

        source_location = parsed["logging.googleapis.com/sourceLocation"]
        assert source_location["file"] == "test.py"
        assert source_location["line"] == "42"
        assert "function" in source_location

    def test_format_includes_trace_id_when_present(
        self, formatter: CloudRunJSONFormatter, log_record: logging.LogRecord
    ) -> None:
        """Test that trace ID is included when set on the record."""
        log_record.trace_id = "projects/my-project/traces/abc123"
        result = formatter.format(log_record)
        parsed = json.loads(result)

        assert (
            parsed["logging.googleapis.com/trace"]
            == "projects/my-project/traces/abc123"
        )

    def test_format_excludes_trace_id_when_not_present(
        self, formatter: CloudRunJSONFormatter, log_record: logging.LogRecord
    ) -> None:
        """Test that trace ID is excluded when not set."""
        result = formatter.format(log_record)
        parsed = json.loads(result)

        assert "logging.googleapis.com/trace" not in parsed

    def test_format_includes_extra_fields(
        self, formatter: CloudRunJSONFormatter, log_record: logging.LogRecord
    ) -> None:
        """Test that extra fields are included in the output."""
        log_record.extra_fields = {
            "httpRequest": {
                "requestMethod": "GET",
                "requestUrl": "/people/1",
                "status": 200,
            },
            "request_id": "abc123",
        }
        result = formatter.format(log_record)
        parsed = json.loads(result)

        assert parsed["httpRequest"]["requestMethod"] == "GET"
        assert parsed["httpRequest"]["requestUrl"] == "/people/1"
        assert parsed["httpRequest"]["status"] == 200
        assert parsed["request_id"] == "abc123"

    def test_format_includes_exception_info(
        self, formatter: CloudRunJSONFormatter
    ) -> None:
        """Test that exception info is included when present."""
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="/app/test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        result = formatter.format(record)
        parsed = json.loads(result)

        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]
        assert "Test error" in parsed["exception"]

    def test_format_all_severity_levels(self, formatter: CloudRunJSONFormatter) -> None:
        """Test that all severity levels are formatted correctly."""
        levels = [
            (logging.DEBUG, "DEBUG"),
            (logging.INFO, "INFO"),
            (logging.WARNING, "WARNING"),
            (logging.ERROR, "ERROR"),
            (logging.CRITICAL, "CRITICAL"),
        ]

        for level, expected_severity in levels:
            record = logging.LogRecord(
                name="test",
                level=level,
                pathname="test.py",
                lineno=1,
                msg="Test",
                args=(),
                exc_info=None,
            )
            result = formatter.format(record)
            parsed = json.loads(result)
            assert parsed["severity"] == expected_severity

    def test_format_timestamp_is_iso8601(
        self, formatter: CloudRunJSONFormatter, log_record: logging.LogRecord
    ) -> None:
        """Test that timestamp is in ISO 8601 format."""
        result = formatter.format(log_record)
        parsed = json.loads(result)

        # ISO 8601 format should contain 'T' and timezone info
        timestamp = parsed["timestamp"]
        assert "T" in timestamp
        assert "+" in timestamp or "Z" in timestamp or timestamp.endswith("+00:00")


class TestDevelopmentFormatter:
    """Tests for the development formatter."""

    @pytest.fixture
    def formatter(self) -> DevelopmentFormatter:
        """Create a formatter instance."""
        return DevelopmentFormatter()

    @pytest.fixture
    def log_record(self) -> logging.LogRecord:
        """Create a basic log record."""
        return logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

    def test_format_includes_level_and_message(
        self, formatter: DevelopmentFormatter, log_record: logging.LogRecord
    ) -> None:
        """Test that level and message are included in output."""
        result = formatter.format(log_record)

        assert "[INFO" in result
        assert "Test message" in result

    def test_format_includes_extra_fields(
        self, formatter: DevelopmentFormatter, log_record: logging.LogRecord
    ) -> None:
        """Test that extra fields are included in output."""
        log_record.extra_fields = {
            "request_id": "abc123",
            "user_id": "user-001",
        }
        result = formatter.format(log_record)

        # Check for key and value (may have ANSI codes around key)
        assert "request_id" in result
        assert "abc123" in result
        assert "user_id" in result
        assert "user-001" in result

    def test_format_flattens_http_request(
        self, formatter: DevelopmentFormatter, log_record: logging.LogRecord
    ) -> None:
        """Test that httpRequest fields are flattened for display."""
        log_record.extra_fields = {
            "httpRequest": {
                "requestMethod": "GET",
                "requestUrl": "/people/1",
                "status": 200,
                "latency": "45.00ms",
            }
        }
        result = formatter.format(log_record)

        # Check for key and value (may have ANSI codes around key)
        assert "method" in result
        assert "GET" in result
        assert "path" in result
        assert "/people/1" in result
        assert "status" in result
        assert "200" in result
        assert "latency" in result
        assert "45.00ms" in result

    def test_format_includes_exception(self, formatter: DevelopmentFormatter) -> None:
        """Test that exception info is included."""
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="/app/test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        result = formatter.format(record)

        assert "ValueError" in result
        assert "Test error" in result


class TestSetupLogging:
    """Tests for the logging setup function."""

    def test_setup_logging_prod_uses_json_formatter(self) -> None:
        """Test that production environment uses JSON formatter."""
        setup_logging("prod")

        root_logger = logging.getLogger()
        assert len(root_logger.handlers) == 1
        assert isinstance(root_logger.handlers[0].formatter, CloudRunJSONFormatter)

    def test_setup_logging_dev_uses_development_formatter(self) -> None:
        """Test that development environment uses development formatter."""
        setup_logging("dev")

        root_logger = logging.getLogger()
        assert len(root_logger.handlers) == 1
        assert isinstance(root_logger.handlers[0].formatter, DevelopmentFormatter)

    def test_setup_logging_test_uses_development_formatter(self) -> None:
        """Test that test environment uses development formatter."""
        setup_logging("test")

        root_logger = logging.getLogger()
        assert len(root_logger.handlers) == 1
        assert isinstance(root_logger.handlers[0].formatter, DevelopmentFormatter)

    def test_setup_logging_clears_existing_handlers(self) -> None:
        """Test that setup clears existing handlers."""
        root_logger = logging.getLogger()

        # Add a dummy handler
        root_logger.addHandler(logging.StreamHandler())

        setup_logging("dev")

        # Should have exactly one handler after setup
        assert len(root_logger.handlers) == 1

    def test_setup_logging_suppresses_noisy_loggers(self) -> None:
        """Test that noisy third-party loggers are suppressed."""
        setup_logging("dev")

        assert logging.getLogger("httpx").level == logging.WARNING
        assert logging.getLogger("httpcore").level == logging.WARNING
        assert logging.getLogger("urllib3").level == logging.WARNING


class TestGetLogger:
    """Tests for the get_logger function."""

    def test_get_logger_returns_logger_with_name(self) -> None:
        """Test that get_logger returns a logger with the given name."""
        logger = get_logger("my.module")

        assert logger.name == "my.module"
        assert isinstance(logger, logging.Logger)

    def test_get_logger_returns_same_logger_for_same_name(self) -> None:
        """Test that get_logger returns the same logger for the same name."""
        logger1 = get_logger("my.module")
        logger2 = get_logger("my.module")

        assert logger1 is logger2


class TestLoggingIntegration:
    """Integration tests for the logging system."""

    @pytest.fixture(autouse=True)
    def setup_logging_for_test(self) -> None:
        """Setup logging before each test."""
        setup_logging("test")

    def test_log_with_extra_fields_json_format(self) -> None:
        """Test logging with extra fields in JSON format."""
        setup_logging("prod")

        # Capture stdout
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(CloudRunJSONFormatter())

        logger = logging.getLogger("test.integration")
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)

        logger.info(
            "Request completed",
            extra={
                "extra_fields": {
                    "httpRequest": {
                        "requestMethod": "GET",
                        "requestUrl": "/people/1",
                        "status": 200,
                    }
                }
            },
        )

        output = stream.getvalue()
        parsed = json.loads(output.strip())

        assert parsed["message"] == "Request completed"
        assert parsed["httpRequest"]["requestMethod"] == "GET"
