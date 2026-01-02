"""
Unit tests for CLI interface module with rich integration.

Tests use mocked rich components (Console, Panel, Table, Progress) to isolate
from rich implementation details and verify behavior through call assertions.
"""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from folder_extractor.cli.interface import ConsoleInterface, create_console_interface
from folder_extractor.config.constants import VERSION
from folder_extractor.config.settings import settings


@patch("folder_extractor.cli.interface.Console")
class TestConsoleInterface:
    """Test ConsoleInterface class with mocked Console."""

    def setup_method(self):
        """Set up test fixtures."""
        settings.reset_to_defaults()

    def test_show_welcome_prints_version_header(self, mock_console_class):
        """Test welcome message prints version header in minimalist Unix style."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_welcome()

        # Should print directly without Panel
        mock_console.print.assert_called_once()

        # Find the version header in print call
        call_args = mock_console.print.call_args
        output = str(call_args[0][0])
        assert "Folder Extractor v" in output, f"Version header not found in: {output}"

    def test_show_welcome_prints_separator_line(self, mock_console_class):
        """Test welcome message prints separator line after header."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_welcome()

        # Should have a separator line with dashes in single print call
        call_args = mock_console.print.call_args
        output = str(call_args[0][0])
        assert "---" in output, f"Separator line not found in: {output}"

    def test_show_welcome_no_panel_used(self, mock_console_class):
        """Test welcome message does not use Panel component (minimalist style)."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        # Panel should not be imported/used anymore
        interface = ConsoleInterface()
        interface.show_welcome()

        # Verify no Panel-like rich components were passed to print
        for call in mock_console.print.call_args_list:
            if call.args:
                arg = call.args[0]
                # Should be string or simple renderable, not Panel
                assert not hasattr(arg, "renderable"), "Panel-like object detected"

    def test_show_welcome_contains_exact_version(self, mock_console_class):
        """Test welcome message contains exact version from constants."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_welcome()

        call_args = mock_console.print.call_args
        output = str(call_args[0][0])
        expected_version = f"v{VERSION}"
        assert expected_version in output, (
            f"Expected version '{expected_version}' not found in: {output}"
        )

    def test_show_welcome_separator_has_minimum_length(self, mock_console_class):
        """Test welcome separator line has at least 20 dashes for visual separation."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_welcome()

        call_args = mock_console.print.call_args
        output = str(call_args[0][0])
        # Count consecutive dashes - should have at least 20
        dash_count = output.count("-")
        assert dash_count >= 20, (
            f"Separator should have at least 20 dashes, found {dash_count}"
        )

    def test_show_welcome_no_padding_wrapper(self, mock_console_class):
        """Test welcome message is printed directly without Padding wrapper."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_welcome()

        # Verify no Padding-like objects were passed to print
        for call in mock_console.print.call_args_list:
            if call.args:
                arg = call.args[0]
                # Should not have padding attribute (Padding objects have this)
                assert not hasattr(arg, "pad"), "Padding object detected"
                # Argument should be a string, not a rich Padding wrapper
                assert isinstance(arg, str), (
                    f"Expected string output, got {type(arg).__name__}"
                )

    def test_show_message_success(self, mock_console_class):
        """Test showing success message with green style directly (no padding)."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_message("Success!", message_type="success")

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        # Should print message directly, not wrapped in Padding
        assert call_args[0][0] == "Success!"
        assert call_args.kwargs.get("style") == interface.success_style

    def test_show_message_success_uses_basic_green_style(self, mock_console_class):
        """Test success style uses only green color without bold or dim modifiers."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        style = interface.success_style

        # Style should have green color
        assert style.color is not None
        assert style.color.name == "green"
        # Style should NOT have bold or dim modifiers (minimalist)
        assert style.bold is not True, "Success style should not be bold"
        assert style.dim is not True, "Success style should not be dim"

    def test_show_message_error(self, mock_console_class):
        """Test showing error message with red style directly (no padding)."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_message("Error!", message_type="error")

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        # Should print message directly, not wrapped in Padding
        assert call_args[0][0] == "Error!"
        assert call_args.kwargs.get("style") == interface.error_style

    def test_show_message_error_uses_basic_red_style(self, mock_console_class):
        """Test error style uses only red color without bold or dim modifiers."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        style = interface.error_style

        # Style should have red color
        assert style.color is not None
        assert style.color.name == "red"
        # Style should NOT have bold or dim modifiers (minimalist)
        assert style.bold is not True, "Error style should not be bold"
        assert style.dim is not True, "Error style should not be dim"

    def test_show_message_warning(self, mock_console_class):
        """Test showing warning message with yellow style directly (no padding)."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_message("Warning!", message_type="warning")

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        # Should print message directly, not wrapped in Padding
        assert call_args[0][0] == "Warning!"
        assert call_args.kwargs.get("style") == interface.warning_style

    def test_show_message_warning_uses_basic_yellow_style(self, mock_console_class):
        """Test warning style uses only yellow color without bold or dim modifiers."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        style = interface.warning_style

        # Style should have yellow color
        assert style.color is not None
        assert style.color.name == "yellow"
        # Style should NOT have bold or dim modifiers (minimalist)
        assert style.bold is not True, "Warning style should not be bold"
        assert style.dim is not True, "Warning style should not be dim"

    def test_show_message_info(self, mock_console_class):
        """Test showing info message with white style directly (no padding)."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_message("Info!", message_type="info")

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        # Should print message directly, not wrapped in Padding
        assert call_args[0][0] == "Info!"
        assert call_args.kwargs.get("style") == interface.info_style

    def test_show_message_info_uses_basic_white_style(self, mock_console_class):
        """Test info style uses only white color without bold or dim modifiers."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        style = interface.info_style

        # Style should have white color
        assert style.color is not None
        assert style.color.name == "white"
        # Style should NOT have bold or dim modifiers (minimalist)
        assert style.bold is not True, "Info style should not be bold"
        assert style.dim is not True, "Info style should not be dim"

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
        mock_console.input.return_value = "ja"
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        result = interface.confirm_operation(10)

        assert result is True

    def test_confirm_operation_accepts_german_j(self, mock_console_class):
        """Test German 'j' is accepted as confirmation."""
        settings.set("confirm_operations", True)
        mock_console = MagicMock()
        mock_console.input.return_value = "j"
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        result = interface.confirm_operation(10)

        assert result is True

    def test_confirm_operation_accepts_english_yes(self, mock_console_class):
        """Test English 'yes' is accepted as confirmation."""
        settings.set("confirm_operations", True)
        mock_console = MagicMock()
        mock_console.input.return_value = "yes"
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        result = interface.confirm_operation(10)

        assert result is True

    def test_confirm_operation_accepts_english_y(self, mock_console_class):
        """Test English 'y' is accepted as confirmation."""
        settings.set("confirm_operations", True)
        mock_console = MagicMock()
        mock_console.input.return_value = "y"
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        result = interface.confirm_operation(10)

        assert result is True

    def test_confirm_operation_user_declines(self, mock_console_class):
        """Test user declining returns False."""
        settings.set("confirm_operations", True)
        mock_console = MagicMock()
        mock_console.input.return_value = "n"
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

        with patch("folder_extractor.cli.interface.Progress") as mock_progress_class:
            mock_progress = MagicMock()
            mock_progress.add_task.return_value = "task_id_123"
            mock_progress_class.return_value = mock_progress

            interface = ConsoleInterface()
            interface.show_progress(1, 10, "/path/to/file.txt")

            # Verify Progress was created with console and transient=True
            mock_progress_class.assert_called_once()
            call_kwargs = mock_progress_class.call_args.kwargs
            assert call_kwargs["console"] == mock_console
            assert call_kwargs["transient"] is True

            # Verify progress was started and task added
            mock_progress.start.assert_called_once()
            mock_progress.add_task.assert_called_once()
            assert "Verschiebe Dateien" in mock_progress.add_task.call_args[0][0]

            # Verify update was called
            mock_progress.update.assert_called()

    def test_show_progress_no_padding_column(self, mock_console_class):
        """Test Progress is created without padding TextColumn (minimalist style)."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        with patch("folder_extractor.cli.interface.Progress") as mock_progress_class:
            with patch("folder_extractor.cli.interface.TextColumn") as mock_text_col:
                mock_progress = MagicMock()
                mock_progress.add_task.return_value = "task_id"
                mock_progress_class.return_value = mock_progress

                interface = ConsoleInterface()
                interface.show_progress(1, 10, "/path/to/file.txt")

                # Check TextColumn calls - should NOT have a " " (space-only) column
                text_col_calls = [str(call) for call in mock_text_col.call_args_list]
                padding_column_used = any(
                    "(' ',)" in call or '(" ",)' in call for call in text_col_calls
                )
                assert not padding_column_used, (
                    f"Padding TextColumn detected in: {text_col_calls}"
                )

    def test_show_progress_has_minimal_columns(self, mock_console_class):
        """Test Progress uses only essential columns: Spinner, Text, and Bar."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        with patch("folder_extractor.cli.interface.Progress") as mock_progress_class:
            with patch("folder_extractor.cli.interface.SpinnerColumn") as mock_spinner:
                with patch("folder_extractor.cli.interface.TextColumn") as mock_text:
                    with patch("folder_extractor.cli.interface.BarColumn") as mock_bar:
                        mock_progress = MagicMock()
                        mock_progress.add_task.return_value = "task_id"
                        mock_progress_class.return_value = mock_progress

                        interface = ConsoleInterface()
                        interface.show_progress(1, 10, "/path/to/file.txt")

                        # All three minimal columns should be used
                        mock_spinner.assert_called_once()
                        mock_text.assert_called_once()
                        mock_bar.assert_called_once()

                        # TextColumn should have meaningful content (task description)
                        text_call = mock_text.call_args
                        text_arg = text_call[0][0] if text_call[0] else ""
                        assert "{task.description}" in text_arg, (
                            f"TextColumn should contain task description, got: {text_arg}"
                        )

    def test_show_progress_with_path_object(self, mock_console_class):
        """Test progress display handles Path objects."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        with patch("folder_extractor.cli.interface.Progress") as mock_progress_class:
            mock_progress = MagicMock()
            mock_progress.add_task.return_value = "task_id"
            mock_progress_class.return_value = mock_progress

            interface = ConsoleInterface()
            interface.show_progress(1, 10, Path("/path/to/file.txt"))

            mock_progress.update.assert_called()
            update_call = mock_progress.update.call_args
            assert "file.txt" in update_call.kwargs["description"]

    def test_show_progress_with_error(self, mock_console_class):
        """Test error messages are printed immediately with error style."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        with patch("folder_extractor.cli.interface.Progress"):
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
            assert call_args.kwargs["style"] == interface.error_style

    def test_show_progress_with_error_path_object(self, mock_console_class):
        """Test error messages work with Path objects."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        with patch("folder_extractor.cli.interface.Progress"):
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

        with patch("folder_extractor.cli.interface.Progress") as mock_progress_class:
            interface = ConsoleInterface()
            interface.show_progress(1, 10, "/path/to/file.txt")

            # Progress should not be initialized in quiet mode
            mock_progress_class.assert_not_called()

    def test_show_progress_rate_limiting(self, mock_console_class):
        """Test rate limiting of progress updates."""
        mock_console_class.return_value = MagicMock()

        with patch("folder_extractor.cli.interface.Progress") as mock_progress_class:
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

        with patch("folder_extractor.cli.interface.Progress") as mock_progress_class:
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

        with patch("folder_extractor.cli.interface.Progress") as mock_progress_class:
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

        with patch("folder_extractor.cli.interface.Progress") as mock_progress_class:
            mock_progress = MagicMock()
            mock_progress.add_task.return_value = "task_id"
            mock_progress_class.return_value = mock_progress

            interface = ConsoleInterface()
            interface.last_progress_update = 0  # Ensure no rate limiting

            long_filename = "a" * 50 + ".txt"
            interface.show_progress(1, 10, f"/path/{long_filename}")

            mock_progress.update.assert_called()
            update_call = mock_progress.update.call_args
            description = update_call.kwargs["description"]

            # Should be truncated with "..."
            assert "..." in description
            # Original full filename should NOT be in description
            assert long_filename not in description

    def test_finish_progress(self, mock_console_class):
        """Test finish_progress stops Progress and cleans up."""
        mock_console_class.return_value = MagicMock()

        with patch("folder_extractor.cli.interface.Progress") as mock_progress_class:
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
        results = {"status": "no_files", "message": "Keine Dateien gefunden"}
        interface.show_summary(results)

        mock_console.print.assert_called()
        call_args_str = str(mock_console.print.call_args_list)
        assert "Keine Dateien gefunden" in call_args_str

    def test_show_summary_cancelled(self, mock_console_class):
        """Test summary shows cancelled message."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        results = {"status": "cancelled", "message": "Operation abgebrochen"}
        interface.show_summary(results)

        mock_console.print.assert_called()
        call_args_str = str(mock_console.print.call_args_list)
        assert "abgebrochen" in call_args_str.lower()

    def test_show_summary_success_prints_statistics_directly(self, mock_console_class):
        """Test successful summary prints statistics in exact format with colors."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        results = {
            "status": "success",
            "moved": 15,
            "duplicates": 3,
            "errors": 1,
            "created_folders": ["PDF", "BILDER"],
            "removed_directories": 5,
        }
        interface.show_summary(results)

        # Get all print calls in order
        print_calls = mock_console.print.call_args_list

        # Extract first argument of each call (the printed string)
        printed_strings = []
        for call in print_calls:
            if call.args:
                printed_strings.append(call.args[0])

        # First 4 calls should be the summary statistics in exact order
        assert len(printed_strings) >= 4, (
            f"Expected at least 4 print calls for summary, got {len(printed_strings)}"
        )

        # Line 1: Header
        assert printed_strings[0] == "Zusammenfassung:", (
            f"Expected 'Zusammenfassung:', got '{printed_strings[0]}'"
        )

        # Line 2: Moved count with exact format including color codes
        moved_line = printed_strings[1]
        assert "[green][+][/green]" in moved_line, (
            f"Missing green color codes for [+] symbol in: {moved_line}"
        )
        assert "Verschoben:" in moved_line, f"Missing 'Verschoben:' in: {moved_line}"
        assert "[green]15[/green]" in moved_line, (
            f"Missing green color codes for count in: {moved_line}"
        )

        # Line 3: Duplicates count with exact format
        dupes_line = printed_strings[2]
        assert "[yellow][!][/yellow]" in dupes_line, (
            f"Missing yellow color codes for [!] symbol in: {dupes_line}"
        )
        assert "Duplikate:" in dupes_line, f"Missing 'Duplikate:' in: {dupes_line}"
        assert "[yellow]3[/yellow]" in dupes_line, (
            f"Missing yellow color codes for count in: {dupes_line}"
        )

        # Line 4: Errors count with exact format and spacing
        errors_line = printed_strings[3]
        assert "[red][x][/red]" in errors_line, (
            f"Missing red color codes for [x] symbol in: {errors_line}"
        )
        assert "Fehler:" in errors_line, f"Missing 'Fehler:' in: {errors_line}"
        assert "[red]1[/red]" in errors_line, (
            f"Missing red color codes for count in: {errors_line}"
        )
        # Check alignment spacing (5 spaces before error count for alignment)
        assert "Fehler:     " in errors_line, (
            f"Missing alignment spacing in errors line: {errors_line}"
        )

    def test_show_summary_success_no_table_used(self, mock_console_class):
        """Test summary does not use Table component (minimalist style)."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        results = {
            "status": "success",
            "moved": 10,
            "duplicates": 0,
            "errors": 0,
        }
        interface.show_summary(results)

        # Verify no Table-like objects were passed to print
        for call in mock_console.print.call_args_list:
            if call.args:
                arg = call.args[0]
                # Should be string, not Table
                assert not hasattr(arg, "add_row"), "Table-like object detected"
                assert not hasattr(arg, "add_column"), "Table-like object detected"

    def test_show_summary_success_shows_created_folders(self, mock_console_class):
        """Test successful summary shows created folders."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

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

        interface = ConsoleInterface()
        results = {"status": "success", "moved": 10, "removed_directories": 5}
        interface.show_summary(results)

        call_args_str = str(mock_console.print.call_args_list)
        assert "5" in call_args_str
        assert "leere" in call_args_str.lower()

    def test_show_summary_success_shows_undo_hint(self, mock_console_class):
        """Test successful summary shows undo hint."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

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

        interface = ConsoleInterface()
        results = {
            "status": "success",
            "moved": 10,
        }
        interface.show_summary(results)

        call_args_str = str(mock_console.print.call_args_list)
        assert "rückgängig" not in call_args_str.lower()

    def test_show_summary_success_without_moved(self, mock_console_class):
        """Test summary without 'moved' key skips statistics but shows other info."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        results = {
            "status": "success",
            "created_folders": ["PDF"],
            "removed_directories": 2,
        }
        interface.show_summary(results)

        # Statistics should NOT be printed (no moved key)
        call_args_str = str(mock_console.print.call_args_list)
        assert "[+]" not in call_args_str  # No moved statistics

        # But folders and directories should still be shown
        assert "PDF" in call_args_str
        assert "2" in call_args_str

    def test_show_summary_success_shows_content_duplicates(self, mock_console_class):
        """Test successful summary shows content duplicates when present."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        results = {
            "status": "success",
            "moved": 10,
            "content_duplicates": 5,
            "errors": 0,
        }
        interface.show_summary(results)

        call_args_str = str(mock_console.print.call_args_list)
        # Should show cyan symbol and label for local content duplicates
        assert "[cyan][~][/cyan]" in call_args_str
        assert "Lokale Inhalts-Duplikate" in call_args_str
        assert "[cyan]5[/cyan]" in call_args_str

    def test_show_summary_success_no_content_duplicates_when_zero(
        self, mock_console_class
    ):
        """Test summary hides content duplicates line when count is zero."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        results = {
            "status": "success",
            "moved": 10,
            "duplicates": 2,
            "content_duplicates": 0,
            "errors": 0,
        }
        interface.show_summary(results)

        call_args_str = str(mock_console.print.call_args_list)
        # Should NOT show content duplicates symbol when count is 0
        assert "[~]" not in call_args_str

    def test_show_summary_success_no_content_duplicates_key_missing(
        self, mock_console_class
    ):
        """Test summary handles missing content_duplicates key gracefully."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        results = {
            "status": "success",
            "moved": 10,
            "duplicates": 2,
            "errors": 0,
            # No content_duplicates key
        }
        interface.show_summary(results)

        call_args_str = str(mock_console.print.call_args_list)
        # Should NOT show content duplicates symbol when key missing
        assert "[~]" not in call_args_str

    def test_show_summary_content_duplicates_appears_between_name_and_errors(
        self, mock_console_class
    ):
        """Test content duplicates line appears in correct position in summary."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        results = {
            "status": "success",
            "moved": 10,
            "name_duplicates": 2,
            "content_duplicates": 5,
            "errors": 1,
        }
        interface.show_summary(results)

        # Get all print calls in order
        print_calls = mock_console.print.call_args_list
        printed_strings = [str(call.args[0]) for call in print_calls if call.args]

        # Find positions of key lines
        name_dupes_idx = None
        content_dupes_idx = None
        fehler_idx = None

        for idx, line in enumerate(printed_strings):
            if "Namens-Duplikate" in line:
                name_dupes_idx = idx
            if "Lokale Inhalts-Duplikate" in line:
                content_dupes_idx = idx
            if "Fehler:" in line:
                fehler_idx = idx

        # Verify order: Namens-Duplikate < Lokale Inhalts < Fehler
        assert name_dupes_idx is not None, "Namens-Duplikate line not found"
        assert content_dupes_idx is not None, "Lokale Inhalts-Duplikate line not found"
        assert fehler_idx is not None, "Fehler line not found"
        assert name_dupes_idx < content_dupes_idx < fehler_idx, (
            f"Wrong order: Namens@{name_dupes_idx}, "
            f"Lokale@{content_dupes_idx}, Fehler@{fehler_idx}"
        )

    def test_show_summary_shows_three_separate_duplicate_categories(
        self, mock_console_class
    ):
        """Test summary displays name, content, and global duplicates separately."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        results = {
            "status": "success",
            "moved": 10,
            "name_duplicates": 3,
            "content_duplicates": 5,
            "global_duplicates": 2,
            "errors": 0,
        }
        interface.show_summary(results)

        call_args_str = str(mock_console.print.call_args_list)
        # Should show all three duplicate types
        assert "Namens-Duplikate" in call_args_str
        assert "3" in call_args_str
        assert "Lokale Inhalts-Duplikate" in call_args_str
        assert "5" in call_args_str
        assert "Globale Inhalts-Duplikate" in call_args_str
        assert "2" in call_args_str

    def test_show_summary_hides_zero_duplicate_categories(self, mock_console_class):
        """Test summary hides duplicate categories when count is zero."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        results = {
            "status": "success",
            "moved": 10,
            "name_duplicates": 0,
            "content_duplicates": 5,
            "global_duplicates": 0,
            "errors": 0,
        }
        interface.show_summary(results)

        call_args_str = str(mock_console.print.call_args_list)
        # Should NOT show zero categories
        assert "Namens-Duplikate" not in call_args_str
        assert "Globale Inhalts-Duplikate" not in call_args_str
        # Should show non-zero category
        assert "Lokale Inhalts-Duplikate" in call_args_str
        assert "5" in call_args_str

    def test_show_summary_backward_compat_with_old_duplicates_key(
        self, mock_console_class
    ):
        """Test summary falls back to 'duplicates' key when new keys are missing."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        results = {
            "status": "success",
            "moved": 10,
            "duplicates": 7,  # Old-style key, no breakdown
            "errors": 0,
        }
        interface.show_summary(results)

        call_args_str = str(mock_console.print.call_args_list)
        # Should show generic duplicates
        assert "Duplikate" in call_args_str
        assert "7" in call_args_str

    def test_show_summary_no_duplicates_when_all_zero(self, mock_console_class):
        """Test summary shows no duplicate lines when all counts are zero."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        results = {
            "status": "success",
            "moved": 10,
            "name_duplicates": 0,
            "content_duplicates": 0,
            "global_duplicates": 0,
            "duplicates": 0,
            "errors": 0,
        }
        interface.show_summary(results)

        call_args_str = str(mock_console.print.call_args_list)
        # Should NOT show any duplicate lines
        assert "Duplikate" not in call_args_str
        assert "Namens-Duplikate" not in call_args_str
        assert "Inhalts-Duplikate" not in call_args_str


@patch("folder_extractor.cli.interface.Console")
class TestIndexingSpinner:
    """Tests for indexing spinner functionality."""

    def test_show_indexing_spinner_displays_message(self, mock_console_class):
        """Test indexing spinner shows the indexing message."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        with patch("folder_extractor.cli.interface.Progress") as mock_progress_class:
            mock_progress = MagicMock()
            mock_progress_class.return_value = mock_progress

            interface = ConsoleInterface()
            interface.show_indexing_spinner()

            # Should create Progress with spinner
            mock_progress_class.assert_called_once()
            mock_progress.start.assert_called_once()
            # Should add task with indexing message
            mock_progress.add_task.assert_called_once()
            call_args = mock_progress.add_task.call_args
            assert (
                "Indiziere" in call_args[0][0] or "indiziere" in str(call_args).lower()
            )

    def test_hide_indexing_spinner_stops_progress(self, mock_console_class):
        """Test hiding indexing spinner stops the progress display."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        with patch("folder_extractor.cli.interface.Progress") as mock_progress_class:
            mock_progress = MagicMock()
            mock_progress_class.return_value = mock_progress

            interface = ConsoleInterface()
            interface.show_indexing_spinner()
            interface.hide_indexing_spinner()

            mock_progress.stop.assert_called_once()

    def test_hide_indexing_spinner_safe_when_not_started(self, mock_console_class):
        """Test hiding indexing spinner is safe when never started."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        # Should not raise when spinner was never started
        interface.hide_indexing_spinner()

    def test_show_indexing_spinner_quiet_mode(self, mock_console_class):
        """Test indexing spinner not shown in quiet mode."""
        settings.set("quiet", True)
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        with patch("folder_extractor.cli.interface.Progress") as mock_progress_class:
            interface = ConsoleInterface()
            interface.show_indexing_spinner()

            # Progress should not be initialized in quiet mode
            mock_progress_class.assert_not_called()


