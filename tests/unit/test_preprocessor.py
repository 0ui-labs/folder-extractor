"""
Unit tests for file preprocessor module.

Tests cover:
- PreprocessorError exception
- FilePreprocessor class existence
- Preprocessor constants
"""

from __future__ import annotations

import pytest

from folder_extractor.config.constants import (
    PREPROCESSOR_EXOTIC_IMAGE_FORMATS,
    PREPROCESSOR_JPG_QUALITY,
    PREPROCESSOR_MAX_FILE_SIZE_MB,
    PREPROCESSOR_MAX_IMAGE_DIMENSION,
    PREPROCESSOR_MAX_PDF_PAGES,
)
from folder_extractor.core.preprocessor import (
    FilePreprocessor,
    PreprocessorError,
)


class TestPreprocessorError:
    """Tests for PreprocessorError exception."""

    def test_is_exception_subclass(self):
        """PreprocessorError inherits from Exception."""
        assert issubclass(PreprocessorError, Exception)

    def test_can_be_raised_with_message(self):
        """PreprocessorError can be raised with a descriptive message."""
        with pytest.raises(PreprocessorError, match="Preprocessing failed"):
            raise PreprocessorError("Preprocessing failed")

    def test_preserves_error_message(self):
        """PreprocessorError stores the error message correctly."""
        error = PreprocessorError("File too large")
        assert str(error) == "File too large"

    def test_can_be_caught_as_exception(self):
        """PreprocessorError can be caught as base Exception."""
        try:
            raise PreprocessorError("Test error")
        except Exception as e:
            assert isinstance(e, PreprocessorError)
            assert str(e) == "Test error"


class TestFilePreprocessor:
    """Tests for FilePreprocessor class."""

    def test_class_exists(self):
        """FilePreprocessor class is defined and importable."""
        assert FilePreprocessor is not None

    def test_can_be_instantiated(self):
        """FilePreprocessor can be instantiated."""
        preprocessor = FilePreprocessor()
        assert preprocessor is not None
        assert isinstance(preprocessor, FilePreprocessor)


class TestPreprocessorConstants:
    """Tests for preprocessor-related constants."""

    def test_max_file_size_is_defined(self):
        """PREPROCESSOR_MAX_FILE_SIZE_MB constant is defined."""
        assert PREPROCESSOR_MAX_FILE_SIZE_MB is not None

    def test_max_file_size_is_20mb(self):
        """PREPROCESSOR_MAX_FILE_SIZE_MB is set to 20 (Gemini API limit)."""
        assert PREPROCESSOR_MAX_FILE_SIZE_MB == 20

    def test_max_image_dimension_is_defined(self):
        """PREPROCESSOR_MAX_IMAGE_DIMENSION constant is defined."""
        assert PREPROCESSOR_MAX_IMAGE_DIMENSION is not None

    def test_max_image_dimension_is_2048(self):
        """PREPROCESSOR_MAX_IMAGE_DIMENSION is set to 2048 pixels."""
        assert PREPROCESSOR_MAX_IMAGE_DIMENSION == 2048

    def test_jpg_quality_is_defined(self):
        """PREPROCESSOR_JPG_QUALITY constant is defined."""
        assert PREPROCESSOR_JPG_QUALITY is not None

    def test_jpg_quality_is_85(self):
        """PREPROCESSOR_JPG_QUALITY is set to 85."""
        assert PREPROCESSOR_JPG_QUALITY == 85

    def test_max_pdf_pages_is_defined(self):
        """PREPROCESSOR_MAX_PDF_PAGES constant is defined."""
        assert PREPROCESSOR_MAX_PDF_PAGES is not None

    def test_max_pdf_pages_is_5(self):
        """PREPROCESSOR_MAX_PDF_PAGES is set to 5."""
        assert PREPROCESSOR_MAX_PDF_PAGES == 5

    def test_exotic_image_formats_is_defined(self):
        """PREPROCESSOR_EXOTIC_IMAGE_FORMATS constant is defined."""
        assert PREPROCESSOR_EXOTIC_IMAGE_FORMATS is not None

    def test_exotic_image_formats_is_set(self):
        """PREPROCESSOR_EXOTIC_IMAGE_FORMATS contains expected formats."""
        expected = {".tiff", ".tif", ".bmp", ".webp"}
        assert expected == PREPROCESSOR_EXOTIC_IMAGE_FORMATS

    def test_exotic_image_formats_is_set_type(self):
        """PREPROCESSOR_EXOTIC_IMAGE_FORMATS is a set for efficient lookup."""
        assert isinstance(PREPROCESSOR_EXOTIC_IMAGE_FORMATS, set)


