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
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import httpx

from core.config import settings

# Firebase Identity Toolkit REST API endpoints
FIREBASE_API_BASE = "https://identitytoolkit.googleapis.com/v1/accounts"
SIGNUP_URL = f"{FIREBASE_API_BASE}:signUp"
LOGIN_URL = f"{FIREBASE_API_BASE}:signInWithPassword"
REFRESH_URL = "https://securetoken.googleapis.com/v1/token"


@dataclass(frozen=True)
class AuthCommandConfig:
    """Configuration for authentication command output."""

    title: str
    token_key: str = "idToken"
    show_usage: bool = True


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


def _firebase_request(url: str, payload: dict, use_json: bool = True) -> dict:
    """
    Makes a request to Firebase API with common error handling.

    Args:
        url: The Firebase API endpoint URL.
        payload: The request payload.
        use_json: If True, send as JSON; if False, send as form data.

    Returns:
        The JSON response from Firebase.

    Raises:
        FirebaseAuthError: If the request fails.
    """
    api_key = _get_api_key()

    request_kwargs: dict = {
        "params": {"key": api_key},
        "timeout": 30.0,
    }
    if use_json:
        request_kwargs["json"] = payload
    else:
        request_kwargs["data"] = payload

    response = httpx.post(url, **request_kwargs)

    if response.status_code != 200:
        _handle_firebase_error(response)

    return response.json()


def _auth_with_credentials(url: str, email: str, password: str) -> dict:
    """
    Authenticates with email/password to a Firebase endpoint.

    Args:
        url: The Firebase API endpoint URL.
        email: The user's email address.
        password: The user's password.

    Returns:
        A dictionary containing 'idToken', 'refreshToken', 'localId' (uid), etc.

    Raises:
        FirebaseAuthError: If authentication fails.
    """
    return _firebase_request(url, {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    })


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
    return _firebase_request(REFRESH_URL, {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }, use_json=False)


def _print_auth_result(result: dict, config: AuthCommandConfig) -> None:
    """
    Prints formatted authentication result to stdout.

    Args:
        result: The authentication result dictionary.
        config: The command configuration with title, token_key, and show_usage.
    """
    print("\n" + "=" * 60)
    print(f"SUCCESS! {config.title}")
    print("=" * 60)

    # User ID (different keys for different endpoints)
    user_id = result.get("localId") or result.get("user_id")
    print(f"\nUser ID (uid): {user_id}")

    # Email (only present in signup/login responses)
    if "email" in result:
        print(f"Email: {result.get('email')}")

    # Expiration (different keys for different endpoints)
    expires_in = result.get("expiresIn") or result.get("expires_in")
    print(f"Expires in: {expires_in} seconds")

    # Tokens
    print(f"\nID Token:\n{result.get(config.token_key)}")

    refresh_key = "refreshToken" if "refreshToken" in result else "refresh_token"
    print(f"\nRefresh Token:\n{result.get(refresh_key)}")

    print("\n" + "=" * 60)

    # Usage example
    if config.show_usage:
        print("\nUsage example:")
        token_preview = result.get(config.token_key, "")[:50]
        print(f'  curl -H "Authorization: Bearer {token_preview}..." <API_URL>')


def _run_auth_command(
    auth_func: Callable[[], dict],
    args: argparse.Namespace,
    config: AuthCommandConfig,
) -> None:
    """
    Generic handler for authentication commands with error handling.

    Args:
        auth_func: The authentication function to call.
        args: Parsed command line arguments.
        config: The command configuration with title, token_key, and show_usage.
    """
    try:
        result = auth_func()

        if args.quiet:
            print(result[config.token_key])
            return

        _print_auth_result(result, config)

    except (ValueError, FirebaseAuthError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except httpx.RequestError as e:
        print(f"ERROR: Network request failed: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_signup(args: argparse.Namespace) -> None:
    """Handler for the 'signup' command."""
    _run_auth_command(
        lambda: _auth_with_credentials(SIGNUP_URL, args.email, args.password),
        args,
        AuthCommandConfig(title="User created"),
    )


def cmd_login(args: argparse.Namespace) -> None:
    """Handler for the 'login' command."""
    _run_auth_command(
        lambda: _auth_with_credentials(LOGIN_URL, args.email, args.password),
        args,
        AuthCommandConfig(title="Logged in"),
    )


def cmd_refresh(args: argparse.Namespace) -> None:
    """Handler for the 'refresh' command."""
    config = AuthCommandConfig(
        title="Token refreshed",
        token_key="id_token",
        show_usage=False,
    )
    _run_auth_command(lambda: refresh(args.token), args, config)


def _create_parser() -> argparse.ArgumentParser:
    """Creates and configures the argument parser."""
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
    _add_email_password_args(signup_parser)
    _add_quiet_arg(signup_parser)
    signup_parser.set_defaults(func=cmd_signup)

    # Login command
    login_parser = subparsers.add_parser("login", help="Login with email and password")
    _add_email_password_args(login_parser)
    _add_quiet_arg(login_parser)
    login_parser.set_defaults(func=cmd_login)

    # Refresh command
    refresh_parser = subparsers.add_parser("refresh", help="Refresh an expired token")
    refresh_parser.add_argument(
        "-t",
        "--token",
        required=True,
        help="The refresh token from a previous login",
    )
    _add_quiet_arg(refresh_parser)
    refresh_parser.set_defaults(func=cmd_refresh)

    return parser


def _add_email_password_args(parser: argparse.ArgumentParser) -> None:
    """Adds email and password arguments to a parser."""
    parser.add_argument(
        "-e",
        "--email",
        required=True,
        help="User's email address",
    )
    parser.add_argument(
        "-p",
        "--password",
        required=True,
        help="User's password (min 6 characters)",
    )


def _add_quiet_arg(parser: argparse.ArgumentParser) -> None:
    """Adds the quiet flag argument to a parser."""
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Only output the ID token (useful for scripting)",
    )


def main() -> None:
    """Main entry point for the CLI."""
    parser = _create_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
