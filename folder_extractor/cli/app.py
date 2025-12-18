"""
Enhanced CLI application with integrated state management.

Coordinates the command line interface with new state management
and progress tracking capabilities.
"""
import sys
from pathlib import Path
from typing import Optional, Union

from folder_extractor.cli.parser import create_parser
from folder_extractor.cli.interface import (
    create_console_interface, KeyboardHandler
)
from folder_extractor.core.extractor import (
    EnhancedFileExtractor, EnhancedExtractionOrchestrator
)
from folder_extractor.core.state_manager import (
    get_state_manager
)
from folder_extractor.config.settings import configure_from_args
from folder_extractor.config.constants import MESSAGES


class EnhancedFolderExtractorCLI:
    """Enhanced CLI application with state management."""
    
    def __init__(self):
        """Initialize enhanced CLI application."""
        self.parser = create_parser()
        self.interface = create_console_interface()
        self.state_manager = get_state_manager()
    
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
            configure_from_args(parsed_args)
            
            # Migrate settings to state manager
            from folder_extractor.core.migration import MigrationHelper
            MigrationHelper.migrate_settings()

            # Get current directory
            current_dir = Path.cwd()

            # Show welcome message
            if not parsed_args.undo:
                self.interface.show_welcome()
            
            # Execute operation
            if parsed_args.undo:
                return self._execute_undo(current_dir)
            else:
                return self._execute_extraction(current_dir)
        
        except KeyboardInterrupt:
            print("\n" + MESSAGES["OPERATION_CANCELLED"])
            return 1
        
        except Exception as e:
            self.interface.show_message(
                f"Fehler: {str(e)}", 
                message_type="error"
            )
            return 1
    
    def _execute_extraction(self, path: Union[str, Path]) -> int:
        """Execute file extraction operation.

        Args:
            path: Path to extract files from

        Returns:
            Exit code
        """
        # Create extractor and orchestrator
        extractor = EnhancedFileExtractor(state_manager=self.state_manager)
        orchestrator = EnhancedExtractionOrchestrator(extractor, self.state_manager)

        # Set up progress integration
        def progress_callback(current: int, total: int,
                            filepath: Union[str, Path], error: Optional[str] = None):
            self.interface.show_progress(current, total, filepath, error)
        
        # Set up keyboard handler for abort
        keyboard_handler = None
        if not self.state_manager.get_value("dry_run", False):
            keyboard_handler = KeyboardHandler(
                lambda: self.state_manager.request_abort()
            )
            keyboard_handler.start()
        
        try:
            # Execute extraction
            result = orchestrator.execute_extraction(
                source_path=path,
                confirmation_callback=self.interface.confirm_operation,
                progress_callback=progress_callback
            )
            
            # Show summary
            self.interface.show_summary(result)
            
            # Show operation statistics if available
            if "operation_id" in result:
                stats = self.state_manager.get_operation_stats(result["operation_id"])
                if stats and stats.duration:
                    self.interface.show_message(
                        f"\nOperation dauerte {stats.duration:.2f} Sekunden",
                        message_type="info"
                    )
                    if stats.files_processed > 0:
                        rate = stats.files_processed / stats.duration
                        self.interface.show_message(
                            f"Durchschnitt: {rate:.1f} Dateien/Sekunde",
                            message_type="info"
                        )
            
            # Return appropriate exit code
            if result.get("status") == "success":
                return 0
            elif result.get("status") in ["no_files", "cancelled"]:
                return 0  # Not an error
            else:
                return 1
        
        finally:
            # Stop keyboard handler
            if keyboard_handler:
                keyboard_handler.stop()
    
    def _execute_undo(self, path: Union[str, Path]) -> int:
        """Execute undo operation.

        Args:
            path: Path where history is located

        Returns:
            Exit code
        """
        # Create extractor and orchestrator
        extractor = EnhancedFileExtractor(state_manager=self.state_manager)
        orchestrator = EnhancedExtractionOrchestrator(extractor, self.state_manager)
        
        # Show operation message
        self.interface.show_message(
            "Rückgängig machen der letzten Operation...",
            message_type="info"
        )
        
        # Execute undo
        result = orchestrator.execute_undo(path)
        
        # Show result
        self.interface.show_message(
            result["message"],
            message_type="success" if result["status"] == "success" else "warning"
        )
        
        # Show statistics if available
        if result.get("restored", 0) > 0:
            self.interface.show_message(
                f"✓ {result['restored']} Dateien wiederhergestellt",
                message_type="success"
            )
            if result.get("errors", 0) > 0:
                self.interface.show_message(
                    f"✗ {result['errors']} Fehler aufgetreten",
                    message_type="error"
                )
        
        return 0 if result["status"] == "success" else 1


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