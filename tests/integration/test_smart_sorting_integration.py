"""
Integration tests for Smart Sorting workflow.

Tests the complete end-to-end flow:
- File creation and preprocessing
- SmartSorter orchestration
- AI analysis with mocked Gemini API
- Result validation

These tests use real files and real components, but mock
the Gemini API calls to avoid costs and ensure determinism.

Note: These tests require google-generativeai which only works on Python 3.9+.
Tests are skipped if the dependency is not available.

Note: Tests should run with -n0 (no parallelism) because they mock global
genai module state that can conflict between workers.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Skip all tests if google-generativeai is not installed (Python 3.8)
pytest.importorskip("google.api_core.exceptions")
pytest.importorskip("google.generativeai")

from folder_extractor.config.constants import DEFAULT_CATEGORIES  # noqa: E402
from folder_extractor.config.settings import Settings, get_all_categories  # noqa: E402
from folder_extractor.core.ai_async import (  # noqa: E402
    AIClientError,
    AsyncGeminiClient,
)
from folder_extractor.core.smart_sorter import SmartSorter  # noqa: E402

if TYPE_CHECKING:
    from typing import Generator


# =============================================================================
# Helper Functions
# =============================================================================


def create_test_file_with_content(
    directory: Path,
    filename: str,
    content: bytes,
    mime_type: str,
) -> tuple[Path, str]:
    """
    Create a test file with specific content.

    Args:
        directory: Directory to create file in
        filename: Name of the file
        content: Binary content to write
        mime_type: MIME type of the file

    Returns:
        Tuple of (file_path, mime_type)
    """
    file_path = directory / filename
    file_path.write_bytes(content)
    return file_path, mime_type


def mock_api_response(
    mock_genai: MagicMock,
    category: str,
    sender: str | None = None,
    year: int | None = None,
) -> None:
    """
    Configure mock API to return specific response.

    Args:
        mock_genai: Mocked genai module
        category: Category to return
        sender: Optional sender to return
        year: Optional year to return
    """
    response_data = {
        "category": category,
        "sender": sender,
        "year": year,
    }
    mock_response = MagicMock()
    mock_response.text = json.dumps(response_data)
    mock_genai.GenerativeModel.return_value.generate_content_async = AsyncMock(
        return_value=mock_response
    )


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_gemini_api() -> Generator[MagicMock, None, None]:
    """
    Mock Gemini API calls while keeping other components real.

    Mocks genai.upload_file and model.generate_content_async to
    avoid real API calls while testing the full integration flow.
    """
    with patch("folder_extractor.core.ai_async.genai") as mock_genai:
        # Mock upload_file
        mock_uploaded_file = MagicMock()
        mock_genai.upload_file.return_value = mock_uploaded_file

        # Mock model and generate_content_async with default response
        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "category": "Finanzen",
                "sender": "Test Bank AG",
                "year": 2024,
            }
        )
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        yield mock_genai


@pytest.fixture
def integration_test_dir(tmp_path: Path) -> Path:
    """Create temporary directory for integration tests."""
    test_dir = tmp_path / "smart_sorting_tests"
    test_dir.mkdir()
    return test_dir


@pytest.fixture
def test_settings() -> Generator[Settings, None, None]:
    """
    Create isolated Settings instance for testing.

    Resets to defaults before and after each test to ensure isolation.
    """
    test_settings = Settings()
    test_settings.reset_to_defaults()
    yield test_settings
    test_settings.reset_to_defaults()  # Cleanup


@pytest.fixture
def smart_sorter_client(mock_gemini_api: MagicMock) -> AsyncGeminiClient:
    """
    Create AsyncGeminiClient with mocked API.

    Depends on mock_gemini_api fixture for API mocking.
    """
    with patch("folder_extractor.core.ai_async.load_google_api_key") as mock_key:
        mock_key.return_value = "test-api-key"
        client = AsyncGeminiClient()
        return client


# =============================================================================
# Test Class: Smart Sorting Workflow
# =============================================================================


class TestSmartSortingWorkflow:
    """Tests for complete end-to-end smart sorting workflow."""

    def test_complete_workflow_with_pdf(
        self,
        integration_test_dir: Path,
        mock_gemini_api: MagicMock,
        test_settings: Settings,
        smart_sorter_client: AsyncGeminiClient,
    ) -> None:
        """Complete workflow processes PDF and returns correct categorization."""
        # Arrange: Create PDF test file
        test_file, mime_type = create_test_file_with_content(
            integration_test_dir,
            "invoice.pdf",
            b"%PDF-1.4 fake pdf content for testing purposes",
            "application/pdf",
        )

        # Configure expected response
        mock_api_response(mock_gemini_api, "Finanzen", "Test Bank AG", 2024)

        # Create SmartSorter with real Settings
        sorter = SmartSorter(smart_sorter_client, test_settings)

        # Act
        result = asyncio.run(sorter.process_file(test_file, mime_type))

        # Assert
        assert "category" in result
        assert "sender" in result
        assert "year" in result
        assert result["category"] == "Finanzen"
        assert result["sender"] == "Test Bank AG"
        assert result["year"] == 2024

    def test_complete_workflow_with_image(
        self,
        integration_test_dir: Path,
        mock_gemini_api: MagicMock,
        test_settings: Settings,
        smart_sorter_client: AsyncGeminiClient,
    ) -> None:
        """Complete workflow processes JPEG image and returns categorization."""
        # Arrange: Create JPEG test file (with magic bytes)
        jpeg_header = b"\xff\xd8\xff\xe0\x00\x10JFIF"
        test_file, mime_type = create_test_file_with_content(
            integration_test_dir,
            "document.jpg",
            jpeg_header + b"fake jpeg image data",
            "image/jpeg",
        )

        # Configure expected response
        mock_api_response(mock_gemini_api, "Medizin", "Dr. Müller", 2023)

        sorter = SmartSorter(smart_sorter_client, test_settings)

        # Act
        result = asyncio.run(sorter.process_file(test_file, mime_type))

        # Assert
        assert result["category"] == "Medizin"
        assert result["sender"] == "Dr. Müller"
        assert result["year"] == 2023

    def test_complete_workflow_with_text_file(
        self,
        integration_test_dir: Path,
        mock_gemini_api: MagicMock,
        test_settings: Settings,
        smart_sorter_client: AsyncGeminiClient,
    ) -> None:
        """Complete workflow processes text file and returns categorization."""
        # Arrange: Create text file with contract content
        test_file = integration_test_dir / "contract.txt"
        test_file.write_text(
            "Vertrag zwischen Firma A und Firma B\nDatum: 15.03.2024",
            encoding="utf-8",
        )

        # Configure expected response
        mock_api_response(mock_gemini_api, "Verträge", "Firma A", 2024)

        sorter = SmartSorter(smart_sorter_client, test_settings)

        # Act
        result = asyncio.run(sorter.process_file(test_file, "text/plain"))

        # Assert
        assert result["category"] == "Verträge"
        assert result["sender"] == "Firma A"
        assert result["year"] == 2024

    def test_workflow_with_multiple_files_sequentially(
        self,
        integration_test_dir: Path,
        mock_gemini_api: MagicMock,
        test_settings: Settings,
        smart_sorter_client: AsyncGeminiClient,
    ) -> None:
        """Multiple files processed sequentially maintain correct results."""
        # Arrange: Create multiple test files
        files = [
            create_test_file_with_content(
                integration_test_dir,
                "doc1.pdf",
                b"%PDF-1.4 first document",
                "application/pdf",
            ),
            create_test_file_with_content(
                integration_test_dir,
                "photo.jpg",
                b"\xff\xd8\xff\xe0 photo data",
                "image/jpeg",
            ),
            create_test_file_with_content(
                integration_test_dir, "notes.txt", b"Some text content", "text/plain"
            ),
        ]

        # Expected responses for each file
        responses = [
            ("Finanzen", "Bank A", 2024),
            ("Medizin", "Dr. Schmidt", 2023),
            ("Privat", None, None),
        ]

        sorter = SmartSorter(smart_sorter_client, test_settings)

        # Act & Assert: Process each file and verify results
        for (test_file, mime_type), (cat, sender, year) in zip(files, responses):
            # Reconfigure mock for each file
            mock_api_response(mock_gemini_api, cat, sender, year)

            result = asyncio.run(sorter.process_file(test_file, mime_type))

            assert result["category"] == cat
            assert result["sender"] == sender
            assert result["year"] == year


# =============================================================================
# Test Class: Custom Categories
# =============================================================================


class TestCustomCategories:
    """Tests for custom category configuration."""

    def test_workflow_with_custom_categories(
        self,
        integration_test_dir: Path,
        mock_gemini_api: MagicMock,
        test_settings: Settings,
        smart_sorter_client: AsyncGeminiClient,
    ) -> None:
        """Custom categories are used in AI prompt and returned in results."""
        # Arrange: Set custom categories
        test_settings.set("custom_categories", ["Steuern", "Versicherung"])

        test_file, mime_type = create_test_file_with_content(
            integration_test_dir,
            "tax_document.pdf",
            b"%PDF-1.4 tax document content",
            "application/pdf",
        )

        mock_api_response(mock_gemini_api, "Steuern", "Finanzamt", 2024)

        sorter = SmartSorter(smart_sorter_client, test_settings)

        # Act
        result = asyncio.run(sorter.process_file(test_file, mime_type))

        # Assert: Result uses custom category
        assert result["category"] == "Steuern"
        assert result["sender"] == "Finanzamt"

        # Verify prompt contains custom categories
        mock_model = mock_gemini_api.GenerativeModel.return_value
        call_args = mock_model.generate_content_async.call_args[0][0]
        prompt_content = str(call_args)
        assert "Steuern" in prompt_content
        assert "Versicherung" in prompt_content

    def test_custom_categories_merge_with_defaults(
        self,
        integration_test_dir: Path,
        mock_gemini_api: MagicMock,
        test_settings: Settings,
        smart_sorter_client: AsyncGeminiClient,
    ) -> None:
        """Custom categories are merged with defaults, custom taking precedence."""
        # Arrange: Add a custom category that's NOT in defaults
        test_settings.set("custom_categories", ["MeineKategorie"])

        test_file, mime_type = create_test_file_with_content(
            integration_test_dir,
            "document.pdf",
            b"%PDF-1.4 content",
            "application/pdf",
        )

        mock_api_response(mock_gemini_api, "Finanzen", None, None)

        sorter = SmartSorter(smart_sorter_client, test_settings)

        # Act
        _ = asyncio.run(sorter.process_file(test_file, mime_type))

        # Assert: Both custom and default categories appear in prompt
        mock_model = mock_gemini_api.GenerativeModel.return_value
        call_args = mock_model.generate_content_async.call_args[0][0]
        prompt_content = str(call_args)

        # Custom category should be present
        assert "MeineKategorie" in prompt_content

        # Default categories should also be present
        for default_cat in DEFAULT_CATEGORIES[:3]:  # Check first few
            assert default_cat in prompt_content

    def test_fallback_to_sonstiges_category(
        self,
        integration_test_dir: Path,
        mock_gemini_api: MagicMock,
        test_settings: Settings,
        smart_sorter_client: AsyncGeminiClient,
    ) -> None:
        """Fallback category 'Sonstiges' is accepted for unclassifiable files."""
        # Arrange
        test_file, mime_type = create_test_file_with_content(
            integration_test_dir,
            "unknown_file.bin",
            b"\x00\x01\x02\x03 random binary data",
            "application/octet-stream",
        )

        # AI returns "Sonstiges" for unclassifiable content
        mock_api_response(mock_gemini_api, "Sonstiges", None, None)

        sorter = SmartSorter(smart_sorter_client, test_settings)

        # Act
        result = asyncio.run(sorter.process_file(test_file, mime_type))

        # Assert
        assert result["category"] == "Sonstiges"
        assert result["sender"] is None
        assert result["year"] is None


# =============================================================================
# Test Class: Error Scenarios
# =============================================================================


class TestErrorScenarios:
    """Tests for error handling in smart sorting workflow."""

    def test_nonexistent_file_raises_error(
        self,
        integration_test_dir: Path,
        mock_gemini_api: MagicMock,
        test_settings: Settings,
        smart_sorter_client: AsyncGeminiClient,
    ) -> None:
        """Processing non-existent file raises AIClientError."""
        # Arrange
        nonexistent_file = integration_test_dir / "does_not_exist.pdf"
        sorter = SmartSorter(smart_sorter_client, test_settings)

        # Act & Assert
        with pytest.raises(AIClientError, match="does not exist"):
            asyncio.run(sorter.process_file(nonexistent_file, "application/pdf"))

    def test_invalid_mime_type_handled_gracefully(
        self,
        integration_test_dir: Path,
        mock_gemini_api: MagicMock,
        test_settings: Settings,
        smart_sorter_client: AsyncGeminiClient,
    ) -> None:
        """Invalid MIME type is passed to API without causing crash."""
        # Arrange
        test_file, _ = create_test_file_with_content(
            integration_test_dir,
            "strange_file.xyz",
            b"some content",
            "invalid/mime-type",
        )

        mock_api_response(mock_gemini_api, "Sonstiges", None, None)

        sorter = SmartSorter(smart_sorter_client, test_settings)

        # Act - should not crash, API decides how to handle
        result = asyncio.run(sorter.process_file(test_file, "invalid/mime-type"))

        # Assert - file was processed
        assert result["category"] == "Sonstiges"

    def test_api_error_propagates_correctly(
        self,
        integration_test_dir: Path,
        mock_gemini_api: MagicMock,
        test_settings: Settings,
        smart_sorter_client: AsyncGeminiClient,
    ) -> None:
        """API errors are propagated as AIClientError."""
        # Arrange
        test_file, mime_type = create_test_file_with_content(
            integration_test_dir,
            "document.pdf",
            b"%PDF-1.4 content",
            "application/pdf",
        )

        # Configure mock to raise exception
        mock_model = mock_gemini_api.GenerativeModel.return_value
        mock_model.generate_content_async = AsyncMock(
            side_effect=AIClientError("API failed")
        )

        sorter = SmartSorter(smart_sorter_client, test_settings)

        # Act & Assert
        with pytest.raises(AIClientError, match="API failed"):
            asyncio.run(sorter.process_file(test_file, mime_type))

    def test_invalid_json_response_raises_error(
        self,
        integration_test_dir: Path,
        mock_gemini_api: MagicMock,
        test_settings: Settings,
        smart_sorter_client: AsyncGeminiClient,
    ) -> None:
        """Invalid JSON response from API raises AIClientError."""
        # Arrange
        test_file, mime_type = create_test_file_with_content(
            integration_test_dir,
            "document.pdf",
            b"%PDF-1.4 content",
            "application/pdf",
        )

        # Configure mock to return invalid JSON
        mock_response = MagicMock()
        mock_response.text = "not valid json {"
        mock_model = mock_gemini_api.GenerativeModel.return_value
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)

        sorter = SmartSorter(smart_sorter_client, test_settings)

        # Act & Assert
        with pytest.raises(AIClientError, match="Failed to parse"):
            asyncio.run(sorter.process_file(test_file, mime_type))


# =============================================================================
# Test Class: File Type Variations
# =============================================================================


class TestFileTypeVariations:
    """Tests for handling different file types in smart sorting."""

    def test_png_image_processing(
        self,
        integration_test_dir: Path,
        mock_gemini_api: MagicMock,
        test_settings: Settings,
        smart_sorter_client: AsyncGeminiClient,
    ) -> None:
        """PNG images are processed correctly."""
        # Arrange: PNG magic bytes
        png_header = b"\x89PNG\r\n\x1a\n"
        test_file, mime_type = create_test_file_with_content(
            integration_test_dir,
            "scan.png",
            png_header + b"fake png data",
            "image/png",
        )

        mock_api_response(mock_gemini_api, "Dokumente", "Behörde XY", 2024)

        sorter = SmartSorter(smart_sorter_client, test_settings)

        # Act
        result = asyncio.run(sorter.process_file(test_file, mime_type))

        # Assert
        assert result["category"] == "Dokumente"
        assert result["sender"] == "Behörde XY"

    def test_tiff_image_processing(
        self,
        integration_test_dir: Path,
        mock_gemini_api: MagicMock,
        test_settings: Settings,
        smart_sorter_client: AsyncGeminiClient,
    ) -> None:
        """TIFF images are processed with preprocessing mocked.

        Note: We mock the preprocessor because creating valid TIFF files
        for testing is complex. The important behavior tested here is that
        exotic formats flow through the pipeline correctly.
        """
        # Arrange: TIFF file (content doesn't matter since preprocessor is mocked)
        test_file, mime_type = create_test_file_with_content(
            integration_test_dir,
            "scan.tiff",
            b"fake tiff data - preprocessor will be mocked",
            "image/tiff",
        )

        mock_api_response(mock_gemini_api, "Archiv", None, 2020)

        # Mock preprocessor to skip actual image processing
        with patch.object(
            smart_sorter_client.preprocessor, "prepare_file"
        ) as mock_prep:
            # Return original file path with no cleanup needed
            mock_prep.return_value = (test_file, False)

            sorter = SmartSorter(smart_sorter_client, test_settings)

            # Act
            result = asyncio.run(sorter.process_file(test_file, mime_type))

        # Assert
        assert result["category"] == "Archiv"
        assert result["year"] == 2020
        # Verify preprocessing was attempted
        mock_prep.assert_called_once_with(test_file)

    def test_multiple_file_types_in_sequence(
        self,
        integration_test_dir: Path,
        mock_gemini_api: MagicMock,
        test_settings: Settings,
        smart_sorter_client: AsyncGeminiClient,
    ) -> None:
        """Different file types processed sequentially produce correct results."""
        # Arrange: Create files with proper magic bytes
        files_and_types = [
            ("doc.pdf", b"%PDF-1.4 pdf content", "application/pdf"),
            ("photo.jpg", b"\xff\xd8\xff\xe0 jpeg", "image/jpeg"),
            ("image.png", b"\x89PNG\r\n\x1a\n png", "image/png"),
            ("note.txt", b"plain text content", "text/plain"),
        ]

        expected_categories = ["Finanzen", "Fotos", "Dokumente", "Notizen"]

        sorter = SmartSorter(smart_sorter_client, test_settings)

        # Act & Assert
        for (filename, content, mime), expected_cat in zip(
            files_and_types, expected_categories
        ):
            test_file, _ = create_test_file_with_content(
                integration_test_dir, filename, content, mime
            )
            mock_api_response(mock_gemini_api, expected_cat, None, None)

            result = asyncio.run(sorter.process_file(test_file, mime))
            assert result["category"] == expected_cat


# =============================================================================
# Test Class: Result Validation
# =============================================================================


class TestResultValidation:
    """Tests for validating smart sorting results."""

    def test_result_contains_all_required_fields(
        self,
        integration_test_dir: Path,
        mock_gemini_api: MagicMock,
        test_settings: Settings,
        smart_sorter_client: AsyncGeminiClient,
    ) -> None:
        """Result dictionary contains category, sender, and year fields."""
        # Arrange
        test_file, mime_type = create_test_file_with_content(
            integration_test_dir,
            "document.pdf",
            b"%PDF-1.4 content",
            "application/pdf",
        )

        mock_api_response(mock_gemini_api, "Finanzen", "Company Inc", 2024)

        sorter = SmartSorter(smart_sorter_client, test_settings)

        # Act
        result = asyncio.run(sorter.process_file(test_file, mime_type))

        # Assert: All required fields present with correct types
        assert "category" in result
        assert "sender" in result
        assert "year" in result
        assert isinstance(result["category"], str)
        assert result["sender"] is None or isinstance(result["sender"], str)
        assert result["year"] is None or isinstance(result["year"], int)

    def test_result_with_null_values(
        self,
        integration_test_dir: Path,
        mock_gemini_api: MagicMock,
        test_settings: Settings,
        smart_sorter_client: AsyncGeminiClient,
    ) -> None:
        """Null values for sender and year are handled correctly."""
        # Arrange
        test_file, mime_type = create_test_file_with_content(
            integration_test_dir,
            "unknown.pdf",
            b"%PDF-1.4 unclear content",
            "application/pdf",
        )

        # Response with null values
        mock_api_response(mock_gemini_api, "Privat", None, None)

        sorter = SmartSorter(smart_sorter_client, test_settings)

        # Act
        result = asyncio.run(sorter.process_file(test_file, mime_type))

        # Assert
        assert result["category"] == "Privat"
        assert result["sender"] is None
        assert result["year"] is None

    def test_category_from_default_list(
        self,
        integration_test_dir: Path,
        mock_gemini_api: MagicMock,
        test_settings: Settings,
        smart_sorter_client: AsyncGeminiClient,
    ) -> None:
        """Returned category comes from available categories list."""
        # Arrange
        test_file, mime_type = create_test_file_with_content(
            integration_test_dir,
            "document.pdf",
            b"%PDF-1.4 content",
            "application/pdf",
        )

        # Use a category from DEFAULT_CATEGORIES
        expected_category = DEFAULT_CATEGORIES[0]
        mock_api_response(mock_gemini_api, expected_category, None, None)

        sorter = SmartSorter(smart_sorter_client, test_settings)

        # Act
        result = asyncio.run(sorter.process_file(test_file, mime_type))

        # Assert: Category is from available list
        all_categories = get_all_categories() + ["Sonstiges"]
        assert result["category"] in all_categories
