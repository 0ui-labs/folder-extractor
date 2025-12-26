"""
Tests for AI client with retry handling and API mocking.

These tests verify:
1. Async file analysis with Google Gemini API
2. Retry mechanism for rate limits (429) and server errors (5xx)
3. API key loading and security
4. Error handling for invalid files and API failures

Note: These tests require google-generativeai which needs Python 3.9+.
The module will be skipped on Python 3.8 and earlier.
"""

from __future__ import annotations

import sys

import pytest

# Skip entire module on Python < 3.9 (google-generativeai requires 3.9+)
if sys.version_info < (3, 9):
    pytest.skip(
        "google-generativeai requires Python 3.9+",
        allow_module_level=True,
    )

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from google.api_core.exceptions import (
    InternalServerError,
    ResourceExhausted,
    ServiceUnavailable,
)

from folder_extractor.core.ai_async import (
    AIClientError,
    AsyncGeminiClient,
    IAIClient,
)
from folder_extractor.core.ai_resilience import ai_retry, create_ai_retry_decorator
from folder_extractor.core.security import APIKeyError

# Note: Individual async tests are marked with @pytest.mark.asyncio
# We don't use module-level pytestmark to avoid warnings on sync tests


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_uploaded_file():
    """
    Mock for genai.upload_file() response.

    Returns a mock object simulating Google's UploadedFile.
    """
    mock_file = Mock()
    mock_file.name = "files/test-file-id-12345"
    mock_file.uri = (
        "https://generativelanguage.googleapis.com/v1beta/files/test-file-id-12345"
    )
    mock_file.mime_type = "image/jpeg"
    return mock_file


@pytest.fixture
def mock_gemini_response():
    """
    Factory fixture to create mock Gemini API responses.

    Usage:
        response = mock_gemini_response({"category": "document", "confidence": 0.95})
    """

    def _create(response_data: dict) -> Mock:
        mock_response = Mock()
        mock_response.text = json.dumps(response_data)
        return mock_response

    return _create


@pytest.fixture
def mock_generative_model(mock_gemini_response):
    """
    Mock for genai.GenerativeModel with async generate_content_async.

    Returns a mock model that can be configured for different test scenarios.
    """
    mock_model = Mock()
    # Default successful response
    default_response = mock_gemini_response({"status": "success", "result": "analyzed"})
    mock_model.generate_content_async = AsyncMock(return_value=default_response)
    return mock_model


@pytest.fixture
def test_image_file(temp_dir):
    """
    Create a test image file for analysis.

    Returns path to a dummy image file with known content.
    """
    image_path = Path(temp_dir) / "test_image.jpg"
    # Create a minimal valid JPEG header (for file existence tests)
    image_path.write_bytes(
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    )
    return image_path


# =============================================================================
# TestAsyncGeminiClient
# =============================================================================