class TestNeedsOptimization:
    """Tests for FilePreprocessor._needs_optimization() method."""

    def test_small_file_with_normal_format_returns_false(self, tmp_path):
        """A small file (< 20MB) with a normal format does not need optimization."""
        # Arrange: Create a 1MB .jpg file
        test_file = tmp_path / "small_image.jpg"
        test_file.write_bytes(b"x" * (1 * 1024 * 1024))  # 1 MB

        preprocessor = FilePreprocessor()

        # Act
        result = preprocessor._needs_optimization(test_file)

        # Assert
        assert result is False

    def test_large_file_returns_true(self, tmp_path):
        """A file larger than 20MB needs optimization regardless of format."""
        # Arrange: Create a 21MB .jpg file
        test_file = tmp_path / "large_image.jpg"
        test_file.write_bytes(b"x" * (21 * 1024 * 1024))  # 21 MB

        preprocessor = FilePreprocessor()

        # Act
        result = preprocessor._needs_optimization(test_file)

        # Assert
        assert result is True

    def test_small_file_with_exotic_format_tiff_returns_true(self, tmp_path):
        """A small file with .tiff extension needs optimization."""
        # Arrange: Create a 1MB .tiff file
        test_file = tmp_path / "image.tiff"
        test_file.write_bytes(b"x" * (1 * 1024 * 1024))  # 1 MB

        preprocessor = FilePreprocessor()

        # Act
        result = preprocessor._needs_optimization(test_file)

        # Assert
        assert result is True

    def test_small_file_with_exotic_format_tif_returns_true(self, tmp_path):
        """A small file with .tif extension (short form) needs optimization."""
        # Arrange: Create a 1MB .tif file
        test_file = tmp_path / "image.tif"
        test_file.write_bytes(b"x" * (1 * 1024 * 1024))  # 1 MB

        preprocessor = FilePreprocessor()

        # Act
        result = preprocessor._needs_optimization(test_file)

        # Assert
        assert result is True

    def test_small_file_with_exotic_format_bmp_returns_true(self, tmp_path):
        """A small file with .bmp extension needs optimization."""
        # Arrange: Create a 1MB .bmp file
        test_file = tmp_path / "image.bmp"
        test_file.write_bytes(b"x" * (1 * 1024 * 1024))  # 1 MB

        preprocessor = FilePreprocessor()

        # Act
        result = preprocessor._needs_optimization(test_file)

        # Assert
        assert result is True

    def test_small_file_with_exotic_format_webp_returns_true(self, tmp_path):
        """A small file with .webp extension needs optimization."""
        # Arrange: Create a 1MB .webp file
        test_file = tmp_path / "image.webp"
        test_file.write_bytes(b"x" * (1 * 1024 * 1024))  # 1 MB

        preprocessor = FilePreprocessor()

        # Act
        result = preprocessor._needs_optimization(test_file)

        # Assert
        assert result is True

    def test_large_file_with_exotic_format_returns_true(self, tmp_path):
        """A large file with an exotic format needs optimization (both criteria met)."""
        # Arrange: Create a 25MB .tiff file
        test_file = tmp_path / "large_image.tiff"
        test_file.write_bytes(b"x" * (25 * 1024 * 1024))  # 25 MB

        preprocessor = FilePreprocessor()

        # Act
        result = preprocessor._needs_optimization(test_file)

        # Assert
        assert result is True

    def test_exactly_20mb_file_returns_false(self, tmp_path):
        """A file of exactly 20MB does not need optimization (boundary not exceeded)."""
        # Arrange: Create exactly 20MB .jpg file
        test_file = tmp_path / "boundary_image.jpg"
        test_file.write_bytes(b"x" * (20 * 1024 * 1024))  # Exactly 20 MB

        preprocessor = FilePreprocessor()

        # Act
        result = preprocessor._needs_optimization(test_file)

        # Assert
        assert result is False

    def test_uppercase_extension_is_handled(self, tmp_path):
        """Uppercase file extensions are correctly normalized and detected."""
        # Arrange: Create a 1MB .TIFF file (uppercase)
        test_file = tmp_path / "image.TIFF"
        test_file.write_bytes(b"x" * (1 * 1024 * 1024))  # 1 MB

        preprocessor = FilePreprocessor()

        # Act
        result = preprocessor._needs_optimization(test_file)

        # Assert
        assert result is True

    def test_pdf_file_does_not_need_optimization_by_format(self, tmp_path):
        """A small PDF file does not need optimization (not an exotic format)."""
        # Arrange: Create a 1MB .pdf file
        test_file = tmp_path / "document.pdf"
        test_file.write_bytes(b"x" * (1 * 1024 * 1024))  # 1 MB

        preprocessor = FilePreprocessor()

        # Act
        result = preprocessor._needs_optimization(test_file)

        # Assert
        assert result is False

    def test_png_file_does_not_need_optimization_by_format(self, tmp_path):
        """A small PNG file does not need optimization (not an exotic format)."""
        # Arrange: Create a 1MB .png file
        test_file = tmp_path / "image.png"
        test_file.write_bytes(b"x" * (1 * 1024 * 1024))  # 1 MB

        preprocessor = FilePreprocessor()

        # Act
        result = preprocessor._needs_optimization(test_file)

        # Assert
        assert result is False


