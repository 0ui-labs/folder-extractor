"""
Command line interface module.

Handles user interaction, progress display, and terminal operations.
"""
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.style import Style
from rich.table import Table

from folder_extractor.config.constants import MESSAGES, VERSION, AUTHOR
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

        # Rich integration
        self.console = Console()
        self.progress = None
        self.task_id = None

        # Theme styles
        self.success_style = Style(color="green", bold=True)
        self.error_style = Style(color="red", bold=True)
        self.warning_style = Style(color="yellow")
        self.info_style = Style(color="cyan")
    
    def show_welcome(self) -> None:
        """Show welcome message."""
        message = MESSAGES["WELCOME"].format(
            version=VERSION,
            author=AUTHOR
        )
        panel = Panel(
            message,
            title="Folder Extractor",
            border_style="cyan",
            padding=(1, 2)
        )
        self.console.print(panel)
    
    def show_message(self, message: str, message_type: str = "info") -> None:
        """Show a message to the user.

        Args:
            message: Message to display
            message_type: Type of message (info, success, error, warning)
        """
        if settings.get("quiet", False):
            return

        # Apply style based on type
        if message_type == "success":
            self.console.print(message, style=self.success_style)
        elif message_type == "error":
            self.console.print(message, style=self.error_style)
        elif message_type == "warning":
            self.console.print(message, style=self.warning_style)
        elif message_type == "info":
            self.console.print(message, style=self.info_style)
        else:
            # Unknown message types - print without styling
            self.console.print(message)
    
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
        self.console.print(MESSAGES["FILES_FOUND"].format(count=file_count))

        # Get confirmation - accept both German and English responses
        try:
            response = self.console.input(MESSAGES["CONFIRM_MOVE"]).lower().strip()
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

        # Initialize Progress on first call
        if self.progress is None:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=self.console,
                transient=True
            )
            self.progress.start()
            self.task_id = self.progress.add_task("Verschiebe Dateien...", total=total)

        # Handle errors immediately - no rate limiting for error messages
        if error:
            message = MESSAGES["MOVE_ERROR"].format(
                file=Path(filepath).name,
                error=error
            )
            # Still advance progress for error files
            self.progress.update(self.task_id, completed=current)
            self.console.print(message, style=self.error_style)
            return

        # Rate limit normal progress updates (not errors)
        current_time = time.time()
        if (current_time - self.last_progress_update) < self.progress_update_interval:
            return
        self.last_progress_update = current_time

        # Get filename and truncate if necessary
        filename = Path(filepath).name

        # Truncate filename if too long
        max_length = 40
        if len(filename) > max_length:
            filename = filename[:max_length-3] + "..."

        # Update progress
        self.progress.update(
            self.task_id,
            completed=current,
            description=f"Verschiebe: {filename}"
        )

    def finish_progress(self) -> None:
        """Stop the progress display."""
        if self.progress is not None:
            self.progress.stop()
            self.progress = None
            self.task_id = None
    
    def show_summary(self, results: dict) -> None:
        """Show operation summary.

        Args:
            results: Dictionary with operation results
        """
        # Finish progress display
        self.finish_progress()

        # Check if operation was aborted
        if results.get("aborted", False):
            self.console.print(MESSAGES["OPERATION_ABORTED"])

        # Show summary based on operation type
        if results.get("status") == "no_files":
            self.console.print(results.get("message", MESSAGES["NO_FILES_FOUND"]))

        elif results.get("status") == "cancelled":
            self.console.print(results.get("message", MESSAGES["OPERATION_CANCELLED"]))

        elif results.get("status") == "success":
            # Show move summary using rich Table
            if "moved" in results:
                table = Table(title="Zusammenfassung", border_style="cyan", show_header=True)
                table.add_column("Kategorie", style="bold")
                table.add_column("Anzahl", justify="right")

                table.add_row("✓ Verschoben", str(results.get("moved", 0)), style="green")
                table.add_row("⚠️ Duplikate", str(results.get("duplicates", 0)), style="yellow")
                table.add_row("✗ Fehler", str(results.get("errors", 0)), style="red")

                self.console.print(table)

            # Show created folders if sort by type
            if results.get("created_folders"):
                self.console.print("\nErstellte Ordner:")
                for folder in results["created_folders"]:
                    self.console.print(f"  ✓ {folder}", style="green")

            # Show removed directories
            if results.get("removed_directories", 0) > 0:
                self.console.print(MESSAGES["EMPTY_FOLDERS_REMOVED"].format(
                    count=results["removed_directories"]
                ))

            # Show undo hint
            if not settings.get("dry_run", False) and results.get("moved", 0) > 0:
                self.console.print(MESSAGES["UNDO_AVAILABLE"])


def create_console_interface() -> ConsoleInterface:
    """Create and return a console interface."""
    return ConsoleInterface()