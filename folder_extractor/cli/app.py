"""
Main CLI application module.

Coordinates the command line interface for Folder Extractor.
"""
import os
import sys
from typing import Optional

from folder_extractor.cli.parser import create_parser
from folder_extractor.cli.interface import (
    create_console_interface, KeyboardHandler
)
from folder_extractor.core.extractor import (
    FileExtractor, ExtractionOrchestrator
)
from folder_extractor.core.state import get_app_state, OperationContext
from folder_extractor.config.settings import configure_from_args, settings
from folder_extractor.config.constants import MESSAGES


class FolderExtractorCLI:
    """Main CLI application class."""
    
    def __init__(self):
        """Initialize CLI application."""
        self.parser = create_parser()
        self.interface = create_console_interface()
        self.app_state = get_app_state()
    
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
            
            # Get current directory
            current_dir = os.getcwd()
            
            # Show welcome message
            if not parsed_args.undo:
                self.interface.show_welcome()
            
            # Execute operation
            with OperationContext(self.app_state) as context:
                if parsed_args.undo:
                    return self._execute_undo(current_dir, context)
                else:
                    return self._execute_extraction(current_dir, context)
        
        except KeyboardInterrupt:
            print("\n" + MESSAGES["OPERATION_CANCELLED"])
            return 1
        
        except Exception as e:
            self.interface.show_message(
                f"Fehler: {str(e)}", 
                message_type="error"
            )
            return 1
    
    def _execute_extraction(self, path: str, context: OperationContext) -> int:
        """Execute file extraction operation.
        
        Args:
            path: Path to extract files from
            context: Operation context
        
        Returns:
            Exit code
        """
        # Create extractor and orchestrator
        extractor = FileExtractor(abort_signal=context.abort_signal)
        orchestrator = ExtractionOrchestrator(extractor)
        
        # Set up keyboard handler for abort
        keyboard_handler = None
        if not settings.get("dry_run", False):
            keyboard_handler = KeyboardHandler(
                lambda: self.app_state.request_abort()
            )
            keyboard_handler.start()
        
        try:
            # Execute extraction
            result = orchestrator.execute_extraction(
                source_path=path,
                confirmation_callback=self.interface.confirm_operation,
                progress_callback=self.interface.show_progress
            )
            
            # Check if aborted
            if self.app_state.is_abort_requested():
                result["aborted"] = True
            
            # Show summary
            self.interface.show_summary(result)
            
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
    
    def _execute_undo(self, path: str, context: OperationContext) -> int:
        """Execute undo operation.
        
        Args:
            path: Path where history is located
            context: Operation context
        
        Returns:
            Exit code
        """
        # Create extractor and orchestrator
        extractor = FileExtractor(abort_signal=context.abort_signal)
        orchestrator = ExtractionOrchestrator(extractor)
        
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
        
        return 0 if result["status"] == "success" else 1


def main(args: Optional[list] = None) -> int:
    """Main entry point for the CLI.
    
    Args:
        args: Optional command line arguments
    
    Returns:
        Exit code
    """
    app = FolderExtractorCLI()
    return app.run(args)


if __name__ == "__main__":
    sys.exit(main())