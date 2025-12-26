"""
Security and credential management module.

Handles secure loading of API keys from environment variables
and .env files with proper error handling.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


class APIKeyError(Exception):
    """Raised when API key cannot be loaded or is invalid."""

    pass


def load_api_key(
    key_name: str = "GOOGLE_API_KEY",
    env_file: Optional[Path] = None,
    required: bool = True,
) -> Optional[str]:
    """
    Load API key from environment variables or .env file.

    Search order:
    1. Environment variable (os.environ)
    2. .env file in current directory (if env_file not specified)
    3. .env file at specified path (if env_file provided)

    Args:
        key_name: Name of the environment variable (default: "GOOGLE_API_KEY")
        env_file: Optional path to .env file. If None, searches in current directory
        required: If True, raises APIKeyError when key not found

    Returns:
        The API key string, or None if not found and required=False

    Raises:
        APIKeyError: If key not found and required=True

    Example:
        >>> api_key = load_api_key()  # Loads GOOGLE_API_KEY
        >>> api_key = load_api_key("CUSTOM_KEY", required=False)
    """
    # Check environment variable first (highest priority)
    api_key = os.environ.get(key_name)
    if api_key:
        return api_key.strip()

    # Load .env file
    if env_file is not None:
        load_dotenv(env_file)
    else:
        load_dotenv()

    # Check environment variable again after .env load
    api_key = os.environ.get(key_name)
    if api_key:
        return api_key.strip()

    # Handle missing key
    if required:
        raise APIKeyError(
            f"API key '{key_name}' not found in environment variables or .env file. "
            f"Please set the environment variable or create a .env file with "
            f"{key_name}=your_key"
        )

    return None


def load_google_api_key(env_file: Optional[Path] = None) -> str:
    """
    Load Google Gemini API key.

    Convenience wrapper around load_api_key() specifically for Google API.

    Args:
        env_file: Optional path to .env file

    Returns:
        The Google API key

    Raises:
        APIKeyError: If key not found
    """
    result = load_api_key("GOOGLE_API_KEY", env_file=env_file, required=True)
    # result is guaranteed to be str when required=True (never None)
    assert result is not None  # for type checker
    return result
