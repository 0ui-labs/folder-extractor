"""
Asynchronous AI client module for Google Gemini.

Provides async interface for file analysis using Google's Gemini models
with automatic retry handling for transient failures.
"""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional

import google.generativeai as genai
from google.api_core.exceptions import (
    InternalServerError,
    ResourceExhausted,
    ServiceUnavailable,
)

from folder_extractor.core.ai_resilience import ai_retry
from folder_extractor.core.security import load_google_api_key

logger = logging.getLogger(__name__)


class AIClientError(Exception):
    """Raised when AI client operations fail."""

    pass


class IAIClient(ABC):
    """
    Interface for AI client implementations.

    Provides async methods for file analysis with automatic
    retry handling for transient failures.
    """

    @abstractmethod
    async def analyze_file(
        self,
        filepath: Path,
        mime_type: str,
        prompt: str,
    ) -> Dict[str, Any]:
        """
        Analyze a file using AI model.

        Args:
            filepath: Path to the file to analyze
            mime_type: MIME type of the file (e.g., "image/jpeg")
            prompt: Analysis prompt for the AI model

        Returns:
            Dictionary containing the analysis results (parsed JSON)

        Raises:
            AIClientError: If analysis fails after all retries
        """
        pass


class AsyncGeminiClient(IAIClient):
    """
    Async client for Google Gemini API.

    Supports: gemini-1.5-flash model with JSON response format
    Features: Automatic retry on rate limits and server errors
    """

    DEFAULT_MODEL: str = "gemini-1.5-flash"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = DEFAULT_MODEL,
    ):
        """
        Initialize Gemini client.

        Args:
            api_key: Google API key (loads from env if not provided)
            model_name: Gemini model to use (default: gemini-1.5-flash)

        Raises:
            APIKeyError: If API key cannot be loaded
        """
        if api_key is None:
            api_key = load_google_api_key()

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name

    @ai_retry
    async def analyze_file(
        self,
        filepath: Path,
        mime_type: str,
        prompt: str,
    ) -> Dict[str, Any]:
        """
        Analyze file using Gemini model with automatic retry.

        Uploads file, sends prompt, and returns JSON response.
        Automatically retries on rate limits (429) and server errors (5xx).

        Args:
            filepath: Path to the file to analyze
            mime_type: MIME type of the file
            prompt: Analysis prompt

        Returns:
            Parsed JSON response as dictionary

        Raises:
            AIClientError: If file doesn't exist, is not a file, or parsing fails
        """
        # Validate filepath
        if not filepath.exists():
            raise AIClientError(f"File does not exist: {filepath}")

        if not filepath.is_file():
            raise AIClientError(f"Path is not a file: {filepath}")

        try:
            # Upload file in thread pool (blocking operation)
            uploaded_file = await asyncio.to_thread(
                genai.upload_file,
                path=str(filepath),
                mime_type=mime_type,
            )

            # Generate content with JSON response format
            response = await self.model.generate_content_async(
                [uploaded_file, prompt],
                generation_config={"response_mime_type": "application/json"},
            )

            # Parse JSON response
            try:
                return json.loads(response.text)
            except json.JSONDecodeError as e:
                raise AIClientError(
                    f"Failed to parse JSON response: {e}. "
                    f"Response was: {response.text[:200]}..."
                )

        except (ResourceExhausted, InternalServerError, ServiceUnavailable):
            # Re-raise retriable exceptions for @ai_retry decorator to handle
            raise
        except AIClientError:
            # Re-raise our own errors (not retriable)
            raise
        except Exception as e:
            # Wrap only non-retriable, unexpected errors
            raise AIClientError(f"AI analysis failed: {e}") from e
