"""
Security utilities for authentication and authorization.

This module provides Firebase authentication verification and
FastAPI dependencies for protecting API endpoints.

Supports both:
- Direct access with Authorization Bearer token (Cloud Run)
- API Gateway access with X-Apigateway-Api-Userinfo header
"""

import base64
import json
from typing import Annotated

import firebase_admin
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth, credentials

from core.config import settings

# Mock token accepted in dev/test environments
MOCK_TOKEN = "mock-token"

# Header used by Google API Gateway to pass validated user info
API_GATEWAY_USER_INFO_HEADER = "X-Apigateway-Api-Userinfo"

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


def _extract_user_from_gateway_header(request: Request) -> dict | None:
    """
    Extracts user info from API Gateway's X-Apigateway-Api-Userinfo header.

    When API Gateway validates a JWT, it passes the validated claims
    as a base64url-encoded JSON in this header.

    Args:
        request: The incoming FastAPI request.

    Returns:
        A dictionary containing the user's claims, or None if header not present.
    """
    user_info_header = request.headers.get(API_GATEWAY_USER_INFO_HEADER)

    if not user_info_header:
        return None

    try:
        # API Gateway uses base64url encoding (may have padding issues)
        # Add padding if necessary
        padding = 4 - len(user_info_header) % 4
        if padding != 4:
            user_info_header += "=" * padding

        decoded_bytes = base64.urlsafe_b64decode(user_info_header)
        user_info = json.loads(decoded_bytes.decode("utf-8"))

        # Map Firebase JWT claims to our expected format
        return {
            "uid": user_info.get("sub") or user_info.get("user_id"),
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "email_verified": user_info.get("email_verified", False),
        }
    except Exception:
        return None


async def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(security_scheme)
    ] = None,
) -> dict:
    """
    FastAPI dependency that extracts and verifies the Firebase ID Token.

    Supports two authentication modes:
    1. API Gateway: Reads validated user info from X-Apigateway-Api-Userinfo header
    2. Direct: Validates Firebase ID Token from Authorization header

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
    # Priority 1: Check for API Gateway validated user info header
    gateway_user = _extract_user_from_gateway_header(request)
    if gateway_user:
        return gateway_user

    # Priority 2: In test environment, allow requests without auth header
    if settings.ENVIRONMENT == "test" and credentials is None:
        return {
            "uid": "test-user",
            "email": "test@example.com",
            "name": "Test User",
        }

    # Priority 3: Validate Authorization Bearer token
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
        ) from None

    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid ID token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# Type alias for dependency injection
CurrentUser = Annotated[dict, Depends(get_current_user)]
