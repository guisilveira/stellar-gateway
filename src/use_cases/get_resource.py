"""
GetResource Use Case.

This module implements the Cache-Aside pattern for fetching SWAPI resources.
It first checks the cache, and only calls SWAPI on cache miss.
Supports data enrichment (hydration) to replace URLs with resource names.
Optionally validates data against domain models for type safety.
"""

import asyncio
import re
from typing import Any, Type

from domain.models import (
    Film,
    Person,
    Planet,
    Species,
    Starship,
    SwapiBaseModel,
    Vehicle,
)
from interfaces.cache_interface import CacheInterface
from interfaces.swapi_interface import SwapiInterface

# Default cache TTL: 5 minutes
DEFAULT_CACHE_TTL_SECONDS = 300

# Mapping of resource types to their domain models
# This enables type validation and IDE autocomplete
RESOURCE_MODELS: dict[str, Type[SwapiBaseModel]] = {
    "people": Person,
    "planets": Planet,
    "films": Film,
    "species": Species,
    "vehicles": Vehicle,
    "starships": Starship,
}

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
    3. If cache miss: fetch from SWAPI, validate with model, cache the result
    4. Optionally enrich the data by replacing URLs with resource names

    Attributes:
        _swapi: The SWAPI client interface.
        _cache: The cache client interface.
        _cache_ttl_seconds: TTL for cached entries.
        _validate: Whether to validate data against domain models.
    """

    def __init__(
        self,
        swapi: SwapiInterface,
        cache: CacheInterface,
        cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS,
        validate: bool = True,
    ) -> None:
        """
        Initializes the GetResourceUseCase.

        Args:
            swapi: The SWAPI client implementing SwapiInterface.
            cache: The cache client implementing CacheInterface.
            cache_ttl_seconds: Time-to-live for cached entries (default: 300s).
            validate: Whether to validate data against Pydantic models
                     (default: True). Set to False to disable validation
                     for better performance.
        """
        self._swapi = swapi
        self._cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds
        self._validate = validate

    def _get_model_for_resource(
        self, resource_type: str
    ) -> Type[SwapiBaseModel] | None:
        """
        Gets the domain model class for a resource type.

        Args:
            resource_type: The type of resource (e.g., "people", "planets").

        Returns:
            The Pydantic model class, or None if not found.
        """
        return RESOURCE_MODELS.get(resource_type)

    def _validate_data(
        self, resource_type: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Validates resource data against its domain model.

        Args:
            resource_type: The type of resource.
            data: The raw data from SWAPI or cache.

        Returns:
            The validated data (as dict for enrichment compatibility).

        Raises:
            ValidationError: If data doesn't match the model schema.
        """
        if not self._validate:
            return data

        model_class = self._get_model_for_resource(resource_type)
        if model_class is None:
            # Unknown resource type, return as-is
            return data

        # Validate with Pydantic and convert back to dict with JSON-serializable values
        validated = model_class(**data)
        return validated.model_dump(mode="json")

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

    def _parse_swapi_url(self, url: Any) -> tuple[str, int] | None:
        """
        Extracts resource type and ID from a SWAPI URL.

        Handles both string URLs and Pydantic HttpUrl objects.

        Args:
            url: The SWAPI URL to parse (str or HttpUrl).

        Returns:
            A tuple of (resource_type, resource_id) or None if invalid.
        """
        # Convert HttpUrl to string if needed
        url_str = str(url) if url else ""
        match = SWAPI_URL_PATTERN.match(url_str)
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
            # Also disable validation for sub-resources to avoid overhead
            resource_data = await self.execute(
                resource_type, resource_id, enrich=False, validate=False
            )
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
                self._fetch_resource_name(url, display_field) for url in field_value
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
        validate: bool | None = None,
    ) -> dict[str, Any]:
        """
        Fetches a resource using the Cache-Aside pattern.

        First checks the cache for the resource. If found, returns the cached
        data. If not found, fetches from SWAPI, validates with domain model,
        caches the result, and returns.
        Optionally enriches the data by replacing URLs with resource names.

        Args:
            resource_type: The type of resource (e.g., "people", "planets").
            resource_id: The unique identifier of the resource.
            enrich: Whether to enrich URLs with resource names (default: True).
                   Set to False when fetching sub-resources to avoid recursion.
            validate: Whether to validate data against Pydantic models.
                     If None, uses the instance's validate setting (default: True).
                     Set to False for sub-resources to reduce overhead.

        Returns:
            A dictionary containing the resource data (optionally enriched).

        Raises:
            ResourceNotFoundException: If the resource does not exist in SWAPI.
            ExternalServiceException: If SWAPI is unavailable.
            ValidationError: If data doesn't match the domain model schema.
        """
        # Use instance default if not specified
        if validate is None:
            validate = self._validate

        cache_key = self._generate_cache_key(resource_type, resource_id)

        # Step 1: Check cache
        cached_data = await self._cache.get(cache_key)

        if cached_data is not None:
            # Cache hit - validate and enrich if requested
            if validate:
                cached_data = self._validate_data(resource_type, cached_data)
            if enrich:
                cached_data = await self._enrich_resource(cached_data)
            return cached_data

        # Step 2: Cache miss - fetch from SWAPI
        resource_data = await self._swapi.get_resource(resource_type, resource_id)

        # Step 3: Validate data against domain model (before caching)
        if validate:
            resource_data = self._validate_data(resource_type, resource_data)

        # Step 4: Cache the validated result (before enrichment)
        await self._cache.set(
            cache_key,
            resource_data,
            ttl_seconds=self._cache_ttl_seconds,
        )

        # Step 5: Optionally enrich the data
        if enrich:
            resource_data = await self._enrich_resource(resource_data)

        return resource_data