@patch("folder_extractor.cli.interface.Console")
def test_create_console_interface(mock_console_class):
    """Test interface factory function creates ConsoleInterface."""
    mock_console_class.return_value = MagicMock()

    interface = create_console_interface()

    assert isinstance(interface, ConsoleInterface)


@patch("folder_extractor.cli.interface.Console")
class TestArchiveProgress:
    """Tests for archive extraction progress functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        settings.reset_to_defaults()

    def test_show_archive_progress_extracting_shows_spinner(self, mock_console_class):
        """Test extracting status shows spinner with archive name."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        with patch("folder_extractor.cli.interface.Progress") as mock_progress_class:
            mock_progress = MagicMock()
            mock_progress_class.return_value = mock_progress

            interface = ConsoleInterface()
            interface.show_archive_progress("test.zip", "extracting")

            # Should create Progress with spinner
            mock_progress_class.assert_called_once()
            mock_progress.start.assert_called_once()
            # Should add task with extracting message
            mock_progress.add_task.assert_called_once()
            call_args = mock_progress.add_task.call_args
            assert "test.zip" in str(call_args) or "Entpacke" in str(call_args)

    def test_show_archive_progress_extracted_shows_success(self, mock_console_class):
        """Test extracted status shows success message with file count."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_archive_progress("test.zip", "extracted", count=5)

        mock_console.print.assert_called()
        call_args = mock_console.print.call_args
        output = str(call_args[0][0])
        assert "test.zip" in output
        assert "5" in output

    def test_show_archive_progress_error_shows_error_message(self, mock_console_class):
        """Test error status shows error message with details."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_archive_progress("test.zip", "error", error="Permission denied")

        mock_console.print.assert_called()
        call_args = mock_console.print.call_args
        output = str(call_args[0][0])
        assert "test.zip" in output
        assert "Permission denied" in output
        # Should use error style
        assert call_args.kwargs.get("style") == interface.error_style

    def test_show_archive_progress_quiet_mode_no_output(self, mock_console_class):
        """Test archive progress is suppressed in quiet mode."""
        settings.set("quiet", True)
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_archive_progress("test.zip", "extracting")

        mock_console.print.assert_not_called()

    def test_show_archive_progress_finish_stops_spinner(self, mock_console_class):
        """Test finish status stops the spinner."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        with patch("folder_extractor.cli.interface.Progress") as mock_progress_class:
            mock_progress = MagicMock()
            mock_progress_class.return_value = mock_progress

            interface = ConsoleInterface()
            interface.show_archive_progress("test.zip", "extracting")
            interface.show_archive_progress("test.zip", "finish")

            mock_progress.stop.assert_called()

    def test_show_archive_progress_security_error_shows_warning(
        self, mock_console_class
    ):
        """Test security error shows warning message."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_archive_progress("test.zip", "security_error")

        mock_console.print.assert_called()
        call_args = mock_console.print.call_args
        output = str(call_args[0][0])
        assert "test.zip" in output
        # Should mention security or Zip Slip
        assert "SICHERHEIT" in output.upper() or "Zip Slip" in output


