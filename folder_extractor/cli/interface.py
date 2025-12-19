"""
Command line interface module.

Handles user interaction, progress display, and terminal operations.
"""

import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union

from rich import box
from rich.console import Console
from rich.padding import Padding
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
)
from rich.style import Style
from rich.table import Table

from folder_extractor.config.constants import AUTHOR, MESSAGES, VERSION
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
    def show_progress(
        self,
        current: int,
        total: int,
        filepath: Union[str, Path],
        error: Optional[str] = None,
    ) -> None:
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
        self.success_style = Style(color="green")
        self.error_style = Style(color="red")
        self.warning_style = Style(color="yellow")
        self.info_style = Style(color="white", dim=True)
        self.highlight_style = Style(color="blue", bold=True)

    def _print(self, renderable, style=None) -> None:
        """Print with consistent left padding."""
        padded = Padding(renderable, (0, 2))
        if style:
            self.console.print(padded, style=style)
        else:
            self.console.print(padded)

    def show_welcome(self) -> None:
        """Show welcome message."""
        # Leerzeile vor Header
        self.console.print()

        # Minimalistischer Header ohne Panel
        header = f"Folder Extractor v{VERSION}  ➜  Aufräumen von: {Path.cwd()}"
        self._print(header, style="bold blue")

        # Leerzeile nach Header
        self.console.print()

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
            self._print(message, style=self.success_style)
        elif message_type == "error":
            self._print(message, style=self.error_style)
        elif message_type == "warning":
            self._print(message, style=self.warning_style)
        elif message_type == "info":
            self._print(message, style=self.info_style)
        else:
            # Unknown message types - print without styling
            self._print(message)

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
        self._print(MESSAGES["FILES_FOUND"].format(count=file_count))

        # Get confirmation - accept both German and English responses
        try:
            response = self.console.input(MESSAGES["CONFIRM_MOVE"]).lower().strip()
            return response in ["j", "ja", "y", "yes"]
        except (KeyboardInterrupt, EOFError):
            return False

    def show_progress(
        self,
        current: int,
        total: int,
        filepath: Union[str, Path],
        error: Optional[str] = None,
    ) -> None:
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
                TextColumn(" "),  # Padding-Spalte
                SpinnerColumn("dots", style="blue"),
                TextColumn("[bold]{task.description}"),
                BarColumn(bar_width=40, style="dim white", complete_style="blue"),
                console=self.console,
                transient=True,
            )
            self.progress.start()
            self.task_id = self.progress.add_task("Verschiebe Dateien...", total=total)

        # Handle errors immediately - no rate limiting for error messages
        if error:
            message = MESSAGES["MOVE_ERROR"].format(
                file=Path(filepath).name, error=error
            )
            # Still advance progress for error files
            self.progress.update(self.task_id, completed=current)
            self._print(message, style=self.error_style)
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
            filename = filename[: max_length - 3] + "..."

        # Update progress
        desc = f"Verschiebe: {filename}"
        self.progress.update(self.task_id, completed=current, description=desc)

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
            self._print(MESSAGES["OPERATION_ABORTED"])

        # Show summary based on operation type
        if results.get("status") == "no_files":
            self._print(results.get("message", MESSAGES["NO_FILES_FOUND"]))

        elif results.get("status") == "cancelled":
            self._print(results.get("message", MESSAGES["OPERATION_CANCELLED"]))

        elif results.get("status") == "security_error":
            # Show security error with prominent styling
            self._print(results.get("message", "Sicherheitsfehler"), style=self.error_style)

        elif results.get("status") == "error":
            # Show general error
            self._print(results.get("message", "Ein Fehler ist aufgetreten"), style=self.error_style)

        elif results.get("status") == "success":
            # Show move summary using rich Table
            if "moved" in results:
                # Überschrift als separate Zeile
                self._print("Zusammenfassung", style="bold blue")
                self.console.print()  # Leerzeile

                # Minimalistische Tabelle
                table = Table(box=box.SIMPLE, show_header=True, border_style="dim white")
                table.add_column("Kategorie", style="dim white")
                table.add_column("Anzahl", justify="right", style="bold")

                moved = str(results.get("moved", 0))
                dupes = str(results.get("duplicates", 0))
                table.add_row("✓ Verschoben", moved, style="green")
                table.add_row("⚠ Duplikate", dupes, style="yellow")
                table.add_row("✗ Fehler", str(results.get("errors", 0)), style="red")

                self._print(table)

            # Show created folders if sort by type
            if results.get("created_folders"):
                self._print("\nErstellte Ordner:")
                for folder in results["created_folders"]:
                    self._print(f"  ✓ {folder}", style="green")

            # Show removed directories
            if results.get("removed_directories", 0) > 0:
                self._print(
                    MESSAGES["EMPTY_FOLDERS_REMOVED"].format(
                        count=results["removed_directories"]
                    )
                )

            # Show skipped directories (not removed)
            skipped = results.get("skipped_directories", [])
            if skipped:
                self._print(
                    MESSAGES["FOLDERS_NOT_REMOVED"].format(count=len(skipped)),
                    style="yellow",
                )
                for name, reason in skipped:
                    self._print(
                        MESSAGES["FOLDER_SKIP_REASON"].format(name=name, reason=reason),
                        style="dim white",
                    )

            # Show undo hint
            if not settings.get("dry_run", False) and results.get("moved", 0) > 0:
                self._print(MESSAGES["UNDO_AVAILABLE"])


def create_console_interface() -> ConsoleInterface:
    """Create and return a console interface."""
    return ConsoleInterface()
