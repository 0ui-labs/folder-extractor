"""
Enhanced CLI application with integrated state management.

Coordinates the command line interface with new state management
and progress tracking capabilities.
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Optional

from watchdog.observers import Observer

from folder_extractor.cli.interface import create_console_interface
from folder_extractor.cli.parser import create_parser
from folder_extractor.config.constants import MESSAGES
from folder_extractor.config.settings import Settings, configure_from_args
from folder_extractor.core.ai_async import AsyncGeminiClient
from folder_extractor.core.extractor import (
    EnhancedExtractionOrchestrator,
    EnhancedFileExtractor,
)
from folder_extractor.core.memory.graph import KnowledgeGraph
from folder_extractor.core.monitor import StabilityMonitor
from folder_extractor.core.smart_sorter import SmartSorter
from folder_extractor.core.state_manager import StateManager
from folder_extractor.core.watch import FolderEventHandler, SmartFolderEventHandler
from folder_extractor.core.zone_manager import ZoneManager


class EnhancedFolderExtractorCLI:
    """Enhanced CLI application with state management."""

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize enhanced CLI application.

        Args:
            settings: Optional Settings instance for dependency injection.
                     If None, creates a new Settings instance.
        """
        self.settings = settings or Settings()
        self.state_manager = StateManager()
        self.parser = create_parser()
        self.interface = create_console_interface(self.settings)

    def run(self, args: Optional[list] = None) -> int:
        """Run the CLI application.

        Args:
            args: Optional command line arguments

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        try:
            # Parse arguments
            parsed_args = self.parser.parse_args(args)

            # Configure settings from arguments
            configure_from_args(self.settings, parsed_args)

            # Get current directory
            current_dir = Path.cwd()

            # Show welcome message
            if not parsed_args.undo:
                self.interface.show_welcome()

            # Execute operation
            if parsed_args.undo:
                return self._execute_undo(current_dir)
            elif getattr(parsed_args, "ask", None):
                return self._execute_query(parsed_args.ask)
            elif getattr(parsed_args, "watch", False):
                return self._execute_watch(current_dir)
            else:
                return self._execute_extraction(current_dir)

        except KeyboardInterrupt:
            print("\n" + MESSAGES["OPERATION_CANCELLED"])
            return 1

        except Exception as e:
            self.interface.show_message(f"Fehler: {str(e)}", message_type="error")
            return 1

    def _execute_extraction(self, path: Path) -> int:
        """Execute file extraction operation.

        Args:
            path: Path object to extract files from

        Returns:
            Exit code
        """
        path = Path(path)
        # Create extractor and orchestrator
        extractor = EnhancedFileExtractor(
            settings=self.settings, state_manager=self.state_manager
        )
        orchestrator = EnhancedExtractionOrchestrator(extractor, self.state_manager)

        # Set up progress integration
        def progress_callback(
            current: int,
            total: int,
            filepath: str,
            error: Optional[str] = None,
        ):
            self.interface.show_progress(current, total, filepath, error)

        # Set up indexing callback for global dedup spinner
        def indexing_callback(event: str):
            if event == "start":
                self.interface.show_indexing_spinner()
            elif event == "end":
                self.interface.hide_indexing_spinner()

        try:
            # Execute extraction
            result = orchestrator.execute_extraction(
                source_path=path,
                confirmation_callback=self.interface.confirm_operation,
                progress_callback=progress_callback,
                indexing_callback=indexing_callback,
            )

            # Show summary
            self.interface.show_summary(result)

            # Show operation statistics if available
            if "operation_id" in result:
                stats = self.state_manager.get_operation_stats(result["operation_id"])
                if stats and stats.duration:
                    self.interface.show_message(
                        f"\nOperation dauerte {stats.duration:.2f} Sekunden",
                        message_type="info",
                    )
                    if stats.files_processed > 0:
                        rate = stats.files_processed / stats.duration
                        self.interface.show_message(
                            f"Durchschnitt: {rate:.1f} Dateien/Sekunde",
                            message_type="info",
                        )

            # Return appropriate exit code
            if result.get("status") == "success":
                return 0
            elif result.get("status") in ["no_files", "cancelled"]:
                return 0  # Not an error
            else:
                return 1

        except KeyboardInterrupt:
            # User pressed Ctrl+C - request abort via state manager
            self.state_manager.request_abort()
            self.interface.finish_progress()
            self.interface.show_message(
                "\nOperation wird abgebrochen...", message_type="warning"
            )
            return 1

    def _execute_undo(self, path: Path) -> int:
        """Execute undo operation.

        Args:
            path: Path object where history is located

        Returns:
            Exit code
        """
        path = Path(path)
        # Create extractor and orchestrator
        extractor = EnhancedFileExtractor(
            settings=self.settings, state_manager=self.state_manager
        )
        orchestrator = EnhancedExtractionOrchestrator(extractor, self.state_manager)

        # Show operation message
        self.interface.show_message(
            "Rückgängig machen der letzten Operation...", message_type="info"
        )

        # Execute undo
        result = orchestrator.execute_undo(path)

        # Show result
        self.interface.show_message(
            result["message"],
            message_type="success" if result["status"] == "success" else "warning",
        )

        # Show statistics if available
        if result.get("restored", 0) > 0:
            self.interface.show_message(
                f"✓ {result['restored']} Dateien wiederhergestellt",
                message_type="success",
            )
            if result.get("errors", 0) > 0:
                self.interface.show_message(
                    f"✗ {result['errors']} Fehler aufgetreten", message_type="error"
                )
            if result.get("removed_directories", 0) > 0:
                self.interface.show_message(
                    f"✓ {result['removed_directories']} leere Ordner entfernt",
                    message_type="success",
                )

        return 0 if result["status"] == "success" else 1

    def _execute_watch(self, path: Path) -> int:
        """Execute watch mode operation.

        Starts a filesystem watcher that monitors the given path for new files
        and automatically processes them using the extraction orchestrator.

        Args:
            path: Path object to watch for new files

        Returns:
            Exit code (0 for normal exit)
        """
        path = Path(path)
        # Create monitor and orchestrator
        monitor = StabilityMonitor(self.state_manager)
        extractor = EnhancedFileExtractor(
            settings=self.settings, state_manager=self.state_manager
        )
        orchestrator = EnhancedExtractionOrchestrator(extractor, self.state_manager)

        # Define progress callback for watch events
        def progress_callback(
            current: int,
            total: int,
            filepath: str,
            error: Optional[str] = None,
        ) -> None:
            self.interface.show_progress(current, total, filepath, error)

        # Define event callback for UI status updates
        def event_callback(
            status: str,
            filename: str,
            error: Optional[str] = None,
        ) -> None:
            # show_watch_event expects (event_type, filename, status, error)
            self.interface.show_watch_event("file", filename, status, error)

        # Create event handler
        handler = FolderEventHandler(
            orchestrator,
            monitor,
            self.state_manager,
            progress_callback,
            on_event_callback=event_callback,
        )

        # Create and configure observer
        observer = Observer()
        observer.schedule(handler, str(path), recursive=False)

        # Show status
        self.interface.show_watch_status(path)

        # Start observer
        observer.start()

        try:
            # Main loop - wait for abort signal
            while not self.state_manager.is_abort_requested():
                time.sleep(1)
        except KeyboardInterrupt:
            # User pressed Ctrl+C
            self.state_manager.request_abort()
        finally:
            # Clean shutdown
            observer.stop()
            observer.join()
            self.interface.show_watch_stopped()

        return 0

    def _execute_watch_smart(self, zone_id: str) -> int:
        """Execute smart watch mode with AI categorization.

        Loads a zone configuration and starts a SmartFolderEventHandler
        that uses the SmartSorter for AI-powered file categorization.

        Args:
            zone_id: ID of the zone to watch

        Returns:
            Exit code (0 for normal exit, 1 for error)
        """
        # Load zone configuration
        zone_manager = ZoneManager()
        zone = zone_manager.get_zone(zone_id)

        if zone is None:
            self.interface.show_message(
                f"Zone '{zone_id}' nicht gefunden",
                message_type="error",
            )
            return 1

        # Build complete smart watch profile from zone configuration
        # Read all fields from zone with sensible defaults
        profile = {
            "name": zone.get("name", ""),
            "path": zone.get("path", ""),
            "folder_structure": zone.get(
                "folder_structure", "{category}/{sender}/{year}"
            ),
            "categories": zone.get("categories", []),
            "file_types": zone.get("file_types"),  # File extensions like ["pdf", "jpg"]
            "recursive": zone.get("recursive", False),
            "exclude_subfolders": zone.get("exclude_subfolders", []),
            "ignore_patterns": zone.get("ignore_patterns"),
        }

        # Configure settings with zone's custom categories for SmartSorter
        # This ensures the AI uses zone-specific categories
        self.settings.set("custom_categories", profile["categories"])

        # Create AI client and SmartSorter with configured settings
        ai_client = AsyncGeminiClient()
        smart_sorter = SmartSorter(client=ai_client, settings=self.settings)

        # Create stability monitor
        monitor = StabilityMonitor(self.state_manager)

        # Define event callback for UI status updates
        def event_callback(
            status: str,
            filename: str,
            error: Optional[str] = None,
        ) -> None:
            self.interface.show_watch_event("file", filename, status, error)

        # Create SmartFolderEventHandler with profile configuration
        # file_types: extensions for filtering, categories: for AI categorization
        handler = SmartFolderEventHandler(
            smart_sorter=smart_sorter,
            monitor=monitor,
            state_manager=self.state_manager,
            base_path=profile["path"],
            folder_structure=profile["folder_structure"],
            file_types=profile.get("file_types"),  # File extensions for filtering
            ignore_patterns=profile.get("ignore_patterns"),
            exclude_subfolders=profile["exclude_subfolders"],
            recursive=profile["recursive"],
            on_event_callback=event_callback,
        )

        # Create and configure observer
        observer = Observer()
        observer.schedule(handler, profile["path"], recursive=profile["recursive"])

        # Show status banner
        self.interface.show_smart_watch_status(profile)

        # Start observer
        observer.start()

        try:
            # Main loop - wait for abort signal
            while not self.state_manager.is_abort_requested():
                time.sleep(1)
        except KeyboardInterrupt:
            # User pressed Ctrl+C
            self.state_manager.request_abort()
        finally:
            # Clean shutdown
            observer.stop()
            observer.join()
            self.interface.show_watch_stopped()
            # Reset custom_categories after watch mode completes
            self.settings.set("custom_categories", [])

        return 0

    def _execute_query(self, query_text: str) -> int:
        """Execute knowledge graph query operation.

        Args:
            query_text: Natural language query string

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        try:
            # Show query message
            self.interface.show_message(
                MESSAGES["QUERY_EXECUTING"].format(query=query_text),
                message_type="info",
            )

            # Initialize knowledge graph
            kg = KnowledgeGraph()

            # Execute query (async call via asyncio.run)
            results = asyncio.run(kg.query_documents(query_text))

            # Display results
            if not results:
                self.interface.show_message(
                    MESSAGES["QUERY_NO_RESULTS"].format(query=query_text),
                    message_type="warning",
                )
                return 0

            # Show results header
            self.interface.show_message(
                MESSAGES["QUERY_RESULTS_HEADER"].format(count=len(results)),
                message_type="success",
            )

            # Show each result
            for result_path in results:
                self.interface.show_message(
                    MESSAGES["QUERY_RESULT_ITEM"].format(path=result_path),
                    message_type="info",
                )

            return 0

        except Exception as e:
            self.interface.show_message(
                MESSAGES["QUERY_ERROR"].format(error=str(e)),
                message_type="error",
            )
            return 1


def main(args: Optional[list] = None) -> int:
    """Main entry point for the enhanced CLI.

    Args:
        args: Optional command line arguments

    Returns:
        Exit code
    """
    app = EnhancedFolderExtractorCLI()
    return app.run(args)


if __name__ == "__main__":
    sys.exit(main())
