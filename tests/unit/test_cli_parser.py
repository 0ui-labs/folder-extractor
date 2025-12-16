"""
Unit tests for CLI parser module.
"""
import pytest
import sys
from io import StringIO
from unittest.mock import patch

from folder_extractor.cli.parser import ArgumentParser, create_parser


class TestArgumentParser:
    """Test ArgumentParser class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = create_parser()
    
    def test_default_arguments(self):
        """Test parsing with default arguments."""
        args = self.parser.parse_args([])
        
        assert args.depth == 0
        assert args.dry_run is False
        assert args.sort_by_type is False
        assert args.undo is False
        assert args.include_hidden is False
        assert args.type is None
        assert args.domain is None
    
    def test_depth_argument(self):
        """Test depth argument parsing."""
        # Valid depth
        args = self.parser.parse_args(['--depth', '5'])
        assert args.depth == 5
        
        args = self.parser.parse_args(['-d', '10'])
        assert args.depth == 10
        
        # Invalid depth
        with pytest.raises(SystemExit):
            self.parser.parse_args(['--depth', '-1'])
        
        with pytest.raises(SystemExit):
            self.parser.parse_args(['--depth', 'abc'])
    
    def test_type_argument(self):
        """Test type argument parsing."""
        args = self.parser.parse_args(['--type', 'pdf,jpg,mp3'])
        assert args.type == 'pdf,jpg,mp3'
        
        args = self.parser.parse_args(['-t', 'txt'])
        assert args.type == 'txt'
    
    def test_boolean_flags(self):
        """Test boolean flag arguments."""
        # Dry run
        args = self.parser.parse_args(['--dry-run'])
        assert args.dry_run is True
        
        args = self.parser.parse_args(['-n'])
        assert args.dry_run is True
        
        # Sort by type
        args = self.parser.parse_args(['--sort-by-type'])
        assert args.sort_by_type is True
        
        args = self.parser.parse_args(['-s'])
        assert args.sort_by_type is True
        
        # Undo
        args = self.parser.parse_args(['--undo'])
        assert args.undo is True
        
        args = self.parser.parse_args(['-u'])
        assert args.undo is True
        
        # Include hidden
        args = self.parser.parse_args(['--include-hidden'])
        assert args.include_hidden is True
    
    def test_domain_argument(self):
        """Test domain argument parsing."""
        args = self.parser.parse_args(['--domain', 'youtube.com,github.com'])
        assert args.domain == 'youtube.com,github.com'
    
    def test_help_flag(self):
        """Test help flag handling."""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                self.parser.parse_args(['--help'])
            
            assert exc_info.value.code == 0
            output = mock_stdout.getvalue()
            assert "Folder Extractor" in output
            assert "Verwendung:" in output
    
    def test_version_flag(self):
        """Test version flag handling."""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                self.parser.parse_args(['--version'])
            
            assert exc_info.value.code == 0
            output = mock_stdout.getvalue()
            assert "folder-extractor" in output
            assert "Von" in output
    
    def test_combined_arguments(self):
        """Test combining multiple arguments."""
        args = self.parser.parse_args([
            '--depth', '3',
            '--type', 'pdf,doc',
            '--dry-run',
            '--sort-by-type',
            '--include-hidden',
            '--domain', 'example.com'
        ])
        
        assert args.depth == 3
        assert args.type == 'pdf,doc'
        assert args.dry_run is True
        assert args.sort_by_type is True
        assert args.include_hidden is True
        assert args.domain == 'example.com'
    
    def test_short_and_long_forms(self):
        """Test that short and long forms work the same."""
        # Test equivalent arguments
        args1 = self.parser.parse_args(['-d', '5', '-t', 'pdf', '-n', '-s', '-u'])
        args2 = self.parser.parse_args([
            '--depth', '5', 
            '--type', 'pdf',
            '--dry-run',
            '--sort-by-type',
            '--undo'
        ])
        
        assert args1.depth == args2.depth
        assert args1.type == args2.type
        assert args1.dry_run == args2.dry_run
        assert args1.sort_by_type == args2.sort_by_type
        assert args1.undo == args2.undo