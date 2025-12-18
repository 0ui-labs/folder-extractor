"""
Command line interface module.

Handles user interaction, progress display, and terminal operations.
"""
import sys
import threading
import time
from pathlib import Path
from typing import Optional, Callable, Any, Union
from abc import ABC, abstractmethod

from folder_extractor.config.constants import (
    MESSAGES, VERSION, AUTHOR, TERMINAL_CLEAR_LINE
)
from folder_extractor.utils.terminal import (
    Color, clear_line, format_progress_bar, 
    save_terminal_settings, restore_terminal_settings,
    set_raw_mode
)
from folder_extractor.config.settings import settings


class IUserInterface(ABC):
    """Interface for user interaction."""
    
    @abstractmethod
    def show_welcome(self) -> None:
        """Show welcome message."""
        pass
    
    @abstractmethod
    def show_message(self, message: str, message_type: str = "info") -> None:
        """Show a message to the user."""
        pass
    
    @abstractmethod
    def confirm_operation(self, file_count: int) -> bool:
        """Get user confirmation for operation."""
        pass
    
    @abstractmethod
    def show_progress(self, current: int, total: int,
                     filepath: Union[str, Path], error: Optional[str] = None) -> None:
        """Show operation progress."""
        pass
    
    @abstractmethod
    def show_summary(self, results: dict) -> None:
        """Show operation summary."""
        pass


class ConsoleInterface(IUserInterface):
    """Console-based user interface implementation."""
    
    def __init__(self):
        """Initialize console interface."""
        self.last_progress_update = 0
        self.progress_update_interval = 0.1
    
    def show_welcome(self) -> None:
        """Show welcome message."""
        message = MESSAGES["WELCOME"].format(
            version=VERSION,
            author=AUTHOR
        )
        print(message)
    
    def show_message(self, message: str, message_type: str = "info") -> None:
        """Show a message to the user.
        
        Args:
            message: Message to display
            message_type: Type of message (info, success, error, warning)
        """
        if settings.get("quiet", False):
            return
        
        # Apply color based on type
        if message_type == "success":
            message = Color.success(message)
        elif message_type == "error":
            message = Color.error(message)
        elif message_type == "warning":
            message = Color.warning(message)
        elif message_type == "info":
            message = Color.info(message)
        
        print(message)
    
    def confirm_operation(self, file_count: int) -> bool:
        """Get user confirmation for operation.
        
        Args:
            file_count: Number of files to be processed
        
        Returns:
            True if user confirms, False otherwise
        """
        if settings.get("dry_run", False):
            return True  # No confirmation needed for dry run
        
        if not settings.get("confirm_operations", True):
            return True  # Auto-confirm if disabled
        
        # Show file count
        print(MESSAGES["FILES_FOUND"].format(count=file_count))
        
        # Get confirmation
        try:
            response = input(MESSAGES["CONFIRM_MOVE"]).lower().strip()
            return response in ['j', 'ja', 'y', 'yes']
        except (KeyboardInterrupt, EOFError):
            return False
    
    def show_progress(self, current: int, total: int,
                     filepath: Union[str, Path], error: Optional[str] = None) -> None:
        """Show operation progress.

        Args:
            current: Current file number
            total: Total number of files
            filepath: Current file path
            error: Optional error message
        """
        if settings.get("quiet", False):
            return
        
        # Rate limit updates
        current_time = time.time()
        if (current_time - self.last_progress_update) < self.progress_update_interval:
            return
        self.last_progress_update = current_time
        
        # Clear previous line
        clear_line()
        
        # Format message
        if error:
            message = MESSAGES["MOVE_ERROR"].format(
                file=Path(filepath).name,
                error=error
            )
            print(message)
        else:
            # Show progress bar
            progress_bar = format_progress_bar(current, total, width=30)
            filename = Path(filepath).name
            
            # Truncate filename if too long
            max_length = 40
            if len(filename) > max_length:
                filename = filename[:max_length-3] + "..."
            
            print(f"{progress_bar} {filename}", end='', flush=True)
    
    def show_summary(self, results: dict) -> None:
        """Show operation summary.
        
        Args:
            results: Dictionary with operation results
        """
        # Clear progress line
        clear_line()
        
        # Check if operation was aborted
        if results.get("aborted", False):
            print(MESSAGES["OPERATION_ABORTED"])
        
        # Show summary based on operation type
        if results.get("status") == "no_files":
            print(results.get("message", MESSAGES["NO_FILES_FOUND"]))
        
        elif results.get("status") == "cancelled":
            print(results.get("message", MESSAGES["OPERATION_CANCELLED"]))
        
        elif results.get("status") == "success":
            # Show move summary
            if "moved" in results:
                summary = MESSAGES["MOVE_SUMMARY"].format(
                    moved=results.get("moved", 0),
                    duplicates=results.get("duplicates", 0),
                    errors=results.get("errors", 0)
                )
                print(summary)
            
            # Show created folders if sort by type
            if results.get("created_folders"):
                print("\nErstellte Ordner:")
                for folder in results["created_folders"]:
                    print(f"  ✓ {folder}")
            
            # Show removed directories
            if results.get("removed_directories", 0) > 0:
                print(MESSAGES["EMPTY_FOLDERS_REMOVED"].format(
                    count=results["removed_directories"]
                ))
            
            # Show undo hint
            if not settings.get("dry_run", False) and results.get("moved", 0) > 0:
                print(MESSAGES["UNDO_AVAILABLE"])


class KeyboardHandler:
    """Handles keyboard input for abort functionality."""
    
    def __init__(self, abort_callback: Callable[[], None]):
        """Initialize keyboard handler.
        
        Args:
            abort_callback: Function to call when ESC is pressed
        """
        self.abort_callback = abort_callback
        self.running = False
        self.thread = None
        self.terminal_settings = None
    
    def start(self) -> None:
        """Start listening for keyboard input."""
        if sys.platform == 'win32':
            # Windows not supported for now
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
        
        # Show hint
        print(MESSAGES["ESC_TO_ABORT"])
    
    def stop(self) -> None:
        """Stop listening for keyboard input."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=0.5)
    
    def _listen(self) -> None:
        """Listen for ESC key press."""
        try:
            # Save terminal settings
            self.terminal_settings = save_terminal_settings()
            
            # Set raw mode
            if not set_raw_mode():
                return
            
            # Listen for keys - requires actual terminal interaction
            while self.running:  # pragma: no cover
                try:
                    if sys.stdin.isatty():
                        # Read one character
                        char = sys.stdin.read(1)

                        # Check for ESC (ASCII 27)
                        if ord(char) == 27:
                            self.abort_callback()
                            break
                except Exception:
                    pass

                time.sleep(0.01)

        finally:
            # Restore terminal settings
            if self.terminal_settings:  # pragma: no cover
                restore_terminal_settings(self.terminal_settings)


def create_console_interface() -> ConsoleInterface:
    """Create and return a console interface."""
    return ConsoleInterface()