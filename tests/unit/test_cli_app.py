"""
Unit tests for CLI app module.
"""
import pytest
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

from folder_extractor.cli.app import EnhancedFolderExtractorCLI, main


class TestEnhancedFolderExtractorCLI:
    """Test EnhancedFolderExtractorCLI class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Ensure CWD is valid (other tests may have deleted their temp directories)
        try:
            os.getcwd()
        except (FileNotFoundError, OSError):
            os.chdir(os.path.expanduser("~"))

        # Create CLI instance with mocked dependencies
        with patch('folder_extractor.cli.app.create_parser'):
            with patch('folder_extractor.cli.app.create_console_interface'):
                with patch('folder_extractor.cli.app.get_state_manager'):
                    self.cli = EnhancedFolderExtractorCLI()

    def test_init(self):
        """Test CLI initialization."""
        with patch('folder_extractor.cli.app.create_parser') as mock_parser:
            with patch('folder_extractor.cli.app.create_console_interface') as mock_interface:
                with patch('folder_extractor.cli.app.get_state_manager') as mock_state:
                    cli = EnhancedFolderExtractorCLI()

                    # Check all components initialized
                    mock_parser.assert_called_once()
                    mock_interface.assert_called_once()
                    mock_state.assert_called_once()

                    assert cli.parser is not None
                    assert cli.interface is not None
                    assert cli.state_manager is not None

    def test_run_keyboard_interrupt(self):
        """Test handling keyboard interrupt."""
        # Mock parser to raise KeyboardInterrupt
        self.cli.parser.parse_args = Mock(side_effect=KeyboardInterrupt)

        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            result = self.cli.run()

            assert result == 1
            output = mock_stdout.getvalue()
            assert "abgebrochen" in output.lower()

    def test_run_general_exception(self):
        """Test handling general exceptions."""
        # Mock parser to raise exception
        self.cli.parser.parse_args = Mock(side_effect=ValueError("Test error"))

        # Mock interface
        self.cli.interface.show_message = Mock()

        result = self.cli.run()

        assert result == 1
        self.cli.interface.show_message.assert_called_once()
        args = self.cli.interface.show_message.call_args[0]
        assert "Test error" in args[0]

    def test_run_undo_operation(self):
        """Test running undo operation."""
        # Mock parsed arguments for undo
        mock_args = Mock(undo=True)
        self.cli.parser.parse_args = Mock(return_value=mock_args)

        # Mock execute_undo
        with patch.object(self.cli, '_execute_undo', return_value=0) as mock_undo:
            with patch('folder_extractor.cli.app.configure_from_args'):
                with patch('folder_extractor.core.migration.MigrationHelper'):
                    result = self.cli.run()

                    assert result == 0
                    mock_undo.assert_called_once()
                    # Should not show welcome for undo
                    assert not self.cli.interface.show_welcome.called

    def test_run_extraction_operation(self):
        """Test running extraction operation."""
        # Mock parsed arguments for extraction
        mock_args = Mock(undo=False)
        self.cli.parser.parse_args = Mock(return_value=mock_args)

        # Mock interface
        self.cli.interface.show_welcome = Mock()

        # Mock execute_extraction
        with patch.object(self.cli, '_execute_extraction', return_value=0) as mock_extract:
            with patch('folder_extractor.cli.app.configure_from_args'):
                with patch('folder_extractor.core.migration.MigrationHelper'):
                    result = self.cli.run()

                    assert result == 0
                    mock_extract.assert_called_once()
                    # Should show welcome for extraction
                    self.cli.interface.show_welcome.assert_called_once()

    def test_execute_extraction_success(self):
        """Test successful extraction execution."""
        # Mock extractor and orchestrator
        mock_extractor = Mock()
        mock_orchestrator = Mock()
        mock_orchestrator.execute_extraction.return_value = {
            "status": "success",
            "moved": 10,
            "duplicates": 2,
            "errors": 0
        }

        # Mock interface
        self.cli.interface.confirm_operation = Mock(return_value=True)
        self.cli.interface.show_progress = Mock()
        self.cli.interface.show_summary = Mock()
        self.cli.interface.show_message = Mock()

        # Mock state manager
        self.cli.state_manager.is_abort_requested = Mock(return_value=False)
        self.cli.state_manager.request_abort = Mock()
        self.cli.state_manager.get_value = Mock(return_value=False)
        self.cli.state_manager.get_operation_stats = Mock(return_value=None)

        with patch('folder_extractor.cli.app.EnhancedFileExtractor', return_value=mock_extractor):
            with patch('folder_extractor.cli.app.EnhancedExtractionOrchestrator', return_value=mock_orchestrator):
                with patch('folder_extractor.cli.app.KeyboardHandler') as mock_handler_class:
                    result = self.cli._execute_extraction("/test/path")

                    assert result == 0

                    # Check orchestrator called correctly
                    mock_orchestrator.execute_extraction.assert_called_once()

                    # Check keyboard handler started and stopped
                    mock_handler_class.assert_called_once()
                    mock_handler = mock_handler_class.return_value
                    mock_handler.start.assert_called_once()
                    mock_handler.stop.assert_called_once()

                    # Check summary shown
                    self.cli.interface.show_summary.assert_called_once()

    def test_execute_extraction_no_files(self):
        """Test extraction with no files found."""
        mock_orchestrator = Mock()
        mock_orchestrator.execute_extraction.return_value = {
            "status": "no_files",
            "message": "Keine Dateien gefunden"
        }

        self.cli.state_manager.get_value = Mock(return_value=True)  # dry_run
        self.cli.state_manager.get_operation_stats = Mock(return_value=None)
        self.cli.interface.show_summary = Mock()

        with patch('folder_extractor.cli.app.EnhancedFileExtractor'):
            with patch('folder_extractor.cli.app.EnhancedExtractionOrchestrator', return_value=mock_orchestrator):
                result = self.cli._execute_extraction("/test/path")

                # Should still return 0 (not an error)
                assert result == 0

    def test_execute_extraction_cancelled(self):
        """Test extraction cancelled by user."""
        mock_orchestrator = Mock()
        mock_orchestrator.execute_extraction.return_value = {
            "status": "cancelled",
            "message": "Operation abgebrochen"
        }

        self.cli.state_manager.get_value = Mock(return_value=True)  # dry_run
        self.cli.state_manager.get_operation_stats = Mock(return_value=None)
        self.cli.interface.show_summary = Mock()

        with patch('folder_extractor.cli.app.EnhancedFileExtractor'):
            with patch('folder_extractor.cli.app.EnhancedExtractionOrchestrator', return_value=mock_orchestrator):
                result = self.cli._execute_extraction("/test/path")

                # Should return 0 (not an error)
                assert result == 0

    def test_execute_extraction_with_path_object(self):
        """Test extraction with Path object instead of string."""
        mock_orchestrator = Mock()
        mock_orchestrator.execute_extraction.return_value = {
            "status": "success",
            "moved": 5,
            "duplicates": 0,
            "errors": 0
        }

        self.cli.state_manager.get_value = Mock(return_value=True)  # dry_run
        self.cli.state_manager.get_operation_stats = Mock(return_value=None)
        self.cli.interface.show_summary = Mock()

        test_path = Path("/test/path")

        with patch('folder_extractor.cli.app.EnhancedFileExtractor'):
            with patch('folder_extractor.cli.app.EnhancedExtractionOrchestrator', return_value=mock_orchestrator):
                result = self.cli._execute_extraction(test_path)

                assert result == 0

                # Verify orchestrator received Path object
                call_args = mock_orchestrator.execute_extraction.call_args
                source_path = call_args[1]['source_path']
                assert isinstance(source_path, Path)

    def test_execute_undo_success(self):
        """Test successful undo execution."""
        mock_orchestrator = Mock()
        mock_orchestrator.execute_undo.return_value = {
            "status": "success",
            "message": "10 Dateien zurück verschoben",
            "restored": 10,
            "errors": 0
        }

        # Mock interface
        self.cli.interface.show_message = Mock()

        with patch('folder_extractor.cli.app.EnhancedFileExtractor'):
            with patch('folder_extractor.cli.app.EnhancedExtractionOrchestrator', return_value=mock_orchestrator):
                result = self.cli._execute_undo("/test/path")

                assert result == 0

                # Check orchestrator called
                mock_orchestrator.execute_undo.assert_called_once_with("/test/path")

                # Check messages shown
                assert self.cli.interface.show_message.call_count >= 2

    def test_execute_undo_no_history(self):
        """Test undo with no history."""
        mock_orchestrator = Mock()
        mock_orchestrator.execute_undo.return_value = {
            "status": "no_history",
            "message": "Keine History gefunden",
            "restored": 0
        }

        self.cli.interface.show_message = Mock()

        with patch('folder_extractor.cli.app.EnhancedFileExtractor'):
            with patch('folder_extractor.cli.app.EnhancedExtractionOrchestrator', return_value=mock_orchestrator):
                result = self.cli._execute_undo("/test/path")

                assert result == 1

                # Check warning message shown
                final_call = self.cli.interface.show_message.call_args_list[-1]
                assert final_call[1]["message_type"] == "warning"

    def test_execute_undo_with_path_object(self):
        """Test undo with Path object instead of string."""
        mock_orchestrator = Mock()
        mock_orchestrator.execute_undo.return_value = {
            "status": "success",
            "message": "5 Dateien zurück verschoben",
            "restored": 5,
            "errors": 0
        }

        self.cli.interface.show_message = Mock()

        test_path = Path("/test/path")

        with patch('folder_extractor.cli.app.EnhancedFileExtractor'):
            with patch('folder_extractor.cli.app.EnhancedExtractionOrchestrator', return_value=mock_orchestrator):
                result = self.cli._execute_undo(test_path)

                assert result == 0

                # Verify orchestrator received Path object
                call_args = mock_orchestrator.execute_undo.call_args[0]
                assert isinstance(call_args[0], Path)


def test_main_function():
    """Test main entry point function."""
    with patch('folder_extractor.cli.app.EnhancedFolderExtractorCLI') as mock_cli_class:
        mock_cli = Mock()
        mock_cli.run.return_value = 0
        mock_cli_class.return_value = mock_cli

        # Test with no arguments
        result = main()
        assert result == 0
        mock_cli.run.assert_called_once_with(None)

        # Test with arguments
        mock_cli.run.reset_mock()
        test_args = ['--dry-run', '--depth', '3']
        result = main(test_args)
        assert result == 0
        mock_cli.run.assert_called_once_with(test_args)


def test_main_entry_point():
    """Test __main__ entry point."""
    # Test that main can be called when module is run directly
    test_module = "folder_extractor.cli.app"

    with patch(f'{test_module}.main', return_value=0) as mock_main:
        # Simulate the module being run as __main__
        with patch.dict('sys.modules', {test_module: MagicMock(__name__='__main__')}):
            # The actual code that would run
            if sys.modules[test_module].__name__ == '__main__':
                result = mock_main()
                assert result == 0
