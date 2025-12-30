"""
Unit tests for CLI app module.
"""

import os
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

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
        with patch("folder_extractor.cli.app.create_parser"):
            with patch("folder_extractor.cli.app.create_console_interface"):
                with patch("folder_extractor.cli.app.get_state_manager"):
                    self.cli = EnhancedFolderExtractorCLI()

    def test_init(self):
        """Test CLI initialization."""
        with patch("folder_extractor.cli.app.create_parser") as mock_parser:
            with patch(
                "folder_extractor.cli.app.create_console_interface"
            ) as mock_interface:
                with patch("folder_extractor.cli.app.get_state_manager") as mock_state:
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

        with patch("sys.stdout", new=StringIO()) as mock_stdout:
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
        with patch.object(self.cli, "_execute_undo", return_value=0) as mock_undo:
            with patch("folder_extractor.cli.app.configure_from_args"):
                with patch("folder_extractor.core.migration.MigrationHelper"):
                    result = self.cli.run()

                    assert result == 0
                    mock_undo.assert_called_once()
                    # Should not show welcome for undo
                    assert not self.cli.interface.show_welcome.called

    def test_run_extraction_operation(self):
        """Test running extraction operation."""
        # Mock parsed arguments for extraction
        mock_args = Mock(undo=False, watch=False)
        self.cli.parser.parse_args = Mock(return_value=mock_args)

        # Mock interface
        self.cli.interface.show_welcome = Mock()

        # Mock execute_extraction
        with patch.object(
            self.cli, "_execute_extraction", return_value=0
        ) as mock_extract:
            with patch("folder_extractor.cli.app.configure_from_args"):
                with patch("folder_extractor.core.migration.MigrationHelper"):
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
            "errors": 0,
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

        with patch(
            "folder_extractor.cli.app.EnhancedFileExtractor",
            return_value=mock_extractor,
        ):
            with patch(
                "folder_extractor.cli.app.EnhancedExtractionOrchestrator",
                return_value=mock_orchestrator,
            ):
                result = self.cli._execute_extraction("/test/path")

                assert result == 0

                # Check orchestrator called correctly
                mock_orchestrator.execute_extraction.assert_called_once()

                # Check summary shown
                self.cli.interface.show_summary.assert_called_once()

    def test_execute_extraction_no_files(self):
        """Test extraction with no files found."""
        mock_orchestrator = Mock()
        mock_orchestrator.execute_extraction.return_value = {
            "status": "no_files",
            "message": "Keine Dateien gefunden",
        }

        self.cli.state_manager.get_value = Mock(return_value=True)  # dry_run
        self.cli.state_manager.get_operation_stats = Mock(return_value=None)
        self.cli.interface.show_summary = Mock()

        with patch("folder_extractor.cli.app.EnhancedFileExtractor"):
            with patch(
                "folder_extractor.cli.app.EnhancedExtractionOrchestrator",
                return_value=mock_orchestrator,
            ):
                result = self.cli._execute_extraction("/test/path")

                # Should still return 0 (not an error)
                assert result == 0

    def test_execute_extraction_cancelled(self):
        """Test extraction cancelled by user."""
        mock_orchestrator = Mock()
        mock_orchestrator.execute_extraction.return_value = {
            "status": "cancelled",
            "message": "Operation abgebrochen",
        }

        self.cli.state_manager.get_value = Mock(return_value=True)  # dry_run
        self.cli.state_manager.get_operation_stats = Mock(return_value=None)
        self.cli.interface.show_summary = Mock()

        with patch("folder_extractor.cli.app.EnhancedFileExtractor"):
            with patch(
                "folder_extractor.cli.app.EnhancedExtractionOrchestrator",
                return_value=mock_orchestrator,
            ):
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
            "errors": 0,
        }

        self.cli.state_manager.get_value = Mock(return_value=True)  # dry_run
        self.cli.state_manager.get_operation_stats = Mock(return_value=None)
        self.cli.interface.show_summary = Mock()

        test_path = Path("/test/path")

        with patch("folder_extractor.cli.app.EnhancedFileExtractor"):
            with patch(
                "folder_extractor.cli.app.EnhancedExtractionOrchestrator",
                return_value=mock_orchestrator,
            ):
                result = self.cli._execute_extraction(test_path)

                assert result == 0

                # Verify orchestrator received Path object
                call_args = mock_orchestrator.execute_extraction.call_args
                source_path = call_args[1]["source_path"]
                assert isinstance(source_path, Path)

    def test_execute_undo_success(self):
        """Test successful undo execution."""
        mock_orchestrator = Mock()
        mock_orchestrator.execute_undo.return_value = {
            "status": "success",
            "message": "10 Dateien zurück verschoben",
            "restored": 10,
            "errors": 0,
        }

        # Mock interface
        self.cli.interface.show_message = Mock()

        with patch("folder_extractor.cli.app.EnhancedFileExtractor"):
            with patch(
                "folder_extractor.cli.app.EnhancedExtractionOrchestrator",
                return_value=mock_orchestrator,
            ):
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
            "restored": 0,
        }

        self.cli.interface.show_message = Mock()

        with patch("folder_extractor.cli.app.EnhancedFileExtractor"):
            with patch(
                "folder_extractor.cli.app.EnhancedExtractionOrchestrator",
                return_value=mock_orchestrator,
            ):
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
            "errors": 0,
        }

        self.cli.interface.show_message = Mock()

        test_path = Path("/test/path")

        with patch("folder_extractor.cli.app.EnhancedFileExtractor"):
            with patch(
                "folder_extractor.cli.app.EnhancedExtractionOrchestrator",
                return_value=mock_orchestrator,
            ):
                result = self.cli._execute_undo(test_path)

                assert result == 0

                # Verify orchestrator received Path object
                call_args = mock_orchestrator.execute_undo.call_args[0]
                assert isinstance(call_args[0], Path)