@patch("folder_extractor.cli.interface.Console")
class TestArchiveSummary:
    """Tests for archive statistics in show_summary."""

    def setup_method(self):
        """Set up test fixtures."""
        settings.reset_to_defaults()

    def test_show_summary_shows_archives_extracted_count(self, mock_console_class):
        """Test summary displays number of archives extracted."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        results = {
            "status": "success",
            "moved": 10,
            "errors": 0,
            "archives_extracted": 3,
        }
        interface.show_summary(results)

        call_args_str = str(mock_console.print.call_args_list)
        # Should show archives extracted count
        assert "3" in call_args_str
        assert "Entpackt" in call_args_str

    def test_show_summary_shows_archives_deleted_count(self, mock_console_class):
        """Test summary displays number of archives deleted after extraction."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        results = {
            "status": "success",
            "moved": 10,
            "errors": 0,
            "archives_extracted": 3,
            "archives_deleted": 2,
        }
        interface.show_summary(results)

        call_args_str = str(mock_console.print.call_args_list)
        # Should show archives deleted count
        assert "2" in call_args_str
        assert "gelöscht" in call_args_str.lower() or "Archive" in call_args_str

    def test_show_summary_hides_archives_when_zero(self, mock_console_class):
        """Test summary hides archive lines when counts are zero."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        results = {
            "status": "success",
            "moved": 10,
            "errors": 0,
            "archives_extracted": 0,
            "archives_deleted": 0,
        }
        interface.show_summary(results)

        call_args_str = str(mock_console.print.call_args_list)
        # Should NOT show archive lines when count is 0
        assert "Entpackt" not in call_args_str

    def test_show_summary_hides_archives_when_key_missing(self, mock_console_class):
        """Test summary handles missing archive keys gracefully."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        results = {
            "status": "success",
            "moved": 10,
            "errors": 0,
            # No archive keys
        }
        interface.show_summary(results)

        call_args_str = str(mock_console.print.call_args_list)
        # Should NOT show archive lines when keys missing
        assert "Entpackt" not in call_args_str

    def test_show_summary_archive_order_after_moved(self, mock_console_class):
        """Test archives appear after 'Verschoben' in summary."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        results = {
            "status": "success",
            "moved": 10,
            "errors": 0,
            "archives_extracted": 3,
        }
        interface.show_summary(results)

        # Get all print calls in order
        print_calls = mock_console.print.call_args_list
        printed_strings = [str(call.args[0]) for call in print_calls if call.args]

        # Find positions
        moved_idx = None
        archives_idx = None
        fehler_idx = None

        for idx, line in enumerate(printed_strings):
            if "Verschoben" in line:
                moved_idx = idx
            if "Entpackt" in line:
                archives_idx = idx
            if "Fehler:" in line:
                fehler_idx = idx

        # Archives should appear after Verschoben and before Fehler
        assert moved_idx is not None, "Verschoben line not found"
        assert archives_idx is not None, "Entpackt line not found"
        assert fehler_idx is not None, "Fehler line not found"
        assert moved_idx < archives_idx < fehler_idx, (
            f"Wrong order: Verschoben@{moved_idx}, Entpackt@{archives_idx}, Fehler@{fehler_idx}"
        )


@patch("folder_extractor.cli.interface.Console")
class TestConsoleInterfaceStyles:
    """Test style attributes are correctly initialized."""

    def test_has_style_attributes(self, mock_console_class):
        """Test ConsoleInterface has all style attributes."""
        mock_console_class.return_value = MagicMock()

        interface = ConsoleInterface()

        assert hasattr(interface, "success_style")
        assert hasattr(interface, "error_style")
        assert hasattr(interface, "warning_style")
        assert hasattr(interface, "info_style")

    def test_styles_are_configured(self, mock_console_class):
        """Test styles are non-None Style objects."""
        mock_console_class.return_value = MagicMock()

        interface = ConsoleInterface()

        # All styles should be defined (not None)
        assert interface.success_style is not None
        assert interface.error_style is not None
        assert interface.warning_style is not None
        assert interface.info_style is not None

    def test_dedupe_style_exists_and_is_cyan(self, mock_console_class):
        """Test dedupe_style exists with cyan color and no modifiers."""
        mock_console_class.return_value = MagicMock()

        interface = ConsoleInterface()

        # dedupe_style should exist
        assert hasattr(interface, "dedupe_style")
        assert interface.dedupe_style is not None

        # Style should have cyan color
        style = interface.dedupe_style
        assert style.color is not None
        assert style.color.name == "cyan"

        # Style should NOT have bold or dim modifiers (minimalist)
        assert style.bold is not True, "dedupe_style should not be bold"
        assert style.dim is not True, "dedupe_style should not be dim"


@patch("folder_extractor.cli.interface.Console")
class TestConsoleInterfaceAttributes:
    """Test ConsoleInterface initialization and attributes."""

    def test_has_console_attribute(self, mock_console_class):
        """Test ConsoleInterface has a console attribute."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()

        assert hasattr(interface, "console")
        assert interface.console == mock_console

    def test_progress_initialized_to_none(self, mock_console_class):
        """Test progress attribute is initialized to None."""
        mock_console_class.return_value = MagicMock()

        interface = ConsoleInterface()

        assert hasattr(interface, "progress")
        assert interface.progress is None

    def test_task_id_initialized_to_none(self, mock_console_class):
        """Test task_id attribute is initialized to None."""
        mock_console_class.return_value = MagicMock()

        interface = ConsoleInterface()

        assert hasattr(interface, "task_id")
        assert interface.task_id is None

    def test_last_progress_update_initialized(self, mock_console_class):
        """Test last_progress_update is initialized to 0."""
        mock_console_class.return_value = MagicMock()

        interface = ConsoleInterface()

        assert hasattr(interface, "last_progress_update")
        assert interface.last_progress_update == 0

    def test_progress_update_interval_configured(self, mock_console_class):
        """Test progress_update_interval is configured."""
        mock_console_class.return_value = MagicMock()

        interface = ConsoleInterface()

        assert hasattr(interface, "progress_update_interval")
        assert interface.progress_update_interval > 0


