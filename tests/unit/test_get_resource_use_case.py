"""
Unit tests for the GetResourceUseCase.

These tests verify the Cache-Aside pattern implementation:
1. Cache hit: Return cached data without calling SWAPI
2. Cache miss: Fetch from SWAPI, cache the result, and return
"""

from unittest.mock import AsyncMock

import pytest

from use_cases.get_resource import GetResourceUseCase


class TestGetResourceUseCaseCacheHit:
    """Test suite for cache hit scenarios."""

    @pytest.fixture
    def mock_swapi(self) -> AsyncMock:
        """Creates a mock SwapiInterface."""
        return AsyncMock()

    @pytest.fixture
    def mock_cache(self) -> AsyncMock:
        """Creates a mock CacheInterface."""
        return AsyncMock()

    @pytest.fixture
    def use_case(
        self, mock_swapi: AsyncMock, mock_cache: AsyncMock
    ) -> GetResourceUseCase:
        """Creates a GetResourceUseCase with mocked dependencies."""
        return GetResourceUseCase(swapi=mock_swapi, cache=mock_cache)

    @pytest.mark.asyncio
    async def test_returns_cached_data_when_cache_hit(
        self,
        use_case: GetResourceUseCase,
        mock_swapi: AsyncMock,
        mock_cache: AsyncMock,
    ) -> None:
        """Should return cached data without calling SWAPI when cache hit."""
        cached_person = {
            "name": "Luke Skywalker",
            "height": "172",
            "url": "https://swapi.dev/api/people/1/",
        }
        mock_cache.get.return_value = cached_person

        result = await use_case.execute("people", 1)

        assert result == cached_person
        mock_cache.get.assert_called_once_with("swapi:people:1")
        mock_swapi.get_resource.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_call_cache_set_on_cache_hit(
        self,
        use_case: GetResourceUseCase,
        mock_swapi: AsyncMock,
        mock_cache: AsyncMock,
    ) -> None:
        """Should not call cache.set when data is already cached."""
        mock_cache.get.return_value = {"name": "Cached Data"}

        await use_case.execute("planets", 1)

        mock_cache.set.assert_not_called()


class TestGetResourceUseCaseCacheMiss:
    """Test suite for cache miss scenarios."""

    @pytest.fixture
    def mock_swapi(self) -> AsyncMock:
        """Creates a mock SwapiInterface."""
        return AsyncMock()

    @pytest.fixture
    def mock_cache(self) -> AsyncMock:
        """Creates a mock CacheInterface."""
        return AsyncMock()

    @pytest.fixture
    def use_case(
        self, mock_swapi: AsyncMock, mock_cache: AsyncMock
    ) -> GetResourceUseCase:
        """Creates a GetResourceUseCase with mocked dependencies."""
        return GetResourceUseCase(swapi=mock_swapi, cache=mock_cache)

    @pytest.fixture
    def swapi_person_response(self) -> dict:
        """Valid SWAPI person response."""
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

    @pytest.mark.asyncio
    async def test_fetches_from_swapi_when_cache_miss(
        self,
        use_case: GetResourceUseCase,
        mock_swapi: AsyncMock,
        mock_cache: AsyncMock,
        swapi_person_response: dict,
    ) -> None:
        """Should fetch from SWAPI when cache returns None."""
        mock_cache.get.return_value = None
        mock_swapi.get_resource.return_value = swapi_person_response

        result = await use_case.execute("people", 1, enrich=False)

        assert result == swapi_person_response
        mock_swapi.get_resource.assert_called_once_with("people", 1)

    @pytest.mark.asyncio
    async def test_caches_swapi_response_on_cache_miss(
        self,
        use_case: GetResourceUseCase,
        mock_swapi: AsyncMock,
        mock_cache: AsyncMock,
        swapi_person_response: dict,
    ) -> None:
        """Should cache the SWAPI response after fetching."""
        mock_cache.get.return_value = None
        mock_swapi.get_resource.return_value = swapi_person_response

        await use_case.execute("people", 1, enrich=False)

        mock_cache.set.assert_called_once()
        call_args = mock_cache.set.call_args
        assert call_args[0][0] == "swapi:people:1"  # key
        assert call_args[0][1] == swapi_person_response  # value

    @pytest.mark.asyncio
    async def test_cache_key_format_for_different_resources(
        self,
        use_case: GetResourceUseCase,
        mock_swapi: AsyncMock,
        mock_cache: AsyncMock,
    ) -> None:
        """Should generate correct cache keys for different resource types."""
        mock_cache.get.return_value = None
        mock_swapi.get_resource.return_value = {"name": "Test"}

        # Test planets
        await use_case.execute("planets", 5)
        mock_cache.get.assert_called_with("swapi:planets:5")

        # Test starships
        await use_case.execute("starships", 10)
        mock_cache.get.assert_called_with("swapi:starships:10")

    @pytest.mark.asyncio
    async def test_sets_cache_with_ttl(
        self,
        mock_swapi: AsyncMock,
        mock_cache: AsyncMock,
    ) -> None:
        """Should set cache with configurable TTL."""
        use_case = GetResourceUseCase(
            swapi=mock_swapi,
            cache=mock_cache,
            cache_ttl_seconds=600,
        )
        mock_cache.get.return_value = None
        mock_swapi.get_resource.return_value = {"name": "Test"}

        await use_case.execute("people", 1)

        call_kwargs = mock_cache.set.call_args[1]
        assert call_kwargs.get("ttl_seconds") == 600


