"""
Structured logging for Cloud Run.

This module provides JSON-formatted logging that integrates with
Google Cloud Logging when running on Cloud Run.

Cloud Run automatically captures stdout/stderr, so we just need to:
1. Format logs as JSON in production
2. Use human-readable format in development
3. Include special fields for Cloud Logging integration
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class CloudRunJSONFormatter(logging.Formatter):
    """
    JSON formatter that outputs logs in Cloud Logging format.

    Special fields recognized by Cloud Logging:
    - severity: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - message: Main log message
    - logging.googleapis.com/trace: Request trace ID for correlation
    - logging.googleapis.com/sourceLocation: Source file/line/function

    Reference: https://cloud.google.com/logging/docs/structured-logging
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON string for Cloud Logging."""
        log_entry: dict[str, Any] = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "logger": record.name,
        }

        # Add source location for debugging
        log_entry["logging.googleapis.com/sourceLocation"] = {
            "file": record.filename,
            "line": str(record.lineno),
            "function": record.funcName,
        }

        # Add trace ID if available (set by middleware for request correlation)
        if hasattr(record, "trace_id") and record.trace_id:
            log_entry["logging.googleapis.com/trace"] = record.trace_id

        # Add extra fields from the record
        if hasattr(record, "extra_fields") and record.extra_fields:
            log_entry.update(record.extra_fields)

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


class DevelopmentFormatter(logging.Formatter):
    """
    Human-readable colored formatter for local development.

    Provides a clean, colorful output that's easy to read during development.
    """

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record with colors for terminal output."""
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Build the main message
        msg = (
            f"{color}{timestamp} [{record.levelname:8}]{self.RESET} "
            f"{record.getMessage()}"
        )

        # Add extra fields if present
        if hasattr(record, "extra_fields") and record.extra_fields:
            # Flatten httpRequest for display
            extras = record.extra_fields.copy()
            if "httpRequest" in extras:
                http_req = extras.pop("httpRequest")
                extras.update(
                    {
                        "method": http_req.get("requestMethod", ""),
                        "path": http_req.get("requestUrl", ""),
                        "status": http_req.get("status", ""),
                        "latency": http_req.get("latency", ""),
                    }
                )
            # Format extras as key=value pairs
            extras_str = " ".join(
                f"{self.BOLD}{k}{self.RESET}={v}" for k, v in extras.items() if v
            )
            if extras_str:
                msg += f" {color}|{self.RESET} {extras_str}"

        # Add exception info if present
        if record.exc_info:
            msg += f"\n{self.formatException(record.exc_info)}"

        return msg


def setup_logging(environment: str = "dev") -> None:
    """
    Configure logging based on environment.

    Args:
        environment: The environment ("dev", "test", or "prod").
                    In prod, uses JSON format; otherwise, uses colored text.
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create handler for stdout
    handler = logging.StreamHandler(sys.stdout)

    # Use JSON in production, pretty in development
    if environment == "prod":
        handler.setFormatter(CloudRunJSONFormatter())
    else:
        handler.setFormatter(DevelopmentFormatter())

    root_logger.addHandler(handler)

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: The logger name (typically __name__).

    Returns:
        A configured logger instance.
    """
    return logging.getLogger(name)
