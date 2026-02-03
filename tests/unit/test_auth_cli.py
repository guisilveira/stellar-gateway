"""
Unit tests for the Firebase Authentication CLI script.

Tests the signup, login, and refresh functions with mocked HTTP responses.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from auth import (
    FirebaseAuthError,
    _get_api_key,
    _handle_firebase_error,
    login,
    refresh,
    signup,
)


class TestGetApiKey:
    """Tests for the _get_api_key function."""

    @patch("auth.settings")
    def test_returns_api_key_when_set(self, mock_settings: MagicMock) -> None:
        """Should return API key when FIREBASE_WEB_API_KEY is configured."""
        mock_settings.FIREBASE_WEB_API_KEY = "test-api-key-123"

        result = _get_api_key()

        assert result == "test-api-key-123"

    @patch("auth.settings")
    def test_raises_error_when_not_set(self, mock_settings: MagicMock) -> None:
        """Should raise ValueError when FIREBASE_WEB_API_KEY is empty."""
        mock_settings.FIREBASE_WEB_API_KEY = ""

        with pytest.raises(ValueError) as exc_info:
            _get_api_key()

        assert "FIREBASE_WEB_API_KEY is not set" in str(exc_info.value)


class TestHandleFirebaseError:
    """Tests for the _handle_firebase_error function."""

    def test_handles_email_exists_error(self) -> None:
        """Should provide friendly message for EMAIL_EXISTS error."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": {"message": "EMAIL_EXISTS"}}

        with pytest.raises(FirebaseAuthError) as exc_info:
            _handle_firebase_error(mock_response)

        assert "already registered" in str(exc_info.value)
        assert exc_info.value.error_code == "EMAIL_EXISTS"

    def test_handles_invalid_password_error(self) -> None:
        """Should provide friendly message for INVALID_PASSWORD error."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": {"message": "INVALID_PASSWORD"}}

        with pytest.raises(FirebaseAuthError) as exc_info:
            _handle_firebase_error(mock_response)

        assert "Incorrect password" in str(exc_info.value)

    def test_handles_invalid_login_credentials_error(self) -> None:
        """Should provide friendly message for INVALID_LOGIN_CREDENTIALS error."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": {"message": "INVALID_LOGIN_CREDENTIALS"}
        }

        with pytest.raises(FirebaseAuthError) as exc_info:
            _handle_firebase_error(mock_response)

        assert "Invalid email or password" in str(exc_info.value)

    def test_handles_weak_password_error(self) -> None:
        """Should provide friendly message for WEAK_PASSWORD error."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": {"message": "WEAK_PASSWORD"}}

        with pytest.raises(FirebaseAuthError) as exc_info:
            _handle_firebase_error(mock_response)

        assert "at least 6 characters" in str(exc_info.value)

    def test_handles_unknown_error(self) -> None:
        """Should include error code for unknown errors."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": {"message": "SOME_NEW_ERROR"}}

        with pytest.raises(FirebaseAuthError) as exc_info:
            _handle_firebase_error(mock_response)

        assert "SOME_NEW_ERROR" in str(exc_info.value)

    def test_handles_malformed_response(self) -> None:
        """Should handle responses without proper error structure."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with pytest.raises(FirebaseAuthError) as exc_info:
            _handle_firebase_error(mock_response)

        assert "500" in str(exc_info.value)


class TestSignup:
    """Tests for the signup function."""

    @patch("auth.httpx.post")
    @patch("auth.settings")
    def test_signup_success(
        self, mock_settings: MagicMock, mock_post: MagicMock
    ) -> None:
        """Should return user data on successful signup."""
        mock_settings.FIREBASE_WEB_API_KEY = "test-api-key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "idToken": "test-id-token",
            "refreshToken": "test-refresh-token",
            "localId": "user-123",
            "email": "test@example.com",
            "expiresIn": "3600",
        }
        mock_post.return_value = mock_response

        result = signup("test@example.com", "password123")

        assert result["idToken"] == "test-id-token"
        assert result["localId"] == "user-123"
        mock_post.assert_called_once()

    @patch("auth.httpx.post")
    @patch("auth.settings")
    def test_signup_email_exists(
        self, mock_settings: MagicMock, mock_post: MagicMock
    ) -> None:
        """Should raise FirebaseAuthError when email already exists."""
        mock_settings.FIREBASE_WEB_API_KEY = "test-api-key"

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": {"message": "EMAIL_EXISTS"}}
        mock_post.return_value = mock_response

        with pytest.raises(FirebaseAuthError) as exc_info:
            signup("existing@example.com", "password123")

        assert "already registered" in str(exc_info.value)


class TestLogin:
    """Tests for the login function."""

    @patch("auth.httpx.post")
    @patch("auth.settings")
    def test_login_success(
        self, mock_settings: MagicMock, mock_post: MagicMock
    ) -> None:
        """Should return tokens on successful login."""
        mock_settings.FIREBASE_WEB_API_KEY = "test-api-key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "idToken": "test-id-token",
            "refreshToken": "test-refresh-token",
            "localId": "user-123",
            "email": "test@example.com",
            "expiresIn": "3600",
        }
        mock_post.return_value = mock_response

        result = login("test@example.com", "password123")

        assert result["idToken"] == "test-id-token"
        assert result["refreshToken"] == "test-refresh-token"

    @patch("auth.httpx.post")
    @patch("auth.settings")
    def test_login_invalid_credentials(
        self, mock_settings: MagicMock, mock_post: MagicMock
    ) -> None:
        """Should raise FirebaseAuthError for invalid credentials."""
        mock_settings.FIREBASE_WEB_API_KEY = "test-api-key"

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {"message": "INVALID_LOGIN_CREDENTIALS"}
        }
        mock_post.return_value = mock_response

        with pytest.raises(FirebaseAuthError) as exc_info:
            login("test@example.com", "wrongpassword")

        assert "Invalid email or password" in str(exc_info.value)

    @patch("auth.httpx.post")
    @patch("auth.settings")
    def test_login_user_not_found(
        self, mock_settings: MagicMock, mock_post: MagicMock
    ) -> None:
        """Should raise FirebaseAuthError when user doesn't exist."""
        mock_settings.FIREBASE_WEB_API_KEY = "test-api-key"

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": {"message": "EMAIL_NOT_FOUND"}}
        mock_post.return_value = mock_response

        with pytest.raises(FirebaseAuthError) as exc_info:
            login("nonexistent@example.com", "password123")

        assert "No account found" in str(exc_info.value)


