"""
SWAPI HTTP Adapter.

This module implements the SwapiInterface using httpx for async HTTP requests.
Includes retry logic with exponential backoff for resilience.
Uses a persistent AsyncClient for connection pooling.
"""

from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.config import settings
from domain.exceptions import ExternalServiceException, ResourceNotFoundException

# Retry configuration constants
MAX_RETRY_ATTEMPTS = 3
RETRY_WAIT_MIN_SECONDS = 1
RETRY_WAIT_MAX_SECONDS = 10
REQUEST_TIMEOUT_SECONDS = 10.0

# Module-level singleton for the SWAPI client
_swapi_client: "SwapiClient | None" = None


class SwapiClient:
    """
    HTTP client for fetching data from the Star Wars API (SWAPI).

    Implements the SwapiInterface protocol with retry logic and
    proper error handling for resilience.

    Uses a persistent httpx.AsyncClient for connection pooling,
    improving performance by reusing TCP connections.

    Attributes:
        _base_url: The base URL for SWAPI (default from settings).
        _client: The persistent httpx.AsyncClient instance.
        _owns_client: Whether this instance owns the client (for cleanup).
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = REQUEST_TIMEOUT_SECONDS,
        http_client: Any | None = None,
    ) -> None:
        """
        Initializes the SWAPI client.

        Args:
            base_url: Optional base URL override (useful for testing).
            timeout: Request timeout in seconds (default: 10).
            http_client: Optional pre-configured httpx.AsyncClient (for testing).
                        If not provided, a persistent client will be created.
        """
        self._base_url = base_url or settings.SWAPI_BASE_URL
        self._timeout = timeout

        if http_client is not None:
            self._client = http_client
            self._owns_client = False
        else:
            self._client = httpx.AsyncClient(timeout=self._timeout)
            self._owns_client = True

    async def close(self) -> None:
        """
        Closes the underlying HTTP client connection pool.

        Should be called when the client is no longer needed.
        Only closes if this instance owns the client.
        """
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    async def __aenter__(self) -> "SwapiClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit - closes the client."""
        await self.close()

    @retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(min=RETRY_WAIT_MIN_SECONDS, max=RETRY_WAIT_MAX_SECONDS),
        reraise=True,
    )
    async def _make_request(self, url: str, params: dict | None = None) -> dict:
        """
        Makes an HTTP GET request with retry logic.

        This method handles retries for transient network errors only.
        HTTP errors (4xx, 5xx) are not retried.

        Args:
            url: The full URL to request.
            params: Optional query parameters.

        Returns:
            The JSON response as a dictionary.

        Raises:
            httpx.HTTPStatusError: For non-2xx responses.
            httpx.ConnectError: For connection failures (after retries exhausted).
            httpx.TimeoutException: For timeouts (after retries exhausted).
        """
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def get_resource(self, resource_type: str, resource_id: int) -> dict:
        """
        Fetches a single resource from SWAPI by ID.

        Args:
            resource_type: The type of resource (e.g., "people", "planets").
            resource_id: The unique identifier of the resource.

        Returns:
            A dictionary containing the raw SWAPI response.

        Raises:
            ResourceNotFoundException: If the resource does not exist (404).
            ExternalServiceException: If the external service fails.
        """
        url = f"{self._base_url}/{resource_type}/{resource_id}/"

        try:
            return await self._make_request(url)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ResourceNotFoundException(
                    resource_type=resource_type,
                    resource_id=resource_id,
                ) from e
            raise ExternalServiceException(
                service_name="SWAPI",
                status_code=e.response.status_code,
                message=f"SWAPI returned status {e.response.status_code}",
            ) from e

        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise ExternalServiceException(
                service_name="SWAPI",
                message=f"Failed to connect to SWAPI: {str(e)}",
            ) from e

    async def list_resources(
        self,
        resource_type: str,
        page: int | None = None,
        search: str | None = None,
    ) -> dict:
        """
        Lists resources from SWAPI with optional pagination and search.

        Args:
            resource_type: The type of resource (e.g., "people", "planets").
            page: Optional page number for pagination.
            search: Optional search query string.

        Returns:
            A dictionary containing the paginated SWAPI response.

        Raises:
            ExternalServiceException: If the external service fails.
        """
        url = f"{self._base_url}/{resource_type}/"
        params: dict[str, str | int] = {}

        if page is not None:
            params["page"] = page
        if search is not None:
            params["search"] = search

        try:
            return await self._make_request(url, params=params or None)

        except httpx.HTTPStatusError as e:
            raise ExternalServiceException(
                service_name="SWAPI",
                status_code=e.response.status_code,
                message=f"SWAPI returned status {e.response.status_code}",
            ) from e

        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise ExternalServiceException(
                service_name="SWAPI",
                message=f"Failed to connect to SWAPI: {str(e)}",
            ) from e


def get_swapi_client() -> SwapiClient:
    """
    Returns a singleton SwapiClient instance.

    This ensures all parts of the application share the same
    connection pool for efficient resource usage.

    Returns:
        The singleton SwapiClient instance.
    """
    global _swapi_client

    if _swapi_client is None:
        _swapi_client = SwapiClient()

    return _swapi_client
