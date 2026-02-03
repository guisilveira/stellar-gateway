"""
Unit tests for GetPersonUseCase.

This test injects a Fake adapter to verify the Use Case logic
without making real HTTP requests.
"""

import pytest

from domain.models import Person
from use_cases.get_person import GetPersonUseCase


class FakeSwapiAdapter:
    """
    In-memory fake implementation of SwapiInterface for testing.
    """

    def __init__(self, data: dict) -> None:
        self._data = data

    async def get_resource(self, resource_type: str, resource_id: int) -> dict:
        """Returns the pre-configured data."""
        return self._data

    async def list_resources(
        self,
        resource_type: str,
        page: int | None = None,
        search: str | None = None,
    ) -> dict:
        """Not used in this test."""
        return {}


class TestGetPersonUseCase:
    """Test suite for the GetPersonUseCase."""

    @pytest.fixture
    def valid_person_data(self) -> dict:
        """Fixture providing valid raw SWAPI person data."""
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
            "films": [
                "https://swapi.dev/api/films/1/",
                "https://swapi.dev/api/films/2/",
            ],
            "species": [],
            "vehicles": [
                "https://swapi.dev/api/vehicles/14/",
            ],
            "starships": [
                "https://swapi.dev/api/starships/12/",
            ],
            "created": "2014-12-09T13:50:51.644000Z",
            "edited": "2014-12-20T21:17:56.891000Z",
            "url": "https://swapi.dev/api/people/1/",
        }

    @pytest.mark.asyncio
    async def test_execute_returns_person_model(self, valid_person_data: dict) -> None:
        """
        GetPersonUseCase.execute should return a valid Person domain model.
        """
        # Arrange
        fake_adapter = FakeSwapiAdapter(data=valid_person_data)
        use_case = GetPersonUseCase(swapi_client=fake_adapter)

        # Act
        result = await use_case.execute(person_id=1)

        # Assert
        assert isinstance(result, Person)
        assert result.name == "Luke Skywalker"
        assert result.gender == "male"

    @pytest.mark.asyncio
    async def test_execute_calls_adapter_with_correct_id(
        self, valid_person_data: dict
    ) -> None:
        """
        GetPersonUseCase should pass the correct ID to the adapter.
        """
        # Arrange
        captured_id: int | None = None
        captured_resource_type: str | None = None

        class SpySwapiAdapter:
            async def get_resource(self, resource_type: str, resource_id: int) -> dict:
                nonlocal captured_id, captured_resource_type
                captured_id = resource_id
                captured_resource_type = resource_type
                return valid_person_data

            async def list_resources(
                self,
                resource_type: str,
                page: int | None = None,
                search: str | None = None,
            ) -> dict:
                return {}

        spy_adapter = SpySwapiAdapter()
        use_case = GetPersonUseCase(swapi_client=spy_adapter)

        # Act
        await use_case.execute(person_id=42)

        # Assert
        assert captured_id == 42
        assert captured_resource_type == "people"
