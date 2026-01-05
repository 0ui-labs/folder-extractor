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

    def test_init_with_settings(self):
        """SmartSorter correctly stores client and settings."""
        mock_client = MagicMock()
        mock_settings = MagicMock()

        sorter = SmartSorter(mock_client, settings=mock_settings)

        assert sorter._client is mock_client
        assert sorter._settings is mock_settings


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


class TestSmartSorterKnowledgeGraphIntegration:
    """Tests for KnowledgeGraph integration in SmartSorter."""

    @pytest.mark.asyncio
    async def test_process_file_ingests_to_knowledge_graph(self, tmp_path: Path):
        """Successfully analyzed files are ingested into KnowledgeGraph."""
        from folder_extractor.core.memory import reset_knowledge_graph

        # Reset singleton to ensure clean state
        reset_knowledge_graph()

        mock_client = AsyncMock()
        mock_client.analyze_file.return_value = {
            "category": "Finanzen",
            "sender": "Test GmbH",
            "year": "2024",
            "entities": [{"name": "Test GmbH", "type": "Organization"}],
        }

        mock_settings = MagicMock()
        mock_settings.get.return_value = []

        # Create a real temp file for hash calculation
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"test content")

        sorter = SmartSorter(mock_client, settings=mock_settings)

        with patch(
            "folder_extractor.core.memory.graph.get_knowledge_graph"
        ) as mock_get_kg:
            mock_kg = MagicMock()
            mock_get_kg.return_value = mock_kg

            await sorter.process_file(test_file, "application/pdf")

            # Verify ingest was called
            mock_kg.ingest.assert_called_once()

            # Verify file_info structure
            file_info = mock_kg.ingest.call_args[0][0]
            assert file_info["path"] == str(test_file.resolve())
            assert "hash" in file_info
            assert file_info["category"] == "Finanzen"
            assert file_info["entities"] == [
                {"name": "Test GmbH", "type": "Organization"}
            ]
            assert "timestamp" in file_info

        reset_knowledge_graph()

    @pytest.mark.asyncio
    async def test_knowledge_graph_error_does_not_block_workflow(self, tmp_path: Path):
        """KnowledgeGraph errors are logged but don't prevent file processing."""
        from folder_extractor.core.memory import (
            KnowledgeGraphError,
            reset_knowledge_graph,
        )

        reset_knowledge_graph()

        expected_result = {
            "category": "Finanzen",
            "sender": "Test GmbH",
            "year": "2024",
            "entities": [],
        }

        mock_client = AsyncMock()
        mock_client.analyze_file.return_value = expected_result

        mock_settings = MagicMock()
        mock_settings.get.return_value = []

        # Create a real temp file
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"test content")

        sorter = SmartSorter(mock_client, settings=mock_settings)

        with patch(
            "folder_extractor.core.memory.graph.get_knowledge_graph"
        ) as mock_get_kg:
            mock_kg = MagicMock()
            mock_kg.ingest.side_effect = KnowledgeGraphError("DB connection failed")
            mock_get_kg.return_value = mock_kg

            # Should NOT raise - error should be caught and logged
            result = await sorter.process_file(test_file, "application/pdf")

            # Result should still be returned despite graph error
            assert result == expected_result

        reset_knowledge_graph()

    @pytest.mark.asyncio
    async def test_unexpected_error_in_graph_does_not_block_workflow(
        self, tmp_path: Path
    ):
        """Unexpected errors in KnowledgeGraph are caught and logged."""
        from folder_extractor.core.memory import reset_knowledge_graph

        reset_knowledge_graph()

        expected_result = {
            "category": "Privat",
            "sender": None,
            "year": None,
            "entities": [],
        }

        mock_client = AsyncMock()
        mock_client.analyze_file.return_value = expected_result

        mock_settings = MagicMock()
        mock_settings.get.return_value = []

        test_file = tmp_path / "photo.jpg"
        test_file.write_bytes(b"image data")

        sorter = SmartSorter(mock_client, settings=mock_settings)

        with patch(
            "folder_extractor.core.memory.graph.get_knowledge_graph"
        ) as mock_get_kg:
            mock_kg = MagicMock()
            mock_kg.ingest.side_effect = RuntimeError("Unexpected crash")
            mock_get_kg.return_value = mock_kg

            # Should NOT raise
            result = await sorter.process_file(test_file, "image/jpeg")

            assert result == expected_result

        reset_knowledge_graph()

    @pytest.mark.asyncio
    async def test_file_info_contains_absolute_path(self, tmp_path: Path):
        """Ingested file_info contains absolute path for consistent storage."""
        from folder_extractor.core.memory import reset_knowledge_graph

        reset_knowledge_graph()

        mock_client = AsyncMock()
        mock_client.analyze_file.return_value = {
            "category": "Test",
            "entities": [],
        }

        mock_settings = MagicMock()
        mock_settings.get.return_value = []

        # Create file with relative-looking path
        test_file = tmp_path / "subdir" / "test.pdf"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_bytes(b"content")

        sorter = SmartSorter(mock_client, settings=mock_settings)

        with patch(
            "folder_extractor.core.memory.graph.get_knowledge_graph"
        ) as mock_get_kg:
            mock_kg = MagicMock()
            mock_get_kg.return_value = mock_kg

            await sorter.process_file(test_file, "application/pdf")

            file_info = mock_kg.ingest.call_args[0][0]
            # Path should be absolute
            assert file_info["path"].startswith("/")
            assert str(test_file.resolve()) == file_info["path"]

        reset_knowledge_graph()

    @pytest.mark.asyncio
    async def test_entities_from_ai_response_passed_to_graph(self, tmp_path: Path):
        """Entities extracted by AI are passed to KnowledgeGraph."""
        from folder_extractor.core.memory import reset_knowledge_graph

        reset_knowledge_graph()

        entities = [
            {"name": "Apple Inc.", "type": "Organization"},
            {"name": "Tim Cook", "type": "Person"},
            {"name": "iPhone", "type": "Product"},
        ]

        mock_client = AsyncMock()
        mock_client.analyze_file.return_value = {
            "category": "Technik",
            "sender": "Apple Inc.",
            "year": "2024",
            "entities": entities,
        }

        mock_settings = MagicMock()
        mock_settings.get.return_value = []

        test_file = tmp_path / "report.pdf"
        test_file.write_bytes(b"report content")

        sorter = SmartSorter(mock_client, settings=mock_settings)

        with patch(
            "folder_extractor.core.memory.graph.get_knowledge_graph"
        ) as mock_get_kg:
            mock_kg = MagicMock()
            mock_get_kg.return_value = mock_kg

            await sorter.process_file(test_file, "application/pdf")

            file_info = mock_kg.ingest.call_args[0][0]
            assert file_info["entities"] == entities

        reset_knowledge_graph()

    @pytest.mark.asyncio
    async def test_missing_entities_defaults_to_empty_list(self, tmp_path: Path):
        """Missing entities in AI response defaults to empty list for graph."""
        from folder_extractor.core.memory import reset_knowledge_graph

        reset_knowledge_graph()

        # AI response without entities field
        mock_client = AsyncMock()
        mock_client.analyze_file.return_value = {
            "category": "Privat",
            "sender": None,
            "year": None,
            # No "entities" key
        }

        mock_settings = MagicMock()
        mock_settings.get.return_value = []

        test_file = tmp_path / "photo.jpg"
        test_file.write_bytes(b"image")

        sorter = SmartSorter(mock_client, settings=mock_settings)

        with patch(
            "folder_extractor.core.memory.graph.get_knowledge_graph"
        ) as mock_get_kg:
            mock_kg = MagicMock()
            mock_get_kg.return_value = mock_kg

            await sorter.process_file(test_file, "image/jpeg")

            file_info = mock_kg.ingest.call_args[0][0]
            assert file_info["entities"] == []

        reset_knowledge_graph()

    @pytest.mark.asyncio
    async def test_missing_kuzu_dependency_does_not_block_workflow(
        self, tmp_path: Path
    ):
        """Missing kuzu package is handled gracefully without blocking processing."""
        expected_result = {
            "category": "Finanzen",
            "sender": "Test GmbH",
            "year": "2024",
            "entities": [],
        }

        mock_client = AsyncMock()
        mock_client.analyze_file.return_value = expected_result

        mock_settings = MagicMock()
        mock_settings.get.return_value = []

        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"test content")

        sorter = SmartSorter(mock_client, settings=mock_settings)

        # Simulate missing kuzu by making the import fail
        with patch.dict("sys.modules", {"kuzu": None}):
            with patch(
                "folder_extractor.core.smart_sorter.time"
            ):  # Avoid actual time call
                # Patch the import to raise ModuleNotFoundError
                import builtins

                original_import = builtins.__import__

                def mock_import(name, *args, **kwargs):
                    if (
                        "memory.graph" in name
                        or name == "folder_extractor.core.memory.graph"
                    ):
                        raise ModuleNotFoundError("No module named 'kuzu'")
                    return original_import(name, *args, **kwargs)

                with patch.object(builtins, "__import__", mock_import):
                    # Should NOT raise - ModuleNotFoundError should be caught
                    result = await sorter.process_file(test_file, "application/pdf")

                    # Result should still be returned
                    assert result == expected_result
