"""Secure storage helpers for API keys."""

from __future__ import annotations

import keyring

SERVICE_NAME = "meshy_desktop_app"
ACCOUNT_NAME = "api_key"


def load_key() -> str | None:
    """Load the API key from secure storage."""
    return keyring.get_password(SERVICE_NAME, ACCOUNT_NAME)


def save_key(api_key: str) -> None:
    """Save the API key to secure storage."""
    keyring.set_password(SERVICE_NAME, ACCOUNT_NAME, api_key)


def delete_key() -> None:
    """Remove the API key from secure storage."""
    keyring.delete_password(SERVICE_NAME, ACCOUNT_NAME)