class TestOptimizeImage:
    """Tests for FilePreprocessor._optimize_image() method."""

    def test_image_is_converted_to_jpg(self, tmp_path):
        """An image file is converted to JPG format."""
        from PIL import Image

        # Arrange: Create a PNG image
        input_image = tmp_path / "test_image.png"
        img = Image.new("RGB", (100, 100), color="red")
        img.save(input_image, "PNG")

        preprocessor = FilePreprocessor()

        # Act
        result_path = preprocessor._optimize_image(input_image)

        # Assert
        assert result_path.suffix == ".jpg"
        assert result_path.exists()
        # Verify it's a valid JPEG
        with Image.open(result_path) as result_img:
            assert result_img.format == "JPEG"

    def test_large_image_is_scaled_down_to_max_dimension(self, tmp_path):
        """An image larger than 2048px is scaled down while preserving aspect ratio."""
        from PIL import Image

        # Arrange: Create a large image (3000x2000)
        input_image = tmp_path / "large_image.png"
        img = Image.new("RGB", (3000, 2000), color="blue")
        img.save(input_image, "PNG")

        preprocessor = FilePreprocessor()

        # Act
        result_path = preprocessor._optimize_image(input_image)

        # Assert
        with Image.open(result_path) as result_img:
            width, height = result_img.size
            # Max dimension should be 2048
            assert max(width, height) == PREPROCESSOR_MAX_IMAGE_DIMENSION
            # Aspect ratio should be preserved (3000:2000 = 3:2)
            assert width == 2048
            assert height == 1365  # 2048 * (2000/3000) ≈ 1365

    def test_small_image_is_not_scaled(self, tmp_path):
        """An image smaller than 2048px is not scaled."""
        from PIL import Image

        # Arrange: Create a small image (800x600)
        input_image = tmp_path / "small_image.png"
        original_size = (800, 600)
        img = Image.new("RGB", original_size, color="green")
        img.save(input_image, "PNG")

        preprocessor = FilePreprocessor()

        # Act
        result_path = preprocessor._optimize_image(input_image)

        # Assert
        with Image.open(result_path) as result_img:
            assert result_img.size == original_size

    def test_rgba_image_is_converted_to_rgb(self, tmp_path):
        """An RGBA image (with alpha channel) is converted to RGB for JPG compatibility."""
        from PIL import Image

        # Arrange: Create an RGBA image with transparency
        input_image = tmp_path / "rgba_image.png"
        img = Image.new(
            "RGBA", (100, 100), color=(255, 0, 0, 128)
        )  # Semi-transparent red
        img.save(input_image, "PNG")

        preprocessor = FilePreprocessor()

        # Act
        result_path = preprocessor._optimize_image(input_image)

        # Assert
        with Image.open(result_path) as result_img:
            assert result_img.mode == "RGB"
            assert result_img.format == "JPEG"

    def test_palette_mode_image_is_converted_to_rgb(self, tmp_path):
        """A palette mode (P) image is converted to RGB for JPG compatibility."""
        from PIL import Image

        # Arrange: Create a palette mode image
        input_image = tmp_path / "palette_image.gif"
        img = Image.new("P", (100, 100))
        img.putpalette([i for i in range(256)] * 3)  # Simple palette
        img.save(input_image, "GIF")

        preprocessor = FilePreprocessor()

        # Act
        result_path = preprocessor._optimize_image(input_image)

        # Assert
        with Image.open(result_path) as result_img:
            assert result_img.mode == "RGB"
            assert result_img.format == "JPEG"

    def test_grayscale_image_is_converted_to_rgb(self, tmp_path):
        """A grayscale (L mode) image is converted to RGB for JPG compatibility."""
        from PIL import Image

        # Arrange: Create a grayscale image
        input_image = tmp_path / "grayscale_image.png"
        img = Image.new("L", (100, 100), color=128)  # Gray
        img.save(input_image, "PNG")

        preprocessor = FilePreprocessor()

        # Act
        result_path = preprocessor._optimize_image(input_image)

        # Assert
        with Image.open(result_path) as result_img:
            assert result_img.mode == "RGB"
            assert result_img.format == "JPEG"

    def test_invalid_image_raises_preprocessor_error(self, tmp_path):
        """An invalid image file raises PreprocessorError."""
        # Arrange: Create a file with invalid image data
        input_file = tmp_path / "invalid_image.png"
        input_file.write_bytes(b"This is not a valid image file")

        preprocessor = FilePreprocessor()

        # Act & Assert
        with pytest.raises(PreprocessorError, match="Failed to optimize image"):
            preprocessor._optimize_image(input_file)

    def test_output_is_in_temp_directory_with_optimized_suffix(self, tmp_path):
        """Output file is placed in a temp directory with '_optimized.jpg' suffix."""
        import tempfile

        from PIL import Image

        # Arrange: Create an image
        input_image = tmp_path / "my_photo.png"
        img = Image.new("RGB", (100, 100), color="yellow")
        img.save(input_image, "PNG")

        preprocessor = FilePreprocessor()

        # Act
        result_path = preprocessor._optimize_image(input_image)

        # Assert
        assert result_path.name == "my_photo_optimized.jpg"
        # Check it's in a temp directory (starts with system temp prefix)
        assert str(result_path.parent).startswith(tempfile.gettempdir())
        assert "preprocessor_" in str(result_path.parent)

    def test_jpg_quality_is_85(self, tmp_path):
        """Optimized image uses quality 85 (verifiable through file size comparison)."""
        from PIL import Image

        # Arrange: Create a colorful image that will compress noticeably at different qualities
        input_image = tmp_path / "colorful_image.png"
        img = Image.new("RGB", (500, 500))
        # Create a gradient for more realistic compression behavior
        pixels = img.load()
        for x in range(500):
            for y in range(500):
                pixels[x, y] = (x % 256, y % 256, (x + y) % 256)
        img.save(input_image, "PNG")

        preprocessor = FilePreprocessor()

        # Act
        result_path = preprocessor._optimize_image(input_image)

        # Assert: Save same image at quality 100 and 50 for comparison
        high_quality_path = tmp_path / "high_quality.jpg"
        low_quality_path = tmp_path / "low_quality.jpg"

        img_to_save = Image.open(input_image)
        img_to_save.save(high_quality_path, "JPEG", quality=100)
        img_to_save.save(low_quality_path, "JPEG", quality=50)

        result_size = result_path.stat().st_size
        high_quality_size = high_quality_path.stat().st_size
        low_quality_size = low_quality_path.stat().st_size

        # Quality 85 should be between quality 50 and 100
        assert low_quality_size < result_size < high_quality_size

    def test_la_mode_image_is_converted_to_rgb(self, tmp_path):
        """An LA mode (grayscale with alpha) image is converted to RGB."""
        from PIL import Image

        # Arrange: Create an LA mode image
        input_image = tmp_path / "la_image.png"
        img = Image.new("LA", (100, 100), color=(128, 200))
        img.save(input_image, "PNG")

        preprocessor = FilePreprocessor()

        # Act
        result_path = preprocessor._optimize_image(input_image)

        # Assert
        with Image.open(result_path) as result_img:
            assert result_img.mode == "RGB"
            assert result_img.format == "JPEG"

    def test_tall_image_is_scaled_by_height(self, tmp_path):
        """A tall image (height > width) is scaled based on height."""
        from PIL import Image

        # Arrange: Create a tall image (1500x3000)
        input_image = tmp_path / "tall_image.png"
        img = Image.new("RGB", (1500, 3000), color="purple")
        img.save(input_image, "PNG")

        preprocessor = FilePreprocessor()

        # Act
        result_path = preprocessor._optimize_image(input_image)

        # Assert
        with Image.open(result_path) as result_img:
            width, height = result_img.size
            # Height should be the max dimension
            assert height == PREPROCESSOR_MAX_IMAGE_DIMENSION
            # Aspect ratio preserved (1500:3000 = 1:2)
            assert width == 1024  # 2048 * (1500/3000) = 1024

    def test_image_exactly_at_max_dimension_is_not_scaled(self, tmp_path):
        """An image exactly at 2048px max dimension is not scaled."""
        from PIL import Image

        # Arrange: Create an image at exactly max dimension
        input_image = tmp_path / "exact_size.png"
        original_size = (2048, 1500)
        img = Image.new("RGB", original_size, color="cyan")
        img.save(input_image, "PNG")

        preprocessor = FilePreprocessor()

        # Act
        result_path = preprocessor._optimize_image(input_image)

        # Assert
        with Image.open(result_path) as result_img:
            assert result_img.size == original_size


