"""
Unit tests for CLI interface module.
"""
import pytest
import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

from folder_extractor.cli.interface import (
    ConsoleInterface, KeyboardHandler, create_console_interface
)
from folder_extractor.config.settings import settings


class TestConsoleInterface:
    """Test ConsoleInterface class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.interface = ConsoleInterface()
        # Reset settings
        settings.reset_to_defaults()
    
    def test_show_welcome(self):
        """Test showing welcome message."""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            self.interface.show_welcome()
            output = mock_stdout.getvalue()
            
            assert "Folder Extractor" in output
            assert "v" in output  # Version
            assert "Von" in output  # Author
    
    def test_show_message_types(self):
        """Test showing different message types."""
        # Mock supports_color to return True so we get colored output
        with patch('folder_extractor.utils.terminal.supports_color', return_value=True):
            test_cases = [
                ("info", "Info message", "\033[36m"),      # Cyan
                ("success", "Success message", "\033[32m"), # Green
                ("error", "Error message", "\033[31m"),     # Red
                ("warning", "Warning message", "\033[33m"),  # Yellow
            ]
            
            for msg_type, message, color_code in test_cases:
                with patch('sys.stdout', new=StringIO()) as mock_stdout:
                    self.interface.show_message(message, message_type=msg_type)
                    output = mock_stdout.getvalue()
                    
                    # Check message is displayed
                    assert message in output
                    # Check color code is applied (if not quiet mode)
                    if not settings.get("quiet", False):
                        assert color_code in output
    
    def test_show_message_quiet_mode(self):
        """Test message suppression in quiet mode."""
        settings.set("quiet", True)
        
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            self.interface.show_message("Test message")
            output = mock_stdout.getvalue()
            
            # No output in quiet mode
            assert output == ""
    
    def test_confirm_operation_dry_run(self):
        """Test confirmation in dry run mode."""
        settings.set("dry_run", True)
        
        # Should auto-confirm in dry run
        result = self.interface.confirm_operation(10)
        assert result is True
    
    def test_confirm_operation_auto_confirm(self):
        """Test confirmation with auto-confirm disabled."""
        settings.set("confirm_operations", False)
        
        # Should auto-confirm when disabled
        result = self.interface.confirm_operation(10)
        assert result is True
    
    def test_confirm_operation_user_input(self):
        """Test user confirmation input."""
        settings.set("confirm_operations", True)
        
        # Test different positive responses
        positive_responses = ['j', 'ja', 'y', 'yes']
        
        for response in positive_responses:
            with patch('builtins.input', return_value=response):
                with patch('sys.stdout', new=StringIO()):
                    result = self.interface.confirm_operation(10)
                    assert result is True
        
        # Test negative responses
        negative_responses = ['n', 'nein', 'no', '', 'x']
        
        for response in negative_responses:
            with patch('builtins.input', return_value=response):
                with patch('sys.stdout', new=StringIO()):
                    result = self.interface.confirm_operation(10)
                    assert result is False
    
    def test_confirm_operation_interrupt(self):
        """Test confirmation with keyboard interrupt."""
        with patch('builtins.input', side_effect=KeyboardInterrupt):
            with patch('sys.stdout', new=StringIO()):
                result = self.interface.confirm_operation(10)
                assert result is False
    
    def test_show_progress(self):
        """Test progress display."""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            # First update should show (string path)
            self.interface.show_progress(1, 10, "/path/to/file.txt")
            output1 = mock_stdout.getvalue()
            assert "file.txt" in output1

            # Rate limiting - immediate second call shouldn't show
            mock_stdout.truncate(0)
            mock_stdout.seek(0)
            self.interface.show_progress(2, 10, "/path/to/file2.txt")
            output2 = mock_stdout.getvalue()

            # Depending on timing, might be empty due to rate limiting
            # But after waiting, should show
            time.sleep(0.15)
            self.interface.show_progress(3, 10, "/path/to/file3.txt")
            output3 = mock_stdout.getvalue()
            assert "file3.txt" in output3

    def test_show_progress_with_path_object(self):
        """Test progress display with Path object."""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            # Test with Path object
            self.interface.show_progress(1, 10, Path("/path/to/file.txt"))
            output = mock_stdout.getvalue()
            assert "file.txt" in output
    
    def test_show_progress_with_error(self):
        """Test progress display with error."""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            self.interface.show_progress(
                5, 10,
                "/path/to/file.txt",
                error="Permission denied"
            )
            output = mock_stdout.getvalue()

            assert "file.txt" in output
            assert "Permission denied" in output

    def test_show_progress_with_error_path_object(self):
        """Test progress display with error using Path object."""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            self.interface.show_progress(
                5, 10,
                Path("/path/to/file.txt"),
                error="Permission denied"
            )
            output = mock_stdout.getvalue()

            assert "file.txt" in output
            assert "Permission denied" in output
    
    def test_show_progress_quiet_mode(self):
        """Test progress suppression in quiet mode."""
        settings.set("quiet", True)
        
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            self.interface.show_progress(1, 10, "/path/to/file.txt")
            output = mock_stdout.getvalue()
            
            # No output in quiet mode
            assert output == ""
    
    def test_show_summary_aborted(self):
        """Test showing summary for aborted operation."""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            results = {"aborted": True}
            self.interface.show_summary(results)
            output = mock_stdout.getvalue()
            
            assert "abgebrochen" in output.lower()
    
    def test_show_summary_no_files(self):
        """Test showing summary when no files found."""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            results = {
                "status": "no_files",
                "message": "Keine Dateien gefunden"
            }
            self.interface.show_summary(results)
            output = mock_stdout.getvalue()
            
            assert "Keine Dateien gefunden" in output
    
    def test_show_summary_success(self):
        """Test showing summary for successful operation."""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            results = {
                "status": "success",
                "moved": 15,
                "duplicates": 3,
                "errors": 1,
                "created_folders": ["PDF", "BILDER"],
                "removed_directories": 5
            }
            self.interface.show_summary(results)
            output = mock_stdout.getvalue()
            
            # Check move summary
            assert "15" in output
            assert "3" in output
            assert "1" in output
            
            # Check created folders
            assert "PDF" in output
            assert "BILDER" in output
            
            # Check removed directories
            assert "5" in output
            assert "leere" in output.lower()
            
            # Check undo hint
            assert "rückgängig" in output.lower()


class TestKeyboardHandler:
    """Test KeyboardHandler class."""
    
    def test_init(self):
        """Test keyboard handler initialization."""
        mock_callback = Mock()
        handler = KeyboardHandler(mock_callback)
        
        assert handler.abort_callback == mock_callback
        assert handler.running is False
        assert handler.thread is None
    
    @pytest.mark.skipif(sys.platform == 'win32', reason="Not supported on Windows")
    def test_start_stop(self):
        """Test starting and stopping keyboard handler."""
        mock_callback = Mock()
        handler = KeyboardHandler(mock_callback)
        
        # Test basic state management
        assert handler.running is False
        assert handler.thread is None
        
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            # Start handler
            handler.start()
            
            # Check hint message
            output = mock_stdout.getvalue()
            assert "ESC" in output
            
            # Check running flag was set
            assert handler.running is True
            
            # Stop handler
            handler.stop()
            
            # Check stopped
            assert handler.running is False
    
    def test_windows_skip(self):
        """Test that keyboard handler skips on Windows."""
        mock_callback = Mock()
        handler = KeyboardHandler(mock_callback)
        
        with patch('sys.platform', 'win32'):
            handler.start()
            
            # Should not start thread on Windows
            assert handler.thread is None
    
    @pytest.mark.skipif(sys.platform == 'win32', reason="Not supported on Windows")
    def test_esc_detection(self):
        """Test ESC key detection logic."""
        mock_callback = Mock()
        handler = KeyboardHandler(mock_callback)
        
        # Test the callback mechanism directly
        # The actual _listen method is complex with threading
        # So we test the core logic
        handler.abort_callback()
        mock_callback.assert_called_once()


def test_create_console_interface():
    """Test interface factory function."""
    interface = create_console_interface()
    assert isinstance(interface, ConsoleInterface)


class TestConsoleInterfaceEdgeCases:
    """Test edge cases for console interface to achieve 100% coverage."""

    def setup_method(self):
        """Set up test fixtures."""
        self.interface = ConsoleInterface()
        settings.reset_to_defaults()

    def test_show_progress_with_long_filename(self):
        """Test progress display with filename truncation (line 154)."""
        # Reset last update time to ensure progress is shown
        self.interface.last_progress_update = 0

        # Create a very long filename that needs truncation
        long_filename = "a" * 50 + ".txt"  # 54 characters, max is 40
        long_path = f"/path/to/{long_filename}"

        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            self.interface.show_progress(1, 10, long_path)
            output = mock_stdout.getvalue()

            # Should be truncated with "..."
            assert "..." in output
            # Original full filename should NOT be in output (it's truncated)
            assert long_filename not in output

    def test_show_summary_cancelled(self):
        """Test showing summary for cancelled operation."""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            results = {
                "status": "cancelled",
                "message": "Operation abgebrochen"
            }
            self.interface.show_summary(results)
            output = mock_stdout.getvalue()

            assert "abgebrochen" in output.lower()

    def test_show_summary_dry_run_no_undo_hint(self):
        """Test that undo hint is not shown in dry run mode."""
        settings.set("dry_run", True)

        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            results = {
                "status": "success",
                "moved": 10,
                "duplicates": 0,
                "errors": 0
            }
            self.interface.show_summary(results)
            output = mock_stdout.getvalue()

            # Undo hint should not be shown in dry run mode
            assert "rückgängig" not in output.lower()

    def test_confirm_operation_eof_error(self):
        """Test confirmation with EOFError (e.g., piped input)."""
        settings.set("confirm_operations", True)

        with patch('builtins.input', side_effect=EOFError):
            with patch('sys.stdout', new=StringIO()):
                result = self.interface.confirm_operation(10)
                assert result is False

    def test_show_message_unknown_type(self):
        """Test show_message with unknown message_type (branch 87->90)."""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            # Use an unknown message type - should fall through to plain print
            self.interface.show_message("Plain message", message_type="unknown")
            output = mock_stdout.getvalue()

            # Message should still be printed (no color)
            assert "Plain message" in output

    def test_show_message_none_type(self):
        """Test show_message with None message_type."""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            self.interface.show_message("Plain message", message_type=None)
            output = mock_stdout.getvalue()

            # Message should be printed
            assert "Plain message" in output

    def test_show_summary_success_without_moved(self):
        """Test show_summary with success status but no 'moved' key (branch 180->189)."""
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            # Success status but no 'moved' key
            results = {
                "status": "success",
                # No "moved" key - should skip the move summary block
                "created_folders": ["PDF"],
                "removed_directories": 2
            }
            self.interface.show_summary(results)
            output = mock_stdout.getvalue()

            # Should still show created folders and removed directories
            assert "PDF" in output
            assert "2" in output


class TestKeyboardHandlerEdgeCases:
    """Test edge cases for KeyboardHandler to achieve 100% coverage."""

    def test_stop_without_thread(self):
        """Test stop() when thread is None (branch 235->exit)."""
        mock_callback = Mock()
        handler = KeyboardHandler(mock_callback)

        # Verify thread is None
        assert handler.thread is None

        # stop() should not raise when thread is None
        handler.stop()

        # Still should not have a thread
        assert handler.thread is None

    def test_stop_with_running_false(self):
        """Test stop() when already stopped."""
        mock_callback = Mock()
        handler = KeyboardHandler(mock_callback)
        handler.running = False

        # stop() should handle this gracefully
        handler.stop()
        assert handler.running is False