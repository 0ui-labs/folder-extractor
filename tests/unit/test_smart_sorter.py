"""
Unit tests for SmartSorter module.

Tests cover:
- SmartSorter initialization with client and settings
- process_file method behavior
- Prompt construction from categories
- Error propagation from AI client
- Integration with real Settings structure

Note: These tests require google-generativeai which only works on Python 3.9+.
Tests are skipped if the dependency is not available.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Skip all tests if google-generativeai is not installed (Python 3.8)
pytest.importorskip("google.api_core.exceptions")
pytest.importorskip("google.generativeai")

from folder_extractor.config.constants import DEFAULT_CATEGORIES  # noqa: E402
from folder_extractor.core.ai_async import AIClientError  # noqa: E402
from folder_extractor.core.smart_sorter import SmartSorter  # noqa: E402


class TestSmartSorterInitialization:
    """Tests for SmartSorter initialization."""

    def test_init_with_client_only_uses_global_settings(self):
        """SmartSorter uses global settings when none provided."""
        mock_client = MagicMock()

        # Import the actual global settings to compare
        from folder_extractor.config.settings import settings as global_settings

        sorter = SmartSorter(mock_client)

        # Verify it uses the global settings singleton
        assert sorter._client is mock_client
        assert sorter._settings is global_settings

    def test_init_with_explicit_settings(self):
        """SmartSorter uses provided settings instead of global."""
        mock_client = MagicMock()
        mock_settings = MagicMock()

        sorter = SmartSorter(mock_client, settings=mock_settings)

        assert sorter._client is mock_client
        assert sorter._settings is mock_settings


class TestSmartSorterGetAllCategories:
    """Tests for _get_all_categories method."""

    def test_returns_default_categories_when_no_custom(self):
        """Returns default categories when no custom categories defined."""
        mock_client = MagicMock()
        mock_settings = MagicMock()
        mock_settings.get.return_value = []

        sorter = SmartSorter(mock_client, settings=mock_settings)
        categories = sorter._get_all_categories()

        mock_settings.get.assert_called_once_with("custom_categories", [])
        assert categories == list(DEFAULT_CATEGORIES)

    def test_custom_categories_take_precedence(self):
        """Custom categories appear before default categories."""
        mock_client = MagicMock()
        mock_settings = MagicMock()
        custom_cats = ["Meine Kategorie", "Andere"]
        mock_settings.get.return_value = custom_cats

        sorter = SmartSorter(mock_client, settings=mock_settings)
        categories = sorter._get_all_categories()

        # Custom categories should be first
        assert categories[0] == "Meine Kategorie"
        assert categories[1] == "Andere"
        # Default categories should follow (excluding duplicates)
        for default_cat in DEFAULT_CATEGORIES:
            if default_cat not in custom_cats:
                assert default_cat in categories

    def test_duplicate_categories_removed(self):
        """Duplicate categories from custom list are not repeated from defaults."""
        mock_client = MagicMock()
        mock_settings = MagicMock()
        # "Finanzen" is a default category
        mock_settings.get.return_value = ["Finanzen", "Meine Kategorie"]

        sorter = SmartSorter(mock_client, settings=mock_settings)
        categories = sorter._get_all_categories()

        # Count occurrences of "Finanzen" - should only appear once
        finanzen_count = categories.count("Finanzen")
        assert finanzen_count == 1

        # "Finanzen" should be at position 0 (from custom, not default)
        assert categories[0] == "Finanzen"


class TestSmartSorterProcessFile:
    """Tests for process_file method."""

    @pytest.mark.asyncio
    async def test_process_file_calls_analyze_with_correct_params(self):
        """process_file passes filepath, mime_type, and generated prompt to client."""
        mock_client = AsyncMock()
        mock_client.analyze_file.return_value = {
            "category": "Finanzen",
            "sender": "Test GmbH",
            "year": "2024",
        }

        mock_settings = MagicMock()
        mock_settings.get.return_value = []

        sorter = SmartSorter(mock_client, settings=mock_settings)

        filepath = Path("/test/invoice.pdf")
        mime_type = "application/pdf"

        await sorter.process_file(filepath, mime_type)

        # Verify analyze_file was called with correct parameters
        mock_client.analyze_file.assert_called_once()
        call_kwargs = mock_client.analyze_file.call_args.kwargs

        assert call_kwargs["filepath"] == filepath
        assert call_kwargs["mime_type"] == mime_type
        assert isinstance(call_kwargs["prompt"], str)
        assert len(call_kwargs["prompt"]) > 0

    @pytest.mark.asyncio
    async def test_process_file_prompt_contains_categories(self):
        """Generated prompt contains available categories."""
        mock_client = AsyncMock()
        mock_client.analyze_file.return_value = {"category": "Test"}

        mock_settings = MagicMock()
        custom_cats = ["Rechnungen", "Briefe"]
        mock_settings.get.return_value = custom_cats

        sorter = SmartSorter(mock_client, settings=mock_settings)

        await sorter.process_file(Path("/test.pdf"), "application/pdf")

        # Get the prompt that was passed
        call_kwargs = mock_client.analyze_file.call_args.kwargs
        prompt = call_kwargs["prompt"]

        # Verify custom categories are in the prompt
        assert "Rechnungen" in prompt
        assert "Briefe" in prompt

    @pytest.mark.asyncio
    async def test_process_file_returns_client_result_directly(self):
        """process_file returns the client's result unchanged."""
        expected_result = {
            "category": "Verträge",
            "sender": "Insurance Corp",
            "year": "2023",
        }

        mock_client = AsyncMock()
        mock_client.analyze_file.return_value = expected_result

        mock_settings = MagicMock()
        mock_settings.get.return_value = []

        sorter = SmartSorter(mock_client, settings=mock_settings)

        result = await sorter.process_file(Path("/contract.pdf"), "application/pdf")

        assert result == expected_result

    @pytest.mark.asyncio
    async def test_process_file_returns_result_with_null_values(self):
        """process_file correctly returns results with null sender/year."""
        expected_result = {
            "category": "Privat",
            "sender": None,
            "year": None,
        }

        mock_client = AsyncMock()
        mock_client.analyze_file.return_value = expected_result

        mock_settings = MagicMock()
        mock_settings.get.return_value = []

        sorter = SmartSorter(mock_client, settings=mock_settings)

        result = await sorter.process_file(Path("/photo.jpg"), "image/jpeg")

        assert result["category"] == "Privat"
        assert result["sender"] is None
        assert result["year"] is None


