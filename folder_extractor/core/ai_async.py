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
from typing import Any, Optional

import google.generativeai as genai
from google.api_core.exceptions import (
    InternalServerError,
    ResourceExhausted,
    ServiceUnavailable,
)

from folder_extractor.core.ai_resilience import ai_retry
from folder_extractor.core.preprocessor import FilePreprocessor, PreprocessorError
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
    ) -> dict[str, Any]:
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

    Supports: gemini-3-flash-preview model with JSON response format
    Features: Automatic retry on rate limits and server errors
    """

    DEFAULT_MODEL: str = "gemini-3-flash-preview"

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
        self.preprocessor = FilePreprocessor()

    @ai_retry
    async def analyze_file(
        self,
        filepath: Path,
        mime_type: str,
        prompt: str,
    ) -> dict[str, Any]:
        """
        Analyze file using Gemini model with automatic retry.

        Uploads file, sends prompt, and returns JSON response.
        Automatically retries on rate limits (429) and server errors (5xx).
        Files are automatically preprocessed before upload if they exceed
        size limits or use exotic formats.

        Args:
            filepath: Path to the file to analyze. Files > 20MB are
                automatically optimized before upload.
            mime_type: MIME type of the file
            prompt: Analysis prompt

        Returns:
            Parsed JSON response as dictionary

        Raises:
            AIClientError: If file doesn't exist, is not a file, parsing fails,
                or file preprocessing fails

        Notes:
            Files are automatically preprocessed before upload:
            - Images > 20MB are resized to max 2048px and converted to JPG
            - PDFs > 20MB have only first 5 pages extracted
            - Exotic formats (TIFF, BMP, WebP) are converted to JPG
            - Temporary files are automatically cleaned up after analysis
        """
        # Validate filepath
        if not filepath.exists():
            raise AIClientError(f"File does not exist: {filepath}")

        if not filepath.is_file():
            raise AIClientError(f"Path is not a file: {filepath}")

        # Preprocess file (may create optimized temporary copy)
        try:
            optimized_path, needs_cleanup = self.preprocessor.prepare_file(filepath)
            logger.info(
                f"File preprocessed: {filepath.name} -> {optimized_path.name} "
                f"(cleanup={needs_cleanup})"
            )
        except PreprocessorError as e:
            raise AIClientError(f"File preprocessing failed: {e}") from e

        try:
            logger.debug(f"Uploading file: {optimized_path}")

            # Upload file in thread pool (blocking operation)
            # Use run_in_executor for Python 3.8 compatibility (to_thread requires 3.9+)
            loop = asyncio.get_running_loop()
            uploaded_file = await loop.run_in_executor(
                None,  # Use default executor
                lambda: genai.upload_file(
                    path=str(optimized_path), mime_type=mime_type
                ),
            )

            # Generate content with JSON response format
            response = await self.model.generate_content_async(
                [uploaded_file, prompt],
                generation_config={"response_mime_type": "application/json"},
            )

            # Parse JSON response
            try:
                result = json.loads(response.text)
                logger.info(f"File analyzed successfully: {filepath.name}")
                return result
            except json.JSONDecodeError as e:
                raise AIClientError(
                    f"Failed to parse JSON response: {e}. "
                    f"Response was: {response.text[:200]}..."
                ) from e

        except (ResourceExhausted, InternalServerError, ServiceUnavailable):
            # Re-raise retriable exceptions for @ai_retry decorator to handle
            raise
        except AIClientError:
            # Re-raise our own errors (not retriable)
            raise
        except Exception as e:
            # Wrap only non-retriable, unexpected errors
            raise AIClientError(f"AI analysis failed: {e}") from e
        finally:
            # Always cleanup temporary files
            if needs_cleanup:
                self._cleanup_temp_file(optimized_path)

    def _cleanup_temp_file(self, filepath: Path) -> None:
        """Clean up temporary file created by preprocessor.

        Attempts to delete the temporary file and its parent directory
        if empty. Errors are logged but not raised, as cleanup failures
        should not block the main operation.

        Args:
            filepath: Path to temporary file to delete

        Note:
            Silently ignores errors if file doesn't exist or can't be deleted.
        """
        try:
            if filepath.exists():
                filepath.unlink()
                logger.debug(f"Cleaned up temporary file: {filepath}")

                # Remove parent directory if empty
                parent = filepath.parent
                if parent.exists() and not any(parent.iterdir()):
                    parent.rmdir()
                    logger.debug(f"Removed empty temp directory: {parent}")

        except OSError as e:
            logger.warning(f"Failed to cleanup temporary file {filepath}: {e}")
