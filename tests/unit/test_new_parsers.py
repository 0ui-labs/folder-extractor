"""
Unit tests for the new parser module.
"""

import pytest

from folder_extractor.utils.parsers import parse_depth, parse_domains, parse_file_types


class TestNewParsers:
    """Test the refactored parser functions."""

    def test_parse_file_types_compatibility(self):
        """Test that new parser maintains compatibility."""
        # Import both old and new
        from folder_extractor.main import parse_dateitypen as old_parse

        test_cases = [
            "pdf",
            "pdf,jpg,png",
            ".pdf,.jpg",
            "*.pdf,*.jpg",
            "PDF,JPG",
            "",
            None,
            "pdf, jpg, png",
        ]

        for test in test_cases:
            old_result = old_parse(test)
            new_result = parse_file_types(test)
            assert old_result == new_result, f"Mismatch for input '{test}'"

    def test_parse_domains_compatibility(self):
        """Test that new domain parser maintains compatibility."""
        from folder_extractor.main import parse_domains as old_parse

        test_cases = [
            "youtube.com",
            "youtube.com,github.com",
            "www.youtube.com",
            "",
            None,
            "youtube.com, github.com",
        ]

        for test in test_cases:
            old_result = old_parse(test)
            new_result = parse_domains(test)
            assert old_result == new_result, f"Mismatch for input '{test}'"

    def test_parse_depth_new_functionality(self):
        """Test the new depth parser."""
        # Valid depths
        assert parse_depth("0") == 0
        assert parse_depth("5") == 5
        assert parse_depth("100") == 100

        # Invalid depths
        with pytest.raises(ValueError, match="positive Zahl"):
            parse_depth("-1")

        with pytest.raises(ValueError, match="keine Zahl"):
            parse_depth("abc")

        with pytest.raises(ValueError, match="keine Zahl"):
            parse_depth("1.5")


class TestParserEdgeCases:
    """Test edge cases for parsers to achieve 100% coverage."""

    def test_parse_file_types_star_prefix_without_dot(self):
        """Test parse_file_types with *prefix (no dot) pattern (line 42)."""
        # Pattern like "*pdf" (star but no dot)
        result = parse_file_types("*pdf")
        assert result == [".pdf"]

        # Multiple patterns with mixed formats
        result = parse_file_types("*pdf,*.jpg,.txt,doc")
        assert result == [".pdf", ".jpg", ".txt", ".doc"]

    def test_parse_file_types_empty_items(self):
        """Test parse_file_types with empty items after split."""
        # Double comma creates empty item
        result = parse_file_types("pdf,,jpg")
        assert result == [".pdf", ".jpg"]

        # Trailing comma
        result = parse_file_types("pdf,")
        assert result == [".pdf"]

    def test_parse_file_types_whitespace_only(self):
        """Test parse_file_types with whitespace-only string."""
        result = parse_file_types("   ")
        assert result is None

    def test_parse_domains_whitespace_only(self):
        """Test parse_domains with whitespace-only string."""
        result = parse_domains("   ")
        assert result is None

    def test_parse_domains_empty_items(self):
        """Test parse_domains with empty items after split."""
        # Double comma creates empty item
        result = parse_domains("example.com,,test.org")
        assert result == ["example.com", "test.org"]