class TestGetResourceUseCaseCacheKeyGeneration:
    """Test suite for cache key generation."""

    @pytest.fixture
    def mock_swapi(self) -> AsyncMock:
        """Creates a mock SwapiInterface."""
        return AsyncMock()

    @pytest.fixture
    def mock_cache(self) -> AsyncMock:
        """Creates a mock CacheInterface."""
        return AsyncMock()

    @pytest.fixture
    def use_case(
        self, mock_swapi: AsyncMock, mock_cache: AsyncMock
    ) -> GetResourceUseCase:
        """Creates a GetResourceUseCase with mocked dependencies."""
        return GetResourceUseCase(swapi=mock_swapi, cache=mock_cache)

    @pytest.mark.asyncio
    async def test_generate_cache_key_returns_correct_format(
        self,
        use_case: GetResourceUseCase,
    ) -> None:
        """Should generate cache key in format 'swapi:{resource_type}:{resource_id}'."""
        key = use_case._generate_cache_key("people", 1)
        assert key == "swapi:people:1"

        key = use_case._generate_cache_key("planets", 42)
        assert key == "swapi:planets:42"

        key = use_case._generate_cache_key("starships", 100)
        assert key == "swapi:starships:100"


class TestGetResourceUseCaseEnrichment:
    """Test suite for data enrichment (hydration) functionality."""

    @pytest.fixture
    def mock_swapi(self) -> AsyncMock:
        """Creates a mock SwapiInterface."""
        return AsyncMock()

    @pytest.fixture
    def mock_cache(self) -> AsyncMock:
        """Creates a mock CacheInterface."""
        return AsyncMock()

    @pytest.fixture
    def use_case(
        self, mock_swapi: AsyncMock, mock_cache: AsyncMock
    ) -> GetResourceUseCase:
        """Creates a GetResourceUseCase with mocked dependencies."""
        return GetResourceUseCase(swapi=mock_swapi, cache=mock_cache)

    @pytest.fixture
    def swapi_person_with_homeworld(self) -> dict:
        """Person response with homeworld URL."""
        return {
            "name": "Luke Skywalker",
            "height": "172",
            "homeworld": "https://swapi.dev/api/planets/1/",
            "films": [],
            "species": [],
            "vehicles": [],
            "starships": [],
            "url": "https://swapi.dev/api/people/1/",
        }

    @pytest.fixture
    def swapi_planet_tatooine(self) -> dict:
        """Tatooine planet response."""
        return {
            "name": "Tatooine",
            "climate": "arid",
            "url": "https://swapi.dev/api/planets/1/",
        }

    @pytest.mark.asyncio
    async def test_enriches_homeworld_url_with_planet_name(
        self,
        use_case: GetResourceUseCase,
        mock_swapi: AsyncMock,
        mock_cache: AsyncMock,
        swapi_person_with_homeworld: dict,
        swapi_planet_tatooine: dict,
    ) -> None:
        """Should replace homeworld URL with planet name."""
        # First call: person (cache miss)
        # Second call: planet for enrichment (cache miss)
        mock_cache.get.return_value = None
        mock_swapi.get_resource.side_effect = [
            swapi_person_with_homeworld,
            swapi_planet_tatooine,
        ]

        result = await use_case.execute("people", 1)

        assert result["homeworld"] == "Tatooine"

    @pytest.mark.asyncio
    async def test_enriches_films_list_with_titles(
        self,
        use_case: GetResourceUseCase,
        mock_swapi: AsyncMock,
        mock_cache: AsyncMock,
    ) -> None:
        """Should replace films URLs with film titles."""
        person_with_films = {
            "name": "Luke Skywalker",
            "homeworld": "https://swapi.dev/api/planets/1/",
            "films": [
                "https://swapi.dev/api/films/1/",
                "https://swapi.dev/api/films/2/",
            ],
            "species": [],
            "vehicles": [],
            "starships": [],
            "url": "https://swapi.dev/api/people/1/",
        }
        planet = {"name": "Tatooine", "url": "https://swapi.dev/api/planets/1/"}
        film1 = {"title": "A New Hope", "url": "https://swapi.dev/api/films/1/"}
        film2 = {"title": "The Empire Strikes Back", "url": "https://swapi.dev/api/films/2/"}

        mock_cache.get.return_value = None
        mock_swapi.get_resource.side_effect = [
            person_with_films,
            planet,
            film1,
            film2,
        ]

        result = await use_case.execute("people", 1)

        assert result["films"] == ["A New Hope", "The Empire Strikes Back"]

    @pytest.mark.asyncio
    async def test_enrichment_uses_cache_for_sub_resources(
        self,
        use_case: GetResourceUseCase,
        mock_swapi: AsyncMock,
        mock_cache: AsyncMock,
        swapi_person_with_homeworld: dict,
        swapi_planet_tatooine: dict,
    ) -> None:
        """Should use cache when fetching sub-resources for enrichment."""
        # Person: cache miss, Planet: cache hit
        mock_cache.get.side_effect = [
            None,  # Person cache miss
            swapi_planet_tatooine,  # Planet cache hit
        ]
        mock_swapi.get_resource.return_value = swapi_person_with_homeworld

        result = await use_case.execute("people", 1)

        # Planet should come from cache, not SWAPI
        assert result["homeworld"] == "Tatooine"
        # SWAPI should only be called once (for person)
        assert mock_swapi.get_resource.call_count == 1

    @pytest.mark.asyncio
    async def test_enrichment_preserves_url_on_fetch_failure(
        self,
        use_case: GetResourceUseCase,
        mock_swapi: AsyncMock,
        mock_cache: AsyncMock,
        swapi_person_with_homeworld: dict,
    ) -> None:
        """Should preserve original URL if enrichment fetch fails."""
        mock_cache.get.return_value = None
        mock_swapi.get_resource.side_effect = [
            swapi_person_with_homeworld,
            Exception("Network error"),  # Planet fetch fails
        ]

        result = await use_case.execute("people", 1)

        # Should keep original URL when enrichment fails
        assert result["homeworld"] == "https://swapi.dev/api/planets/1/"

    @pytest.mark.asyncio
    async def test_enrichment_disabled_with_enrich_false(
        self,
        use_case: GetResourceUseCase,
        mock_swapi: AsyncMock,
        mock_cache: AsyncMock,
        swapi_person_with_homeworld: dict,
    ) -> None:
        """Should skip enrichment when enrich=False."""
        mock_cache.get.return_value = None
        mock_swapi.get_resource.return_value = swapi_person_with_homeworld

        result = await use_case.execute("people", 1, enrich=False)

        # Homeworld should remain as URL
        assert result["homeworld"] == "https://swapi.dev/api/planets/1/"
        # SWAPI should only be called once (no enrichment calls)
        assert mock_swapi.get_resource.call_count == 1

    @pytest.mark.asyncio
    async def test_enrichment_handles_empty_lists(
        self,
        use_case: GetResourceUseCase,
        mock_swapi: AsyncMock,
        mock_cache: AsyncMock,
    ) -> None:
        """Should handle empty lists gracefully."""
        person_with_empty_lists = {
            "name": "Luke Skywalker",
            "homeworld": "https://swapi.dev/api/planets/1/",
            "films": [],
            "species": [],
            "vehicles": [],
            "starships": [],
            "url": "https://swapi.dev/api/people/1/",
        }
        planet = {"name": "Tatooine", "url": "https://swapi.dev/api/planets/1/"}

        mock_cache.get.return_value = None
        mock_swapi.get_resource.side_effect = [person_with_empty_lists, planet]

        result = await use_case.execute("people", 1)

        assert result["films"] == []
        assert result["species"] == []

    @pytest.mark.asyncio
    async def test_enrichment_fetches_in_parallel(
        self,
        use_case: GetResourceUseCase,
        mock_swapi: AsyncMock,
        mock_cache: AsyncMock,
    ) -> None:
        """Should fetch multiple enrichment resources in parallel."""
        person = {
            "name": "Luke Skywalker",
            "homeworld": "https://swapi.dev/api/planets/1/",
            "films": [
                "https://swapi.dev/api/films/1/",
                "https://swapi.dev/api/films/2/",
            ],
            "species": ["https://swapi.dev/api/species/1/"],
            "vehicles": [],
            "starships": [],
            "url": "https://swapi.dev/api/people/1/",
        }

        mock_cache.get.return_value = None
        mock_swapi.get_resource.side_effect = [
            person,
            {"name": "Tatooine"},  # homeworld
            {"title": "A New Hope"},  # film 1
            {"title": "Empire Strikes Back"},  # film 2
            {"name": "Human"},  # species
        ]

        result = await use_case.execute("people", 1)

        assert result["homeworld"] == "Tatooine"
        assert result["films"] == ["A New Hope", "Empire Strikes Back"]
        assert result["species"] == ["Human"]
