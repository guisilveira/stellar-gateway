"""
ListResources Use Case.

This module implements listing resources with pagination, filtering, and sorting.
Uses Cache-Aside pattern for performance.
"""

from typing import Any, Literal

from interfaces.cache_interface import CacheInterface
from interfaces.swapi_interface import SwapiInterface

# Default cache TTL: 5 minutes
DEFAULT_CACHE_TTL_SECONDS = 300

# Sort order type
SortOrder = Literal["asc", "desc"]


class ListResourcesUseCase:
    """
    Use case for listing resources with pagination, filtering, and sorting.

    This use case implements the following flow:
    1. Check if the listing exists in cache (with params as key)
    2. If cache hit: return cached data
    3. If cache miss: fetch from SWAPI, cache the result, return data
    4. Apply sorting in memory (since SWAPI doesn't support sorting)

    Attributes:
        _swapi: The SWAPI client interface.
        _cache: The cache client interface.
        _cache_ttl_seconds: TTL for cached entries.
    """

    def __init__(
        self,
        swapi: SwapiInterface,
        cache: CacheInterface,
        cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
    ) -> None:
        """
        Initializes the ListResourcesUseCase.

        Args:
            swapi: The SWAPI client implementing SwapiInterface.
            cache: The cache client implementing CacheInterface.
            cache_ttl_seconds: Time-to-live for cached entries (default: 300s).
        """
        self._swapi = swapi
        self._cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds

    def _generate_cache_key(
        self,
        resource_type: str,
        page: int | None,
        search: str | None,
    ) -> str:
        """
        Generates a cache key for a resource listing.

        Args:
            resource_type: The type of resource (e.g., "people", "planets").
            page: Optional page number.
            search: Optional search query.

        Returns:
            A cache key in format 'swapi:{resource_type}:list[:page=N][:search=X]'.
        """
        key = f"swapi:{resource_type}:list"

        if page is not None:
            key += f":page={page}"
        if search is not None:
            key += f":search={search}"

        return key

    def _get_sort_key(self, item: dict[str, Any], field: str) -> Any:
        """
        Extracts a sort key from an item, handling numeric and unknown values.

        Args:
            item: The resource dictionary.
            field: The field to sort by.

        Returns:
            A tuple of (is_valid, value) for sorting:
            - is_valid: False puts 'unknown' and missing fields at the end
            - value: The actual value for comparison
        """
        value = item.get(field)

        # Missing field - sort to end
        if value is None:
            return (1, "")

        # Handle 'unknown' values - sort to end
        if isinstance(value, str) and value.lower() == "unknown":
            return (1, "")

        # Try numeric conversion for fields like height, mass, etc.
        if isinstance(value, str):
            try:
                return (0, float(value))
            except ValueError:
                # String value - sort alphabetically
                return (0, value.lower())

        # Already numeric (e.g., episode_id)
        if isinstance(value, (int, float)):
            return (0, value)

        return (0, str(value).lower())

    def _sort_results(
        self,
        results: list[dict[str, Any]],
        sort_by: str,
        sort_order: SortOrder = "asc",
    ) -> list[dict[str, Any]]:
        """
        Sorts results in memory by the specified field.

        Args:
            results: The list of resource dictionaries.
            sort_by: The field to sort by.
            sort_order: "asc" for ascending, "desc" for descending.

        Returns:
            A new sorted list of results.
        """
        reverse = sort_order == "desc"
        return sorted(
            results,
            key=lambda item: self._get_sort_key(item, sort_by),
            reverse=reverse,
        )

    async def execute(
        self,
        resource_type: str,
        page: int | None = None,
        search: str | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder = "asc",
    ) -> dict[str, Any]:
        """
        Lists resources with optional pagination, filtering, and sorting.

        First checks the cache for the listing. If found, returns the cached
        data. If not found, fetches from SWAPI, caches the result, and returns.
        Sorting is applied in memory after fetching.

        Args:
            resource_type: The type of resource (e.g., "people", "planets").
            page: Optional page number for pagination.
            search: Optional search query (maps to SWAPI's ?search= param).
            sort_by: Optional field to sort by (e.g., "name", "height").
            sort_order: Sort order - "asc" (default) or "desc".

        Returns:
            A dictionary containing the paginated response with results.

        Raises:
            ExternalServiceException: If SWAPI is unavailable.
        """
        cache_key = self._generate_cache_key(resource_type, page, search)

        # Step 1: Check cache
        cached_data = await self._cache.get(cache_key)

        if cached_data is not None:
            # Cache hit - apply sorting if requested and return
            if sort_by:
                cached_data = cached_data.copy()
                cached_data["results"] = self._sort_results(
                    cached_data["results"],
                    sort_by,
                    sort_order,
                )
            return cached_data

        # Step 2: Cache miss - fetch from SWAPI
        response = await self._swapi.list_resources(
            resource_type=resource_type,
            page=page,
            search=search,
        )

        # Step 3: Cache the raw result (before sorting)
        await self._cache.set(
            cache_key,
            response,
            ttl_seconds=self._cache_ttl_seconds,
        )

        # Step 4: Apply sorting if requested
        if sort_by:
            response = response.copy()
            response["results"] = self._sort_results(
                response["results"],
                sort_by,
                sort_order,
            )

        return response