class TestSmartSorterErrorPropagation:
    """Tests for error propagation from AI client."""

    @pytest.mark.asyncio
    async def test_propagates_ai_client_error(self):
        """AIClientError from client is propagated to caller."""
        mock_client = AsyncMock()
        mock_client.analyze_file.side_effect = AIClientError("Analysis failed")

        mock_settings = MagicMock()
        mock_settings.get.return_value = []

        sorter = SmartSorter(mock_client, settings=mock_settings)

        with pytest.raises(AIClientError, match="Analysis failed"):
            await sorter.process_file(Path("/test.pdf"), "application/pdf")

    @pytest.mark.asyncio
    async def test_propagates_file_not_found_error(self):
        """AIClientError for missing file is propagated."""
        mock_client = AsyncMock()
        mock_client.analyze_file.side_effect = AIClientError(
            "File does not exist: /missing.pdf"
        )

        mock_settings = MagicMock()
        mock_settings.get.return_value = []

        sorter = SmartSorter(mock_client, settings=mock_settings)

        with pytest.raises(AIClientError, match="File does not exist"):
            await sorter.process_file(Path("/missing.pdf"), "application/pdf")

    @pytest.mark.asyncio
    async def test_propagates_json_parse_error(self):
        """AIClientError for JSON parsing failure is propagated."""
        mock_client = AsyncMock()
        mock_client.analyze_file.side_effect = AIClientError(
            "Failed to parse JSON response"
        )

        mock_settings = MagicMock()
        mock_settings.get.return_value = []

        sorter = SmartSorter(mock_client, settings=mock_settings)

        with pytest.raises(AIClientError, match="Failed to parse JSON"):
            await sorter.process_file(Path("/test.pdf"), "application/pdf")

    @pytest.mark.asyncio
    async def test_propagates_preprocessing_error(self):
        """AIClientError for preprocessing failure is propagated."""
        mock_client = AsyncMock()
        mock_client.analyze_file.side_effect = AIClientError(
            "File preprocessing failed: image too large"
        )

        mock_settings = MagicMock()
        mock_settings.get.return_value = []

        sorter = SmartSorter(mock_client, settings=mock_settings)

        with pytest.raises(AIClientError, match="preprocessing failed"):
            await sorter.process_file(Path("/huge.tiff"), "image/tiff")


