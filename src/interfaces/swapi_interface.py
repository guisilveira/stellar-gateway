"""
Interfaces for external data sources.

This module defines Protocols (contracts) that adapters must implement.
Following the Dependency Inversion Principle (DIP).
"""

from typing import Protocol


class SwapiInterface(Protocol):
    """
    Contract for SWAPI data fetching.

    Any adapter that fetches data from SWAPI (or a mock) must implement this.
    """

    async def get_resource(self, resource_type: str, resource_id: int) -> dict:
        """
        Fetches raw resource data from SWAPI.

        Args:
            resource_type: The type of resource (e.g., "people", "planets").
            resource_id: The unique identifier of the resource.

        Returns:
            A dictionary containing the raw SWAPI response.

        Raises:
            ResourceNotFoundException: If the resource does not exist.
            ExternalServiceException: If the external service fails.
        """
        ...

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
        ...
