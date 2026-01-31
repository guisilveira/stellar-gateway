"""
Unit tests for the security module.

Tests the verify_token function and get_current_user dependency
with mocked Firebase authentication.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.security import MOCK_TOKEN, CurrentUser, verify_token


@pytest.fixture
def app() -> FastAPI:
    """Creates a FastAPI test application."""
    app = FastAPI()

    @app.get("/protected")
    async def protected_route(current_user: CurrentUser) -> dict:
        return {"user": current_user}

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Creates a test client for the FastAPI app."""
    return TestClient(app)


class TestVerifyToken:
    """Test suite for the verify_token function."""

    @patch("core.security.settings")
    def test_verify_token_accepts_mock_in_dev_environment(
        self, mock_settings: MagicMock
    ) -> None:
        """In dev environment, mock-token should return a fake user."""
        mock_settings.ENVIRONMENT = "dev"

        result = verify_token(MOCK_TOKEN)

        assert result["uid"] == "mock-user-001"
        assert result["email"] == "mock@example.com"

    @patch("core.security.settings")
    def test_verify_token_accepts_mock_in_test_environment(
        self, mock_settings: MagicMock
    ) -> None:
        """In test environment, mock-token should return a fake user."""
        mock_settings.ENVIRONMENT = "test"

        result = verify_token(MOCK_TOKEN)

        assert result["uid"] == "mock-user-001"
        assert result["email"] == "mock@example.com"


class TestGetCurrentUserDependency:
    """Test suite for the get_current_user FastAPI dependency."""

    @patch("core.security.settings")
    def test_allows_mock_token_in_dev(
        self, mock_settings: MagicMock, client: TestClient
    ) -> None:
        """In dev environment, mock-token should be accepted."""
        mock_settings.ENVIRONMENT = "dev"

        response = client.get(
            "/protected", headers={"Authorization": f"Bearer {MOCK_TOKEN}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user"]["uid"] == "mock-user-001"

    @patch("core.security.settings")
    def test_allows_requests_without_auth_in_test(
        self, mock_settings: MagicMock, client: TestClient
    ) -> None:
        """In test environment, requests without auth header should be allowed."""
        mock_settings.ENVIRONMENT = "test"

        response = client.get("/protected")

        assert response.status_code == 200
        data = response.json()
        assert data["user"]["uid"] == "test-user"

    @patch("core.security.settings")
    def test_rejects_missing_auth_header_in_prod(
        self, mock_settings: MagicMock, client: TestClient
    ) -> None:
        """In prod environment, missing auth header should return 401."""
        mock_settings.ENVIRONMENT = "prod"

        response = client.get("/protected")

        assert response.status_code == 401
        data = response.json()
        assert "Missing Authorization header" in data["detail"]

    @patch("core.security.settings")
    @patch("core.security.auth")
    @patch("core.security.initialize_firebase")
    def test_handles_invalid_token_error(
        self,
        mock_init_firebase: MagicMock,
        mock_auth: MagicMock,
        mock_settings: MagicMock,
        client: TestClient,
    ) -> None:
        """Invalid tokens should return 401 with appropriate message."""
        from firebase_admin import auth as real_auth

        mock_settings.ENVIRONMENT = "prod"
        mock_auth.verify_id_token.side_effect = real_auth.InvalidIdTokenError("Invalid")
        mock_auth.InvalidIdTokenError = real_auth.InvalidIdTokenError
        mock_auth.ExpiredIdTokenError = real_auth.ExpiredIdTokenError
        mock_auth.RevokedIdTokenError = real_auth.RevokedIdTokenError

        response = client.get(
            "/protected", headers={"Authorization": "Bearer invalid-token"}
        )

        assert response.status_code == 401
        data = response.json()
        assert "Invalid ID token" in data["detail"]
