"""
Unit tests for the new parser module.
"""
import pytest
from folder_extractor.utils.parsers import (
    parse_file_types,
    parse_domains,
    parse_depth
)


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
            "pdf, jpg, png"
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
            "youtube.com, github.com"
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