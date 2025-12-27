"""
File preprocessing module for AI API uploads.

Automatically validates and optimizes files before sending to AI API:
- Size check: Files > 20MB are optimized
- Format check: Exotic formats (TIFF, BMP, WebP) converted to JPG
- Image optimization: Resize to max 2048px, JPG quality 85
- PDF optimization: Extract first 5 pages only
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path

from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from folder_extractor.config.constants import (
    PREPROCESSOR_EXOTIC_IMAGE_FORMATS,
    PREPROCESSOR_JPG_QUALITY,
    PREPROCESSOR_MAX_FILE_SIZE_MB,
    PREPROCESSOR_MAX_IMAGE_DIMENSION,
    PREPROCESSOR_MAX_PDF_PAGES,
)

logger = logging.getLogger(__name__)


class PreprocessorError(Exception):
    """Exception raised for file preprocessing errors."""

    pass


class FilePreprocessor:
    """Preprocesses files before AI API upload."""

    # Supported image formats for optimization
    # Note: PREPROCESSOR_EXOTIC_IMAGE_FORMATS (from constants) is a subset
    # that always triggers optimization
    _IMAGE_FORMATS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp"}

    def prepare_file(self, filepath: Path) -> tuple[Path, bool]:
        """Prepare a file for AI API upload by optimizing if necessary.

        This is the main public interface for file preprocessing. It validates
        the file, checks if optimization is needed, and returns the optimized
        path along with a cleanup flag.

        Args:
            filepath: Path to the file to prepare

        Returns:
            Tuple of (optimized_path, needs_cleanup):
            - optimized_path: Path to optimized file (or original if no optimization)
            - needs_cleanup: True if a temporary file was created. Caller is responsible
              for deleting the temporary file and its parent directory after use.

        Raises:
            PreprocessorError: If file does not exist or is not a file
        """
        # Validation
        if not filepath.exists():
            raise PreprocessorError(f"File does not exist: {filepath}")
        if not filepath.is_file():
            raise PreprocessorError(f"Path is not a file: {filepath}")

        # Check if optimization is needed
        if not self._needs_optimization(filepath):
            return (filepath, False)

        # Determine file type and optimize accordingly
        ext = filepath.suffix.lower()

        # Handle image formats
        if ext in self._IMAGE_FORMATS:
            optimized_path = self._optimize_image(filepath)
            return (optimized_path, True)

        # Handle PDF format
        if ext == ".pdf":
            optimized_path = self._optimize_pdf(filepath)
            # PDF might not be optimized if <= 5 pages
            needs_cleanup = optimized_path != filepath
            return (optimized_path, needs_cleanup)

        # Unknown format - log warning and return original
        logger.warning(f"Unknown file type for optimization: {filepath.name}")
        return (filepath, False)

    def _needs_optimization(self, filepath: Path) -> bool:
        """Check if a file needs optimization before API upload.

        A file needs optimization if:
        1. Its size exceeds the maximum allowed (> 20MB)
        2. Its format is an exotic image format (TIFF, BMP, WebP)

        Args:
            filepath: Path to the file to check

        Returns:
            True if file needs optimization, False otherwise
        """
        # Size check
        file_size_mb = filepath.stat().st_size / (1024 * 1024)
        if file_size_mb > PREPROCESSOR_MAX_FILE_SIZE_MB:
            return True

        # Format check
        ext = filepath.suffix.lower()
        return ext in PREPROCESSOR_EXOTIC_IMAGE_FORMATS

    def _optimize_image(self, filepath: Path) -> Path:
        """Optimize an image for AI API upload.

        Scales large images and converts to JPG format.

        Args:
            filepath: Path to the image file to optimize

        Returns:
            Path to the optimized image in a temporary directory

        Raises:
            PreprocessorError: If image optimization fails
        """
        temp_dir = None
        try:
            # Create temporary directory
            temp_dir = Path(tempfile.mkdtemp(prefix="preprocessor_"))

            # Load image using context manager to ensure file handle is closed
            with Image.open(filepath) as img:
                # Load image data into memory before context exits
                img.load()

                # Convert to RGB if necessary (for JPG compatibility)
                # convert() returns a new image that persists after context
                if img.mode in ("RGBA", "P", "LA", "L"):
                    image = img.convert("RGB")
                else:
                    # Create a copy that persists after context manager exits
                    image = img.copy()

            # Check dimensions and scale if necessary
            width, height = image.size
            max_dim = PREPROCESSOR_MAX_IMAGE_DIMENSION
            if max(width, height) > max_dim:
                # Use thumbnail to resize while preserving aspect ratio
                image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

            # Save as JPG with specified quality
            output_path = temp_dir / f"{filepath.stem}_optimized.jpg"
            image.save(
                output_path, "JPEG", quality=PREPROCESSOR_JPG_QUALITY, optimize=True
            )

            logger.info(f"Image optimized: {filepath.name} -> {output_path.name}")

            return output_path

        except Exception as e:
            # Clean up temp directory on failure to prevent leaks
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            error_msg = f"Failed to optimize image {filepath.name}: {e}"
            raise PreprocessorError(error_msg) from e

    def _optimize_pdf(self, filepath: Path) -> Path:
        """Optimize a PDF for AI API upload by extracting first pages.

        Extracts only the first MAX_PDF_PAGES (5) pages from PDFs with more pages.

        Args:
            filepath: Path to the PDF file to optimize

        Returns:
            Path to the optimized PDF (or original if <= MAX_PDF_PAGES pages)

        Raises:
            PreprocessorError: If PDF optimization fails
        """
        temp_dir = None
        try:
            # Load PDF
            reader = PdfReader(filepath)
            num_pages = len(reader.pages)

            # Check if optimization is needed
            if num_pages <= PREPROCESSOR_MAX_PDF_PAGES:
                return filepath

            logger.info(
                f"PDF has {num_pages} pages, "
                f"extracting first {PREPROCESSOR_MAX_PDF_PAGES}"
            )

            # Create temporary directory
            temp_dir = Path(tempfile.mkdtemp(prefix="preprocessor_"))

            # Extract first MAX_PDF_PAGES pages
            writer = PdfWriter()
            for i in range(PREPROCESSOR_MAX_PDF_PAGES):
                writer.add_page(reader.pages[i])

            # Save optimized PDF
            output_path = temp_dir / f"{filepath.stem}_optimized.pdf"
            with open(output_path, "wb") as f:
                writer.write(f)

            logger.info(
                f"PDF optimized: {filepath.name} -> {output_path.name} "
                f"({PREPROCESSOR_MAX_PDF_PAGES} pages)"
            )

            return output_path

        except PdfReadError as e:
            # Clean up temp directory on failure to prevent leaks
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            error_msg = f"Failed to optimize PDF {filepath.name}: {e}"
            raise PreprocessorError(error_msg) from e
        except Exception as e:
            # Clean up temp directory on failure to prevent leaks
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            error_msg = f"Failed to optimize PDF {filepath.name}: {e}"
            raise PreprocessorError(error_msg) from e
