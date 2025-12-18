"""
Unit tests for CLI interface module with rich integration.

Tests use mocked rich components (Console, Panel, Table, Progress) to isolate
from rich implementation details and verify behavior through call assertions.
"""
import pytest
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, ANY

from folder_extractor.cli.interface import (
    ConsoleInterface, create_console_interface
)
from folder_extractor.config.settings import settings


@patch('folder_extractor.cli.interface.Console')
class TestConsoleInterface:
    """Test ConsoleInterface class with mocked Console."""

    def setup_method(self):
        """Set up test fixtures."""
        settings.reset_to_defaults()

    def test_show_welcome(self, mock_console_class):
        """Test showing welcome message creates Panel and prints it."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        with patch('folder_extractor.cli.interface.Panel') as mock_panel_class:
            mock_panel = MagicMock()
            mock_panel_class.return_value = mock_panel

            interface = ConsoleInterface()
            interface.show_welcome()

            # Verify Panel was created with correct parameters
            mock_panel_class.assert_called_once()
            call_args = mock_panel_class.call_args
            # Check title parameter
            assert call_args.kwargs.get('title') == "Folder Extractor"
            assert call_args.kwargs.get('border_style') == "cyan"

            # Verify console.print was called with the panel
            mock_console.print.assert_called_once_with(mock_panel)

    def test_show_welcome_includes_version_and_author(self, mock_console_class):
        """Test that welcome Panel content includes version and author info."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        with patch('folder_extractor.cli.interface.Panel') as mock_panel_class:
            interface = ConsoleInterface()
            interface.show_welcome()

            # Check that Panel was called with message containing version info
            call_args = mock_panel_class.call_args
            message = call_args[0][0]  # First positional argument
            assert "v" in message  # Version marker
            assert "Von" in message  # Author marker (German)

    def test_show_message_success(self, mock_console_class):
        """Test showing success message with green bold style."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_message("Success!", message_type="success")

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        assert call_args[0][0] == "Success!"
        assert call_args.kwargs.get('style') == interface.success_style

    def test_show_message_error(self, mock_console_class):
        """Test showing error message with red bold style."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_message("Error!", message_type="error")

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        assert call_args[0][0] == "Error!"
        assert call_args.kwargs.get('style') == interface.error_style

    def test_show_message_warning(self, mock_console_class):
        """Test showing warning message with yellow style."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_message("Warning!", message_type="warning")

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        assert call_args[0][0] == "Warning!"
        assert call_args.kwargs.get('style') == interface.warning_style

    def test_show_message_info(self, mock_console_class):
        """Test showing info message with cyan style."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_message("Info!", message_type="info")

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        assert call_args[0][0] == "Info!"
        assert call_args.kwargs.get('style') == interface.info_style

    def test_show_message_quiet_mode(self, mock_console_class):
        """Test message suppression in quiet mode."""
        settings.set("quiet", True)
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_message("Test message")

        # No output in quiet mode
        mock_console.print.assert_not_called()

    def test_show_message_unknown_type(self, mock_console_class):
        """Test show_message with unknown type prints without style."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_message("Plain message", message_type="unknown")

        # Should be called without style parameter
        mock_console.print.assert_called_once_with("Plain message")

    def test_show_message_none_type(self, mock_console_class):
        """Test show_message with None type prints without style."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_message("Plain message", message_type=None)

        mock_console.print.assert_called_once_with("Plain message")

    def test_confirm_operation_dry_run(self, mock_console_class):
        """Test confirmation auto-accepts in dry run mode."""
        settings.set("dry_run", True)
        mock_console_class.return_value = MagicMock()

        interface = ConsoleInterface()
        result = interface.confirm_operation(10)

        assert result is True

    def test_confirm_operation_auto_confirm(self, mock_console_class):
        """Test confirmation auto-accepts when confirm_operations is disabled."""
        settings.set("confirm_operations", False)
        mock_console_class.return_value = MagicMock()

        interface = ConsoleInterface()
        result = interface.confirm_operation(10)

        assert result is True

    def test_confirm_operation_accepts_german_ja(self, mock_console_class):
        """Test German 'ja' is accepted as confirmation."""
        settings.set("confirm_operations", True)
        mock_console = MagicMock()
        mock_console.input.return_value = 'ja'
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        result = interface.confirm_operation(10)

        assert result is True

    def test_confirm_operation_accepts_german_j(self, mock_console_class):
        """Test German 'j' is accepted as confirmation."""
        settings.set("confirm_operations", True)
        mock_console = MagicMock()
        mock_console.input.return_value = 'j'
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        result = interface.confirm_operation(10)

        assert result is True

    def test_confirm_operation_accepts_english_yes(self, mock_console_class):
        """Test English 'yes' is accepted as confirmation."""
        settings.set("confirm_operations", True)
        mock_console = MagicMock()
        mock_console.input.return_value = 'yes'
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        result = interface.confirm_operation(10)

        assert result is True

    def test_confirm_operation_accepts_english_y(self, mock_console_class):
        """Test English 'y' is accepted as confirmation."""
        settings.set("confirm_operations", True)
        mock_console = MagicMock()
        mock_console.input.return_value = 'y'
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        result = interface.confirm_operation(10)

        assert result is True

    def test_confirm_operation_user_declines(self, mock_console_class):
        """Test user declining returns False."""
        settings.set("confirm_operations", True)
        mock_console = MagicMock()
        mock_console.input.return_value = 'n'
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        result = interface.confirm_operation(10)

        assert result is False
        # File count message should still be shown
        mock_console.print.assert_called()

    def test_confirm_operation_keyboard_interrupt(self, mock_console_class):
        """Test KeyboardInterrupt during confirmation returns False."""
        settings.set("confirm_operations", True)
        mock_console = MagicMock()
        mock_console.input.side_effect = KeyboardInterrupt
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        result = interface.confirm_operation(10)

        assert result is False

    def test_confirm_operation_eof_error(self, mock_console_class):
        """Test EOFError during confirmation returns False."""
        settings.set("confirm_operations", True)
        mock_console = MagicMock()
        mock_console.input.side_effect = EOFError
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        result = interface.confirm_operation(10)

        assert result is False

    def test_show_progress_initializes_progress(self, mock_console_class):
        """Test first progress call initializes Progress component."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        with patch('folder_extractor.cli.interface.Progress') as mock_progress_class:
            mock_progress = MagicMock()
            mock_progress.add_task.return_value = "task_id_123"
            mock_progress_class.return_value = mock_progress

            interface = ConsoleInterface()
            interface.show_progress(1, 10, "/path/to/file.txt")

            # Verify Progress was created with console and transient=True
            mock_progress_class.assert_called_once()
            call_kwargs = mock_progress_class.call_args.kwargs
            assert call_kwargs['console'] == mock_console
            assert call_kwargs['transient'] is True

            # Verify progress was started and task added
            mock_progress.start.assert_called_once()
            mock_progress.add_task.assert_called_once()
            assert "Verschiebe Dateien" in mock_progress.add_task.call_args[0][0]

            # Verify update was called
            mock_progress.update.assert_called()

    def test_show_progress_with_path_object(self, mock_console_class):
        """Test progress display handles Path objects."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        with patch('folder_extractor.cli.interface.Progress') as mock_progress_class:
            mock_progress = MagicMock()
            mock_progress.add_task.return_value = "task_id"
            mock_progress_class.return_value = mock_progress

            interface = ConsoleInterface()
            interface.show_progress(1, 10, Path("/path/to/file.txt"))

            mock_progress.update.assert_called()
            update_call = mock_progress.update.call_args
            assert "file.txt" in update_call.kwargs['description']

    def test_show_progress_with_error(self, mock_console_class):
        """Test error messages are printed immediately with error style."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        with patch('folder_extractor.cli.interface.Progress'):
            interface = ConsoleInterface()
            interface.show_progress(
                5, 10, "/path/to/file.txt", error="Permission denied"
            )

            # Error should be printed via console
            mock_console.print.assert_called()
            call_args = mock_console.print.call_args
            error_message = call_args[0][0]
            assert "file.txt" in error_message
            assert "Permission denied" in error_message
            assert call_args.kwargs['style'] == interface.error_style

    def test_show_progress_with_error_path_object(self, mock_console_class):
        """Test error messages work with Path objects."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        with patch('folder_extractor.cli.interface.Progress'):
            interface = ConsoleInterface()
            interface.show_progress(
                5, 10, Path("/path/to/file.txt"), error="Permission denied"
            )

            mock_console.print.assert_called()
            call_args = mock_console.print.call_args
            error_message = call_args[0][0]
            assert "file.txt" in error_message
            assert "Permission denied" in error_message

    def test_show_progress_quiet_mode(self, mock_console_class):
        """Test progress is not shown in quiet mode."""
        settings.set("quiet", True)
        mock_console_class.return_value = MagicMock()

        with patch('folder_extractor.cli.interface.Progress') as mock_progress_class:
            interface = ConsoleInterface()
            interface.show_progress(1, 10, "/path/to/file.txt")

            # Progress should not be initialized in quiet mode
            mock_progress_class.assert_not_called()

    def test_show_progress_rate_limiting(self, mock_console_class):
        """Test rate limiting of progress updates."""
        mock_console_class.return_value = MagicMock()

        with patch('folder_extractor.cli.interface.Progress') as mock_progress_class:
            mock_progress = MagicMock()
            mock_progress.add_task.return_value = "task_id"
            mock_progress_class.return_value = mock_progress

            interface = ConsoleInterface()

            # First call
            interface.show_progress(1, 10, "/path/to/file1.txt")
            update_count_1 = mock_progress.update.call_count

            # Immediate second call should be rate-limited
            interface.show_progress(2, 10, "/path/to/file2.txt")
            update_count_2 = mock_progress.update.call_count

            # Should be the same (rate limited)
            assert update_count_2 == update_count_1

            # Wait and try again
            time.sleep(0.15)
            interface.show_progress(3, 10, "/path/to/file3.txt")
            update_count_3 = mock_progress.update.call_count

            # Should have increased
            assert update_count_3 > update_count_2

    def test_show_progress_error_bypasses_rate_limiting(self, mock_console_class):
        """Test error messages bypass rate limiting."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        with patch('folder_extractor.cli.interface.Progress') as mock_progress_class:
            mock_progress = MagicMock()
            mock_progress.add_task.return_value = "task_id"
            mock_progress_class.return_value = mock_progress

            interface = ConsoleInterface()

            # First call - normal progress
            interface.show_progress(1, 10, "/path/to/file1.txt")

            # Immediate second call with error - should NOT be rate-limited
            interface.show_progress(
                2, 10, "/path/to/file2.txt", error="Permission denied"
            )

            # Error message should have been printed
            mock_console.print.assert_called()
            call_args = mock_console.print.call_args
            assert "Permission denied" in call_args[0][0]

    def test_show_progress_reuses_progress_instance(self, mock_console_class):
        """Test subsequent calls reuse the same Progress instance."""
        mock_console_class.return_value = MagicMock()

        with patch('folder_extractor.cli.interface.Progress') as mock_progress_class:
            mock_progress = MagicMock()
            mock_progress.add_task.return_value = "task_id"
            mock_progress_class.return_value = mock_progress

            interface = ConsoleInterface()

            # First call
            interface.show_progress(1, 10, "/path/to/file1.txt")

            # Wait to avoid rate limiting
            time.sleep(0.15)

            # Second call
            interface.show_progress(2, 10, "/path/to/file2.txt")

            # Progress should only be created once
            mock_progress_class.assert_called_once()
            mock_progress.start.assert_called_once()

    def test_show_progress_long_filename_truncation(self, mock_console_class):
        """Test long filenames are truncated to 40 characters."""
        mock_console_class.return_value = MagicMock()

        with patch('folder_extractor.cli.interface.Progress') as mock_progress_class:
            mock_progress = MagicMock()
            mock_progress.add_task.return_value = "task_id"
            mock_progress_class.return_value = mock_progress

            interface = ConsoleInterface()
            interface.last_progress_update = 0  # Ensure no rate limiting

            long_filename = "a" * 50 + ".txt"
            interface.show_progress(1, 10, f"/path/{long_filename}")

            mock_progress.update.assert_called()
            update_call = mock_progress.update.call_args
            description = update_call.kwargs['description']

            # Should be truncated with "..."
            assert "..." in description
            # Original full filename should NOT be in description
            assert long_filename not in description

    def test_finish_progress(self, mock_console_class):
        """Test finish_progress stops Progress and cleans up."""
        mock_console_class.return_value = MagicMock()

        with patch('folder_extractor.cli.interface.Progress') as mock_progress_class:
            mock_progress = MagicMock()
            mock_progress.add_task.return_value = "task_id"
            mock_progress_class.return_value = mock_progress

            interface = ConsoleInterface()

            # Initialize progress
            interface.show_progress(1, 10, "/path/to/file.txt")
            assert interface.progress is not None
            assert interface.task_id is not None

            # Finish progress
            interface.finish_progress()

            # Verify stop was called
            mock_progress.stop.assert_called_once()

            # Verify attributes are reset
            assert interface.progress is None
            assert interface.task_id is None

    def test_finish_progress_when_not_started(self, mock_console_class):
        """Test finish_progress is safe when progress was never started."""
        mock_console_class.return_value = MagicMock()

        interface = ConsoleInterface()
        # Should not raise when progress is None
        interface.finish_progress()

        assert interface.progress is None
        assert interface.task_id is None

    def test_show_summary_aborted(self, mock_console_class):
        """Test summary shows abort message when operation was aborted."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        results = {"aborted": True}
        interface.show_summary(results)

        # Should print abort message
        mock_console.print.assert_called()
        call_args_str = str(mock_console.print.call_args_list)
        assert "abgebrochen" in call_args_str.lower()

    def test_show_summary_no_files(self, mock_console_class):
        """Test summary shows no files message."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        results = {
            "status": "no_files",
            "message": "Keine Dateien gefunden"
        }
        interface.show_summary(results)

        mock_console.print.assert_called()
        call_args_str = str(mock_console.print.call_args_list)
        assert "Keine Dateien gefunden" in call_args_str

    def test_show_summary_cancelled(self, mock_console_class):
        """Test summary shows cancelled message."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        results = {
            "status": "cancelled",
            "message": "Operation abgebrochen"
        }
        interface.show_summary(results)

        mock_console.print.assert_called()
        call_args_str = str(mock_console.print.call_args_list)
        assert "abgebrochen" in call_args_str.lower()

    def test_show_summary_success_creates_table(self, mock_console_class):
        """Test successful summary creates Table with move statistics."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        with patch('folder_extractor.cli.interface.Table') as mock_table_class:
            mock_table = MagicMock()
            mock_table_class.return_value = mock_table

            interface = ConsoleInterface()
            results = {
                "status": "success",
                "moved": 15,
                "duplicates": 3,
                "errors": 1,
                "created_folders": ["PDF", "BILDER"],
                "removed_directories": 5
            }
            interface.show_summary(results)

            # Verify Table was created with correct parameters
            mock_table_class.assert_called_once()
            call_kwargs = mock_table_class.call_args.kwargs
            assert call_kwargs.get('title') == "Zusammenfassung"
            assert call_kwargs.get('border_style') == "cyan"

            # Verify columns were added
            assert mock_table.add_column.call_count == 2

            # Verify rows were added (moved, duplicates, errors)
            assert mock_table.add_row.call_count == 3

            # Verify table was printed
            table_printed = any(
                call[0][0] == mock_table
                for call in mock_console.print.call_args_list
                if call[0]
            )
            assert table_printed

    def test_show_summary_success_shows_created_folders(self, mock_console_class):
        """Test successful summary shows created folders."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        with patch('folder_extractor.cli.interface.Table'):
            interface = ConsoleInterface()
            results = {
                "status": "success",
                "moved": 10,
                "created_folders": ["PDF", "BILDER"],
            }
            interface.show_summary(results)

            call_args_str = str(mock_console.print.call_args_list)
            assert "PDF" in call_args_str
            assert "BILDER" in call_args_str

    def test_show_summary_success_shows_removed_directories(self, mock_console_class):
        """Test successful summary shows removed directories count."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        with patch('folder_extractor.cli.interface.Table'):
            interface = ConsoleInterface()
            results = {
                "status": "success",
                "moved": 10,
                "removed_directories": 5
            }
            interface.show_summary(results)

            call_args_str = str(mock_console.print.call_args_list)
            assert "5" in call_args_str
            assert "leere" in call_args_str.lower()

    def test_show_summary_success_shows_undo_hint(self, mock_console_class):
        """Test successful summary shows undo hint."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        with patch('folder_extractor.cli.interface.Table'):
            interface = ConsoleInterface()
            results = {
                "status": "success",
                "moved": 10,
            }
            interface.show_summary(results)

            call_args_str = str(mock_console.print.call_args_list)
            assert "rückgängig" in call_args_str.lower()

    def test_show_summary_dry_run_no_undo_hint(self, mock_console_class):
        """Test undo hint is not shown in dry run mode."""
        settings.set("dry_run", True)
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        with patch('folder_extractor.cli.interface.Table'):
            interface = ConsoleInterface()
            results = {
                "status": "success",
                "moved": 10,
            }
            interface.show_summary(results)

            call_args_str = str(mock_console.print.call_args_list)
            assert "rückgängig" not in call_args_str.lower()

    def test_show_summary_success_without_moved(self, mock_console_class):
        """Test summary without 'moved' key skips table but shows other info."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        with patch('folder_extractor.cli.interface.Table') as mock_table_class:
            interface = ConsoleInterface()
            results = {
                "status": "success",
                "created_folders": ["PDF"],
                "removed_directories": 2
            }
            interface.show_summary(results)

            # Table should NOT be created (no moved key)
            mock_table_class.assert_not_called()

            # But folders and directories should still be shown
            call_args_str = str(mock_console.print.call_args_list)
            assert "PDF" in call_args_str
            assert "2" in call_args_str


@patch('folder_extractor.cli.interface.Console')
def test_create_console_interface(mock_console_class):
    """Test interface factory function creates ConsoleInterface."""
    mock_console_class.return_value = MagicMock()

    interface = create_console_interface()

    assert isinstance(interface, ConsoleInterface)


@patch('folder_extractor.cli.interface.Console')
class TestConsoleInterfaceStyles:
    """Test style attributes are correctly initialized."""

    def test_has_style_attributes(self, mock_console_class):
        """Test ConsoleInterface has all style attributes."""
        mock_console_class.return_value = MagicMock()

        interface = ConsoleInterface()

        assert hasattr(interface, 'success_style')
        assert hasattr(interface, 'error_style')
        assert hasattr(interface, 'warning_style')
        assert hasattr(interface, 'info_style')

    def test_styles_are_configured(self, mock_console_class):
        """Test styles are non-None Style objects."""
        mock_console_class.return_value = MagicMock()

        interface = ConsoleInterface()

        # All styles should be defined (not None)
        assert interface.success_style is not None
        assert interface.error_style is not None
        assert interface.warning_style is not None
        assert interface.info_style is not None


@patch('folder_extractor.cli.interface.Console')
class TestConsoleInterfaceAttributes:
    """Test ConsoleInterface initialization and attributes."""

    def test_has_console_attribute(self, mock_console_class):
        """Test ConsoleInterface has a console attribute."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()

        assert hasattr(interface, 'console')
        assert interface.console == mock_console

    def test_progress_initialized_to_none(self, mock_console_class):
        """Test progress attribute is initialized to None."""
        mock_console_class.return_value = MagicMock()

        interface = ConsoleInterface()

        assert hasattr(interface, 'progress')
        assert interface.progress is None

    def test_task_id_initialized_to_none(self, mock_console_class):
        """Test task_id attribute is initialized to None."""
        mock_console_class.return_value = MagicMock()

        interface = ConsoleInterface()

        assert hasattr(interface, 'task_id')
        assert interface.task_id is None

    def test_last_progress_update_initialized(self, mock_console_class):
        """Test last_progress_update is initialized to 0."""
        mock_console_class.return_value = MagicMock()

        interface = ConsoleInterface()

        assert hasattr(interface, 'last_progress_update')
        assert interface.last_progress_update == 0

    def test_progress_update_interval_configured(self, mock_console_class):
        """Test progress_update_interval is configured."""
        mock_console_class.return_value = MagicMock()

        interface = ConsoleInterface()

        assert hasattr(interface, 'progress_update_interval')
        assert interface.progress_update_interval > 0
