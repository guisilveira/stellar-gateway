"""
Stellar Gateway - SWAPI Proxy API.

This module creates and configures the FastAPI application.
Entry point for the serverless Cloud Function.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from adapters.redis import get_redis_client
from adapters.swapi import get_swapi_client
from api.errors import InvalidResourceMiddleware, register_exception_handlers
from api.middleware import RequestLoggingMiddleware
from api.routes import router
from core.config import settings
from core.logging import get_logger, setup_logging

# Initialize logging before anything else
setup_logging(settings.ENVIRONMENT)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events for resource cleanup.
    Ensures proper cleanup of connection pools.
    """
    # Startup
    logger.info(
        "Application starting",
        extra={
            "extra_fields": {
                "event": "startup",
                "environment": settings.ENVIRONMENT,
                "version": "1.0.0",
            }
        },
    )
    yield

    # Shutdown: close connection pools
    logger.info(
        "Application shutting down",
        extra={"extra_fields": {"event": "shutdown"}},
    )

    swapi_client = get_swapi_client()
    await swapi_client.close()

    redis_client = get_redis_client()
    await redis_client.close()

    logger.info(
        "Application shutdown complete",
        extra={"extra_fields": {"event": "shutdown_complete"}},
    )


def create_app() -> FastAPI:
    """
    Creates and configures the FastAPI application.

    Returns:
        A configured FastAPI application instance.
    """
    app = FastAPI(
        title="Stellar Gateway",
        description="A serverless proxy for the Star Wars API (SWAPI)",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.ENVIRONMENT != "prod" else None,
        redoc_url=None,
    )

    # Register exception handlers
    register_exception_handlers(app)

    # Add request logging middleware (outermost, logs all requests)
    app.add_middleware(RequestLoggingMiddleware)

    # Add resource validation middleware
    app.add_middleware(InvalidResourceMiddleware)

    # Health check endpoint - defined BEFORE router to avoid being caught by /{resource}
    @app.get("/health", tags=["Health"])
    async def health_check() -> dict[str, str]:
        """Health check endpoint for load balancers."""
        return {"status": "healthy"}

    # Include routes AFTER health check
    app.include_router(router)

    return app


# Create the application instance
app = create_app()
