"""
Integration tests for API routes.

Tests the FastAPI routes with mocked use cases using FastAPI's dependency override.
"""

import os
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from domain.exceptions import ExternalServiceException, ResourceNotFoundException

# Set test environment before importing app
os.environ["ENVIRONMENT"] = "test"

# Import app after setting environment
from api.dependencies import (  # noqa: E402
    get_get_resource_use_case,
    get_list_resources_use_case,
)
from main import app  # noqa: E402


@pytest.fixture
def mock_get_resource_use_case() -> MagicMock:
    """Creates a mock GetResourceUseCase."""
    mock = MagicMock()
    mock.execute = AsyncMock()
    return mock


@pytest.fixture
def mock_list_resources_use_case() -> MagicMock:
    """Creates a mock ListResourcesUseCase."""
    mock = MagicMock()
    mock.execute = AsyncMock()
    return mock


@pytest.fixture
def client(
    mock_get_resource_use_case: MagicMock,
    mock_list_resources_use_case: MagicMock,
) -> Generator[TestClient, None, None]:
    """Creates a test client with mocked dependencies."""
    app.dependency_overrides[get_get_resource_use_case] = (
        lambda: mock_get_resource_use_case
    )
    app.dependency_overrides[get_list_resources_use_case] = (
        lambda: mock_list_resources_use_case
    )

    yield TestClient(app)

    # Clean up overrides
    app.dependency_overrides.clear()


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_check_returns_healthy(self) -> None:
        """Should return healthy status."""
        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestMeEndpoint:
    """Tests for the /me endpoint."""

    def test_me_returns_user_info(self, client: TestClient) -> None:
        """Should return the authenticated user's info."""
        response = client.get("/me")

        assert response.status_code == 200
        data = response.json()
        assert "uid" in data
        assert "email" in data


class TestGetResourceEndpoint:
    """Tests for the /{resource}/{id} endpoint."""

    def test_get_person_returns_resource(
        self,
        client: TestClient,
        mock_get_resource_use_case: MagicMock,
    ) -> None:
        """Should return a resource when found."""
        mock_get_resource_use_case.execute = AsyncMock(
            return_value={
                "name": "Luke Skywalker",
                "height": "172",
                "homeworld": "Tatooine",
            }
        )

        response = client.get("/people/1")

        assert response.status_code == 200
        assert response.json()["name"] == "Luke Skywalker"
        mock_get_resource_use_case.execute.assert_called_once_with(
            resource_type="people",
            resource_id=1,
            enrich=True,
        )

    def test_get_resource_not_found_returns_404(
        self,
        client: TestClient,
        mock_get_resource_use_case: MagicMock,
    ) -> None:
        """Should return 404 with RFC 7807 Problem Details when resource not found."""
        mock_get_resource_use_case.execute = AsyncMock(
            side_effect=ResourceNotFoundException(
                resource_type="people",
                resource_id=999,
            )
        )

        response = client.get("/people/999")

        assert response.status_code == 404
        assert response.headers["content-type"] == "application/problem+json"
        data = response.json()
        assert data["title"] == "Resource Not Found"
        assert data["status"] == 404
        assert "people" in data["detail"].lower()

    def test_get_resource_external_error_returns_502(
        self,
        client: TestClient,
        mock_get_resource_use_case: MagicMock,
    ) -> None:
        """Should return 502 with RFC 7807 Problem Details on SWAPI error."""
        mock_get_resource_use_case.execute = AsyncMock(
            side_effect=ExternalServiceException(
                service_name="SWAPI",
                status_code=500,
                message="SWAPI returned status 500",
            )
        )

        response = client.get("/people/1")

        assert response.status_code == 502
        assert response.headers["content-type"] == "application/problem+json"
        data = response.json()
        assert data["title"] == "External Service Error"
        assert data["status"] == 502

    def test_get_resource_with_enrich_false(
        self,
        client: TestClient,
        mock_get_resource_use_case: MagicMock,
    ) -> None:
        """Should pass enrich=False to use case when specified."""
        mock_get_resource_use_case.execute = AsyncMock(
            return_value={
                "name": "Luke Skywalker",
                "homeworld": "https://swapi.dev/api/planets/1/",
            }
        )

        response = client.get("/people/1?enrich=false")

        assert response.status_code == 200
        mock_get_resource_use_case.execute.assert_called_once_with(
            resource_type="people",
            resource_id=1,
            enrich=False,
        )