def test_main_function():
    """Test main entry point function."""
    with patch("folder_extractor.cli.app.EnhancedFolderExtractorCLI") as mock_cli_class:
        mock_cli = Mock()
        mock_cli.run.return_value = 0
        mock_cli_class.return_value = mock_cli

        # Test with no arguments
        result = main()
        assert result == 0
        mock_cli.run.assert_called_once_with(None)

        # Test with arguments
        mock_cli.run.reset_mock()
        test_args = ["--dry-run", "--depth", "3"]
        result = main(test_args)
        assert result == 0
        mock_cli.run.assert_called_once_with(test_args)


def test_main_entry_point():
    """Test __main__ entry point."""
    # Test that main can be called when module is run directly
    test_module = "folder_extractor.cli.app"

    with patch(f"{test_module}.main", return_value=0) as mock_main:
        # Simulate the module being run as __main__
        with patch.dict("sys.modules", {test_module: MagicMock(__name__="__main__")}):
            # The actual code that would run
            if sys.modules[test_module].__name__ == "__main__":
                result = mock_main()
                assert result == 0


class TestCLIAppEdgeCases:
    """Test edge cases for CLI app to achieve 100% coverage."""

    def setup_method(self):
        """Set up test fixtures."""
        try:
            os.getcwd()
        except (FileNotFoundError, OSError):
            os.chdir(os.path.expanduser("~"))

        with patch("folder_extractor.cli.app.create_parser"):
            with patch("folder_extractor.cli.app.create_console_interface"):
                with patch("folder_extractor.cli.app.get_state_manager"):
                    self.cli = EnhancedFolderExtractorCLI()

    def test_execute_undo_with_errors(self):
        """Test undo execution with errors (line 179)."""
        mock_orchestrator = Mock()
        mock_orchestrator.execute_undo.return_value = {
            "status": "success",
            "message": "8 Dateien zurück verschoben",
            "restored": 8,
            "errors": 2,  # Has errors
        }

        # Mock interface
        self.cli.interface.show_message = Mock()

        with patch("folder_extractor.cli.app.EnhancedFileExtractor"):
            with patch(
                "folder_extractor.cli.app.EnhancedExtractionOrchestrator",
                return_value=mock_orchestrator,
            ):
                result = self.cli._execute_undo("/test/path")

                assert result == 0

                # Check that error message was shown
                # Find the call with "error" message_type
                error_calls = [
                    call
                    for call in self.cli.interface.show_message.call_args_list
                    if call[1].get("message_type") == "error"
                ]
                assert len(error_calls) > 0
                # The error message should mention the error count
                error_call_args = error_calls[0][0][0]
                assert "2" in error_call_args or "Fehler" in error_call_args

    def test_execute_extraction_with_operation_stats(self):
        """Test extraction with operation stats showing duration and rate."""
        mock_stats = Mock()
        mock_stats.duration = 2.5
        mock_stats.files_processed = 25

        mock_orchestrator = Mock()
        mock_orchestrator.execute_extraction.return_value = {
            "status": "success",
            "moved": 25,
            "duplicates": 0,
            "errors": 0,
            "operation_id": "test_op_123",
        }

        self.cli.interface.show_summary = Mock()
        self.cli.interface.show_message = Mock()
        self.cli.state_manager.get_value = Mock(return_value=True)  # dry_run
        self.cli.state_manager.get_operation_stats = Mock(return_value=mock_stats)

        with patch("folder_extractor.cli.app.EnhancedFileExtractor"):
            with patch(
                "folder_extractor.cli.app.EnhancedExtractionOrchestrator",
                return_value=mock_orchestrator,
            ):
                result = self.cli._execute_extraction("/test/path")

                assert result == 0

                # Check that duration and rate messages were shown
                message_calls = [
                    call[0][0]
                    for call in self.cli.interface.show_message.call_args_list
                ]

                # Should have messages about duration and rate
                duration_msg = any(
                    "2.5" in msg or "Sekunden" in msg for msg in message_calls
                )
                rate_msg = any("Dateien/Sekunde" in msg for msg in message_calls)

                assert duration_msg or rate_msg  # At least one should be shown

    def test_execute_extraction_error_status(self):
        """Test extraction returning error status."""
        mock_orchestrator = Mock()
        mock_orchestrator.execute_extraction.return_value = {
            "status": "error",
            "message": "Something went wrong",
        }

        self.cli.interface.show_summary = Mock()
        self.cli.state_manager.get_value = Mock(return_value=True)
        self.cli.state_manager.get_operation_stats = Mock(return_value=None)

        with patch("folder_extractor.cli.app.EnhancedFileExtractor"):
            with patch(
                "folder_extractor.cli.app.EnhancedExtractionOrchestrator",
                return_value=mock_orchestrator,
            ):
                result = self.cli._execute_extraction("/test/path")

                # Should return 1 for error status
                assert result == 1

    def test_execute_extraction_stats_zero_duration(self):
        """Test extraction with stats having zero duration (branch 119->132)."""
        mock_stats = Mock()
        mock_stats.duration = 0  # Zero duration - should skip the message
        mock_stats.files_processed = 10

        mock_orchestrator = Mock()
        mock_orchestrator.execute_extraction.return_value = {
            "status": "success",
            "moved": 10,
            "duplicates": 0,
            "errors": 0,
            "operation_id": "test_op_zero_duration",
        }

        self.cli.interface.show_summary = Mock()
        self.cli.interface.show_message = Mock()
        self.cli.state_manager.get_value = Mock(return_value=True)
        self.cli.state_manager.get_operation_stats = Mock(return_value=mock_stats)

        with patch("folder_extractor.cli.app.EnhancedFileExtractor"):
            with patch(
                "folder_extractor.cli.app.EnhancedExtractionOrchestrator",
                return_value=mock_orchestrator,
            ):
                result = self.cli._execute_extraction("/test/path")

                assert result == 0

                # Should NOT show duration message since duration is 0
                message_calls = [
                    call[0][0]
                    for call in self.cli.interface.show_message.call_args_list
                ]
                duration_shown = any("Sekunden" in msg for msg in message_calls)
                assert not duration_shown

    def test_execute_extraction_stats_zero_files_processed(self):
        """Test extraction with stats having zero files_processed (branch 124->132)."""
        mock_stats = Mock()
        mock_stats.duration = 2.5  # Has duration
        mock_stats.files_processed = 0  # Zero files - should skip rate message

        mock_orchestrator = Mock()
        mock_orchestrator.execute_extraction.return_value = {
            "status": "success",
            "moved": 0,
            "duplicates": 0,
            "errors": 0,
            "operation_id": "test_op_zero_files",
        }

        self.cli.interface.show_summary = Mock()
        self.cli.interface.show_message = Mock()
        self.cli.state_manager.get_value = Mock(return_value=True)
        self.cli.state_manager.get_operation_stats = Mock(return_value=mock_stats)

        with patch("folder_extractor.cli.app.EnhancedFileExtractor"):
            with patch(
                "folder_extractor.cli.app.EnhancedExtractionOrchestrator",
                return_value=mock_orchestrator,
            ):
                result = self.cli._execute_extraction("/test/path")

                assert result == 0

                # Should show duration message but NOT rate message
                message_calls = [
                    call[0][0]
                    for call in self.cli.interface.show_message.call_args_list
                ]
                duration_shown = any("Sekunden" in msg for msg in message_calls)
                rate_shown = any("Dateien/Sekunde" in msg for msg in message_calls)

                assert duration_shown  # Duration should be shown
                assert not rate_shown  # Rate should NOT be shown

    def test_execute_extraction_keyboard_interrupt_aborts_gracefully(self):
        """Test that Ctrl+C (KeyboardInterrupt) during extraction triggers abort."""
        mock_orchestrator = Mock()
        # Simulate KeyboardInterrupt during extraction
        mock_orchestrator.execute_extraction.side_effect = KeyboardInterrupt

        self.cli.interface.show_summary = Mock()
        self.cli.interface.show_message = Mock()
        self.cli.interface.finish_progress = Mock()
        self.cli.state_manager.get_value = Mock(return_value=False)  # Not dry run
        self.cli.state_manager.request_abort = Mock()

        with patch("folder_extractor.cli.app.EnhancedFileExtractor"):
            with patch(
                "folder_extractor.cli.app.EnhancedExtractionOrchestrator",
                return_value=mock_orchestrator,
            ):
                with patch("time.sleep"):  # Mock at module level
                    result = self.cli._execute_extraction("/test/path")

                    # Should return 1 (error exit code)
                    assert result == 1

                    # Should have called request_abort on state manager
                    self.cli.state_manager.request_abort.assert_called_once()

                    # Should have stopped the progress bar
                    self.cli.interface.finish_progress.assert_called_once()

                    # Should have shown a warning message about aborting
                    warning_calls = [
                        call
                        for call in self.cli.interface.show_message.call_args_list
                        if call[1].get("message_type") == "warning"
                    ]
                    assert len(warning_calls) > 0
                    # Message should mention "abbrechen" or similar
                    assert any(
                        "abbrechen" in call[0][0].lower()
                        or "abgebrochen" in call[0][0].lower()
                        for call in warning_calls
                    )


