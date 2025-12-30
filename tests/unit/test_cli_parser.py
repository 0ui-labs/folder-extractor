"""
Unit tests for CLI parser module.
"""

from io import StringIO
from unittest.mock import patch

import pytest

from folder_extractor.cli.parser import create_parser


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
        assert args.deduplicate is False
        assert args.type is None
        assert args.domain is None

    def test_depth_argument(self):
        """Test depth argument parsing."""
        # Valid depth
        args = self.parser.parse_args(["--depth", "5"])
        assert args.depth == 5

        args = self.parser.parse_args(["-d", "10"])
        assert args.depth == 10

        # Invalid depth
        with pytest.raises(SystemExit):
            self.parser.parse_args(["--depth", "-1"])

        with pytest.raises(SystemExit):
            self.parser.parse_args(["--depth", "abc"])

    def test_type_argument(self):
        """Test type argument parsing."""
        args = self.parser.parse_args(["--type", "pdf,jpg,mp3"])
        assert args.type == "pdf,jpg,mp3"

        args = self.parser.parse_args(["-t", "txt"])
        assert args.type == "txt"

    def test_boolean_flags(self):
        """Test boolean flag arguments."""
        # Dry run
        args = self.parser.parse_args(["--dry-run"])
        assert args.dry_run is True

        args = self.parser.parse_args(["-n"])
        assert args.dry_run is True

        # Sort by type
        args = self.parser.parse_args(["--sort-by-type"])
        assert args.sort_by_type is True

        args = self.parser.parse_args(["-s"])
        assert args.sort_by_type is True

        # Undo
        args = self.parser.parse_args(["--undo"])
        assert args.undo is True

        args = self.parser.parse_args(["-u"])
        assert args.undo is True

        # Include hidden
        args = self.parser.parse_args(["--include-hidden"])
        assert args.include_hidden is True

        # Deduplicate
        args = self.parser.parse_args(["--deduplicate"])
        assert args.deduplicate is True

        # Smart-merge (alias for deduplicate)
        args = self.parser.parse_args(["--smart-merge"])
        assert args.deduplicate is True

    def test_domain_argument(self):
        """Test domain argument parsing."""
        args = self.parser.parse_args(["--domain", "youtube.com,github.com"])
        assert args.domain == "youtube.com,github.com"

    def test_global_dedup_flag(self):
        """Test global deduplication flag enables content-based dedup across entire destination."""
        # Default should be False
        args = self.parser.parse_args([])
        assert args.global_dedup is False

        # Flag enables global deduplication
        args = self.parser.parse_args(["--global-dedup"])
        assert args.global_dedup is True

    def test_deduplicate_and_global_dedup_flags_together(self):
        """Test that both deduplication flags can be used together."""
        args = self.parser.parse_args(["--deduplicate", "--global-dedup"])
        assert args.deduplicate is True
        assert args.global_dedup is True

    def test_help_flag(self):
        """Test help flag handling."""
        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                self.parser.parse_args(["--help"])

            assert exc_info.value.code == 0
            output = mock_stdout.getvalue()
            assert "Folder Extractor" in output
            assert "Verwendung:" in output

    def test_version_flag(self):
        """Test version flag handling."""
        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            with pytest.raises(SystemExit) as exc_info:
                self.parser.parse_args(["--version"])

            assert exc_info.value.code == 0
            output = mock_stdout.getvalue()
            assert "folder-extractor" in output
            assert "Von" in output

    def test_combined_arguments(self):
        """Test combining multiple arguments."""
        args = self.parser.parse_args(
            [
                "--depth",
                "3",
                "--type",
                "pdf,doc",
                "--dry-run",
                "--sort-by-type",
                "--include-hidden",
                "--deduplicate",
                "--global-dedup",
                "--domain",
                "example.com",
            ]
        )

        assert args.depth == 3
        assert args.type == "pdf,doc"
        assert args.dry_run is True
        assert args.sort_by_type is True
        assert args.include_hidden is True
        assert args.deduplicate is True
        assert args.global_dedup is True
        assert args.domain == "example.com"

    def test_short_and_long_forms(self):
        """Test that short and long forms work the same."""
        # Test equivalent arguments
        args1 = self.parser.parse_args(["-d", "5", "-t", "pdf", "-n", "-s", "-u"])
        args2 = self.parser.parse_args(
            ["--depth", "5", "--type", "pdf", "--dry-run", "--sort-by-type", "--undo"]
        )

        assert args1.depth == args2.depth
        assert args1.type == args2.type
        assert args1.dry_run == args2.dry_run
        assert args1.sort_by_type == args2.sort_by_type
        assert args1.undo == args2.undo

    def test_extract_archives_flag_default_is_false(self):
        """Test extract-archives flag defaults to False when not specified."""
        args = self.parser.parse_args([])
        assert args.extract_archives is False

    def test_extract_archives_flag_enables_archive_extraction(self):
        """Test --extract-archives flag enables archive extraction mode."""
        args = self.parser.parse_args(["--extract-archives"])
        assert args.extract_archives is True

    def test_delete_archives_flag_default_is_false(self):
        """Test delete-archives flag defaults to False when not specified."""
        args = self.parser.parse_args([])
        assert args.delete_archives is False

    def test_delete_archives_flag_enables_archive_deletion(self):
        """Test --delete-archives flag enables deletion of extracted archives."""
        args = self.parser.parse_args(["--delete-archives"])
        assert args.delete_archives is True

    def test_extract_and_delete_archives_flags_together(self):
        """Test both archive flags can be used together."""
        args = self.parser.parse_args(["--extract-archives", "--delete-archives"])
        assert args.extract_archives is True
        assert args.delete_archives is True

    def test_archive_flags_with_other_options(self):
        """Test archive flags work alongside other extraction options."""
        args = self.parser.parse_args(
            [
                "--extract-archives",
                "--delete-archives",
                "--deduplicate",
                "--sort-by-type",
            ]
        )
        assert args.extract_archives is True
        assert args.delete_archives is True
        assert args.deduplicate is True
        assert args.sort_by_type is True

    def test_watch_flag_default_is_false(self):
        """Test watch flag defaults to False when not specified."""
        args = self.parser.parse_args([])
        assert args.watch is False

    def test_watch_flag_enables_watch_mode(self):
        """Test --watch flag enables folder monitoring mode."""
        args = self.parser.parse_args(["--watch"])
        assert args.watch is True

    def test_watch_flag_combines_with_sort_by_type(self):
        """Test --watch can be used together with --sort-by-type."""
        args = self.parser.parse_args(["--watch", "--sort-by-type"])
        assert args.watch is True
        assert args.sort_by_type is True

    def test_watch_flag_combines_with_deduplicate(self):
        """Test --watch can be used together with --deduplicate."""
        args = self.parser.parse_args(["--watch", "--deduplicate"])
        assert args.watch is True
        assert args.deduplicate is True

    def test_watch_flag_combines_with_extract_archives(self):
        """Test --watch can be used together with --extract-archives."""
        args = self.parser.parse_args(["--watch", "--extract-archives"])
        assert args.watch is True
        assert args.extract_archives is True

    def test_watch_flag_with_all_common_options(self):
        """Test --watch works with all commonly used extraction options."""
        args = self.parser.parse_args(
            [
                "--watch",
                "--sort-by-type",
                "--deduplicate",
                "--global-dedup",
                "--extract-archives",
                "--depth",
                "2",
                "--type",
                "pdf,jpg",
            ]
        )
        assert args.watch is True
        assert args.sort_by_type is True
        assert args.deduplicate is True
        assert args.global_dedup is True
        assert args.extract_archives is True
        assert args.depth == 2
        assert args.type == "pdf,jpg"

    # --ask flag tests for Knowledge Graph queries
    def test_ask_flag_default_is_none(self):
        """Test --ask flag defaults to None when not specified."""
        args = self.parser.parse_args([])
        assert args.ask is None

    def test_ask_flag_accepts_query_string(self):
        """Test --ask flag accepts a natural language query string."""
        args = self.parser.parse_args(["--ask", "Welche Versicherungsdokumente habe ich?"])
        assert args.ask == "Welche Versicherungsdokumente habe ich?"

    def test_ask_flag_accepts_query_with_entity(self):
        """Test --ask flag accepts queries mentioning entities like company names."""
        args = self.parser.parse_args(["--ask", "Zeig mir Rechnungen von Apple"])
        assert args.ask == "Zeig mir Rechnungen von Apple"

    def test_ask_flag_accepts_empty_string(self):
        """Test --ask flag accepts empty string (validation happens later)."""
        args = self.parser.parse_args(["--ask", ""])
        assert args.ask == ""

    def test_ask_flag_requires_argument(self):
        """Test --ask flag requires a query argument."""
        with pytest.raises(SystemExit):
            self.parser.parse_args(["--ask"])

    def test_ask_flag_with_special_characters(self):
        """Test --ask flag handles queries with special characters like quotes."""
        args = self.parser.parse_args(["--ask", "Dokumente mit 'wichtig' im Namen"])
        assert args.ask == "Dokumente mit 'wichtig' im Namen"

    def test_ask_flag_with_german_umlauts(self):
        """Test --ask flag handles German umlauts correctly."""
        args = self.parser.parse_args(["--ask", "Verträge und Kündigungsschreiben"])
        assert args.ask == "Verträge und Kündigungsschreiben"