class TestAsyncGeminiClient:
    """Tests for AsyncGeminiClient with mocked Google API."""

    # -------------------------------------------------------------------------
    # Initialization Tests
    # -------------------------------------------------------------------------

    def test_init_with_explicit_api_key(self):
        """Client initializes successfully with explicit API key."""
        with patch(
            "folder_extractor.core.ai_async.genai.configure"
        ) as mock_configure, patch(
            "folder_extractor.core.ai_async.genai.GenerativeModel"
        ) as mock_model:
            AsyncGeminiClient(api_key="test-api-key-12345")

            mock_configure.assert_called_once_with(api_key="test-api-key-12345")
            mock_model.assert_called_once_with("gemini-1.5-flash")

    def test_init_loads_api_key_from_environment(self, monkeypatch):
        """Client loads API key from environment when not provided."""
        monkeypatch.setenv("GOOGLE_API_KEY", "env-api-key-67890")

        with patch(
            "folder_extractor.core.ai_async.genai.configure"
        ) as mock_configure, patch(
            "folder_extractor.core.ai_async.genai.GenerativeModel"
        ):
            AsyncGeminiClient()

            mock_configure.assert_called_once_with(api_key="env-api-key-67890")

    def test_init_raises_api_key_error_when_key_missing(self, monkeypatch):
        """Client raises APIKeyError when no API key available."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        # Also ensure no .env file interferes
        with patch("folder_extractor.core.security.load_dotenv"):
            with pytest.raises(APIKeyError, match="API key.*not found"):
                AsyncGeminiClient()

    def test_init_with_custom_model_name(self):
        """Client accepts custom model name."""
        with patch("folder_extractor.core.ai_async.genai.configure"), patch(
            "folder_extractor.core.ai_async.genai.GenerativeModel"
        ) as mock_model:
            AsyncGeminiClient(api_key="test-key", model_name="gemini-1.5-pro")

            mock_model.assert_called_once_with("gemini-1.5-pro")

    # -------------------------------------------------------------------------
    # Successful Analysis Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_analyze_file_returns_parsed_json(
        self, test_image_file, mock_uploaded_file, mock_gemini_response
    ):
        """analyze_file returns parsed JSON from Gemini response."""
        expected_result = {
            "category": "image",
            "objects": ["cat", "tree"],
            "confidence": 0.92,
        }

        with patch("folder_extractor.core.ai_async.genai.configure"), patch(
            "folder_extractor.core.ai_async.genai.GenerativeModel"
        ) as mock_model_class, patch(
            "folder_extractor.core.ai_async.genai.upload_file",
            return_value=mock_uploaded_file,
        ):
            # Setup mock model
            mock_model = Mock()
            mock_model.generate_content_async = AsyncMock(
                return_value=mock_gemini_response(expected_result)
            )
            mock_model_class.return_value = mock_model

            client = AsyncGeminiClient(api_key="test-key")
            result = await client.analyze_file(
                filepath=test_image_file,
                mime_type="image/jpeg",
                prompt="Analyze this image",
            )

            assert result == expected_result
            assert result["category"] == "image"
            assert len(result["objects"]) == 2

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "mime_type,file_extension",
        [
            ("image/jpeg", ".jpg"),
            ("image/png", ".png"),
            ("application/pdf", ".pdf"),
            ("text/plain", ".txt"),
            ("video/mp4", ".mp4"),
        ],
    )
    async def test_analyze_file_handles_different_mime_types(
        self,
        temp_dir,
        mime_type,
        file_extension,
        mock_uploaded_file,
        mock_gemini_response,
    ):
        """analyze_file correctly handles various MIME types."""
        test_file = Path(temp_dir) / f"test{file_extension}"
        test_file.write_bytes(b"test content")

        with patch("folder_extractor.core.ai_async.genai.configure"), patch(
            "folder_extractor.core.ai_async.genai.GenerativeModel"
        ) as mock_model_class, patch(
            "folder_extractor.core.ai_async.genai.upload_file",
            return_value=mock_uploaded_file,
        ) as mock_upload:
            mock_model = Mock()
            mock_model.generate_content_async = AsyncMock(
                return_value=mock_gemini_response({"type": mime_type})
            )
            mock_model_class.return_value = mock_model

            client = AsyncGeminiClient(api_key="test-key")
            result = await client.analyze_file(
                filepath=test_file, mime_type=mime_type, prompt="Analyze"
            )

            # Verify genai.upload_file was called with correct mime_type
            mock_upload.assert_called_once()
            call_kwargs = mock_upload.call_args.kwargs
            assert call_kwargs["mime_type"] == mime_type
            assert result["type"] == mime_type

    # -------------------------------------------------------------------------
    # Retry Mechanism Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_analyze_file_retries_on_rate_limit_then_succeeds(
        self, test_image_file, mock_uploaded_file, mock_gemini_response
    ):
        """
        analyze_file retries on ResourceExhausted (429) and succeeds on second attempt.

        This is the critical test scenario from the task requirements:
        1. First attempt -> Error 429
        2. Second attempt -> Success
        """
        success_response = mock_gemini_response({"status": "success"})

        with patch("folder_extractor.core.ai_async.genai.configure"), patch(
            "folder_extractor.core.ai_async.genai.GenerativeModel"
        ) as mock_model_class, patch(
            "folder_extractor.core.ai_async.genai.upload_file",
            return_value=mock_uploaded_file,
        ):
            # Setup mock model with side_effect: first call raises, second succeeds
            mock_model = Mock()
            mock_model.generate_content_async = AsyncMock(
                side_effect=[ResourceExhausted("Rate limit exceeded"), success_response]
            )
            mock_model_class.return_value = mock_model

            client = AsyncGeminiClient(api_key="test-key")
            result = await client.analyze_file(
                filepath=test_image_file, mime_type="image/jpeg", prompt="Test prompt"
            )

            # Verify retry happened: generate_content_async called twice
            assert mock_model.generate_content_async.call_count == 2
            assert result["status"] == "success"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "exception_class,error_message",
        [
            (ResourceExhausted, "Rate limit exceeded"),
            (InternalServerError, "Internal server error"),
            (ServiceUnavailable, "Service temporarily unavailable"),
        ],
    )
    async def test_analyze_file_retries_on_various_errors(
        self,
        test_image_file,
        mock_uploaded_file,
        mock_gemini_response,
        exception_class,
        error_message,
    ):
        """analyze_file retries on ResourceExhausted, InternalServerError, and ServiceUnavailable."""
        success_response = mock_gemini_response({"recovered": True})

        with patch("folder_extractor.core.ai_async.genai.configure"), patch(
            "folder_extractor.core.ai_async.genai.GenerativeModel"
        ) as mock_model_class, patch(
            "folder_extractor.core.ai_async.genai.upload_file",
            return_value=mock_uploaded_file,
        ):
            mock_model = Mock()
            mock_model.generate_content_async = AsyncMock(
                side_effect=[exception_class(error_message), success_response]
            )
            mock_model_class.return_value = mock_model

            client = AsyncGeminiClient(api_key="test-key")
            result = await client.analyze_file(
                filepath=test_image_file, mime_type="image/jpeg", prompt="Test"
            )

            assert mock_model.generate_content_async.call_count == 2
            assert result["recovered"] is True

    @pytest.mark.asyncio
    async def test_analyze_file_fails_after_max_retries(
        self, test_image_file, mock_uploaded_file
    ):
        """analyze_file raises exception after exhausting all retry attempts."""
        with patch("folder_extractor.core.ai_async.genai.configure"), patch(
            "folder_extractor.core.ai_async.genai.GenerativeModel"
        ) as mock_model_class, patch(
            "folder_extractor.core.ai_async.genai.upload_file",
            return_value=mock_uploaded_file,
        ):
            # Always raise ResourceExhausted
            mock_model = Mock()
            mock_model.generate_content_async = AsyncMock(
                side_effect=ResourceExhausted("Persistent rate limit")
            )
            mock_model_class.return_value = mock_model

            client = AsyncGeminiClient(api_key="test-key")

            with pytest.raises(ResourceExhausted, match="Persistent rate limit"):
                await client.analyze_file(
                    filepath=test_image_file, mime_type="image/jpeg", prompt="Test"
                )

            # Verify it tried multiple times (default: 5 attempts)
            assert mock_model.generate_content_async.call_count == 5

    # -------------------------------------------------------------------------
    # Error Handling Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_analyze_file_raises_error_for_nonexistent_file(self, temp_dir):
        """analyze_file raises AIClientError for non-existent files."""
        nonexistent_file = Path(temp_dir) / "does_not_exist.jpg"

        with patch("folder_extractor.core.ai_async.genai.configure"), patch(
            "folder_extractor.core.ai_async.genai.GenerativeModel"
        ):
            client = AsyncGeminiClient(api_key="test-key")

            with pytest.raises(
                AIClientError, match="[Ff]ile.*not.*exist|does not exist"
            ):
                await client.analyze_file(
                    filepath=nonexistent_file, mime_type="image/jpeg", prompt="Test"
                )

    @pytest.mark.asyncio
    async def test_analyze_file_raises_error_for_directory(self, temp_dir):
        """analyze_file raises AIClientError when path is a directory."""
        directory_path = Path(temp_dir) / "test_dir"
        directory_path.mkdir()

        with patch("folder_extractor.core.ai_async.genai.configure"), patch(
            "folder_extractor.core.ai_async.genai.GenerativeModel"
        ):
            client = AsyncGeminiClient(api_key="test-key")

            with pytest.raises(AIClientError, match="[Nn]ot a file|not.*file"):
                await client.analyze_file(
                    filepath=directory_path, mime_type="image/jpeg", prompt="Test"
                )

    @pytest.mark.asyncio
    async def test_analyze_file_raises_error_for_invalid_json_response(
        self, test_image_file, mock_uploaded_file
    ):
        """analyze_file raises AIClientError when response is not valid JSON."""
        with patch("folder_extractor.core.ai_async.genai.configure"), patch(
            "folder_extractor.core.ai_async.genai.GenerativeModel"
        ) as mock_model_class, patch(
            "folder_extractor.core.ai_async.genai.upload_file",
            return_value=mock_uploaded_file,
        ):
            # Mock response with invalid JSON
            mock_response = Mock()
            mock_response.text = "This is not valid JSON {{"

            mock_model = Mock()
            mock_model.generate_content_async = AsyncMock(return_value=mock_response)
            mock_model_class.return_value = mock_model

            client = AsyncGeminiClient(api_key="test-key")

            with pytest.raises(AIClientError, match="[Jj][Ss][Oo][Nn]|[Pp]arse"):
                await client.analyze_file(
                    filepath=test_image_file, mime_type="image/jpeg", prompt="Test"
                )


# =============================================================================
# TestRetryConfiguration
# =============================================================================


class TestRetryConfiguration:
    """Tests for retry configuration and decorator behavior."""

    def test_create_ai_retry_decorator_with_custom_parameters(self):
        """create_ai_retry_decorator accepts custom retry parameters."""
        custom_retry = create_ai_retry_decorator(
            max_attempts=3, multiplier=2, min_wait=1, max_wait=10
        )

        # Verify decorator is callable
        assert callable(custom_retry)

        # Verify it can decorate a function
        @custom_retry
        async def test_func():
            return "success"

        assert asyncio.run(test_func()) == "success"

    def test_ai_retry_decorator_is_preconfigured(self):
        """ai_retry is a pre-configured decorator ready to use."""
        assert callable(ai_retry)

        @ai_retry
        async def test_func():
            return "decorated"

        assert asyncio.run(test_func()) == "decorated"

    @pytest.mark.asyncio
    async def test_retry_decorator_logs_warnings_before_retry(
        self, test_image_file, mock_uploaded_file, caplog
    ):
        """Retry decorator logs warnings before each retry attempt."""
        import logging

        caplog.set_level(logging.WARNING)

        with patch("folder_extractor.core.ai_async.genai.configure"), patch(
            "folder_extractor.core.ai_async.genai.GenerativeModel"
        ) as mock_model_class, patch(
            "folder_extractor.core.ai_async.genai.upload_file",
            return_value=mock_uploaded_file,
        ):
            mock_model = Mock()
            mock_model.generate_content_async = AsyncMock(
                side_effect=[
                    ResourceExhausted("Rate limit"),
                    Mock(text='{"success": true}'),
                ]
            )
            mock_model_class.return_value = mock_model

            client = AsyncGeminiClient(api_key="test-key")
            await client.analyze_file(
                filepath=test_image_file, mime_type="image/jpeg", prompt="Test"
            )

            # Verify warning was logged (tenacity logs before retry)
            assert any("Retrying" in record.message for record in caplog.records)


# =============================================================================
# TestInterfaceCompliance
# =============================================================================


class TestInterfaceCompliance:
    """Tests for IAIClient interface compliance."""

    def test_async_gemini_client_implements_interface(self):
        """AsyncGeminiClient implements IAIClient interface."""
        with patch("folder_extractor.core.ai_async.genai.configure"), patch(
            "folder_extractor.core.ai_async.genai.GenerativeModel"
        ):
            client = AsyncGeminiClient(api_key="test-key")

            assert isinstance(client, IAIClient)
            assert hasattr(client, "analyze_file")
            assert callable(client.analyze_file)

    def test_interface_has_required_methods(self):
        """IAIClient interface defines required abstract methods."""
        assert hasattr(IAIClient, "analyze_file")

        # Verify it's abstract
        with pytest.raises(TypeError, match="[Aa]bstract|[Cc]an't instantiate"):
            IAIClient()
