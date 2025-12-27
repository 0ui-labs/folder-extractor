"""
Unit tests for asynchronous AI client module.

Tests cover:
- AsyncGeminiClient initialization
- File analysis behavior
- Error handling
- Interface compliance
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
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
from folder_extractor.core.security import APIKeyError


class TestAIClientError:
    """Tests for AIClientError exception."""

    def test_is_exception_subclass(self):
        """AIClientError inherits from Exception."""
        assert issubclass(AIClientError, Exception)

    def test_can_be_raised_with_message(self):
        """AIClientError can be raised with a descriptive message."""
        with pytest.raises(AIClientError, match="Analysis failed"):
            raise AIClientError("Analysis failed")


class TestIAIClientInterface:
    """Tests for IAIClient abstract interface."""

    def test_interface_defines_analyze_file_method(self):
        """IAIClient interface defines analyze_file as abstract method."""
        assert hasattr(IAIClient, "analyze_file")
        # Check it's abstract
        assert getattr(IAIClient.analyze_file, "__isabstractmethod__", False)

    def test_cannot_instantiate_interface_directly(self):
        """IAIClient cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IAIClient()

    def test_concrete_implementation_must_implement_analyze_file(self):
        """Concrete classes must implement analyze_file method."""

        class IncompleteClient(IAIClient):
            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteClient()


class TestAsyncGeminiClientInitialization:
    """Tests for AsyncGeminiClient initialization."""

    @patch("folder_extractor.core.ai_async.genai")
    @patch("folder_extractor.core.ai_async.load_google_api_key")
    def test_loads_api_key_from_environment_when_not_provided(
        self, mock_load_key, mock_genai
    ):
        """Client loads API key from environment when not explicitly provided."""
        mock_load_key.return_value = "env-api-key"

        client = AsyncGeminiClient()

        mock_load_key.assert_called_once()
        mock_genai.configure.assert_called_once_with(api_key="env-api-key")

    @patch("folder_extractor.core.ai_async.genai")
    @patch("folder_extractor.core.ai_async.load_google_api_key")
    def test_uses_provided_api_key_directly(self, mock_load_key, mock_genai):
        """Client uses provided API key instead of loading from environment."""
        client = AsyncGeminiClient(api_key="explicit-key")

        mock_load_key.assert_not_called()
        mock_genai.configure.assert_called_once_with(api_key="explicit-key")

    @patch("folder_extractor.core.ai_async.genai")
    @patch("folder_extractor.core.ai_async.load_google_api_key")
    def test_uses_default_model(self, mock_load_key, mock_genai):
        """Client uses gemini-1.5-flash as default model."""
        mock_load_key.return_value = "test-key"

        client = AsyncGeminiClient()

        mock_genai.GenerativeModel.assert_called_once_with("gemini-3-flash-preview")

    @patch("folder_extractor.core.ai_async.genai")
    @patch("folder_extractor.core.ai_async.load_google_api_key")
    def test_accepts_custom_model_name(self, mock_load_key, mock_genai):
        """Client can be configured with a different model."""
        mock_load_key.return_value = "test-key"

        client = AsyncGeminiClient(model_name="gemini-pro")

        mock_genai.GenerativeModel.assert_called_once_with("gemini-pro")

    @patch("folder_extractor.core.ai_async.load_google_api_key")
    def test_raises_api_key_error_when_key_not_found(self, mock_load_key):
        """Client raises APIKeyError when API key cannot be loaded."""
        mock_load_key.side_effect = APIKeyError("Key not found")

        with pytest.raises(APIKeyError, match="Key not found"):
            AsyncGeminiClient()

    @patch("folder_extractor.core.ai_async.genai")
    @patch("folder_extractor.core.ai_async.load_google_api_key")
    def test_implements_iai_client_interface(self, mock_load_key, mock_genai):
        """AsyncGeminiClient implements IAIClient interface."""
        mock_load_key.return_value = "test-key"

        client = AsyncGeminiClient()

        assert isinstance(client, IAIClient)


