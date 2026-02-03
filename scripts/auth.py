#!/usr/bin/env python3
"""
Firebase Authentication CLI (Dev Tool).

This script provides commands to manage Firebase user authentication:
- signup: Create a new user with email/password
- login: Authenticate and get an ID Token
- refresh: Renew an expired token using a refresh token

Usage:
    python scripts/auth.py signup -e user@example.com -p password123
    python scripts/auth.py login -e user@example.com -p password123
    python scripts/auth.py refresh -t <refresh_token>

    # Quiet mode (only outputs the token, useful for scripting)
    TOKEN=$(python scripts/auth.py login -e user@example.com -p password123 -q)

Requirements:
    - FIREBASE_WEB_API_KEY must be set in .env or environment variables
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import httpx

from core.config import settings

# Firebase Identity Toolkit REST API endpoints
FIREBASE_API_BASE = "https://identitytoolkit.googleapis.com/v1/accounts"
SIGNUP_URL = f"{FIREBASE_API_BASE}:signUp"
LOGIN_URL = f"{FIREBASE_API_BASE}:signInWithPassword"
REFRESH_URL = "https://securetoken.googleapis.com/v1/token"


class FirebaseAuthError(Exception):
    """Custom exception for Firebase authentication errors."""

    def __init__(self, message: str, error_code: str | None = None) -> None:
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


def _get_api_key() -> str:
    """
    Returns the Firebase Web API Key from settings.

    Raises:
        ValueError: If FIREBASE_WEB_API_KEY is not configured.
    """
    if not settings.FIREBASE_WEB_API_KEY:
        raise ValueError(
            "FIREBASE_WEB_API_KEY is not set.\n"
            "Please add it to your .env file or environment variables.\n"
            "You can find it in Firebase Console > Project Settings > "
            "General > Web API Key"
        )
    return settings.FIREBASE_WEB_API_KEY


def _handle_firebase_error(response: httpx.Response) -> None:
    """
    Parses Firebase error response and raises a descriptive exception.

    Args:
        response: The HTTP response from Firebase API.

    Raises:
        FirebaseAuthError: With a user-friendly error message.
    """
    try:
        error_data = response.json().get("error", {})
        error_code = error_data.get("message", "UNKNOWN_ERROR")

        # Map Firebase error codes to user-friendly messages
        error_messages = {
            "EMAIL_EXISTS": "This email is already registered. Try logging in instead.",
            "INVALID_EMAIL": "The email address is not valid.",
            "WEAK_PASSWORD": "Password must be at least 6 characters.",
            "EMAIL_NOT_FOUND": "No account found with this email.",
            "INVALID_PASSWORD": "Incorrect password.",
            "INVALID_LOGIN_CREDENTIALS": "Invalid email or password.",
            "USER_DISABLED": "This account has been disabled.",
            "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many failed attempts. Try again later.",
            "INVALID_REFRESH_TOKEN": "The refresh token is invalid or expired.",
            "TOKEN_EXPIRED": "The token has expired. Please login again.",
        }

        message = error_messages.get(error_code, f"Firebase error: {error_code}")
        raise FirebaseAuthError(message, error_code)

    except (KeyError, ValueError):
        raise FirebaseAuthError(
            f"HTTP {response.status_code}: {response.text}"
        ) from None


def signup(email: str, password: str) -> dict:
    """
    Creates a new user account with email and password.

    Args:
        email: The user's email address.
        password: The user's password (min 6 characters).

    Returns:
        A dictionary containing 'idToken', 'refreshToken', 'localId' (uid), etc.

    Raises:
        FirebaseAuthError: If signup fails.
    """
    api_key = _get_api_key()

    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }

    response = httpx.post(
        SIGNUP_URL,
        json=payload,
        params={"key": api_key},
        timeout=30.0,
    )

    if response.status_code != 200:
        _handle_firebase_error(response)

    return response.json()


def login(email: str, password: str) -> dict:
    """
    Authenticates a user with email and password.

    Args:
        email: The user's email address.
        password: The user's password.

    Returns:
        A dictionary containing 'idToken', 'refreshToken', 'localId' (uid), etc.

    Raises:
        FirebaseAuthError: If login fails.
    """
    api_key = _get_api_key()

    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    }

    response = httpx.post(
        LOGIN_URL,
        json=payload,
        params={"key": api_key},
        timeout=30.0,
    )

    if response.status_code != 200:
        _handle_firebase_error(response)

    return response.json()


def refresh(refresh_token: str) -> dict:
    """
    Exchanges a refresh token for a new ID token.

    Args:
        refresh_token: The refresh token from a previous login/signup.

    Returns:
        A dictionary containing 'id_token', 'refresh_token', 'expires_in', etc.

    Raises:
        FirebaseAuthError: If refresh fails.
    """
    api_key = _get_api_key()

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    response = httpx.post(
        REFRESH_URL,
        data=payload,  # Note: refresh endpoint uses form data, not JSON
        params={"key": api_key},
        timeout=30.0,
    )

    if response.status_code != 200:
        _handle_firebase_error(response)

    return response.json()


def cmd_signup(args: argparse.Namespace) -> None:
    """Handler for the 'signup' command."""
    try:
        result = signup(args.email, args.password)

        if args.quiet:
            print(result["idToken"])
            return

        print("\n" + "=" * 60)
        print("SUCCESS! User created")
        print("=" * 60)
        print(f"\nUser ID (uid): {result.get('localId')}")
        print(f"Email: {result.get('email')}")
        print(f"Expires in: {result.get('expiresIn')} seconds")
        print(f"\nID Token:\n{result.get('idToken')}")
        print(f"\nRefresh Token:\n{result.get('refreshToken')}")
        print("\n" + "=" * 60)
        print("\nUsage example:")
        token_preview = result.get("idToken", "")[:50]
        print(f'  curl -H "Authorization: Bearer {token_preview}..." <API_URL>')

    except (ValueError, FirebaseAuthError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except httpx.RequestError as e:
        print(f"ERROR: Network request failed: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_login(args: argparse.Namespace) -> None:
    """Handler for the 'login' command."""
    try:
        result = login(args.email, args.password)

        if args.quiet:
            print(result["idToken"])
            return

        print("\n" + "=" * 60)
        print("SUCCESS! Logged in")
        print("=" * 60)
        print(f"\nUser ID (uid): {result.get('localId')}")
        print(f"Email: {result.get('email')}")
        print(f"Expires in: {result.get('expiresIn')} seconds")
        print(f"\nID Token:\n{result.get('idToken')}")
        print(f"\nRefresh Token:\n{result.get('refreshToken')}")
        print("\n" + "=" * 60)
        print("\nUsage example:")
        token_preview = result.get("idToken", "")[:50]
        print(f'  curl -H "Authorization: Bearer {token_preview}..." <API_URL>')

    except (ValueError, FirebaseAuthError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except httpx.RequestError as e:
        print(f"ERROR: Network request failed: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_refresh(args: argparse.Namespace) -> None:
    """Handler for the 'refresh' command."""
    try:
        result = refresh(args.token)

        if args.quiet:
            print(result["id_token"])
            return

        print("\n" + "=" * 60)
        print("SUCCESS! Token refreshed")
        print("=" * 60)
        print(f"\nUser ID (uid): {result.get('user_id')}")
        print(f"Expires in: {result.get('expires_in')} seconds")
        print(f"\nNew ID Token:\n{result.get('id_token')}")
        print(f"\nNew Refresh Token:\n{result.get('refresh_token')}")
        print("\n" + "=" * 60)

    except (ValueError, FirebaseAuthError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except httpx.RequestError as e:
        print(f"ERROR: Network request failed: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Firebase Authentication CLI for Stellar Gateway",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new user
  %(prog)s signup -e user@example.com -p mypassword123

  # Login and get token
  %(prog)s login -e user@example.com -p mypassword123

  # Login in quiet mode (only outputs token, great for scripts)
  TOKEN=$(%(prog)s login -e user@example.com -p mypassword123 -q)
  curl -H "Authorization: Bearer $TOKEN" https://your-api.com/people/1

  # Refresh an expired token
  %(prog)s refresh -t <your_refresh_token>
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Signup command
    signup_parser = subparsers.add_parser("signup", help="Create a new user account")
    signup_parser.add_argument(
        "-e",
        "--email",
        required=True,
        help="User's email address",
    )
    signup_parser.add_argument(
        "-p",
        "--password",
        required=True,
        help="User's password (min 6 characters)",
    )
    signup_parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Only output the ID token (useful for scripting)",
    )
    signup_parser.set_defaults(func=cmd_signup)

    # Login command
    login_parser = subparsers.add_parser("login", help="Login with email and password")
    login_parser.add_argument(
        "-e",
        "--email",
        required=True,
        help="User's email address",
    )
    login_parser.add_argument(
        "-p",
        "--password",
        required=True,
        help="User's password",
    )
    login_parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Only output the ID token (useful for scripting)",
    )
    login_parser.set_defaults(func=cmd_login)

    # Refresh command
    refresh_parser = subparsers.add_parser("refresh", help="Refresh an expired token")
    refresh_parser.add_argument(
        "-t",
        "--token",
        required=True,
        help="The refresh token from a previous login",
    )
    refresh_parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Only output the new ID token (useful for scripting)",
    )
    refresh_parser.set_defaults(func=cmd_refresh)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
