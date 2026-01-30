"""
Security utilities for authentication and authorization.

This module provides Firebase authentication verification and
FastAPI dependencies for protecting API endpoints.
"""

from typing import Annotated

import firebase_admin
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth, credentials

from core.config import settings


# Mock token accepted in dev/test environments
MOCK_TOKEN = "mock-token"

# HTTP Bearer scheme for extracting tokens
security_scheme = HTTPBearer(auto_error=False)


def initialize_firebase() -> None:
    """
    Initializes Firebase Admin SDK if not already initialized.

    Uses the service account credentials from settings.
    Should be called once at application startup.
    """
    if not firebase_admin._apps:
        cred = credentials.Certificate(settings.GOOGLE_APPLICATION_CREDENTIALS)
        firebase_admin.initialize_app(cred)


def verify_token(token: str) -> dict:
    """
    Verifies a Firebase ID Token and returns the decoded claims.

    In dev/test environments, accepts a mock token for easier testing.

    Args:
        token: The Firebase ID Token to verify.

    Returns:
        A dictionary containing the token's decoded claims.
        For mock tokens in dev/test, returns a fake user payload.

    Raises:
        auth.InvalidIdTokenError: If the token is invalid.
        auth.ExpiredIdTokenError: If the token has expired.
        auth.RevokedIdTokenError: If the token has been revoked.
    """
    # In dev/test mode, accept mock token for local testing
    if settings.ENVIRONMENT in ("dev", "test"):
        if token == MOCK_TOKEN:
            return {
                "uid": "mock-user-001",
                "email": "mock@example.com",
                "name": "Mock User",
                "email_verified": True,
            }

    # Ensure Firebase is initialized
    initialize_firebase()

    # Verify the token with Firebase
    decoded_token = auth.verify_id_token(token)
    return dict(decoded_token)


async def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(security_scheme)
    ] = None,
) -> dict:
    """
    FastAPI dependency that extracts and verifies the Firebase ID Token.

    In dev/test environments, the dependency is more lenient:
    - Accepts "mock-token" as a valid token
    - Returns a test user if no token provided in "test" environment

    Args:
        request: The incoming FastAPI request.
        credentials: The extracted Bearer token credentials.

    Returns:
        A dictionary containing the verified user's claims.

    Raises:
        HTTPException: 401 if authentication fails.
    """
    # In test environment, allow requests without auth header
    if settings.ENVIRONMENT == "test" and credentials is None:
        return {
            "uid": "test-user",
            "email": "test@example.com",
            "name": "Test User",
        }

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        decoded_token = verify_token(token)
        return decoded_token

    except auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid ID token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Type alias for dependency injection
CurrentUser = Annotated[dict, Depends(get_current_user)]