class TestAsyncGeminiClientAnalyzeFile:
    """Tests for AsyncGeminiClient.analyze_file method."""

    @pytest.fixture
    def mock_genai(self):
        """Fixture providing mocked genai module."""
        with patch("folder_extractor.core.ai_async.genai") as mock:
            yield mock

    @pytest.fixture
    def mock_load_key(self):
        """Fixture providing mocked load_google_api_key."""
        with patch("folder_extractor.core.ai_async.load_google_api_key") as mock:
            mock.return_value = "test-key"
            yield mock

    @pytest.fixture
    def client(self, mock_genai, mock_load_key):
        """Fixture providing configured AsyncGeminiClient."""
        return AsyncGeminiClient()

    def test_raises_error_for_nonexistent_file(self, client, tmp_path):
        """analyze_file raises AIClientError for non-existent files."""
        nonexistent = tmp_path / "nonexistent.jpg"

        with pytest.raises(AIClientError, match="does not exist"):
            asyncio.run(
                client.analyze_file(
                    filepath=nonexistent,
                    mime_type="image/jpeg",
                    prompt="Describe this",
                )
            )

    def test_raises_error_for_directory_path(self, client, tmp_path):
        """analyze_file raises AIClientError when given a directory."""
        with pytest.raises(AIClientError, match="not a file"):
            asyncio.run(
                client.analyze_file(
                    filepath=tmp_path,  # tmp_path is a directory
                    mime_type="image/jpeg",
                    prompt="Describe this",
                )
            )

    def test_uploads_file_with_correct_parameters(
        self, mock_genai, mock_load_key, tmp_path
    ):
        """analyze_file uploads file with correct path and mime type."""
        # Create test file
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"fake image data")

        # Setup mocks
        mock_uploaded_file = MagicMock()
        mock_genai.upload_file.return_value = mock_uploaded_file

        mock_response = MagicMock()
        mock_response.text = '{"description": "test result"}'
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        client = AsyncGeminiClient()

        asyncio.run(
            client.analyze_file(
                filepath=test_file,
                mime_type="image/jpeg",
                prompt="Describe this",
            )
        )

        # Verify upload was called with correct parameters
        mock_genai.upload_file.assert_called_once()
        call_kwargs = mock_genai.upload_file.call_args
        assert str(test_file) in str(call_kwargs)
        assert "image/jpeg" in str(call_kwargs)

    def test_returns_parsed_json_response(self, mock_genai, mock_load_key, tmp_path):
        """analyze_file returns parsed JSON from model response."""
        # Create test file
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"fake image data")

        # Setup mocks
        mock_uploaded_file = MagicMock()
        mock_genai.upload_file.return_value = mock_uploaded_file

        expected_result = {"description": "A beautiful image", "confidence": 0.95}
        mock_response = MagicMock()
        mock_response.text = json.dumps(expected_result)
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        client = AsyncGeminiClient()

        result = asyncio.run(
            client.analyze_file(
                filepath=test_file,
                mime_type="image/jpeg",
                prompt="Describe this",
            )
        )

        assert result == expected_result

    def test_uses_json_response_format(self, mock_genai, mock_load_key, tmp_path):
        """analyze_file requests JSON response format from model."""
        # Create test file
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"fake image data")

        # Setup mocks
        mock_uploaded_file = MagicMock()
        mock_genai.upload_file.return_value = mock_uploaded_file

        mock_response = MagicMock()
        mock_response.text = '{"result": "ok"}'
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        client = AsyncGeminiClient()

        asyncio.run(
            client.analyze_file(
                filepath=test_file,
                mime_type="image/jpeg",
                prompt="Describe this",
            )
        )

        # Verify generation config includes JSON response type
        call_kwargs = mock_model.generate_content_async.call_args
        assert "generation_config" in call_kwargs.kwargs
        config = call_kwargs.kwargs["generation_config"]
        assert config.get("response_mime_type") == "application/json"

    def test_raises_error_on_invalid_json_response(
        self, mock_genai, mock_load_key, tmp_path
    ):
        """analyze_file raises AIClientError when response is not valid JSON."""
        # Create test file
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"fake image data")

        # Setup mocks
        mock_uploaded_file = MagicMock()
        mock_genai.upload_file.return_value = mock_uploaded_file

        mock_response = MagicMock()
        mock_response.text = "not valid json {"
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        client = AsyncGeminiClient()

        with pytest.raises(AIClientError, match="Failed to parse"):
            asyncio.run(
                client.analyze_file(
                    filepath=test_file,
                    mime_type="image/jpeg",
                    prompt="Describe this",
                )
            )

    def test_includes_prompt_in_generation_request(
        self, mock_genai, mock_load_key, tmp_path
    ):
        """analyze_file includes the prompt in the generation request."""
        # Create test file
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"fake image data")

        # Setup mocks
        mock_uploaded_file = MagicMock()
        mock_genai.upload_file.return_value = mock_uploaded_file

        mock_response = MagicMock()
        mock_response.text = '{"result": "ok"}'
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        client = AsyncGeminiClient()
        test_prompt = "Analyze this image for objects"

        asyncio.run(
            client.analyze_file(
                filepath=test_file,
                mime_type="image/jpeg",
                prompt=test_prompt,
            )
        )

        # Verify prompt was passed to generation
        call_args = mock_model.generate_content_async.call_args[0][0]
        assert test_prompt in call_args

    def test_does_not_wrap_resource_exhausted_in_ai_client_error(
        self, mock_genai, mock_load_key, tmp_path
    ):
        """ResourceExhausted propagates unwrapped for retry decorator to handle."""
        # Create test file
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"fake image data")

        # Setup mocks - generate_content_async raises ResourceExhausted
        mock_uploaded_file = MagicMock()
        mock_genai.upload_file.return_value = mock_uploaded_file

        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(
            side_effect=ResourceExhausted("Rate limited")
        )
        mock_genai.GenerativeModel.return_value = mock_model

        # Patch the ai_retry decorator to not retry (for this test)
        with patch("folder_extractor.core.ai_async.ai_retry", lambda f: f):
            client = AsyncGeminiClient()

            # Should raise ResourceExhausted, NOT AIClientError
            with pytest.raises(ResourceExhausted, match="Rate limited"):
                asyncio.run(
                    client.analyze_file(
                        filepath=test_file,
                        mime_type="image/jpeg",
                        prompt="Describe this",
                    )
                )

    def test_does_not_wrap_internal_server_error_in_ai_client_error(
        self, mock_genai, mock_load_key, tmp_path
    ):
        """InternalServerError propagates unwrapped for retry decorator to handle."""
        # Create test file
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"fake image data")

        # Setup mocks
        mock_uploaded_file = MagicMock()
        mock_genai.upload_file.return_value = mock_uploaded_file

        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(
            side_effect=InternalServerError("Server error")
        )
        mock_genai.GenerativeModel.return_value = mock_model

        with patch("folder_extractor.core.ai_async.ai_retry", lambda f: f):
            client = AsyncGeminiClient()

            with pytest.raises(InternalServerError, match="Server error"):
                asyncio.run(
                    client.analyze_file(
                        filepath=test_file,
                        mime_type="image/jpeg",
                        prompt="Describe this",
                    )
                )

    def test_does_not_wrap_service_unavailable_in_ai_client_error(
        self, mock_genai, mock_load_key, tmp_path
    ):
        """ServiceUnavailable propagates unwrapped for retry decorator to handle."""
        # Create test file
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"fake image data")

        # Setup mocks
        mock_uploaded_file = MagicMock()
        mock_genai.upload_file.return_value = mock_uploaded_file

        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(
            side_effect=ServiceUnavailable("Service unavailable")
        )
        mock_genai.GenerativeModel.return_value = mock_model

        with patch("folder_extractor.core.ai_async.ai_retry", lambda f: f):
            client = AsyncGeminiClient()

            with pytest.raises(ServiceUnavailable, match="Service unavailable"):
                asyncio.run(
                    client.analyze_file(
                        filepath=test_file,
                        mime_type="image/jpeg",
                        prompt="Describe this",
                    )
                )


class TestAsyncGeminiClientConstants:
    """Tests for AsyncGeminiClient class-level constants."""

    def test_default_model_constant_exists(self):
        """AsyncGeminiClient has DEFAULT_MODEL class constant."""
        assert hasattr(AsyncGeminiClient, "DEFAULT_MODEL")

    def test_default_model_is_gemini_flash(self):
        """DEFAULT_MODEL is set to gemini-3-flash-preview."""
        assert AsyncGeminiClient.DEFAULT_MODEL == "gemini-3-flash-preview"
