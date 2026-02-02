"""
Request logging middleware for FastAPI.

This middleware logs every HTTP request with:
- Request method and path
- Response status code
- Request duration in milliseconds
- User ID (if authenticated)
- Trace ID for Cloud Run log correlation
"""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from core.config import settings

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs request/response information.

    Features:
    - Logs request method, path, status code, and duration
    - Extracts Cloud Trace ID for log correlation in Cloud Run
    - Stores request_id and trace_id in request.state for use in handlers
    - Uses appropriate log levels based on response status code
    - Skips logging for health check endpoints to reduce noise
    """

    # Paths to skip logging (health checks, docs)
    SKIP_PATHS = frozenset({"/health", "/docs", "/openapi.json"})

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """
        Process the request and log request/response information.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware or route handler.

        Returns:
            The HTTP response.
        """
        # Skip logging for certain paths
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])

        # Extract Cloud Trace ID for log correlation
        trace_id = self._extract_trace_id(request)

        # Store in request state for use in route handlers
        request.state.request_id = request_id
        request.state.trace_id = trace_id

        # Record start time
        start_time = time.perf_counter()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Extract user ID if available (set by security dependency)
        user_id = getattr(request.state, "user_id", None)

        # Build log extra fields
        extra: dict = {
            "extra_fields": {
                "httpRequest": {
                    "requestMethod": request.method,
                    "requestUrl": str(request.url.path),
                    "status": response.status_code,
                    "latency": f"{duration_ms:.2f}ms",
                },
                "request_id": request_id,
            }
        }

        if user_id:
            extra["extra_fields"]["user_id"] = user_id

        if trace_id:
            extra["trace_id"] = trace_id

        # Build log message
        log_message = f"{request.method} {request.url.path} - {response.status_code}"

        # Log with appropriate level based on status code
        if response.status_code >= 500:
            logger.error(log_message, extra=extra)
        elif response.status_code >= 400:
            logger.warning(log_message, extra=extra)
        else:
            logger.info(log_message, extra=extra)

        return response

    def _extract_trace_id(self, request: Request) -> str | None:
        """
        Extract trace ID from Cloud Trace header.

        Cloud Run sets the X-Cloud-Trace-Context header on incoming requests.
        Format: TRACE_ID/SPAN_ID;o=TRACE_TRUE

        Args:
            request: The incoming HTTP request.

        Returns:
            The full trace resource name or None if not available.
        """
        trace_header = request.headers.get("X-Cloud-Trace-Context")
        if trace_header and settings.GCP_PROJECT:
            # Extract the trace ID (before the /)
            trace = trace_header.split("/")[0]
            return f"projects/{settings.GCP_PROJECT}/traces/{trace}"
        return None