class TestRefresh:
    """Tests for the refresh function."""

    @patch("auth.httpx.post")
    @patch("auth.settings")
    def test_refresh_success(
        self, mock_settings: MagicMock, mock_post: MagicMock
    ) -> None:
        """Should return new tokens on successful refresh."""
        mock_settings.FIREBASE_WEB_API_KEY = "test-api-key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id_token": "new-id-token",
            "refresh_token": "new-refresh-token",
            "user_id": "user-123",
            "expires_in": "3600",
        }
        mock_post.return_value = mock_response

        result = refresh("old-refresh-token")

        assert result["id_token"] == "new-id-token"
        assert result["refresh_token"] == "new-refresh-token"

    @patch("auth.httpx.post")
    @patch("auth.settings")
    def test_refresh_invalid_token(
        self, mock_settings: MagicMock, mock_post: MagicMock
    ) -> None:
        """Should raise FirebaseAuthError for invalid refresh token."""
        mock_settings.FIREBASE_WEB_API_KEY = "test-api-key"

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {"message": "INVALID_REFRESH_TOKEN"}
        }
        mock_post.return_value = mock_response

        with pytest.raises(FirebaseAuthError) as exc_info:
            refresh("invalid-token")

        assert "invalid or expired" in str(exc_info.value)


class TestApiKeyValidation:
    """Tests for API key validation across all functions."""

    @patch("auth.settings")
    def test_signup_requires_api_key(self, mock_settings: MagicMock) -> None:
        """Signup should fail if API key is not set."""
        mock_settings.FIREBASE_WEB_API_KEY = ""

        with pytest.raises(ValueError) as exc_info:
            signup("test@example.com", "password123")

        assert "FIREBASE_WEB_API_KEY" in str(exc_info.value)

    @patch("auth.settings")
    def test_login_requires_api_key(self, mock_settings: MagicMock) -> None:
        """Login should fail if API key is not set."""
        mock_settings.FIREBASE_WEB_API_KEY = ""

        with pytest.raises(ValueError) as exc_info:
            login("test@example.com", "password123")

        assert "FIREBASE_WEB_API_KEY" in str(exc_info.value)

    @patch("auth.settings")
    def test_refresh_requires_api_key(self, mock_settings: MagicMock) -> None:
        """Refresh should fail if API key is not set."""
        mock_settings.FIREBASE_WEB_API_KEY = ""

        with pytest.raises(ValueError) as exc_info:
            refresh("some-token")

        assert "FIREBASE_WEB_API_KEY" in str(exc_info.value)