@patch("folder_extractor.cli.interface.Console")
class TestWatchModeUI:
    """Tests for watch mode UI methods."""

    def setup_method(self):
        """Set up test fixtures."""
        settings.reset_to_defaults()

    # --- Tests for show_watch_status ---

    def test_show_watch_status_displays_path_with_icon(self, mock_console_class):
        """Test show_watch_status prints the watching message with path and eye icon."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_watch_status("/Users/test/Downloads")

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        output = str(call_args[0][0])
        # Should contain path and eye icon from MESSAGES["WATCH_STARTING"]
        assert "/Users/test/Downloads" in output
        assert "Wache" in output or "wache" in output.lower()

    def test_show_watch_status_uses_highlight_style(self, mock_console_class):
        """Test show_watch_status uses blue highlight style."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_watch_status("/path/to/folder")

        call_args = mock_console.print.call_args
        assert call_args.kwargs.get("style") == interface.highlight_style

    def test_show_watch_status_accepts_path_object(self, mock_console_class):
        """Test show_watch_status accepts Path objects."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_watch_status(Path("/Users/test/Downloads"))

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        output = str(call_args[0][0])
        assert "Downloads" in output

    def test_show_watch_status_quiet_mode_no_output(self, mock_console_class):
        """Test show_watch_status is suppressed in quiet mode."""
        settings.set("quiet", True)
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_watch_status("/path/to/folder")

        mock_console.print.assert_not_called()

    # --- Tests for show_watch_event ---

    def test_show_watch_event_incoming_displays_timestamp_and_message(
        self, mock_console_class
    ):
        """Test show_watch_event with incoming status shows timestamp and message."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_watch_event("created", "document.pdf", status="incoming")

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        output = str(call_args[0][0])
        # Should contain timestamp in format [HH:MM:SS]
        assert "[" in output and "]" in output
        assert "document.pdf" in output
        assert "Incoming" in output

    def test_show_watch_event_waiting_displays_waiting_message(
        self, mock_console_class
    ):
        """Test show_watch_event with waiting status shows waiting message."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_watch_event("created", "large_file.zip", status="waiting")

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        output = str(call_args[0][0])
        assert "large_file.zip" in output
        assert "Warte" in output

    def test_show_watch_event_analyzing_displays_analyzing_message(
        self, mock_console_class
    ):
        """Test show_watch_event with analyzing status shows analyzing message."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_watch_event("created", "document.pdf", status="analyzing")

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        output = str(call_args[0][0])
        assert "document.pdf" in output
        assert "Analysiere" in output

    def test_show_watch_event_sorted_displays_success_message(self, mock_console_class):
        """Test show_watch_event with sorted status shows success message."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_watch_event("created", "document.pdf", status="sorted")

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        output = str(call_args[0][0])
        assert "document.pdf" in output
        assert "Sortiert" in output

    def test_show_watch_event_error_displays_error_message(self, mock_console_class):
        """Test show_watch_event with error status shows error message."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_watch_event("created", "broken.pdf", status="error")

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        output = str(call_args[0][0])
        assert "broken.pdf" in output
        assert "Fehler" in output

    def test_show_watch_event_uses_appropriate_styles(self, mock_console_class):
        """Test show_watch_event uses correct styles for each status."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()

        # Test each status has appropriate style
        status_style_map = {
            "incoming": interface.info_style,
            "waiting": interface.warning_style,
            "analyzing": interface.info_style,
            "sorted": interface.success_style,
            "error": interface.error_style,
        }

        for status, expected_style in status_style_map.items():
            mock_console.reset_mock()
            interface.show_watch_event("created", "test.pdf", status=status)
            call_args = mock_console.print.call_args
            assert call_args.kwargs.get("style") == expected_style, (
                f"Wrong style for status '{status}'"
            )

    def test_show_watch_event_timestamp_format(self, mock_console_class):
        """Test show_watch_event timestamp is in HH:MM:SS format."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_watch_event("created", "test.pdf", status="incoming")

        call_args = mock_console.print.call_args
        output = str(call_args[0][0])
        # Extract timestamp pattern [HH:MM:SS]
        import re

        match = re.search(r"\[(\d{2}:\d{2}:\d{2})\]", output)
        assert match is not None, f"Timestamp not found in: {output}"

    def test_show_watch_event_quiet_mode_no_output(self, mock_console_class):
        """Test show_watch_event is suppressed in quiet mode."""
        settings.set("quiet", True)
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_watch_event("created", "test.pdf", status="incoming")

        mock_console.print.assert_not_called()

    def test_show_watch_event_default_status_is_incoming(self, mock_console_class):
        """Test show_watch_event defaults to incoming status."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_watch_event("created", "test.pdf")  # No status specified

        call_args = mock_console.print.call_args
        output = str(call_args[0][0])
        assert "Incoming" in output

    # --- Tests for show_watch_stopped ---

    def test_show_watch_stopped_displays_stopped_message(self, mock_console_class):
        """Test show_watch_stopped prints the stopped message."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_watch_stopped()

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        output = str(call_args[0][0])
        assert "beendet" in output.lower() or "Watch-Mode" in output

    def test_show_watch_stopped_uses_info_style(self, mock_console_class):
        """Test show_watch_stopped uses info style."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_watch_stopped()

        call_args = mock_console.print.call_args
        assert call_args.kwargs.get("style") == interface.info_style

    def test_show_watch_stopped_quiet_mode_no_output(self, mock_console_class):
        """Test show_watch_stopped is suppressed in quiet mode."""
        settings.set("quiet", True)
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        interface.show_watch_stopped()

        mock_console.print.assert_not_called()


@patch("folder_extractor.cli.interface.Console")
class TestSmartWatchUI:
    """Tests for smart watch mode UI methods."""

    def setup_method(self):
        """Set up test fixtures."""
        settings.reset_to_defaults()

    # --- Tests for show_smart_watch_status ---

    def test_show_smart_watch_status_displays_banner(self, mock_console_class):
        """Test show_smart_watch_status displays the smart watch banner."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        profile = {
            "name": "Downloads",
            "path": "/Users/test/Downloads",
            "folder_structure": "{category}/{sender}/{year}",
            "categories": ["Finanzen", "Verträge", "Medizin"],
            "recursive": False,
            "exclude_subfolders": [],
        }
        interface.show_smart_watch_status(profile)

        # Should print multiple lines for the banner
        assert mock_console.print.call_count >= 3
        call_args_str = str(mock_console.print.call_args_list)
        # Should contain banner header
        assert "Smart Watch" in call_args_str

    def test_show_smart_watch_status_displays_path(self, mock_console_class):
        """Test show_smart_watch_status displays the watch path."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        profile = {
            "path": "/Users/test/Downloads",
            "folder_structure": "{category}",
            "categories": [],
            "recursive": False,
        }
        interface.show_smart_watch_status(profile)

        call_args_str = str(mock_console.print.call_args_list)
        assert "/Users/test/Downloads" in call_args_str

    def test_show_smart_watch_status_displays_folder_structure(
        self, mock_console_class
    ):
        """Test show_smart_watch_status displays the folder structure template."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        profile = {
            "path": "/test/path",
            "folder_structure": "{category}/{sender}/{year}",
            "categories": [],
            "recursive": False,
        }
        interface.show_smart_watch_status(profile)

        call_args_str = str(mock_console.print.call_args_list)
        assert "{category}/{sender}/{year}" in call_args_str

    def test_show_smart_watch_status_displays_categories(self, mock_console_class):
        """Test show_smart_watch_status displays configured categories."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        profile = {
            "path": "/test/path",
            "folder_structure": "{category}",
            "categories": ["Finanzen", "Verträge", "Medizin"],
            "recursive": False,
        }
        interface.show_smart_watch_status(profile)

        call_args_str = str(mock_console.print.call_args_list)
        # Categories should be joined with comma
        assert "Finanzen" in call_args_str
        assert "Verträge" in call_args_str

    def test_show_smart_watch_status_displays_recursive_status(
        self, mock_console_class
    ):
        """Test show_smart_watch_status displays recursion status."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        profile = {
            "path": "/test/path",
            "folder_structure": "{category}",
            "categories": [],
            "recursive": True,
        }
        interface.show_smart_watch_status(profile)

        call_args_str = str(mock_console.print.call_args_list)
        # Should show "Ja" for recursive=True
        assert "Ja" in call_args_str or "ja" in call_args_str.lower()

    def test_show_smart_watch_status_displays_exclusions(self, mock_console_class):
        """Test show_smart_watch_status displays excluded subfolders."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        profile = {
            "path": "/test/path",
            "folder_structure": "{category}",
            "categories": [],
            "recursive": True,
            "exclude_subfolders": ["node_modules", ".git"],
        }
        interface.show_smart_watch_status(profile)

        call_args_str = str(mock_console.print.call_args_list)
        assert "node_modules" in call_args_str
        assert ".git" in call_args_str

    def test_show_smart_watch_status_hides_exclusions_when_empty(
        self, mock_console_class
    ):
        """Test show_smart_watch_status hides exclusions line when empty."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        profile = {
            "path": "/test/path",
            "folder_structure": "{category}",
            "categories": [],
            "recursive": False,
            "exclude_subfolders": [],
        }
        interface.show_smart_watch_status(profile)

        call_args_str = str(mock_console.print.call_args_list)
        # Should NOT show exclusions line when empty
        assert "Ausgeschlossen" not in call_args_str

    def test_show_smart_watch_status_quiet_mode_no_output(self, mock_console_class):
        """Test show_smart_watch_status is suppressed in quiet mode."""
        settings.set("quiet", True)
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        profile = {
            "path": "/test/path",
            "folder_structure": "{category}",
            "categories": [],
            "recursive": False,
        }
        interface.show_smart_watch_status(profile)

        mock_console.print.assert_not_called()

    def test_show_smart_watch_status_uses_highlight_style_for_banner(
        self, mock_console_class
    ):
        """Test show_smart_watch_status uses highlight style for banner."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        profile = {
            "path": "/test/path",
            "folder_structure": "{category}",
            "categories": [],
            "recursive": False,
        }
        interface.show_smart_watch_status(profile)

        # First call should be the banner with highlight style
        first_call = mock_console.print.call_args_list[0]
        assert first_call.kwargs.get("style") == interface.highlight_style

    def test_show_smart_watch_status_handles_missing_optional_fields(
        self, mock_console_class
    ):
        """Test show_smart_watch_status handles profiles with missing optional fields."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        # Minimal profile without optional fields
        profile = {
            "path": "/test/path",
            "folder_structure": "{category}",
        }
        # Should not raise exception
        interface.show_smart_watch_status(profile)

        # Should still display the banner and required fields
        assert mock_console.print.call_count >= 2

    def test_show_smart_watch_status_empty_categories_shows_default_hint(
        self, mock_console_class
    ):
        """Test show_smart_watch_status shows hint when categories is empty."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        profile = {
            "path": "/test/path",
            "folder_structure": "{category}",
            "categories": [],
            "recursive": False,
        }
        interface.show_smart_watch_status(profile)

        call_args_str = str(mock_console.print.call_args_list)
        # Should show "Standard" or similar for empty categories
        assert "Standard" in call_args_str or "standard" in call_args_str.lower()

    def test_show_smart_watch_status_displays_file_types(self, mock_console_class):
        """Test show_smart_watch_status displays file type filter when provided."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        profile = {
            "path": "/test/path",
            "folder_structure": "{category}",
            "categories": ["Finanzen"],
            "file_types": ["pdf", "docx", "xlsx"],
            "recursive": False,
        }
        interface.show_smart_watch_status(profile)

        call_args_str = str(mock_console.print.call_args_list)
        # Should show file types
        assert "pdf" in call_args_str
        assert "docx" in call_args_str
        assert "xlsx" in call_args_str

    def test_show_smart_watch_status_hides_file_types_when_empty(
        self, mock_console_class
    ):
        """Test show_smart_watch_status hides file types line when empty or None."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        interface = ConsoleInterface()
        profile = {
            "path": "/test/path",
            "folder_structure": "{category}",
            "categories": [],
            "file_types": None,  # No file type filter
            "recursive": False,
        }
        interface.show_smart_watch_status(profile)

        call_args_str = str(mock_console.print.call_args_list)
        # Should NOT show file types line when None
        assert "Dateitypen" not in call_args_str