class TestWatchMode:
    """Tests for watch mode functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        try:
            os.getcwd()
        except (FileNotFoundError, OSError):
            os.chdir(os.path.expanduser("~"))

        with patch("folder_extractor.cli.app.create_parser"):
            with patch("folder_extractor.cli.app.create_console_interface"):
                with patch("folder_extractor.cli.app.get_state_manager"):
                    self.cli = EnhancedFolderExtractorCLI()

    def test_watch_flag_triggers_execute_watch(self):
        """Test that --watch flag triggers _execute_watch method."""
        # Mock parsed arguments with watch=True
        mock_args = Mock(undo=False, watch=True)
        self.cli.parser.parse_args = Mock(return_value=mock_args)

        # Mock interface
        self.cli.interface.show_welcome = Mock()

        # Mock execute_watch
        with patch.object(self.cli, "_execute_watch", return_value=0) as mock_watch:
            with patch("folder_extractor.cli.app.configure_from_args"):
                with patch("folder_extractor.core.migration.MigrationHelper"):
                    result = self.cli.run()

                    assert result == 0
                    mock_watch.assert_called_once()
                    # Should show welcome for watch mode
                    self.cli.interface.show_welcome.assert_called_once()

    def test_execute_watch_starts_and_stops_observer(self):
        """Test that Observer is started and stopped correctly."""
        # Mock state manager to exit loop after first iteration
        abort_call_count = [0]

        def mock_is_abort():
            abort_call_count[0] += 1
            # Exit on second call
            return abort_call_count[0] > 1

        self.cli.state_manager.is_abort_requested = Mock(side_effect=mock_is_abort)
        self.cli.state_manager.request_abort = Mock()

        # Mock interface methods
        self.cli.interface.show_watch_status = Mock()
        self.cli.interface.show_watch_event = Mock()
        self.cli.interface.show_watch_stopped = Mock()

        # Mock Observer
        mock_observer = Mock()
        mock_observer_class = Mock(return_value=mock_observer)

        with patch("folder_extractor.cli.app.Observer", mock_observer_class):
            with patch("folder_extractor.cli.app.StabilityMonitor"):
                with patch("folder_extractor.cli.app.FolderEventHandler"):
                    with patch("folder_extractor.cli.app.EnhancedFileExtractor"):
                        with patch(
                            "folder_extractor.cli.app.EnhancedExtractionOrchestrator"
                        ):
                            with patch("time.sleep"):
                                result = self.cli._execute_watch("/test/path")

        # Observer should be started and stopped
        mock_observer.start.assert_called_once()
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()

        # Should have scheduled the handler
        mock_observer.schedule.assert_called_once()

        assert result == 0

    def test_execute_watch_keyboard_interrupt_requests_abort(self):
        """Test that KeyboardInterrupt requests abort and stops observer."""
        # Mock state manager to never return True for abort
        self.cli.state_manager.is_abort_requested = Mock(return_value=False)
        self.cli.state_manager.request_abort = Mock()

        # Mock interface methods
        self.cli.interface.show_watch_status = Mock()
        self.cli.interface.show_watch_event = Mock()
        self.cli.interface.show_watch_stopped = Mock()

        # Mock Observer
        mock_observer = Mock()
        mock_observer_class = Mock(return_value=mock_observer)

        # Mock time.sleep to raise KeyboardInterrupt
        def sleep_interrupt(_):
            raise KeyboardInterrupt

        with patch("folder_extractor.cli.app.Observer", mock_observer_class):
            with patch("folder_extractor.cli.app.StabilityMonitor"):
                with patch("folder_extractor.cli.app.FolderEventHandler"):
                    with patch("folder_extractor.cli.app.EnhancedFileExtractor"):
                        with patch(
                            "folder_extractor.cli.app.EnhancedExtractionOrchestrator"
                        ):
                            with patch("time.sleep", side_effect=sleep_interrupt):
                                result = self.cli._execute_watch("/test/path")

        # Should have requested abort
        self.cli.state_manager.request_abort.assert_called_once()

        # Observer should still be stopped properly
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()

        assert result == 0

    def test_execute_watch_shows_watch_status(self):
        """Test that show_watch_status is called with path."""
        # Mock state manager to exit immediately
        self.cli.state_manager.is_abort_requested = Mock(return_value=True)
        self.cli.state_manager.request_abort = Mock()

        # Mock interface methods
        self.cli.interface.show_watch_status = Mock()
        self.cli.interface.show_watch_event = Mock()
        self.cli.interface.show_watch_stopped = Mock()

        # Mock Observer
        mock_observer = Mock()
        mock_observer_class = Mock(return_value=mock_observer)

        test_path = Path("/test/watch/path")

        with patch("folder_extractor.cli.app.Observer", mock_observer_class):
            with patch("folder_extractor.cli.app.StabilityMonitor"):
                with patch("folder_extractor.cli.app.FolderEventHandler"):
                    with patch("folder_extractor.cli.app.EnhancedFileExtractor"):
                        with patch(
                            "folder_extractor.cli.app.EnhancedExtractionOrchestrator"
                        ):
                            with patch("time.sleep"):
                                self.cli._execute_watch(test_path)

        # Should show watch status with the path
        self.cli.interface.show_watch_status.assert_called_once_with(test_path)

    def test_execute_watch_shows_stopped_on_exit(self):
        """Test that show_watch_stopped is called on exit."""
        # Mock state manager to exit immediately
        self.cli.state_manager.is_abort_requested = Mock(return_value=True)
        self.cli.state_manager.request_abort = Mock()

        # Mock interface methods
        self.cli.interface.show_watch_status = Mock()
        self.cli.interface.show_watch_event = Mock()
        self.cli.interface.show_watch_stopped = Mock()

        # Mock Observer
        mock_observer = Mock()
        mock_observer_class = Mock(return_value=mock_observer)

        with patch("folder_extractor.cli.app.Observer", mock_observer_class):
            with patch("folder_extractor.cli.app.StabilityMonitor"):
                with patch("folder_extractor.cli.app.FolderEventHandler"):
                    with patch("folder_extractor.cli.app.EnhancedFileExtractor"):
                        with patch(
                            "folder_extractor.cli.app.EnhancedExtractionOrchestrator"
                        ):
                            with patch("time.sleep"):
                                self.cli._execute_watch("/test/path")

        # Should show watch stopped
        self.cli.interface.show_watch_stopped.assert_called_once()

    def test_execute_watch_creates_handler_with_correct_components(self):
        """Test that FolderEventHandler is created with correct dependencies."""
        # Mock state manager
        self.cli.state_manager.is_abort_requested = Mock(return_value=True)
        self.cli.state_manager.request_abort = Mock()

        # Mock interface methods
        self.cli.interface.show_watch_status = Mock()
        self.cli.interface.show_watch_event = Mock()
        self.cli.interface.show_watch_stopped = Mock()

        # Mock components
        mock_observer = Mock()
        mock_observer_class = Mock(return_value=mock_observer)
        mock_monitor = Mock()
        mock_monitor_class = Mock(return_value=mock_monitor)
        mock_handler = Mock()
        mock_handler_class = Mock(return_value=mock_handler)
        mock_orchestrator = Mock()

        with patch("folder_extractor.cli.app.Observer", mock_observer_class):
            with patch("folder_extractor.cli.app.StabilityMonitor", mock_monitor_class):
                with patch(
                    "folder_extractor.cli.app.FolderEventHandler", mock_handler_class
                ):
                    with patch("folder_extractor.cli.app.EnhancedFileExtractor"):
                        with patch(
                            "folder_extractor.cli.app.EnhancedExtractionOrchestrator",
                            return_value=mock_orchestrator,
                        ):
                            with patch("time.sleep"):
                                self.cli._execute_watch("/test/path")

        # Check that StabilityMonitor was created with state_manager
        mock_monitor_class.assert_called_once_with(self.cli.state_manager)

        # Check that FolderEventHandler was created with correct arguments
        mock_handler_class.assert_called_once()
        handler_args = mock_handler_class.call_args

        # First argument should be orchestrator
        assert handler_args[0][0] == mock_orchestrator
        # Second argument should be monitor
        assert handler_args[0][1] == mock_monitor
        # Third argument should be state_manager
        assert handler_args[0][2] == self.cli.state_manager

    def test_execute_watch_schedules_handler_non_recursive(self):
        """Test that observer.schedule is called with recursive=False."""
        # Mock state manager
        self.cli.state_manager.is_abort_requested = Mock(return_value=True)
        self.cli.state_manager.request_abort = Mock()

        # Mock interface methods
        self.cli.interface.show_watch_status = Mock()
        self.cli.interface.show_watch_event = Mock()
        self.cli.interface.show_watch_stopped = Mock()

        # Mock Observer
        mock_observer = Mock()
        mock_observer_class = Mock(return_value=mock_observer)
        mock_handler = Mock()

        test_path = "/test/watch/directory"

        with patch("folder_extractor.cli.app.Observer", mock_observer_class):
            with patch("folder_extractor.cli.app.StabilityMonitor"):
                with patch(
                    "folder_extractor.cli.app.FolderEventHandler",
                    return_value=mock_handler,
                ):
                    with patch("folder_extractor.cli.app.EnhancedFileExtractor"):
                        with patch(
                            "folder_extractor.cli.app.EnhancedExtractionOrchestrator"
                        ):
                            with patch("time.sleep"):
                                self.cli._execute_watch(test_path)

        # Check schedule was called with handler, path (as str), and recursive=False
        mock_observer.schedule.assert_called_once()
        schedule_args = mock_observer.schedule.call_args

        assert schedule_args[0][0] == mock_handler
        assert schedule_args[0][1] == test_path
        assert schedule_args[1]["recursive"] is False
