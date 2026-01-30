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

    async def get_person_data(self, person_id: int) -> dict:
        """
        Fetches raw person data from SWAPI.

        Args:
            person_id: The unique identifier of the person.

        Returns:
            A dictionary containing the raw SWAPI response.

        Raises:
            ResourceNotFoundError: If the person does not exist.
        """
        ...
