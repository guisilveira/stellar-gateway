"""
Unit tests for ListResourcesUseCase.

Tests the listing flow with pagination, filtering, and sorting.
Following TDD methodology - tests written first.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.exceptions import ExternalServiceException
from use_cases.list_resources import ListResourcesUseCase


@pytest.fixture
def mock_swapi() -> MagicMock:
    """Creates a mock SWAPI client."""
    return MagicMock()


@pytest.fixture
def mock_cache() -> MagicMock:
    """Creates a mock cache client with async methods."""
    cache = MagicMock()
    cache.get = AsyncMock(return_value=None)  # Default: cache miss
    cache.set = AsyncMock()
    return cache


@pytest.fixture
def use_case(mock_swapi: MagicMock, mock_cache: MagicMock) -> ListResourcesUseCase:
    """Creates a ListResourcesUseCase with mocked dependencies."""
    return ListResourcesUseCase(swapi=mock_swapi, cache=mock_cache)


class TestListResourcesUseCase:
    """Tests for the ListResourcesUseCase class."""

    # ==================== Basic Listing ====================

    @pytest.mark.asyncio
    async def test_list_resources_returns_paginated_results(
        self,
        use_case: ListResourcesUseCase,
        mock_swapi: MagicMock,
    ) -> None:
        """Should return paginated results from SWAPI."""
        mock_swapi.list_resources = AsyncMock(
            return_value={
                "count": 82,
                "next": "https://swapi.dev/api/people/?page=2",
                "previous": None,
                "results": [
                    {"name": "Luke Skywalker", "height": "172"},
                    {"name": "C-3PO", "height": "167"},
                ],
            }
        )

        result = await use_case.execute(resource_type="people")

        mock_swapi.list_resources.assert_called_once_with(
            resource_type="people",
            page=None,
            search=None,
        )
        assert result["count"] == 82
        assert len(result["results"]) == 2
        assert result["next"] is not None

    @pytest.mark.asyncio
    async def test_list_resources_with_page_parameter(
        self,
        use_case: ListResourcesUseCase,
        mock_swapi: MagicMock,
    ) -> None:
        """Should pass page parameter to SWAPI."""
        mock_swapi.list_resources = AsyncMock(
            return_value={
                "count": 82,
                "next": "https://swapi.dev/api/people/?page=3",
                "previous": "https://swapi.dev/api/people/?page=1",
                "results": [
                    {"name": "Anakin Skywalker", "height": "188"},
                ],
            }
        )

        result = await use_case.execute(resource_type="people", page=2)

        mock_swapi.list_resources.assert_called_once_with(
            resource_type="people",
            page=2,
            search=None,
        )
        assert result["previous"] is not None

    # ==================== Search/Filter ====================

    @pytest.mark.asyncio
    async def test_list_resources_with_search_filter(
        self,
        use_case: ListResourcesUseCase,
        mock_swapi: MagicMock,
    ) -> None:
        """Should map name filter to SWAPI search parameter."""
        mock_swapi.list_resources = AsyncMock(
            return_value={
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {"name": "Luke Skywalker", "height": "172"},
                ],
            }
        )

        result = await use_case.execute(resource_type="people", search="Luke")

        mock_swapi.list_resources.assert_called_once_with(
            resource_type="people",
            page=None,
            search="Luke",
        )
        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_list_resources_with_page_and_search(
        self,
        use_case: ListResourcesUseCase,
        mock_swapi: MagicMock,
    ) -> None:
        """Should pass both page and search parameters."""
        mock_swapi.list_resources = AsyncMock(
            return_value={
                "count": 15,
                "next": None,
                "previous": "https://swapi.dev/api/planets/?search=ta&page=1",
                "results": [
                    {"name": "Tatooine", "climate": "arid"},
                ],
            }
        )

        await use_case.execute(resource_type="planets", page=2, search="ta")

        mock_swapi.list_resources.assert_called_once_with(
            resource_type="planets",
            page=2,
            search="ta",
        )

    # ==================== Sorting ====================

    @pytest.mark.asyncio
    async def test_list_resources_with_sort_by_name_ascending(
        self,
        use_case: ListResourcesUseCase,
        mock_swapi: MagicMock,
    ) -> None:
        """Should sort results by name in ascending order."""
        mock_swapi.list_resources = AsyncMock(
            return_value={
                "count": 3,
                "next": None,
                "previous": None,
                "results": [
                    {"name": "Luke Skywalker", "height": "172"},
                    {"name": "Anakin Skywalker", "height": "188"},
                    {"name": "C-3PO", "height": "167"},
                ],
            }
        )

        result = await use_case.execute(resource_type="people", sort_by="name")

        # Should be sorted alphabetically
        assert result["results"][0]["name"] == "Anakin Skywalker"
        assert result["results"][1]["name"] == "C-3PO"
        assert result["results"][2]["name"] == "Luke Skywalker"

    @pytest.mark.asyncio
    async def test_list_resources_with_sort_by_name_descending(
        self,
        use_case: ListResourcesUseCase,
        mock_swapi: MagicMock,
    ) -> None:
        """Should sort results by name in descending order."""
        mock_swapi.list_resources = AsyncMock(
            return_value={
                "count": 3,
                "next": None,
                "previous": None,
                "results": [
                    {"name": "Luke Skywalker", "height": "172"},
                    {"name": "Anakin Skywalker", "height": "188"},
                    {"name": "C-3PO", "height": "167"},
                ],
            }
        )

        result = await use_case.execute(
            resource_type="people", sort_by="name", sort_order="desc"
        )

        # Should be sorted in reverse alphabetical order
        assert result["results"][0]["name"] == "Luke Skywalker"
        assert result["results"][1]["name"] == "C-3PO"
        assert result["results"][2]["name"] == "Anakin Skywalker"

    @pytest.mark.asyncio
    async def test_list_resources_with_sort_by_height(
        self,
        use_case: ListResourcesUseCase,
        mock_swapi: MagicMock,
    ) -> None:
        """Should sort results by numeric field (height)."""
        mock_swapi.list_resources = AsyncMock(
            return_value={
                "count": 3,
                "next": None,
                "previous": None,
                "results": [
                    {"name": "Luke Skywalker", "height": "172"},
                    {"name": "Anakin Skywalker", "height": "188"},
                    {"name": "C-3PO", "height": "167"},
                ],
            }
        )

        result = await use_case.execute(resource_type="people", sort_by="height")

        # Should be sorted by height numerically
        assert result["results"][0]["name"] == "C-3PO"  # 167
        assert result["results"][1]["name"] == "Luke Skywalker"  # 172
        assert result["results"][2]["name"] == "Anakin Skywalker"  # 188

    @pytest.mark.asyncio
    async def test_list_resources_sort_handles_unknown_values(
        self,
        use_case: ListResourcesUseCase,
        mock_swapi: MagicMock,
    ) -> None:
        """Should handle 'unknown' values when sorting."""
        mock_swapi.list_resources = AsyncMock(
            return_value={
                "count": 3,
                "next": None,
                "previous": None,
                "results": [
                    {"name": "Luke Skywalker", "height": "172"},
                    {"name": "Unknown Person", "height": "unknown"},
                    {"name": "C-3PO", "height": "167"},
                ],
            }
        )

        result = await use_case.execute(resource_type="people", sort_by="height")

        # 'unknown' should be sorted to the end
        assert result["results"][0]["name"] == "C-3PO"
        assert result["results"][1]["name"] == "Luke Skywalker"
        assert result["results"][2]["name"] == "Unknown Person"

    @pytest.mark.asyncio
    async def test_list_resources_sort_handles_missing_field(
        self,
        use_case: ListResourcesUseCase,
        mock_swapi: MagicMock,
    ) -> None:
        """Should handle missing sort field gracefully."""
        mock_swapi.list_resources = AsyncMock(
            return_value={
                "count": 2,
                "next": None,
                "previous": None,
                "results": [
                    {"name": "Luke Skywalker", "height": "172"},
                    {"name": "C-3PO"},  # Missing height
                ],
            }
        )

        result = await use_case.execute(resource_type="people", sort_by="height")

        # Missing field should be sorted to the end
        assert result["results"][0]["name"] == "Luke Skywalker"
        assert result["results"][1]["name"] == "C-3PO"

    # ==================== Error Handling ====================

    @pytest.mark.asyncio
    async def test_list_resources_propagates_external_service_error(
        self,
        use_case: ListResourcesUseCase,
        mock_swapi: MagicMock,
    ) -> None:
        """Should propagate ExternalServiceException from SWAPI."""
        mock_swapi.list_resources = AsyncMock(
            side_effect=ExternalServiceException(
                service_name="SWAPI",
                status_code=500,
                message="SWAPI returned status 500",
            )
        )

        with pytest.raises(ExternalServiceException) as exc_info:
            await use_case.execute(resource_type="people")

        assert exc_info.value.service_name == "SWAPI"
        assert exc_info.value.status_code == 500

    # ==================== Empty Results ====================

    @pytest.mark.asyncio
    async def test_list_resources_returns_empty_results(
        self,
        use_case: ListResourcesUseCase,
        mock_swapi: MagicMock,
    ) -> None:
        """Should return empty results for no matches."""
        mock_swapi.list_resources = AsyncMock(
            return_value={
                "count": 0,
                "next": None,
                "previous": None,
                "results": [],
            }
        )

        result = await use_case.execute(resource_type="people", search="nonexistent")

        assert result["count"] == 0
        assert result["results"] == []

    # ==================== Sort by Title (for Films) ====================

    @pytest.mark.asyncio
    async def test_list_resources_sort_by_title_for_films(
        self,
        use_case: ListResourcesUseCase,
        mock_swapi: MagicMock,
    ) -> None:
        """Should sort films by title."""
        mock_swapi.list_resources = AsyncMock(
            return_value={
                "count": 3,
                "next": None,
                "previous": None,
                "results": [
                    {"title": "Return of the Jedi", "episode_id": 6},
                    {"title": "A New Hope", "episode_id": 4},
                    {"title": "The Empire Strikes Back", "episode_id": 5},
                ],
            }
        )

        result = await use_case.execute(resource_type="films", sort_by="title")

        assert result["results"][0]["title"] == "A New Hope"
        assert result["results"][1]["title"] == "Return of the Jedi"
        assert result["results"][2]["title"] == "The Empire Strikes Back"

    @pytest.mark.asyncio
    async def test_list_resources_sort_by_episode_id(
        self,
        use_case: ListResourcesUseCase,
        mock_swapi: MagicMock,
    ) -> None:
        """Should sort films by episode_id numerically."""
        mock_swapi.list_resources = AsyncMock(
            return_value={
                "count": 3,
                "next": None,
                "previous": None,
                "results": [
                    {"title": "Return of the Jedi", "episode_id": 6},
                    {"title": "A New Hope", "episode_id": 4},
                    {"title": "The Empire Strikes Back", "episode_id": 5},
                ],
            }
        )

        result = await use_case.execute(resource_type="films", sort_by="episode_id")

        assert result["results"][0]["title"] == "A New Hope"  # Episode 4
        assert result["results"][1]["title"] == "The Empire Strikes Back"  # Episode 5
        assert result["results"][2]["title"] == "Return of the Jedi"  # Episode 6


class TestListResourcesUseCaseCacheKey:
    """Tests for cache key generation."""

    @pytest.mark.asyncio
    async def test_generates_correct_cache_key_without_params(
        self,
        mock_swapi: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Should generate cache key for basic listing."""
        use_case = ListResourcesUseCase(swapi=mock_swapi, cache=mock_cache)

        key = use_case._generate_cache_key("people", None, None)

        assert key == "swapi:people:list"

    @pytest.mark.asyncio
    async def test_generates_correct_cache_key_with_page(
        self,
        mock_swapi: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Should include page in cache key."""
        use_case = ListResourcesUseCase(swapi=mock_swapi, cache=mock_cache)

        key = use_case._generate_cache_key("people", 2, None)

        assert key == "swapi:people:list:page=2"

    @pytest.mark.asyncio
    async def test_generates_correct_cache_key_with_search(
        self,
        mock_swapi: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Should include search in cache key."""
        use_case = ListResourcesUseCase(swapi=mock_swapi, cache=mock_cache)

        key = use_case._generate_cache_key("people", None, "luke")

        assert key == "swapi:people:list:search=luke"

    @pytest.mark.asyncio
    async def test_generates_correct_cache_key_with_all_params(
        self,
        mock_swapi: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Should include all params in cache key."""
        use_case = ListResourcesUseCase(swapi=mock_swapi, cache=mock_cache)

        key = use_case._generate_cache_key("planets", 3, "tatooine")

        assert key == "swapi:planets:list:page=3:search=tatooine"


class TestListResourcesUseCacheBehavior:
    """Tests for Cache-Aside pattern in listing."""

    @pytest.mark.asyncio
    async def test_returns_cached_data_on_cache_hit(
        self,
        mock_swapi: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Should return cached data without calling SWAPI on cache hit."""
        cached_data = {
            "count": 1,
            "next": None,
            "previous": None,
            "results": [{"name": "Cached Luke", "height": "172"}],
        }
        mock_cache.get = AsyncMock(return_value=cached_data)
        mock_swapi.list_resources = AsyncMock()

        use_case = ListResourcesUseCase(swapi=mock_swapi, cache=mock_cache)
        result = await use_case.execute(resource_type="people")

        mock_cache.get.assert_called_once()
        mock_swapi.list_resources.assert_not_called()
        assert result["results"][0]["name"] == "Cached Luke"

    @pytest.mark.asyncio
    async def test_fetches_from_swapi_on_cache_miss(
        self,
        mock_swapi: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Should fetch from SWAPI and cache result on cache miss."""
        swapi_data = {
            "count": 1,
            "next": None,
            "previous": None,
            "results": [{"name": "Luke Skywalker", "height": "172"}],
        }
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_swapi.list_resources = AsyncMock(return_value=swapi_data)

        use_case = ListResourcesUseCase(swapi=mock_swapi, cache=mock_cache)
        result = await use_case.execute(resource_type="people")

        mock_cache.get.assert_called_once()
        mock_swapi.list_resources.assert_called_once()
        mock_cache.set.assert_called_once()
        assert result["results"][0]["name"] == "Luke Skywalker"

    @pytest.mark.asyncio
    async def test_sorting_applied_to_cached_data(
        self,
        mock_swapi: MagicMock,
        mock_cache: MagicMock,
    ) -> None:
        """Should apply sorting to cached data."""
        cached_data = {
            "count": 2,
            "next": None,
            "previous": None,
            "results": [
                {"name": "Zuckuss", "height": "180"},
                {"name": "Ackbar", "height": "170"},
            ],
        }
        mock_cache.get = AsyncMock(return_value=cached_data)

        use_case = ListResourcesUseCase(swapi=mock_swapi, cache=mock_cache)
        result = await use_case.execute(resource_type="people", sort_by="name")

        # Sorting should still be applied to cached data
        assert result["results"][0]["name"] == "Ackbar"
        assert result["results"][1]["name"] == "Zuckuss"
