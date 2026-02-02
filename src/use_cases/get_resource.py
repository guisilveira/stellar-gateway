"""
GetResource Use Case.

This module implements the Cache-Aside pattern for fetching SWAPI resources.
It first checks the cache, and only calls SWAPI on cache miss.
Supports data enrichment (hydration) to replace URLs with resource names.
"""

import asyncio
import re
from typing import Any

from interfaces.cache_interface import CacheInterface
from interfaces.swapi_interface import SwapiInterface


# Default cache TTL: 5 minutes
DEFAULT_CACHE_TTL_SECONDS = 300

# Fields that contain SWAPI URLs and should be enriched
# Maps field name to the attribute used for display (name or title)
ENRICHABLE_FIELDS: dict[str, str] = {
    "homeworld": "name",  # Single URL -> planet name
    "films": "title",  # List of URLs -> film titles
    "species": "name",  # List of URLs -> species names
    "vehicles": "name",  # List of URLs -> vehicle names
    "starships": "name",  # List of URLs -> starship names
    "residents": "name",  # List of URLs -> people names
    "pilots": "name",  # List of URLs -> people names
    "characters": "name",  # List of URLs -> people names
    "planets": "name",  # List of URLs -> planet names
    "people": "name",  # List of URLs -> people names
}

# Regex to extract resource type and ID from SWAPI URLs
SWAPI_URL_PATTERN = re.compile(r"https?://swapi\.dev/api/(\w+)/(\d+)/?")


class GetResourceUseCase:
    """
    Use case for fetching a single resource with Cache-Aside pattern.

    This use case implements the following flow:
    1. Check if the resource exists in cache
    2. If cache hit: return cached data
    3. If cache miss: fetch from SWAPI, cache the result, return data
    4. Optionally enrich the data by replacing URLs with resource names

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
        Initializes the GetResourceUseCase.

        Args:
            swapi: The SWAPI client implementing SwapiInterface.
            cache: The cache client implementing CacheInterface.
            cache_ttl_seconds: Time-to-live for cached entries (default: 300s).
        """
        self._swapi = swapi
        self._cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds

    def _generate_cache_key(self, resource_type: str, resource_id: int) -> str:
        """
        Generates a cache key for a resource.

        Args:
            resource_type: The type of resource (e.g., "people", "planets").
            resource_id: The unique identifier of the resource.

        Returns:
            A cache key in format 'swapi:{resource_type}:{resource_id}'.
        """
        return f"swapi:{resource_type}:{resource_id}"

    def _parse_swapi_url(self, url: str) -> tuple[str, int] | None:
        """
        Extracts resource type and ID from a SWAPI URL.

        Args:
            url: The SWAPI URL to parse.

        Returns:
            A tuple of (resource_type, resource_id) or None if invalid.
        """
        match = SWAPI_URL_PATTERN.match(url)
        if match:
            return match.group(1), int(match.group(2))
        return None

    async def _fetch_resource_name(
        self,
        url: str,
        display_field: str,
    ) -> str:
        """
        Fetches a resource and returns its display name.

        Uses the Cache-Aside pattern internally (calls execute with enrich=False).
        If the fetch fails, returns the original URL.

        Args:
            url: The SWAPI URL to fetch.
            display_field: The field to use as display name (e.g., "name", "title").

        Returns:
            The resource's display name, or the original URL on failure.
        """
        parsed = self._parse_swapi_url(url)
        if not parsed:
            return url

        resource_type, resource_id = parsed

        try:
            # Fetch without enrichment to avoid infinite recursion
            resource_data = await self.execute(resource_type, resource_id, enrich=False)
            return resource_data.get(display_field, url)
        except Exception:
            # On any error, preserve the original URL
            return url

    async def _enrich_field(
        self,
        field_value: Any,
        display_field: str,
    ) -> Any:
        """
        Enriches a field value by replacing URLs with resource names.

        Handles both single URLs (str) and lists of URLs.

        Args:
            field_value: The field value (URL string or list of URLs).
            display_field: The field to use as display name.

        Returns:
            The enriched value (name/title or list of names/titles).
        """
        if isinstance(field_value, str):
            # Single URL (e.g., homeworld)
            return await self._fetch_resource_name(field_value, display_field)
        elif isinstance(field_value, list):
            # List of URLs (e.g., films, species)
            if not field_value:
                return []

            # Fetch all resources in parallel
            tasks = [
                self._fetch_resource_name(url, display_field)
                for url in field_value
            ]
            return await asyncio.gather(*tasks)

        return field_value

    async def _enrich_resource(self, resource_data: dict[str, Any]) -> dict[str, Any]:
        """
        Enriches a resource by replacing URL fields with resource names.

        Uses asyncio.gather to fetch all enrichable fields in parallel.

        Args:
            resource_data: The raw resource data from SWAPI.

        Returns:
            The enriched resource data with URLs replaced by names.
        """
        enriched = resource_data.copy()

        # Collect all enrichment tasks
        enrichment_tasks: list[tuple[str, Any]] = []

        for field_name, display_field in ENRICHABLE_FIELDS.items():
            if field_name in enriched and enriched[field_name]:
                enrichment_tasks.append((field_name, display_field))

        if not enrichment_tasks:
            return enriched

        # Execute all enrichments in parallel
        async def enrich_single_field(
            field_name: str, display_field: str
        ) -> tuple[str, Any]:
            enriched_value = await self._enrich_field(
                enriched[field_name], display_field
            )
            return field_name, enriched_value

        results = await asyncio.gather(
            *[
                enrich_single_field(field_name, display_field)
                for field_name, display_field in enrichment_tasks
            ]
        )

        # Apply enriched values
        for field_name, enriched_value in results:
            enriched[field_name] = enriched_value

        return enriched

    async def execute(
        self,
        resource_type: str,
        resource_id: int,
        enrich: bool = True,
    ) -> dict[str, Any]:
        """
        Fetches a resource using the Cache-Aside pattern.

        First checks the cache for the resource. If found, returns the cached
        data. If not found, fetches from SWAPI, caches the result, and returns.
        Optionally enriches the data by replacing URLs with resource names.

        Args:
            resource_type: The type of resource (e.g., "people", "planets").
            resource_id: The unique identifier of the resource.
            enrich: Whether to enrich URLs with resource names (default: True).
                   Set to False when fetching sub-resources to avoid recursion.

        Returns:
            A dictionary containing the resource data (optionally enriched).

        Raises:
            ResourceNotFoundException: If the resource does not exist in SWAPI.
            ExternalServiceException: If SWAPI is unavailable.
        """
        cache_key = self._generate_cache_key(resource_type, resource_id)

        # Step 1: Check cache
        cached_data = await self._cache.get(cache_key)

        if cached_data is not None:
            # Cache hit - enrich if requested and return
            if enrich:
                cached_data = await self._enrich_resource(cached_data)
            return cached_data

        # Step 2: Cache miss - fetch from SWAPI
        resource_data = await self._swapi.get_resource(resource_type, resource_id)

        # Step 3: Cache the raw result (before enrichment)
        await self._cache.set(
            cache_key,
            resource_data,
            ttl_seconds=self._cache_ttl_seconds,
        )

        # Step 4: Optionally enrich the data
        if enrich:
            resource_data = await self._enrich_resource(resource_data)

        return resource_data
