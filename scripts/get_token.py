#!/usr/bin/env python3
"""
Firebase Token Generator Script (Dev Tool).

This script generates a valid Firebase ID Token for testing purposes.
It uses firebase_admin to create a Custom Token and then exchanges it
for an ID Token using the Google Identity Toolkit REST API.

Usage:
    python scripts/get_token.py [--uid <user_id>]

Requirements:
    - GOOGLE_APPLICATION_CREDENTIALS must point to a valid service account JSON
    - FIREBASE_WEB_API_KEY must be set in .env or environment
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import httpx
import firebase_admin
from firebase_admin import auth, credentials

from core.config import settings


# Firebase Identity Toolkit endpoint for token exchange
IDENTITY_TOOLKIT_URL = (
    "https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken"
)


def initialize_firebase() -> None:
    """
    Initializes Firebase Admin SDK if not already initialized.

    Uses the service account credentials from settings.
    """
    if not firebase_admin._apps:
        cred = credentials.Certificate(settings.GOOGLE_APPLICATION_CREDENTIALS)
        firebase_admin.initialize_app(cred)


def create_custom_token(uid: str) -> str:
    """
    Creates a Firebase Custom Token for a given user ID.

    Args:
        uid: The unique identifier for the user.

    Returns:
        A custom token string that can be exchanged for an ID token.
    """
    custom_token = auth.create_custom_token(uid)
    return custom_token.decode("utf-8") if isinstance(custom_token, bytes) else custom_token


def exchange_custom_token_for_id_token(custom_token: str) -> dict:
    """
    Exchanges a Custom Token for an ID Token using Google Identity Toolkit.

    Args:
        custom_token: The custom token created by Firebase Admin.

    Returns:
        A dictionary containing 'idToken', 'refreshToken', and 'expiresIn'.

    Raises:
        httpx.HTTPStatusError: If the API request fails.
        ValueError: If FIREBASE_WEB_API_KEY is not configured.
    """
    if not settings.FIREBASE_WEB_API_KEY:
        raise ValueError(
            "FIREBASE_WEB_API_KEY is not set. "
            "Please add it to your .env file or environment variables."
        )

    payload = {
        "token": custom_token,
        "returnSecureToken": True,
    }

    params = {"key": settings.FIREBASE_WEB_API_KEY}

    response = httpx.post(
        IDENTITY_TOOLKIT_URL,
        json=payload,
        params=params,
        timeout=30.0,
    )
    response.raise_for_status()

    return response.json()


def main() -> None:
    """
    Main function to generate and display a Firebase ID Token.
    """
    parser = argparse.ArgumentParser(
        description="Generate a Firebase ID Token for testing."
    )
    parser.add_argument(
        "--uid",
        type=str,
        default="test-user-001",
        help="User ID to generate token for (default: test-user-001)",
    )
    args = parser.parse_args()

    print(f"[1/3] Initializing Firebase Admin SDK...")
    try:
        initialize_firebase()
        print("      Firebase initialized successfully.")
    except Exception as e:
        print(f"      ERROR: Failed to initialize Firebase: {e}")
        sys.exit(1)

    print(f"[2/3] Creating Custom Token for UID: {args.uid}...")
    try:
        custom_token = create_custom_token(args.uid)
        print(f"      Custom Token created (length: {len(custom_token)} chars)")
    except Exception as e:
        print(f"      ERROR: Failed to create custom token: {e}")
        sys.exit(1)

    print("[3/3] Exchanging Custom Token for ID Token...")
    try:
        result = exchange_custom_token_for_id_token(custom_token)
        id_token = result.get("idToken", "")
        expires_in = result.get("expiresIn", "unknown")

        print("\n" + "=" * 60)
        print("SUCCESS! Firebase ID Token Generated")
        print("=" * 60)
        print(f"\nExpires in: {expires_in} seconds")
        print(f"\nID Token:\n{id_token}")
        print("\n" + "=" * 60)
        print("\nUsage example:")
        print(f'  curl -H "Authorization: Bearer {id_token[:50]}..." <API_URL>')

    except ValueError as e:
        print(f"      ERROR: {e}")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"      ERROR: HTTP request failed: {e.response.status_code}")
        print(f"      Response: {e.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
