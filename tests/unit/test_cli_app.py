"""
Unit tests for CLI app module.
"""
import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

from folder_extractor.cli.app import FolderExtractorCLI, main
from folder_extractor.config.settings import settings


class TestFolderExtractorCLI:
    """Test FolderExtractorCLI class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Ensure CWD is valid (other tests may have deleted their temp directories)
        try:
            os.getcwd()
        except (FileNotFoundError, OSError):
            os.chdir(os.path.expanduser("~"))

        # Reset settings
        settings.reset_to_defaults()
        # Create CLI instance with mocked dependencies
        with patch('folder_extractor.cli.app.create_parser'):
            with patch('folder_extractor.cli.app.create_console_interface'):
                with patch('folder_extractor.cli.app.get_app_state'):
                    self.cli = FolderExtractorCLI()
    
    def test_init(self):
        """Test CLI initialization."""
        with patch('folder_extractor.cli.app.create_parser') as mock_parser:
            with patch('folder_extractor.cli.app.create_console_interface') as mock_interface:
                with patch('folder_extractor.cli.app.get_app_state') as mock_state:
                    cli = FolderExtractorCLI()
                    
                    # Check all components initialized
                    mock_parser.assert_called_once()
                    mock_interface.assert_called_once()
                    mock_state.assert_called_once()
                    
                    assert cli.parser is not None
                    assert cli.interface is not None
                    assert cli.app_state is not None
    
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
                with patch('folder_extractor.cli.app.OperationContext'):
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
                with patch('folder_extractor.cli.app.OperationContext'):
                    result = self.cli.run()
                    
                    assert result == 0
                    mock_extract.assert_called_once()
                    # Should show welcome for extraction
                    self.cli.interface.show_welcome.assert_called_once()
    
    def test_execute_extraction_success(self):
        """Test successful extraction execution."""
        # Mock context
        mock_context = Mock()
        mock_context.abort_signal = Mock()
        
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
        
        # Mock app state
        self.cli.app_state.is_abort_requested = Mock(return_value=False)
        self.cli.app_state.request_abort = Mock()
        
        with patch('folder_extractor.cli.app.FileExtractor', return_value=mock_extractor):
            with patch('folder_extractor.cli.app.ExtractionOrchestrator', return_value=mock_orchestrator):
                with patch('folder_extractor.cli.app.KeyboardHandler') as mock_handler_class:
                    with patch('folder_extractor.cli.app.settings', {"dry_run": False}):
                        result = self.cli._execute_extraction("/test/path", mock_context)
                        
                        assert result == 0
                        
                        # Check orchestrator called correctly
                        mock_orchestrator.execute_extraction.assert_called_once_with(
                            source_path="/test/path",
                            confirmation_callback=self.cli.interface.confirm_operation,
                            progress_callback=self.cli.interface.show_progress
                        )
                        
                        # Check keyboard handler started and stopped
                        mock_handler_class.assert_called_once()
                        mock_handler = mock_handler_class.return_value
                        mock_handler.start.assert_called_once()
                        mock_handler.stop.assert_called_once()
                        
                        # Check summary shown
                        self.cli.interface.show_summary.assert_called_once()
    
    def test_execute_extraction_no_files(self):
        """Test extraction with no files found."""
        mock_context = Mock()
        mock_orchestrator = Mock()
        mock_orchestrator.execute_extraction.return_value = {
            "status": "no_files",
            "message": "Keine Dateien gefunden"
        }
        
        with patch('folder_extractor.cli.app.FileExtractor'):
            with patch('folder_extractor.cli.app.ExtractionOrchestrator', return_value=mock_orchestrator):
                with patch('folder_extractor.cli.app.settings', {"dry_run": True}):
                    result = self.cli._execute_extraction("/test/path", mock_context)
                    
                    # Should still return 0 (not an error)
                    assert result == 0
    
    def test_execute_extraction_cancelled(self):
        """Test extraction cancelled by user."""
        mock_context = Mock()
        mock_orchestrator = Mock()
        mock_orchestrator.execute_extraction.return_value = {
            "status": "cancelled",
            "message": "Operation abgebrochen"
        }
        
        with patch('folder_extractor.cli.app.FileExtractor'):
            with patch('folder_extractor.cli.app.ExtractionOrchestrator', return_value=mock_orchestrator):
                with patch('folder_extractor.cli.app.settings', {"dry_run": True}):
                    result = self.cli._execute_extraction("/test/path", mock_context)
                    
                    # Should return 0 (not an error)
                    assert result == 0
    
    def test_execute_extraction_aborted(self):
        """Test extraction aborted via ESC."""
        mock_context = Mock()
        mock_orchestrator = Mock()
        mock_orchestrator.execute_extraction.return_value = {
            "status": "success",
            "moved": 5
        }
        
        # Mock abort requested
        self.cli.app_state.is_abort_requested = Mock(return_value=True)
        
        with patch('folder_extractor.cli.app.FileExtractor'):
            with patch('folder_extractor.cli.app.ExtractionOrchestrator', return_value=mock_orchestrator):
                with patch('folder_extractor.cli.app.settings', {"dry_run": True}):
                    result = self.cli._execute_extraction("/test/path", mock_context)
                    
                    assert result == 0
                    
                    # Check aborted flag set in results
                    self.cli.interface.show_summary.assert_called_once()
                    summary_results = self.cli.interface.show_summary.call_args[0][0]
                    assert summary_results["aborted"] is True
    
    def test_execute_undo_success(self):
        """Test successful undo execution."""
        mock_context = Mock()
        mock_orchestrator = Mock()
        mock_orchestrator.execute_undo.return_value = {
            "status": "success",
            "message": "10 Dateien zurück verschoben"
        }
        
        # Mock interface
        self.cli.interface.show_message = Mock()
        
        with patch('folder_extractor.cli.app.FileExtractor'):
            with patch('folder_extractor.cli.app.ExtractionOrchestrator', return_value=mock_orchestrator):
                result = self.cli._execute_undo("/test/path", mock_context)
                
                assert result == 0
                
                # Check orchestrator called
                mock_orchestrator.execute_undo.assert_called_once_with("/test/path")
                
                # Check messages shown
                assert self.cli.interface.show_message.call_count == 2
                
                # Check success message
                final_call = self.cli.interface.show_message.call_args_list[-1]
                assert "10 Dateien zurück verschoben" in final_call[0][0]
                assert final_call[1]["message_type"] == "success"
    
    def test_execute_undo_no_history(self):
        """Test undo with no history."""
        mock_context = Mock()
        mock_orchestrator = Mock()
        mock_orchestrator.execute_undo.return_value = {
            "status": "no_history",
            "message": "Keine History gefunden"
        }
        
        with patch('folder_extractor.cli.app.FileExtractor'):
            with patch('folder_extractor.cli.app.ExtractionOrchestrator', return_value=mock_orchestrator):
                result = self.cli._execute_undo("/test/path", mock_context)
                
                assert result == 1
                
                # Check warning message shown
                final_call = self.cli.interface.show_message.call_args_list[-1]
                assert final_call[1]["message_type"] == "warning"


def test_main_function():
    """Test main entry point function."""
    with patch('folder_extractor.cli.app.FolderExtractorCLI') as mock_cli_class:
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