class TestListResourcesEndpoint:
    """Tests for the /{resource} endpoint."""

    def test_list_resources_returns_paginated_results(
        self,
        client: TestClient,
        mock_list_resources_use_case: MagicMock,
    ) -> None:
        """Should return paginated results."""
        mock_list_resources_use_case.execute = AsyncMock(
            return_value={
                "count": 82,
                "next": "https://swapi.dev/api/people/?page=2",
                "previous": None,
                "results": [{"name": "Luke Skywalker"}],
            }
        )

        response = client.get("/people")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 82
        assert len(data["results"]) == 1

    def test_list_resources_with_pagination(
        self,
        client: TestClient,
        mock_list_resources_use_case: MagicMock,
    ) -> None:
        """Should pass page parameter to use case."""
        mock_list_resources_use_case.execute = AsyncMock(
            return_value={
                "count": 82,
                "next": None,
                "previous": "https://swapi.dev/api/people/?page=1",
                "results": [],
            }
        )

        response = client.get("/people?page=2")

        assert response.status_code == 200
        mock_list_resources_use_case.execute.assert_called_once_with(
            resource_type="people",
            page=2,
            search=None,
            sort_by=None,
            sort_order="asc",
        )

    def test_list_resources_with_search(
        self,
        client: TestClient,
        mock_list_resources_use_case: MagicMock,
    ) -> None:
        """Should pass search parameter to use case."""
        mock_list_resources_use_case.execute = AsyncMock(
            return_value={
                "count": 1,
                "next": None,
                "previous": None,
                "results": [{"name": "Luke Skywalker"}],
            }
        )

        response = client.get("/people?search=Luke")

        assert response.status_code == 200
        mock_list_resources_use_case.execute.assert_called_once_with(
            resource_type="people",
            page=None,
            search="Luke",
            sort_by=None,
            sort_order="asc",
        )

    def test_list_resources_with_sorting(
        self,
        client: TestClient,
        mock_list_resources_use_case: MagicMock,
    ) -> None:
        """Should pass sort parameters to use case."""
        mock_list_resources_use_case.execute = AsyncMock(
            return_value={
                "count": 2,
                "next": None,
                "previous": None,
                "results": [
                    {"name": "Anakin Skywalker"},
                    {"name": "Luke Skywalker"},
                ],
            }
        )

        response = client.get("/people?sort_by=name&sort_order=desc")

        assert response.status_code == 200
        mock_list_resources_use_case.execute.assert_called_once_with(
            resource_type="people",
            page=None,
            search=None,
            sort_by="name",
            sort_order="desc",
        )


class TestInvalidResourceType:
    """Tests for invalid resource type handling."""

    def test_invalid_resource_returns_400(self, client: TestClient) -> None:
        """Should return 400 for invalid resource types."""
        response = client.get("/invalid_resource")

        assert response.status_code == 400
        assert response.headers["content-type"] == "application/problem+json"
        data = response.json()
        assert data["title"] == "Invalid Resource Type"
        assert data["status"] == 400
        assert "invalid_resource" in data["detail"]

    def test_valid_resources_are_accepted(
        self,
        client: TestClient,
        mock_list_resources_use_case: MagicMock,
    ) -> None:
        """Should accept all valid SWAPI resource types."""
        valid_resources = [
            "people",
            "planets",
            "films",
            "species",
            "vehicles",
            "starships",
        ]

        mock_list_resources_use_case.execute = AsyncMock(
            return_value={
                "count": 0,
                "next": None,
                "previous": None,
                "results": [],
            }
        )

        for resource in valid_resources:
            response = client.get(f"/{resource}")
            # Should not get 400 for resource type validation
            assert response.status_code != 400, f"Resource {resource} was rejected"
