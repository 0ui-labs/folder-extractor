"""
Command line interface module.

Handles user interaction, progress display, and terminal operations.
"""

import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
)
from rich.style import Style

from folder_extractor.config.constants import MESSAGES, VERSION
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
        self.indexing_spinner = None
        self._archive_spinner = None

        # Theme styles (minimalist - no bold/dim modifiers)
        self.success_style = Style(color="green")
        self.error_style = Style(color="red")
        self.warning_style = Style(color="yellow")
        self.info_style = Style(color="white")
        self.highlight_style = Style(color="blue")
        self.dedupe_style = Style(color="cyan")

    def _print(self, renderable, style=None) -> None:
        """Print directly to console."""
        if style:
            self.console.print(renderable, style=style)
        else:
            self.console.print(renderable)

    def show_welcome(self) -> None:
        """Show welcome message in minimalist Unix style."""
        header = f"Folder Extractor v{VERSION}\n-----------------------"
        self.console.print(header, style="blue")

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

        # Initialize Progress on first call (minimalist - no padding column)
        if self.progress is None:
            self.progress = Progress(
                SpinnerColumn("dots", style="blue"),
                TextColumn("{task.description}"),
                BarColumn(bar_width=40, complete_style="blue"),
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

    def show_indexing_spinner(self) -> None:
        """Show spinner during index building for global deduplication."""
        if settings.get("quiet", False):
            return

        self.indexing_spinner = Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            console=self.console,
            transient=True,
        )
        self.indexing_spinner.start()
        self.indexing_spinner.add_task(MESSAGES["INDEXING_TARGET"], total=None)

    def hide_indexing_spinner(self) -> None:
        """Hide the indexing spinner."""
        if self.indexing_spinner is not None:
            self.indexing_spinner.stop()
            self.indexing_spinner = None

    def show_archive_progress(
        self,
        archive_name: str,
        status: str,
        count: int = 0,
        error: Optional[str] = None,
    ) -> None:
        """Show archive extraction progress.

        Args:
            archive_name: Name of the archive being processed
            status: Current status (extracting, extracted, error,
                finish, security_error)
            count: Number of files extracted (for extracted status)
            error: Error message (for error status)
        """
        if settings.get("quiet", False):
            return

        if status == "extracting":
            # Start spinner for extraction
            self._archive_spinner = Progress(
                SpinnerColumn("arc", style="blue"),
                TextColumn("{task.description}"),
                console=self.console,
                transient=True,
            )
            self._archive_spinner.start()
            message = MESSAGES["EXTRACTING_ARCHIVE"].format(archive=archive_name)
            self._archive_spinner.add_task(message, total=None)

        elif status == "finish":
            # Stop the archive spinner
            if hasattr(self, "_archive_spinner") and self._archive_spinner is not None:
                self._archive_spinner.stop()
                self._archive_spinner = None

        elif status == "extracted":
            # Stop spinner and show success
            if hasattr(self, "_archive_spinner") and self._archive_spinner is not None:
                self._archive_spinner.stop()
                self._archive_spinner = None
            message = MESSAGES["ARCHIVE_EXTRACTED"].format(
                archive=archive_name, count=count
            )
            self._print(message, style=self.success_style)

        elif status == "error":
            # Stop spinner and show error
            if hasattr(self, "_archive_spinner") and self._archive_spinner is not None:
                self._archive_spinner.stop()
                self._archive_spinner = None
            message = MESSAGES["ARCHIVE_EXTRACT_ERROR"].format(
                archive=archive_name, error=error or "Unbekannter Fehler"
            )
            self._print(message, style=self.error_style)

        elif status == "security_error":
            # Stop spinner and show security warning
            if hasattr(self, "_archive_spinner") and self._archive_spinner is not None:
                self._archive_spinner.stop()
                self._archive_spinner = None
            message = MESSAGES["ARCHIVE_SECURITY_ERROR"].format(archive=archive_name)
            self._print(message, style=self.warning_style)

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
            msg = results.get("message", "Sicherheitsfehler")
            self._print(msg, style=self.error_style)

        elif results.get("status") == "error":
            # Show general error
            msg = results.get("message", "Ein Fehler ist aufgetreten")
            self._print(msg, style=self.error_style)

        elif results.get("status") == "success":
            # Show move summary as plain text (minimalist Unix style)
            if "moved" in results:
                self.console.print("Zusammenfassung:")
                moved = results.get("moved", 0)
                errors = results.get("errors", 0)
                self.console.print(
                    f"[green][+][/green] Verschoben: [green]{moved}[/green]"
                )

                # Show archive extraction statistics
                archives_extracted = results.get("archives_extracted", 0)
                archives_deleted = results.get("archives_deleted", 0)
                if archives_extracted > 0:
                    self.console.print(
                        f"[blue][↓][/blue] Entpackt:   "
                        f"[blue]{archives_extracted}[/blue]"
                    )
                if archives_deleted > 0:
                    self.console.print(
                        f"[yellow][-][/yellow] Archive gelöscht: "
                        f"[yellow]{archives_deleted}[/yellow]"
                    )

                # Get duplicate counts - prefer new granular keys
                name_dupes = results.get("name_duplicates", 0)
                content_dupes = results.get("content_duplicates", 0)
                global_dupes = results.get("global_duplicates", 0)

                # Check if we have the new granular duplicate types
                dup_keys = [
                    "name_duplicates",
                    "content_duplicates",
                    "global_duplicates",
                ]
                has_new_keys = any(key in results for key in dup_keys)

                if has_new_keys:
                    # Show separate duplicate categories (only if > 0)
                    if name_dupes > 0:
                        msg = MESSAGES["DEDUP_NAME_DUPLICATES"]
                        self.console.print(
                            f"[yellow][!][/yellow] {msg}: [yellow]{name_dupes}[/yellow]"
                        )
                    if content_dupes > 0:
                        msg = MESSAGES["DEDUP_CONTENT_DUPLICATES"]
                        self.console.print(
                            f"[cyan][~][/cyan] {msg}: [cyan]{content_dupes}[/cyan]"
                        )
                    if global_dupes > 0:
                        msg = MESSAGES["DEDUP_GLOBAL_DUPLICATES"]
                        val = f"[magenta]{global_dupes}[/magenta]"
                        self.console.print(f"[magenta][≡][/magenta] {msg}: {val}")
                else:
                    # Backward compatibility: show old-style duplicates
                    dupes = results.get("duplicates", 0)
                    if dupes > 0:
                        self.console.print(
                            f"[yellow][!][/yellow] Duplikate: [yellow]{dupes}[/yellow]"
                        )

                self.console.print(f"[red][x][/red] Fehler:     [red]{errors}[/red]")

            # Show created folders if sort by type
            if results.get("created_folders"):
                self.console.print("\nErstellte Ordner:")
                for folder in results["created_folders"]:
                    self.console.print(f"  [green]✓[/green] {folder}")

            # Show removed directories
            if results.get("removed_directories", 0) > 0:
                self.console.print(
                    MESSAGES["EMPTY_FOLDERS_REMOVED"].format(
                        count=results["removed_directories"]
                    )
                )

            # Show skipped directories (not removed)
            skipped = results.get("skipped_directories", [])
            if skipped:
                self.console.print(
                    MESSAGES["FOLDERS_NOT_REMOVED"].format(count=len(skipped)),
                    style=self.warning_style,
                )
                for name, reason in skipped:
                    self.console.print(
                        MESSAGES["FOLDER_SKIP_REASON"].format(name=name, reason=reason),
                        style=self.info_style,
                    )

            # Show undo hint
            if not settings.get("dry_run", False) and results.get("moved", 0) > 0:
                self.console.print(MESSAGES["UNDO_AVAILABLE"])

    def show_watch_status(self, path: Union[str, Path]) -> None:
        """Show watch mode status message.

        Args:
            path: Path being watched
        """
        if settings.get("quiet", False):
            return

        message = MESSAGES["WATCH_STARTING"].format(path=path)
        self._print(message, style=self.highlight_style)

    def show_watch_event(
        self,
        event_type: str,
        filename: str,
        status: str = "incoming",
        error: Optional[str] = None,
    ) -> None:
        """Show watch mode event notification.

        Args:
            event_type: Type of event (created, moved)
            filename: Name of the file
            status: Event status (incoming, waiting, analyzing, sorted, error)
            error: Optional error message for error status
        """
        if settings.get("quiet", False):
            return

        # Get timestamp
        timestamp = datetime.now().strftime("[%H:%M:%S]")

        # Build message based on status
        if status == "incoming":
            msg = MESSAGES["WATCH_FILE_INCOMING"].format(file=filename)
            style = self.info_style
        elif status == "waiting":
            msg = MESSAGES["WATCH_FILE_WAITING"].format(file=filename)
            style = self.warning_style
        elif status == "analyzing":
            msg = MESSAGES["WATCH_FILE_ANALYZING"].format(file=filename)
            style = self.info_style
        elif status == "sorted":
            msg = MESSAGES["WATCH_FILE_SORTED"].format(file=filename)
            style = self.success_style
        elif status == "error":
            msg = MESSAGES["WATCH_FILE_ERROR"].format(file=filename, error=error or "")
            style = self.error_style
        else:
            msg = f"{filename}"
            style = self.info_style

        self._print(f"{timestamp} {msg}", style=style)

    def show_watch_stopped(self) -> None:
        """Show watch mode stopped message."""
        if settings.get("quiet", False):
            return

        self._print(MESSAGES["WATCH_STOPPED"], style=self.info_style)

    def show_smart_watch_status(self, profile: dict) -> None:
        """Show smart watch mode status banner with configuration details.

        Displays the watch configuration including path, folder structure,
        categories, file types, recursion settings, and exclusions.

        Args:
            profile: Smart watch profile dictionary containing:
                - path: Watch directory path
                - folder_structure: Target path template
                - categories: List of AI categories (optional)
                - file_types: List of file extensions to filter (optional)
                - recursive: Whether to watch recursively (optional)
                - exclude_subfolders: Folders to exclude (optional)
        """
        if settings.get("quiet", False):
            return

        # Banner header
        self._print(MESSAGES["SMART_WATCH_BANNER"], style=self.highlight_style)

        # Watch path
        path = profile.get("path", "")
        self._print(MESSAGES["SMART_WATCH_PATH"].format(path=path))

        # Folder structure
        structure = profile.get("folder_structure", "{category}")
        self._print(MESSAGES["SMART_WATCH_STRUCTURE"].format(structure=structure))

        # Categories (show "Standard" if empty or not provided)
        categories = profile.get("categories", [])
        cat_str = ", ".join(categories) if categories else "Standard"
        self._print(MESSAGES["SMART_WATCH_CATEGORIES"].format(categories=cat_str))

        # File types (only show if not empty)
        file_types = profile.get("file_types")
        if file_types:
            ft_str = ", ".join(file_types)
            self._print(MESSAGES["SMART_WATCH_FILE_TYPES"].format(file_types=ft_str))

        # Recursive status
        recursive = profile.get("recursive", False)
        recursive_str = "Ja" if recursive else "Nein"
        self._print(MESSAGES["SMART_WATCH_RECURSIVE"].format(recursive=recursive_str))

        # Exclusions (only show if not empty)
        exclusions = profile.get("exclude_subfolders", [])
        if exclusions:
            excl_str = ", ".join(exclusions)
            self._print(MESSAGES["SMART_WATCH_EXCLUSIONS"].format(exclusions=excl_str))


def create_console_interface() -> ConsoleInterface:
    """Create and return a console interface."""
    return ConsoleInterface()
