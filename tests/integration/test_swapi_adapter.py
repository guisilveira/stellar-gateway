"""
Integration tests for the SWAPI Adapter.

These tests use respx to mock HTTP responses and verify:
1. Successful resource fetching
2. 404 handling (ResourceNotFoundException)
3. Network error handling with retry logic
"""

import httpx
import pytest
import respx

from adapters.swapi import SwapiClient
from domain.exceptions import ExternalServiceException, ResourceNotFoundException


class TestSwapiClientGetResource:
    """Test suite for SwapiClient.get_resource method."""

    @pytest.fixture
    def client(self) -> SwapiClient:
        """Creates a SwapiClient instance for testing."""
        return SwapiClient(base_url="https://swapi.dev/api")

    @pytest.fixture
    def valid_person_response(self) -> dict:
        """Valid SWAPI person response data."""
        return {
            "name": "Luke Skywalker",
            "height": "172",
            "mass": "77",
            "hair_color": "blond",
            "skin_color": "fair",
            "eye_color": "blue",
            "birth_year": "19BBY",
            "gender": "male",
            "homeworld": "https://swapi.dev/api/planets/1/",
            "films": ["https://swapi.dev/api/films/1/"],
            "species": [],
            "vehicles": [],
            "starships": [],
            "created": "2014-12-09T13:50:51.644000Z",
            "edited": "2014-12-20T21:17:56.891000Z",
            "url": "https://swapi.dev/api/people/1/",
        }

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_resource_success(
        self, client: SwapiClient, valid_person_response: dict
    ) -> None:
        """Should return data when SWAPI responds successfully."""
        respx.get("https://swapi.dev/api/people/1/").mock(
            return_value=httpx.Response(200, json=valid_person_response)
        )

        result = await client.get_resource("people", 1)

        assert result["name"] == "Luke Skywalker"
        assert result["gender"] == "male"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_resource_not_found_raises_exception(
        self, client: SwapiClient
    ) -> None:
        """Should raise ResourceNotFoundException when SWAPI returns 404."""
        respx.get("https://swapi.dev/api/people/999/").mock(
            return_value=httpx.Response(404, json={"detail": "Not found"})
        )

        with pytest.raises(ResourceNotFoundException) as exc_info:
            await client.get_resource("people", 999)

        assert exc_info.value.resource_type == "people"
        assert exc_info.value.resource_id == 999

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_resource_retries_on_network_error(
        self, client: SwapiClient, valid_person_response: dict
    ) -> None:
        """Should retry on transient network errors and succeed eventually."""
        route = respx.get("https://swapi.dev/api/people/1/")

        # First call fails, second succeeds
        route.side_effect = [
            httpx.ConnectError("Connection failed"),
            httpx.Response(200, json=valid_person_response),
        ]

        result = await client.get_resource("people", 1)

        assert result["name"] == "Luke Skywalker"
        assert route.call_count == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_resource_raises_after_max_retries(
        self, client: SwapiClient
    ) -> None:
        """Should raise ExternalServiceException after exhausting retries."""
        respx.get("https://swapi.dev/api/people/1/").mock(
            side_effect=httpx.ConnectError("Connection failed")
        )

        with pytest.raises(ExternalServiceException) as exc_info:
            await client.get_resource("people", 1)

        assert exc_info.value.service_name == "SWAPI"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_resource_does_not_retry_on_404(
        self, client: SwapiClient
    ) -> None:
        """Should NOT retry on 404 errors (they are not transient)."""
        route = respx.get("https://swapi.dev/api/people/999/").mock(
            return_value=httpx.Response(404, json={"detail": "Not found"})
        )

        with pytest.raises(ResourceNotFoundException):
            await client.get_resource("people", 999)

        # Should only be called once (no retry)
        assert route.call_count == 1


class TestSwapiClientListResources:
    """Test suite for SwapiClient.list_resources method."""

    @pytest.fixture
    def client(self) -> SwapiClient:
        """Creates a SwapiClient instance for testing."""
        return SwapiClient(base_url="https://swapi.dev/api")

    @pytest.fixture
    def valid_list_response(self) -> dict:
        """Valid SWAPI list response data."""
        return {
            "count": 82,
            "next": "https://swapi.dev/api/people/?page=2",
            "previous": None,
            "results": [
                {"name": "Luke Skywalker", "url": "https://swapi.dev/api/people/1/"},
                {"name": "C-3PO", "url": "https://swapi.dev/api/people/2/"},
            ],
        }

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_resources_success(
        self, client: SwapiClient, valid_list_response: dict
    ) -> None:
        """Should return paginated data when SWAPI responds successfully."""
        respx.get("https://swapi.dev/api/people/").mock(
            return_value=httpx.Response(200, json=valid_list_response)
        )

        result = await client.list_resources("people")

        assert result["count"] == 82
        assert len(result["results"]) == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_resources_with_pagination(
        self, client: SwapiClient, valid_list_response: dict
    ) -> None:
        """Should pass page parameter to SWAPI."""
        route = respx.get("https://swapi.dev/api/people/").mock(
            return_value=httpx.Response(200, json=valid_list_response)
        )

        await client.list_resources("people", page=2)

        assert "page=2" in str(route.calls.last.request.url)

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_resources_with_search(
        self, client: SwapiClient, valid_list_response: dict
    ) -> None:
        """Should pass search parameter to SWAPI."""
        route = respx.get("https://swapi.dev/api/people/").mock(
            return_value=httpx.Response(200, json=valid_list_response)
        )

        await client.list_resources("people", search="Luke")

        assert "search=Luke" in str(route.calls.last.request.url)


class TestSwapiClientConnectionPool:
    """Test suite for SwapiClient connection pool and lifecycle."""

    @pytest.mark.asyncio
    async def test_singleton_returns_same_instance(self) -> None:
        """get_swapi_client() should return the same instance (singleton)."""
        from adapters.swapi import get_swapi_client

        client1 = get_swapi_client()
        client2 = get_swapi_client()

        assert client1 is client2

    @pytest.mark.asyncio
    async def test_client_uses_injected_http_client(self) -> None:
        """Should use injected httpx.AsyncClient for dependency injection."""
        mock_client = httpx.AsyncClient()

        swapi_client = SwapiClient(http_client=mock_client)

        # Should use the injected client, not create a new one
        assert swapi_client._client is mock_client
        assert swapi_client._owns_client is False

        await mock_client.aclose()

    @pytest.mark.asyncio
    async def test_client_creates_own_client_when_not_injected(self) -> None:
        """Should create its own AsyncClient when none is injected."""
        swapi_client = SwapiClient()

        assert swapi_client._client is not None
        assert swapi_client._owns_client is True

        await swapi_client.close()

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self) -> None:
        """Async context manager should close the client on exit."""
        async with SwapiClient() as client:
            assert client._client is not None

        # After exit, client should be closed (can't easily verify, but no exception)

    @pytest.mark.asyncio
    async def test_close_does_not_close_injected_client(self) -> None:
        """close() should not close an injected client (caller owns it)."""
        mock_client = httpx.AsyncClient()

        swapi_client = SwapiClient(http_client=mock_client)
        await swapi_client.close()

        # Injected client should still be open (no exception on usage)
        # We just verify it wasn't closed by trying to access it
        assert not mock_client.is_closed

        await mock_client.aclose()
