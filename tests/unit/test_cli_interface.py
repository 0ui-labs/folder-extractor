"""
Unit tests for CLI interface module.
"""
import pytest
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from folder_extractor.cli.interface import (
    ConsoleInterface, create_console_interface
)
from folder_extractor.config.settings import settings
from folder_extractor.config.constants import VERSION, AUTHOR

# Try to import rich for rich-specific tests
try:
    from rich.console import Console
    from rich.style import Style
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class TestConsoleInterface:
    """Test ConsoleInterface class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.interface = ConsoleInterface()
        # Reset settings
        settings.reset_to_defaults()
    
    def test_show_welcome(self):
        """Test showing welcome message using rich Panel."""
        with patch.object(self.interface.console, 'print') as mock_print:
            self.interface.show_welcome()

            # Verify console.print was called once
            mock_print.assert_called_once()

            # Verify a Panel was passed
            call_args = mock_print.call_args
            from rich.panel import Panel
            assert isinstance(call_args[0][0], Panel)

            # Verify the Panel contains version and author
            panel = call_args[0][0]
            panel_text = panel.renderable
            assert "v" in panel_text or VERSION in panel_text
            assert "Von" in panel_text or AUTHOR in panel_text

    def test_show_welcome_panel_has_title(self):
        """Test that welcome Panel has 'Folder Extractor' title."""
        with patch.object(self.interface.console, 'print') as mock_print:
            self.interface.show_welcome()

            # Get the Panel from the call
            panel = mock_print.call_args[0][0]

            # Verify title
            assert panel.title == "Folder Extractor"

    def test_show_welcome_panel_has_correct_style(self):
        """Test that welcome Panel has cyan border style."""
        with patch.object(self.interface.console, 'print') as mock_print:
            self.interface.show_welcome()

            # Get the Panel from the call
            panel = mock_print.call_args[0][0]

            # Verify border style
            assert panel.border_style == "cyan"
    
    def test_show_message_types(self):
        """Test showing different message types using rich styles."""
        test_cases = [
            ("info", "Info message", "info_style"),
            ("success", "Success message", "success_style"),
            ("error", "Error message", "error_style"),
            ("warning", "Warning message", "warning_style"),
        ]

        for msg_type, message, style_attr in test_cases:
            with patch.object(self.interface.console, 'print') as mock_print:
                self.interface.show_message(message, message_type=msg_type)

                # Verify console.print was called with correct message and style
                expected_style = getattr(self.interface, style_attr)
                mock_print.assert_called_once_with(message, style=expected_style)
    
    def test_show_message_quiet_mode(self):
        """Test message suppression in quiet mode."""
        settings.set("quiet", True)

        with patch.object(self.interface.console, 'print') as mock_print:
            self.interface.show_message("Test message")

            # console.print should NOT be called in quiet mode
            mock_print.assert_not_called()
    
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
    
    def test_confirm_operation_accepts_german_ja(self):
        """Test that German 'ja' is accepted as confirmation."""
        settings.set("confirm_operations", True)

        with patch.object(self.interface.console, 'input', return_value='ja'):
            with patch.object(self.interface.console, 'print'):
                result = self.interface.confirm_operation(10)
                assert result is True

    def test_confirm_operation_accepts_german_j(self):
        """Test that German 'j' is accepted as confirmation."""
        settings.set("confirm_operations", True)

        with patch.object(self.interface.console, 'input', return_value='j'):
            with patch.object(self.interface.console, 'print'):
                result = self.interface.confirm_operation(10)
                assert result is True

    def test_confirm_operation_accepts_english_yes(self):
        """Test that English 'yes' is accepted as confirmation."""
        settings.set("confirm_operations", True)

        with patch.object(self.interface.console, 'input', return_value='yes'):
            with patch.object(self.interface.console, 'print'):
                result = self.interface.confirm_operation(10)
                assert result is True

    def test_confirm_operation_accepts_english_y(self):
        """Test that English 'y' is accepted as confirmation."""
        settings.set("confirm_operations", True)

        with patch.object(self.interface.console, 'input', return_value='y'):
            with patch.object(self.interface.console, 'print'):
                result = self.interface.confirm_operation(10)
                assert result is True

    def test_confirm_operation_user_declines(self):
        """Test user confirmation returns False when declined."""
        settings.set("confirm_operations", True)

        with patch.object(self.interface.console, 'input', return_value='n'):
            with patch.object(self.interface.console, 'print') as mock_print:
                result = self.interface.confirm_operation(10)

                # Should return False
                assert result is False

                # Should still show file count message
                mock_print.assert_called()

    def test_confirm_operation_interrupt(self):
        """Test confirmation with keyboard interrupt."""
        settings.set("confirm_operations", True)

        with patch.object(self.interface.console, 'input', side_effect=KeyboardInterrupt):
            with patch.object(self.interface.console, 'print'):
                result = self.interface.confirm_operation(10)
                assert result is False
    
    def test_show_progress(self):
        """Test progress display using rich.Progress."""

        with patch('folder_extractor.cli.interface.Progress') as MockProgress:
            mock_progress = MagicMock()
            MockProgress.return_value = mock_progress

            # First call should initialize and start Progress
            self.interface.show_progress(1, 10, "/path/to/file.txt")

            # Verify Progress was created with correct columns
            MockProgress.assert_called_once()
            call_kwargs = MockProgress.call_args.kwargs
            assert call_kwargs['console'] == self.interface.console
            assert call_kwargs['transient'] is True

            # Verify start was called
            mock_progress.start.assert_called_once()

            # Verify task was added
            mock_progress.add_task.assert_called_once()
            task_call = mock_progress.add_task.call_args
            assert "Verschiebe Dateien" in task_call[0][0]
            assert task_call.kwargs['total'] == 10

            # Verify update was called with truncated filename
            mock_progress.update.assert_called()
            update_call = mock_progress.update.call_args
            assert update_call.kwargs['completed'] == 1
            assert "file.txt" in update_call.kwargs['description']

    def test_show_progress_with_path_object(self):
        """Test progress display with Path object."""

        with patch('folder_extractor.cli.interface.Progress') as MockProgress:
            mock_progress = MagicMock()
            MockProgress.return_value = mock_progress

            # Test with Path object
            self.interface.show_progress(1, 10, Path("/path/to/file.txt"))

            # Verify update was called
            mock_progress.update.assert_called()
            update_call = mock_progress.update.call_args
            assert "file.txt" in update_call.kwargs['description']

    def test_show_progress_with_error(self):
        """Test progress display with error."""

        with patch('folder_extractor.cli.interface.Progress') as MockProgress:
            mock_progress = MagicMock()
            MockProgress.return_value = mock_progress

            with patch.object(self.interface.console, 'print') as mock_print:
                self.interface.show_progress(
                    5, 10,
                    "/path/to/file.txt",
                    error="Permission denied"
                )

                # Verify error was printed with error_style
                mock_print.assert_called()
                call_args = mock_print.call_args
                error_message = call_args[0][0]
                assert "file.txt" in error_message
                assert "Permission denied" in error_message
                assert call_args.kwargs['style'] == self.interface.error_style

    def test_show_progress_with_error_path_object(self):
        """Test progress display with error using Path object."""

        with patch('folder_extractor.cli.interface.Progress') as MockProgress:
            mock_progress = MagicMock()
            MockProgress.return_value = mock_progress

            with patch.object(self.interface.console, 'print') as mock_print:
                self.interface.show_progress(
                    5, 10,
                    Path("/path/to/file.txt"),
                    error="Permission denied"
                )

                # Verify error was printed
                mock_print.assert_called()
                call_args = mock_print.call_args
                error_message = call_args[0][0]
                assert "file.txt" in error_message
                assert "Permission denied" in error_message

    def test_show_progress_quiet_mode(self):
        """Test progress suppression in quiet mode."""
        settings.set("quiet", True)

        with patch('folder_extractor.cli.interface.Progress') as MockProgress:
            self.interface.show_progress(1, 10, "/path/to/file.txt")

            # Progress should not be initialized in quiet mode
            MockProgress.assert_not_called()

    def test_show_progress_rate_limiting(self):
        """Test rate limiting of progress updates."""

        with patch('folder_extractor.cli.interface.Progress') as MockProgress:
            mock_progress = MagicMock()
            MockProgress.return_value = mock_progress

            # First call
            self.interface.show_progress(1, 10, "/path/to/file1.txt")
            update_count_1 = mock_progress.update.call_count

            # Immediate second call should be rate-limited
            self.interface.show_progress(2, 10, "/path/to/file2.txt")
            update_count_2 = mock_progress.update.call_count

            # Should be the same (rate limited)
            assert update_count_2 == update_count_1

            # Wait and try again
            time.sleep(0.15)
            self.interface.show_progress(3, 10, "/path/to/file3.txt")
            update_count_3 = mock_progress.update.call_count

            # Should have increased
            assert update_count_3 > update_count_2

    def test_show_progress_error_bypasses_rate_limiting(self):
        """Error messages are shown immediately, bypassing rate limiting."""

        with patch('folder_extractor.cli.interface.Progress') as MockProgress:
            mock_progress = MagicMock()
            MockProgress.return_value = mock_progress

            with patch.object(self.interface.console, 'print') as mock_print:
                # First call - normal progress
                self.interface.show_progress(1, 10, "/path/to/file1.txt")

                # Immediate second call with error - should NOT be rate-limited
                self.interface.show_progress(
                    2, 10,
                    "/path/to/file2.txt",
                    error="Permission denied"
                )

                # Error message should have been printed despite rate limiting
                mock_print.assert_called()
                call_args = mock_print.call_args
                error_message = call_args[0][0]
                assert "Permission denied" in error_message

    def test_show_progress_reuses_progress_instance(self):
        """Test that subsequent calls reuse the same Progress instance."""

        with patch('folder_extractor.cli.interface.Progress') as MockProgress:
            mock_progress = MagicMock()
            MockProgress.return_value = mock_progress

            # First call
            self.interface.show_progress(1, 10, "/path/to/file1.txt")

            # Wait to avoid rate limiting
            time.sleep(0.15)

            # Second call
            self.interface.show_progress(2, 10, "/path/to/file2.txt")

            # Progress should only be created once
            MockProgress.assert_called_once()

            # But start should only be called once too
            mock_progress.start.assert_called_once()

    def test_finish_progress(self):
        """Test finish_progress method."""

        with patch('folder_extractor.cli.interface.Progress') as MockProgress:
            mock_progress = MagicMock()
            MockProgress.return_value = mock_progress

            # Initialize progress
            self.interface.show_progress(1, 10, "/path/to/file.txt")

            # Verify progress is set
            assert self.interface.progress is not None
            assert self.interface.task_id is not None

            # Finish progress
            self.interface.finish_progress()

            # Verify stop was called
            mock_progress.stop.assert_called_once()

            # Verify attributes are reset
            assert self.interface.progress is None
            assert self.interface.task_id is None

    def test_finish_progress_when_not_started(self):
        """Test finish_progress when progress was never started."""
        # Should not raise when progress is None
        self.interface.finish_progress()

        # Should remain None
        assert self.interface.progress is None
        assert self.interface.task_id is None
    
    def test_show_summary_aborted(self):
        """Test showing summary for aborted operation uses console.print."""
        results = {"aborted": True}

        with patch.object(self.interface.console, 'print') as mock_print:
            self.interface.show_summary(results)

            # Find calls with abort message
            abort_calls = [call for call in mock_print.call_args_list
                          if len(call[0]) > 0 and isinstance(call[0][0], str) and "abgebrochen" in call[0][0].lower()]
            assert len(abort_calls) >= 1, "Expected abort message to be printed"
    
    def test_show_summary_no_files(self):
        """Test showing summary when no files found uses console.print."""
        results = {
            "status": "no_files",
            "message": "Keine Dateien gefunden"
        }

        with patch.object(self.interface.console, 'print') as mock_print:
            self.interface.show_summary(results)

            # Find calls with no files message
            no_files_calls = [call for call in mock_print.call_args_list
                             if len(call[0]) > 0 and isinstance(call[0][0], str) and "Keine Dateien gefunden" in call[0][0]]
            assert len(no_files_calls) >= 1, "Expected no files message to be printed"
    
    def test_show_summary_success(self):
        """Test showing summary for successful operation uses rich Table."""
        from rich.table import Table

        results = {
            "status": "success",
            "moved": 15,
            "duplicates": 3,
            "errors": 1,
            "created_folders": ["PDF", "BILDER"],
            "removed_directories": 5
        }

        with patch.object(self.interface.console, 'print') as mock_print:
            self.interface.show_summary(results)

            # Find the Table call
            table_calls = [call for call in mock_print.call_args_list
                          if len(call[0]) > 0 and isinstance(call[0][0], Table)]
            assert len(table_calls) >= 1, "Expected at least one Table to be printed"

            # Get the table
            table = table_calls[0][0][0]

            # Verify table has correct title
            assert table.title == "Zusammenfassung"

            # Verify table has correct border style
            assert table.border_style == "cyan"

            # Verify table structure by checking columns
            assert len(table.columns) == 2
            assert table.columns[0].header == "Kategorie"
            assert table.columns[1].header == "Anzahl"

            # Verify table rows contain the expected data
            # We need to check the row data
            assert len(table.rows) == 3

            # Check that created folders are printed
            folder_calls = [call for call in mock_print.call_args_list
                           if len(call[0]) > 0 and isinstance(call[0][0], str) and "PDF" in call[0][0]]
            assert len(folder_calls) >= 1, "Expected created folders to be printed"

            # Check that removed directories message is printed
            removed_calls = [call for call in mock_print.call_args_list
                            if len(call[0]) > 0 and isinstance(call[0][0], str) and "5" in str(call[0][0]) and "leere" in str(call[0][0]).lower()]
            assert len(removed_calls) >= 1, "Expected removed directories message"

            # Check that undo hint is printed
            undo_calls = [call for call in mock_print.call_args_list
                         if len(call[0]) > 0 and isinstance(call[0][0], str) and "rückgängig" in str(call[0][0]).lower()]
            assert len(undo_calls) >= 1, "Expected undo hint to be printed"


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
        """Test progress display with filename truncation."""

        # Reset last update time to ensure progress is shown
        self.interface.last_progress_update = 0

        # Create a very long filename that needs truncation
        long_filename = "a" * 50 + ".txt"  # 54 characters, max is 40
        long_path = f"/path/to/{long_filename}"

        with patch('folder_extractor.cli.interface.Progress') as MockProgress:
            mock_progress = MagicMock()
            MockProgress.return_value = mock_progress

            self.interface.show_progress(1, 10, long_path)

            # Verify update was called
            mock_progress.update.assert_called()
            update_call = mock_progress.update.call_args
            description = update_call.kwargs['description']

            # Should be truncated with "..."
            assert "..." in description
            # Original full filename should NOT be in description (it's truncated)
            assert long_filename not in description
            # Length should not exceed 40 + prefix
            filename_part = description.split(": ")[-1] if ": " in description else description
            assert len(filename_part) <= 40

    def test_show_summary_cancelled(self):
        """Test showing summary for cancelled operation uses console.print."""
        results = {
            "status": "cancelled",
            "message": "Operation abgebrochen"
        }

        with patch.object(self.interface.console, 'print') as mock_print:
            self.interface.show_summary(results)

            # Find calls with cancelled message
            cancelled_calls = [call for call in mock_print.call_args_list
                              if len(call[0]) > 0 and isinstance(call[0][0], str) and "abgebrochen" in call[0][0].lower()]
            assert len(cancelled_calls) >= 1, "Expected cancelled message to be printed"

    def test_show_summary_dry_run_no_undo_hint(self):
        """Test that undo hint is not shown in dry run mode."""
        settings.set("dry_run", True)

        with patch.object(self.interface.console, 'print') as mock_print:
            results = {
                "status": "success",
                "moved": 10,
                "duplicates": 0,
                "errors": 0
            }
            self.interface.show_summary(results)

            # Undo hint should not be shown in dry run mode
            undo_calls = [call for call in mock_print.call_args_list
                         if len(call[0]) > 0 and isinstance(call[0][0], str) and "rückgängig" in str(call[0][0]).lower()]
            assert len(undo_calls) == 0, "Undo hint should not be shown in dry run mode"

    def test_confirm_operation_eof_error(self):
        """Test confirmation with EOFError (e.g., piped input)."""
        settings.set("confirm_operations", True)

        with patch.object(self.interface.console, 'input', side_effect=EOFError):
            with patch.object(self.interface.console, 'print'):
                result = self.interface.confirm_operation(10)
                assert result is False

    def test_show_message_unknown_type(self):
        """Test show_message with unknown message_type falls through to plain console.print."""
        with patch.object(self.interface.console, 'print') as mock_print:
            # Use an unknown message type - should fall through to plain console.print
            self.interface.show_message("Plain message", message_type="unknown")

            # Should be called without style parameter
            mock_print.assert_called_once_with("Plain message")

    def test_show_message_none_type(self):
        """Test show_message with None message_type."""
        with patch.object(self.interface.console, 'print') as mock_print:
            self.interface.show_message("Plain message", message_type=None)

            # Should be called without style parameter
            mock_print.assert_called_once_with("Plain message")

    def test_show_summary_success_without_moved(self):
        """Test show_summary with success status but no 'moved' key uses console.print."""
        from rich.table import Table

        # Success status but no 'moved' key
        results = {
            "status": "success",
            # No "moved" key - should skip the move summary block
            "created_folders": ["PDF"],
            "removed_directories": 2
        }

        with patch.object(self.interface.console, 'print') as mock_print:
            self.interface.show_summary(results)

            # Should NOT print a Table (no moved key)
            table_calls = [call for call in mock_print.call_args_list
                          if len(call[0]) > 0 and isinstance(call[0][0], Table)]
            assert len(table_calls) == 0, "Should not print a Table without 'moved' key"

            # Should still show created folders
            folder_calls = [call for call in mock_print.call_args_list
                           if len(call[0]) > 0 and isinstance(call[0][0], str) and "PDF" in call[0][0]]
            assert len(folder_calls) >= 1, "Expected created folders to be printed"

            # Should still show removed directories
            removed_calls = [call for call in mock_print.call_args_list
                            if len(call[0]) > 0 and isinstance(call[0][0], str) and "2" in str(call[0][0])]
            assert len(removed_calls) >= 1, "Expected removed directories message"


@pytest.mark.skipif(not RICH_AVAILABLE, reason="Rich not installed")
class TestConsoleInterfaceRichIntegration:
    """Test rich library integration in ConsoleInterface."""

    def setup_method(self):
        """Set up test fixtures."""
        self.interface = ConsoleInterface()
        settings.reset_to_defaults()

    def test_has_console_attribute(self):
        """Test that ConsoleInterface has a console attribute."""
        assert hasattr(self.interface, 'console')

    def test_console_is_rich_console(self):
        """Test that console attribute is an instance of rich.console.Console."""
        assert isinstance(self.interface.console, Console)

    def test_has_progress_attribute(self):
        """Test that ConsoleInterface has a progress attribute initialized to None."""
        assert hasattr(self.interface, 'progress')
        assert self.interface.progress is None

    def test_has_task_id_attribute(self):
        """Test that ConsoleInterface has a task_id attribute initialized to None."""
        assert hasattr(self.interface, 'task_id')
        assert self.interface.task_id is None

    def test_has_style_attributes(self):
        """Test that ConsoleInterface has theme style attributes."""
        assert hasattr(self.interface, 'success_style')
        assert hasattr(self.interface, 'error_style')
        assert hasattr(self.interface, 'warning_style')
        assert hasattr(self.interface, 'info_style')

    def test_styles_are_rich_styles(self):
        """Test that style attributes are instances of rich.style.Style."""
        assert isinstance(self.interface.success_style, Style)
        assert isinstance(self.interface.error_style, Style)
        assert isinstance(self.interface.warning_style, Style)
        assert isinstance(self.interface.info_style, Style)

    def test_success_style_is_green_bold(self):
        """Test that success style is green and bold."""
        style = self.interface.success_style
        assert style.color.name == "green"
        assert style.bold is True

    def test_error_style_is_red_bold(self):
        """Test that error style is red and bold."""
        style = self.interface.error_style
        assert style.color.name == "red"
        assert style.bold is True

    def test_warning_style_is_yellow(self):
        """Test that warning style is yellow."""
        style = self.interface.warning_style
        assert style.color.name == "yellow"

    def test_info_style_is_cyan(self):
        """Test that info style is cyan."""
        style = self.interface.info_style
        assert style.color.name == "cyan"