class TestOptimizePdf:
    """Tests for FilePreprocessor._optimize_pdf() method."""

    def test_pdf_with_fewer_pages_returns_original_path(self, tmp_path):
        """A PDF with 5 or fewer pages returns the original path (no optimization needed)."""
        from pypdf import PdfWriter

        # Arrange: Create a 3-page PDF
        input_pdf = tmp_path / "small_document.pdf"
        writer = PdfWriter()
        for _ in range(3):
            writer.add_blank_page(width=612, height=792)  # Letter size
        with open(input_pdf, "wb") as f:
            writer.write(f)

        preprocessor = FilePreprocessor()

        # Act
        result_path = preprocessor._optimize_pdf(input_pdf)

        # Assert: Original path returned, not a temp file
        assert result_path == input_pdf

    def test_pdf_with_exactly_5_pages_returns_original_path(self, tmp_path):
        """A PDF with exactly 5 pages returns the original path (boundary case)."""
        from pypdf import PdfWriter

        # Arrange: Create a 5-page PDF
        input_pdf = tmp_path / "boundary_document.pdf"
        writer = PdfWriter()
        for _ in range(5):
            writer.add_blank_page(width=612, height=792)
        with open(input_pdf, "wb") as f:
            writer.write(f)

        preprocessor = FilePreprocessor()

        # Act
        result_path = preprocessor._optimize_pdf(input_pdf)

        # Assert: Original path returned
        assert result_path == input_pdf

    def test_pdf_with_more_than_5_pages_is_truncated(self, tmp_path):
        """A PDF with more than 5 pages is truncated to exactly 5 pages."""
        from pypdf import PdfReader, PdfWriter

        # Arrange: Create a 10-page PDF
        input_pdf = tmp_path / "large_document.pdf"
        writer = PdfWriter()
        for _ in range(10):
            writer.add_blank_page(width=612, height=792)
        with open(input_pdf, "wb") as f:
            writer.write(f)

        preprocessor = FilePreprocessor()

        # Act
        result_path = preprocessor._optimize_pdf(input_pdf)

        # Assert: New file with exactly 5 pages
        assert result_path != input_pdf
        reader = PdfReader(result_path)
        assert len(reader.pages) == PREPROCESSOR_MAX_PDF_PAGES

    def test_optimized_pdf_is_in_temp_directory(self, tmp_path):
        """Optimized PDF is placed in a temporary directory with preprocessor_ prefix."""
        import tempfile

        from pypdf import PdfWriter

        # Arrange: Create a 7-page PDF
        input_pdf = tmp_path / "document.pdf"
        writer = PdfWriter()
        for _ in range(7):
            writer.add_blank_page(width=612, height=792)
        with open(input_pdf, "wb") as f:
            writer.write(f)

        preprocessor = FilePreprocessor()

        # Act
        result_path = preprocessor._optimize_pdf(input_pdf)

        # Assert
        assert str(result_path.parent).startswith(tempfile.gettempdir())
        assert "preprocessor_" in str(result_path.parent)

    def test_optimized_pdf_has_correct_filename_suffix(self, tmp_path):
        """Optimized PDF file has '_optimized.pdf' suffix."""
        from pypdf import PdfWriter

        # Arrange: Create a 6-page PDF
        input_pdf = tmp_path / "my_document.pdf"
        writer = PdfWriter()
        for _ in range(6):
            writer.add_blank_page(width=612, height=792)
        with open(input_pdf, "wb") as f:
            writer.write(f)

        preprocessor = FilePreprocessor()

        # Act
        result_path = preprocessor._optimize_pdf(input_pdf)

        # Assert
        assert result_path.name == "my_document_optimized.pdf"

    def test_corrupt_pdf_raises_preprocessor_error(self, tmp_path):
        """A corrupt/invalid PDF file raises PreprocessorError."""
        # Arrange: Create a file with invalid PDF content
        input_file = tmp_path / "corrupt.pdf"
        input_file.write_bytes(b"This is not a valid PDF file")

        preprocessor = FilePreprocessor()

        # Act & Assert
        with pytest.raises(PreprocessorError, match="Failed to optimize PDF"):
            preprocessor._optimize_pdf(input_file)

    def test_pdf_with_20_pages_is_reduced_to_5(self, tmp_path):
        """A PDF with 20 pages is reduced to exactly 5 pages."""
        from pypdf import PdfReader, PdfWriter

        # Arrange: Create a 20-page PDF
        input_pdf = tmp_path / "very_long_document.pdf"
        writer = PdfWriter()
        for _ in range(20):
            writer.add_blank_page(width=612, height=792)
        with open(input_pdf, "wb") as f:
            writer.write(f)

        preprocessor = FilePreprocessor()

        # Act
        result_path = preprocessor._optimize_pdf(input_pdf)

        # Assert
        reader = PdfReader(result_path)
        assert len(reader.pages) == 5

    def test_optimized_pdf_is_valid_and_readable(self, tmp_path):
        """The optimized PDF is a valid, readable PDF file."""
        from pypdf import PdfReader, PdfWriter

        # Arrange: Create an 8-page PDF
        input_pdf = tmp_path / "readable_document.pdf"
        writer = PdfWriter()
        for _ in range(8):
            writer.add_blank_page(width=612, height=792)
        with open(input_pdf, "wb") as f:
            writer.write(f)

        preprocessor = FilePreprocessor()

        # Act
        result_path = preprocessor._optimize_pdf(input_pdf)

        # Assert: Verify it's a valid PDF by reading it
        reader = PdfReader(result_path)
        assert len(reader.pages) == 5
        # Ensure pages have expected dimensions
        page = reader.pages[0]
        assert page.mediabox.width > 0
        assert page.mediabox.height > 0

    def test_single_page_pdf_returns_original(self, tmp_path):
        """A single-page PDF returns the original path."""
        from pypdf import PdfWriter

        # Arrange: Create a 1-page PDF
        input_pdf = tmp_path / "single_page.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        with open(input_pdf, "wb") as f:
            writer.write(f)

        preprocessor = FilePreprocessor()

        # Act
        result_path = preprocessor._optimize_pdf(input_pdf)

        # Assert
        assert result_path == input_pdf