class TestSmartSorterIntegration:
    """Integration tests with real Settings structure."""

    @pytest.mark.asyncio
    async def test_integration_with_real_settings_class(self):
        """SmartSorter works correctly with real Settings instance."""
        from folder_extractor.config.settings import Settings

        # Create real Settings instance
        real_settings = Settings()
        real_settings.set("custom_categories", ["Integration Test Cat"])

        mock_client = AsyncMock()
        mock_client.analyze_file.return_value = {
            "category": "Integration Test Cat",
            "sender": "Test",
            "year": "2024",
        }

        sorter = SmartSorter(mock_client, settings=real_settings)

        result = await sorter.process_file(Path("/test.pdf"), "application/pdf")

        # Verify custom category was used
        call_kwargs = mock_client.analyze_file.call_args.kwargs
        prompt = call_kwargs["prompt"]
        assert "Integration Test Cat" in prompt

        assert result["category"] == "Integration Test Cat"

    @pytest.mark.asyncio
    async def test_integration_default_categories_in_prompt(self):
        """Default categories from constants appear in generated prompt."""
        from folder_extractor.config.settings import Settings

        real_settings = Settings()
        real_settings.set("custom_categories", [])

        mock_client = AsyncMock()
        mock_client.analyze_file.return_value = {"category": "Finanzen"}

        sorter = SmartSorter(mock_client, settings=real_settings)

        await sorter.process_file(Path("/test.pdf"), "application/pdf")

        call_kwargs = mock_client.analyze_file.call_args.kwargs
        prompt = call_kwargs["prompt"]

        # Verify default categories are present
        for category in DEFAULT_CATEGORIES:
            assert category in prompt, f"Default category '{category}' missing"

    @pytest.mark.asyncio
    async def test_integration_prompt_structure(self):
        """Generated prompt has correct structure for Gemini API."""
        from folder_extractor.config.settings import Settings

        real_settings = Settings()

        mock_client = AsyncMock()
        mock_client.analyze_file.return_value = {"category": "Test"}

        sorter = SmartSorter(mock_client, settings=real_settings)

        await sorter.process_file(Path("/test.pdf"), "application/pdf")

        call_kwargs = mock_client.analyze_file.call_args.kwargs
        prompt = call_kwargs["prompt"]

        # Verify prompt contains expected sections
        assert "Kategorisierung" in prompt or "Kategorie" in prompt
        assert "JSON" in prompt
        assert "category" in prompt
        assert "sender" in prompt
        assert "year" in prompt


class TestSmartSorterPromptGeneration:
    """Tests for prompt generation integration."""

    @pytest.mark.asyncio
    async def test_uses_get_system_prompt_function(self):
        """SmartSorter uses get_system_prompt to generate prompts."""
        mock_client = AsyncMock()
        mock_client.analyze_file.return_value = {"category": "Test"}

        mock_settings = MagicMock()
        mock_settings.get.return_value = ["Cat1", "Cat2"]

        with patch(
            "folder_extractor.core.smart_sorter.get_system_prompt"
        ) as mock_get_prompt:
            mock_get_prompt.return_value = "Mocked prompt"

            sorter = SmartSorter(mock_client, settings=mock_settings)
            await sorter.process_file(Path("/test.pdf"), "application/pdf")

            # Verify get_system_prompt was called with categories
            mock_get_prompt.assert_called_once()
            call_args = mock_get_prompt.call_args[0][0]
            assert "Cat1" in call_args
            assert "Cat2" in call_args

            # Verify mocked prompt was passed to client
            call_kwargs = mock_client.analyze_file.call_args.kwargs
            assert call_kwargs["prompt"] == "Mocked prompt"

    @pytest.mark.asyncio
    async def test_categories_order_preserved_in_prompt_call(self):
        """Categories are passed to get_system_prompt in correct order."""
        mock_client = AsyncMock()
        mock_client.analyze_file.return_value = {"category": "Test"}

        mock_settings = MagicMock()
        mock_settings.get.return_value = ["First", "Second"]

        sorter = SmartSorter(mock_client, settings=mock_settings)

        with patch(
            "folder_extractor.core.smart_sorter.get_system_prompt"
        ) as mock_get_prompt:
            mock_get_prompt.return_value = "test"

            await sorter.process_file(Path("/test.pdf"), "application/pdf")

            call_args = mock_get_prompt.call_args[0][0]
            # Custom categories should be first
            assert call_args[0] == "First"
            assert call_args[1] == "Second"
