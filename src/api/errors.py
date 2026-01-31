"""
Error Handling for FastAPI.

This module implements RFC 7807 Problem Details for HTTP APIs.
Converts domain exceptions to standardized error responses.
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from domain.exceptions import (
    ExternalServiceException,
    ResourceNotFoundException,
    StellarGatewayException,
)


# Valid SWAPI resource types
VALID_RESOURCES = frozenset(
    {"people", "planets", "films", "species", "vehicles", "starships"}
)


class ProblemDetail:
    """
    RFC 7807 Problem Details response builder.

    This class creates standardized error responses following the
    RFC 7807 specification for HTTP problem details.
    """

    @staticmethod
    def create(
        title: str,
        status_code: int,
        detail: str,
        type_uri: str = "about:blank",
        instance: str | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        """
        Creates a Problem Details response body.

        Args:
            title: A short, human-readable summary of the problem.
            status_code: The HTTP status code.
            detail: A human-readable explanation specific to this occurrence.
            type_uri: A URI reference identifying the problem type.
            instance: A URI reference identifying this specific occurrence.
            **extra: Additional problem-specific properties.

        Returns:
            A dictionary conforming to RFC 7807.
        """
        response: dict[str, Any] = {
            "type": type_uri,
            "title": title,
            "status": status_code,
            "detail": detail,
        }

        if instance:
            response["instance"] = instance

        # Add any extra fields
        response.update(extra)

        return response


async def resource_not_found_handler(
    request: Request,
    exc: ResourceNotFoundException,
) -> JSONResponse:
    """
    Handler for ResourceNotFoundException.

    Returns a 404 Not Found response with RFC 7807 Problem Details.

    Args:
        request: The incoming request.
        exc: The exception that was raised.

    Returns:
        A JSONResponse with Problem Details.
    """
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=ProblemDetail.create(
            title="Resource Not Found",
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
            instance=str(request.url),
            resource_type=exc.resource_type,
            resource_id=exc.resource_id,
        ),
        media_type="application/problem+json",
    )


async def external_service_handler(
    request: Request,
    exc: ExternalServiceException,
) -> JSONResponse:
    """
    Handler for ExternalServiceException.

    Returns a 502 Bad Gateway response with RFC 7807 Problem Details.

    Args:
        request: The incoming request.
        exc: The exception that was raised.

    Returns:
        A JSONResponse with Problem Details.
    """
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content=ProblemDetail.create(
            title="External Service Error",
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.message,
            instance=str(request.url),
            service=exc.service_name,
        ),
        media_type="application/problem+json",
    )


async def generic_exception_handler(
    request: Request,
    exc: StellarGatewayException,
) -> JSONResponse:
    """
    Handler for generic StellarGatewayException.

    Returns a 500 Internal Server Error response with RFC 7807 Problem Details.

    Args:
        request: The incoming request.
        exc: The exception that was raised.

    Returns:
        A JSONResponse with Problem Details.
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ProblemDetail.create(
            title="Internal Server Error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=exc.message,
            instance=str(request.url),
        ),
        media_type="application/problem+json",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Registers all exception handlers with the FastAPI application.

    Args:
        app: The FastAPI application instance.
    """
    app.add_exception_handler(ResourceNotFoundException, resource_not_found_handler)
    app.add_exception_handler(ExternalServiceException, external_service_handler)
    app.add_exception_handler(StellarGatewayException, generic_exception_handler)


class InvalidResourceMiddleware:
    """
    Middleware to validate resource types before routing.

    Returns a 400 Bad Request for invalid resource types.
    """

    def __init__(self, app: FastAPI) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        """
        ASGI middleware entry point.

        Validates resource type in the URL path.
        """
        if scope["type"] == "http":
            path = scope["path"]
            # Check if path matches /{resource} or /{resource}/{id} pattern
            parts = path.strip("/").split("/")
            if parts and parts[0] not in ("me", "docs", "openapi.json", "health"):
                resource = parts[0]
                if resource not in VALID_RESOURCES:
                    # Return 400 Bad Request
                    response = JSONResponse(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        content=ProblemDetail.create(
                            title="Invalid Resource Type",
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Resource type '{resource}' is not valid. "
                            f"Valid types are: {', '.join(sorted(VALID_RESOURCES))}",
                            instance=path,
                        ),
                        media_type="application/problem+json",
                    )
                    await response(scope, receive, send)
                    return

        await self.app(scope, receive, send)
