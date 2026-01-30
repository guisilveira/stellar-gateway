"""
Use Case: Get Person.

This module contains the business logic for fetching a Person entity.
It orchestrates the flow between the adapter (data source) and the domain model.
"""

from domain.models import Person
from interfaces.swapi_interface import SwapiInterface


class GetPersonUseCase:
    """
    Use case for retrieving a Person from SWAPI.

    This class follows the Dependency Inversion Principle by depending
    on an abstract interface rather than a concrete implementation.

    Attributes:
        swapi_client: An adapter implementing SwapiInterface.
    """

    def __init__(self, swapi_client: SwapiInterface) -> None:
        """
        Initializes the use case with a SWAPI client.

        Args:
            swapi_client: An object implementing SwapiInterface
                          for fetching person data.
        """
        self._swapi_client = swapi_client

    async def execute(self, person_id: int) -> Person:
        """
        Fetches and returns a Person domain model.

        Args:
            person_id: The unique identifier of the person to fetch.

        Returns:
            A Person domain model populated with SWAPI data.

        Raises:
            ValidationError: If the SWAPI data doesn't match Person schema.
            ResourceNotFoundError: If the person does not exist.
        """
        data = await self._swapi_client.get_person_data(person_id)
        return Person(**data)