class TestPrepareFile:
    """Tests for FilePreprocessor.prepare_file() public method."""

    def test_non_existent_file_raises_preprocessor_error(self, tmp_path):
        """prepare_file() raises PreprocessorError for non-existent file."""
        # Arrange
        non_existent = tmp_path / "does_not_exist.jpg"
        preprocessor = FilePreprocessor()

        # Act & Assert
        with pytest.raises(PreprocessorError, match="does not exist"):
            preprocessor.prepare_file(non_existent)

    def test_directory_path_raises_preprocessor_error(self, tmp_path):
        """prepare_file() raises PreprocessorError when path is a directory."""
        # Arrange
        directory = tmp_path / "a_directory"
        directory.mkdir()
        preprocessor = FilePreprocessor()

        # Act & Assert
        with pytest.raises(PreprocessorError, match="is not a file"):
            preprocessor.prepare_file(directory)

    def test_small_file_with_normal_format_returns_original_path(self, tmp_path):
        """A small file with normal format returns (original_path, False)."""
        from PIL import Image

        # Arrange: Create a small JPG image (< 20MB, not exotic format)
        input_image = tmp_path / "small_image.jpg"
        img = Image.new("RGB", (100, 100), color="red")
        img.save(input_image, "JPEG")

        preprocessor = FilePreprocessor()

        # Act
        result_path, needs_cleanup = preprocessor.prepare_file(input_image)

        # Assert
        assert result_path == input_image
        assert needs_cleanup is False

    def test_large_image_file_returns_optimized_path_with_cleanup_flag(self, tmp_path):
        """A large image file (> 20MB) returns (optimized_path, True)."""
        from PIL import Image

        # Arrange: Create a large image file (> 20MB)
        # 6000x6000 RGB image is about 108MB uncompressed when saved as BMP
        img = Image.new("RGB", (6000, 6000), color="blue")
        # Save as BMP to ensure large file size (uncompressed)
        input_image_bmp = tmp_path / "large_image.bmp"
        img.save(input_image_bmp, "BMP")

        preprocessor = FilePreprocessor()

        # Act
        result_path, needs_cleanup = preprocessor.prepare_file(input_image_bmp)

        # Assert
        assert result_path != input_image_bmp
        assert result_path.suffix == ".jpg"
        assert needs_cleanup is True

    def test_exotic_image_format_returns_optimized_path_with_cleanup_flag(
        self, tmp_path
    ):
        """An exotic image format (TIFF, BMP, WebP) returns (optimized_path, True)."""
        from PIL import Image

        # Arrange: Create a small TIFF image (exotic format)
        input_image = tmp_path / "exotic_image.tiff"
        img = Image.new("RGB", (100, 100), color="green")
        img.save(input_image, "TIFF")

        preprocessor = FilePreprocessor()

        # Act
        result_path, needs_cleanup = preprocessor.prepare_file(input_image)

        # Assert
        assert result_path != input_image
        assert result_path.suffix == ".jpg"
        assert needs_cleanup is True

    def test_webp_format_returns_optimized_path(self, tmp_path):
        """A WebP image (exotic format) returns (optimized_path, True)."""
        from PIL import Image

        # Arrange: Create a WebP image
        input_image = tmp_path / "image.webp"
        img = Image.new("RGB", (100, 100), color="yellow")
        img.save(input_image, "WEBP")

        preprocessor = FilePreprocessor()

        # Act
        result_path, needs_cleanup = preprocessor.prepare_file(input_image)

        # Assert
        assert result_path != input_image
        assert result_path.suffix == ".jpg"
        assert needs_cleanup is True

    def test_bmp_format_returns_optimized_path(self, tmp_path):
        """A BMP image (exotic format) returns (optimized_path, True)."""
        from PIL import Image

        # Arrange: Create a small BMP image
        input_image = tmp_path / "image.bmp"
        img = Image.new("RGB", (100, 100), color="cyan")
        img.save(input_image, "BMP")

        preprocessor = FilePreprocessor()

        # Act
        result_path, needs_cleanup = preprocessor.prepare_file(input_image)

        # Assert
        assert result_path != input_image
        assert result_path.suffix == ".jpg"
        assert needs_cleanup is True

    def test_small_pdf_with_few_pages_returns_original_path(self, tmp_path):
        """A small PDF with <= 5 pages returns (original_path, False)."""
        from pypdf import PdfWriter

        # Arrange: Create a 3-page PDF (< 20MB, <= 5 pages)
        input_pdf = tmp_path / "small_document.pdf"
        writer = PdfWriter()
        for _ in range(3):
            writer.add_blank_page(width=612, height=792)
        with open(input_pdf, "wb") as f:
            writer.write(f)

        preprocessor = FilePreprocessor()

        # Act
        result_path, needs_cleanup = preprocessor.prepare_file(input_pdf)

        # Assert
        assert result_path == input_pdf
        assert needs_cleanup is False

    def test_pdf_with_5_pages_returns_original_path(self, tmp_path):
        """A PDF with exactly 5 pages returns (original_path, False) - boundary case."""
        from pypdf import PdfWriter

        # Arrange: Create a 5-page PDF
        input_pdf = tmp_path / "boundary_document.pdf"
        writer = PdfWriter()
        for _ in range(5):
            writer.add_blank_page(width=612, height=792)
        with open(input_pdf, "wb") as f:
            writer.write(f)

        preprocessor = FilePreprocessor()

        # Act
        result_path, needs_cleanup = preprocessor.prepare_file(input_pdf)

        # Assert
        assert result_path == input_pdf
        assert needs_cleanup is False

    def test_pdf_small_size_many_pages_returns_original(self, tmp_path):
        """A PDF with > 5 pages but < 20MB returns (original_path, False)."""
        from pypdf import PdfWriter

        # Arrange: Create a PDF with 10 pages but < 20MB
        input_pdf = tmp_path / "small_many_pages.pdf"
        writer = PdfWriter()
        for _ in range(10):
            writer.add_blank_page(width=612, height=792)

        with open(input_pdf, "wb") as f:
            writer.write(f)

        preprocessor = FilePreprocessor()

        # Act
        result_path, needs_cleanup = preprocessor.prepare_file(input_pdf)

        # Assert: PDF with > 5 pages but < 20MB doesn't need optimization
        # (size threshold not exceeded, so _needs_optimization returns False)
        assert result_path == input_pdf
        assert needs_cleanup is False

    def test_large_pdf_with_many_pages_returns_optimized_path(self, tmp_path):
        """A large PDF (> 20MB) with > 5 pages returns (optimized_path, True)."""
        from unittest.mock import patch

        from pypdf import PdfWriter

        # Arrange: Create a PDF with 10 pages
        input_pdf = tmp_path / "large_document.pdf"
        writer = PdfWriter()
        for _ in range(10):
            writer.add_blank_page(width=612, height=792)

        with open(input_pdf, "wb") as f:
            writer.write(f)

        preprocessor = FilePreprocessor()

        # Mock _needs_optimization to return True (simulating > 20MB file)
        with patch.object(preprocessor, "_needs_optimization", return_value=True):
            # Act
            result_path, needs_cleanup = preprocessor.prepare_file(input_pdf)

        # Assert: PDF with > 5 pages gets truncated to 5 pages
        assert result_path != input_pdf
        assert result_path.name == "large_document_optimized.pdf"
        assert needs_cleanup is True

        # Verify the optimized PDF has 5 pages
        from pypdf import PdfReader

        reader = PdfReader(result_path)
        assert len(reader.pages) == 5

    def test_unknown_format_returns_original_path_with_warning(self, tmp_path, caplog):
        """An unknown file format returns (original_path, False) with warning log."""
        import logging

        # Arrange: Create a file with unknown format that exceeds size limit
        input_file = tmp_path / "unknown_file.xyz"
        # Make it > 20MB to trigger _needs_optimization
        input_file.write_bytes(b"x" * (21 * 1024 * 1024))

        preprocessor = FilePreprocessor()

        # Act
        with caplog.at_level(logging.WARNING):
            result_path, needs_cleanup = preprocessor.prepare_file(input_file)

        # Assert
        assert result_path == input_file
        assert needs_cleanup is False
        assert "Unknown file type" in caplog.text or "unknown" in caplog.text.lower()

    def test_unknown_format_small_file_returns_original_without_warning(
        self, tmp_path, caplog
    ):
        """A small unknown format file returns (original_path, False) without warning."""
        import logging

        # Arrange: Create a small file with unknown format
        input_file = tmp_path / "small_unknown.xyz"
        input_file.write_bytes(b"x" * 1024)  # 1KB

        preprocessor = FilePreprocessor()

        # Act
        with caplog.at_level(logging.WARNING):
            result_path, needs_cleanup = preprocessor.prepare_file(input_file)

        # Assert: Small file doesn't need optimization, no warning
        assert result_path == input_file
        assert needs_cleanup is False

    def test_jpg_format_recognized_as_image(self, tmp_path):
        """A .jpg file is correctly recognized as an image format."""
        from PIL import Image

        # Arrange: Create a small JPG
        input_image = tmp_path / "test.jpg"
        img = Image.new("RGB", (100, 100), color="red")
        img.save(input_image, "JPEG")

        preprocessor = FilePreprocessor()

        # Act
        result_path, needs_cleanup = preprocessor.prepare_file(input_image)

        # Assert
        assert result_path == input_image
        assert needs_cleanup is False

    def test_jpeg_format_recognized_as_image(self, tmp_path):
        """A .jpeg file is correctly recognized as an image format."""
        from PIL import Image

        # Arrange: Create a small JPEG
        input_image = tmp_path / "test.jpeg"
        img = Image.new("RGB", (100, 100), color="blue")
        img.save(input_image, "JPEG")

        preprocessor = FilePreprocessor()

        # Act
        result_path, needs_cleanup = preprocessor.prepare_file(input_image)

        # Assert
        assert result_path == input_image
        assert needs_cleanup is False

    def test_png_format_recognized_as_image(self, tmp_path):
        """A .png file is correctly recognized as an image format."""
        from PIL import Image

        # Arrange: Create a small PNG
        input_image = tmp_path / "test.png"
        img = Image.new("RGB", (100, 100), color="green")
        img.save(input_image, "PNG")

        preprocessor = FilePreprocessor()

        # Act
        result_path, needs_cleanup = preprocessor.prepare_file(input_image)

        # Assert
        assert result_path == input_image
        assert needs_cleanup is False

    def test_gif_format_recognized_as_image(self, tmp_path):
        """A .gif file is correctly recognized as an image format."""
        from PIL import Image

        # Arrange: Create a small GIF
        input_image = tmp_path / "test.gif"
        img = Image.new("P", (100, 100))
        img.save(input_image, "GIF")

        preprocessor = FilePreprocessor()

        # Act
        result_path, needs_cleanup = preprocessor.prepare_file(input_image)

        # Assert
        assert result_path == input_image
        assert needs_cleanup is False

    def test_uppercase_extension_is_handled(self, tmp_path):
        """Uppercase file extensions are correctly handled."""
        from PIL import Image

        # Arrange: Create a TIFF with uppercase extension
        input_image = tmp_path / "test.TIFF"
        img = Image.new("RGB", (100, 100), color="purple")
        img.save(input_image, "TIFF")

        preprocessor = FilePreprocessor()

        # Act
        result_path, needs_cleanup = preprocessor.prepare_file(input_image)

        # Assert: TIFF is exotic format, should be optimized
        assert result_path != input_image
        assert result_path.suffix == ".jpg"
        assert needs_cleanup is True

    def test_cleanup_flag_false_when_no_optimization_needed(self, tmp_path):
        """needs_cleanup is False when file doesn't need optimization."""
        from PIL import Image

        # Arrange: Create a small normal image
        input_image = tmp_path / "normal.jpg"
        img = Image.new("RGB", (100, 100), color="white")
        img.save(input_image, "JPEG")

        preprocessor = FilePreprocessor()

        # Act
        result_path, needs_cleanup = preprocessor.prepare_file(input_image)

        # Assert
        assert needs_cleanup is False
        assert result_path == input_image

    def test_cleanup_flag_true_when_optimization_performed(self, tmp_path):
        """needs_cleanup is True when file was optimized (temp file created)."""
        from PIL import Image

        # Arrange: Create a TIFF image (exotic format)
        input_image = tmp_path / "exotic.tiff"
        img = Image.new("RGB", (100, 100), color="black")
        img.save(input_image, "TIFF")

        preprocessor = FilePreprocessor()

        # Act
        result_path, needs_cleanup = preprocessor.prepare_file(input_image)

        # Assert
        assert needs_cleanup is True
        assert result_path != input_image
        assert result_path.exists()

    def test_pdf_extension_correctly_identified(self, tmp_path):
        """A .pdf file is correctly identified as PDF format."""
        from pypdf import PdfWriter

        # Arrange: Create a small PDF
        input_pdf = tmp_path / "document.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        with open(input_pdf, "wb") as f:
            writer.write(f)

        preprocessor = FilePreprocessor()

        # Act
        result_path, needs_cleanup = preprocessor.prepare_file(input_pdf)

        # Assert
        assert result_path == input_pdf
        assert needs_cleanup is False

    def test_returns_tuple_type(self, tmp_path):
        """prepare_file() returns a tuple of (Path, bool)."""
        from pathlib import Path

        from PIL import Image

        # Arrange
        input_image = tmp_path / "test.jpg"
        img = Image.new("RGB", (100, 100), color="red")
        img.save(input_image, "JPEG")

        preprocessor = FilePreprocessor()

        # Act
        result = preprocessor.prepare_file(input_image)

        # Assert
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], Path)
        assert isinstance(result[1], bool)
