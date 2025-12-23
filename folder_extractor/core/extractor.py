"""
Enhanced extractor module with state management integration.

Coordinates file discovery, filtering, and moving operations
with integrated progress tracking and state management.
"""

from abc import ABC, abstractmethod
from contextlib import suppress
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from folder_extractor.config.constants import HISTORY_FILE_NAME, MESSAGES
from folder_extractor.config.settings import settings
from folder_extractor.core.file_discovery import FileDiscovery, IFileDiscovery
from folder_extractor.core.file_operations import (
    FileMover,
    FileOperations,
    HistoryManager,
    IFileOperations,
)
from folder_extractor.core.progress import ProgressInfo, ProgressTracker
from folder_extractor.core.state_manager import (
    IStateManager,
    ManagedOperation,
    get_state_manager,
)
from folder_extractor.utils.path_validators import is_safe_path

# Type alias for progress callback: (current, total, filename, error) -> None
ProgressCallback = Optional[Callable[[int, int, str, Optional[str]], None]]


class ExtractionError(Exception):
    """Base exception for extraction errors."""

    pass


class SecurityError(ExtractionError):
    """Raised when security validation fails."""

    pass


class IEnhancedExtractor(ABC):
    """Interface for enhanced file extraction with state management."""

    @abstractmethod
    def validate_security(self, path: Union[str, Path]) -> None:
        """Validate that the path is safe for operations."""
        pass

    @abstractmethod
    def discover_files(self, path: Union[str, Path]) -> List[str]:
        """Discover files based on current settings."""
        pass

    @abstractmethod
    def extract_files(
        self,
        files: List[str],
        destination: Union[str, Path],
        operation_id: Optional[str] = None,
        progress_callback: ProgressCallback = None,
    ) -> Dict[str, Any]:
        """Extract files to destination with operation tracking."""
        pass

    @abstractmethod
    def undo_last_operation(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Undo the last operation."""
        pass


class EnhancedFileExtractor(IEnhancedExtractor):
    """Enhanced file extractor with integrated state and progress tracking."""

    def __init__(
        self,
        file_discovery: Optional[IFileDiscovery] = None,
        file_operations: Optional[IFileOperations] = None,
        state_manager: Optional[IStateManager] = None,
    ):
        """Initialize enhanced extractor.

        Args:
            file_discovery: File discovery implementation
            file_operations: File operations implementation
            state_manager: State manager implementation
        """
        self.file_discovery = file_discovery or FileDiscovery()
        self.file_operations = file_operations or FileOperations()
        self.state_manager = state_manager or get_state_manager()
        self.history_manager = HistoryManager()

    def validate_security(self, path: Union[str, Path]) -> None:
        """Validate that the path is safe for operations."""
        path = Path(path)
        path_str = str(path)
        if not is_safe_path(path_str):
            raise SecurityError(MESSAGES["SECURITY_ERROR"].format(path=path_str))

    def discover_files(self, path: Union[str, Path]) -> List[str]:
        """Discover files based on current settings."""
        path = Path(path)
        files = self.file_discovery.find_files(
            directory=str(path),
            max_depth=settings.get("max_depth", 0),
            file_type_filter=settings.get("file_type_filter"),
            include_hidden=settings.get("include_hidden", False),
        )

        # Apply domain filter if set
        domain_filter = settings.get("domain_filter")
        if domain_filter:
            filtered_files = []
            for filepath in files:
                # Check if it's a weblink file
                file_path = Path(filepath)
                if file_path.suffix.lower() in [".url", ".webloc"]:
                    # Only include if domain matches
                    domain_matches = self.file_discovery.check_weblink_domain(
                        filepath, domain_filter
                    )
                    if domain_matches:
                        filtered_files.append(filepath)
                else:
                    # Non-weblink files pass through
                    filtered_files.append(filepath)
            files = filtered_files

        return files

    def extract_files(
        self,
        files: List[str],
        destination: Union[str, Path],
        operation_id: Optional[str] = None,
        progress_callback: ProgressCallback = None,
        indexing_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Extract files to destination with operation tracking.

        Args:
            files: List of files to extract
            destination: Destination directory
            operation_id: Optional operation ID for tracking
            progress_callback: Optional progress callback
            indexing_callback: Optional callback for indexing start/end events

        Returns:
            Dictionary with extraction results
        """
        destination = Path(destination)
        destination_str = str(destination)

        results = {
            "moved": 0,
            "skipped": 0,
            "duplicates": 0,
            "name_duplicates": 0,
            "content_duplicates": 0,
            "global_duplicates": 0,
            "errors": 0,
            "created_folders": [],
            "history": [],
        }

        # Get abort signal from state manager
        abort_signal = self.state_manager.get_abort_signal()

        # Create file mover with abort signal and indexing callback
        file_mover = FileMover(self.file_operations, abort_signal, indexing_callback)

        # Create progress tracker
        def update_progress(info: ProgressInfo):
            # Update operation stats in state manager
            if operation_id:
                self.state_manager.update_operation_stats(
                    operation_id,
                    files_processed=1,
                    files_moved=1 if not info.error else 0,
                    errors=1 if info.error else 0,
                )

            # Call external progress callback if provided
            if progress_callback:
                progress_callback(
                    info.current, info.total, info.current_file or "", info.error
                )

        progress_tracker = ProgressTracker(callback=update_progress)
        progress_tracker.start(len(files))

        # Process files
        if settings.get("sort_by_type", False):
            # Create folder override callback for domain filter
            domain_filter = settings.get("domain_filter")
            folder_override = None
            if domain_filter:
                # When domain filter is active, use domain as folder name for weblinks
                def folder_override(filepath):
                    file_path = Path(filepath)
                    if file_path.suffix.lower() in [".url", ".webloc"]:
                        domain = self.file_discovery.extract_weblink_domain(filepath)
                        if domain:
                            return domain
                    return None  # Use default folder determination

            # Move files sorted by type
            deduplicate = settings.get("deduplicate", False)
            global_dedup = settings.get("global_dedup", False)
            if global_dedup:
                # Global deduplication - checks against entire destination tree
                (
                    moved,
                    errors,
                    duplicates,
                    content_duplicates,
                    global_duplicates,
                    history,
                    created_folders,
                ) = file_mover.move_files_sorted(
                    files=files,
                    destination=destination_str,
                    dry_run=settings.get("dry_run", False),
                    progress_callback=lambda c, _t, f, e=None: progress_tracker.update(
                        c, f, e
                    ),
                    folder_override_callback=folder_override,
                    deduplicate=deduplicate,
                    global_dedup=True,
                )
            elif deduplicate:
                (
                    moved,
                    errors,
                    duplicates,
                    content_duplicates,
                    history,
                    created_folders,
                ) = file_mover.move_files_sorted(
                    files=files,
                    destination=destination_str,
                    dry_run=settings.get("dry_run", False),
                    progress_callback=lambda c, _t, f, e=None: progress_tracker.update(
                        c, f, e
                    ),
                    folder_override_callback=folder_override,
                    deduplicate=True,
                )
                global_duplicates = 0
            else:

                def progress_cb(c, _t, f, e=None):
                    progress_tracker.update(c, f, e)

                moved, errors, duplicates, history, created_folders = (
                    file_mover.move_files_sorted(
                        files=files,
                        destination=destination_str,
                        dry_run=settings.get("dry_run", False),
                        progress_callback=progress_cb,
                        folder_override_callback=folder_override,
                    )
                )
                content_duplicates = 0
                global_duplicates = 0
            move_results = {
                "moved": moved,
                "errors": errors,
                "duplicates": duplicates,
                # Map duplicates to name_duplicates for UI
                "name_duplicates": duplicates,
                "content_duplicates": content_duplicates,
                "global_duplicates": global_duplicates,
                "history": history,
                "created_folders": created_folders,
            }
        else:
            # Move files flat
            deduplicate = settings.get("deduplicate", False)
            global_dedup = settings.get("global_dedup", False)
            if global_dedup:
                # Global deduplication - checks against entire destination tree
                (
                    moved,
                    errors,
                    duplicates,
                    content_duplicates,
                    global_duplicates,
                    history,
                ) = file_mover.move_files(
                    files=files,
                    destination=destination_str,
                    dry_run=settings.get("dry_run", False),
                    progress_callback=lambda c, _t, f, e=None: progress_tracker.update(
                        c, f, e
                    ),
                    deduplicate=deduplicate,
                    global_dedup=True,
                )
            elif deduplicate:
                (
                    moved,
                    errors,
                    duplicates,
                    content_duplicates,
                    history,
                ) = file_mover.move_files(
                    files=files,
                    destination=destination_str,
                    dry_run=settings.get("dry_run", False),
                    progress_callback=lambda c, _t, f, e=None: progress_tracker.update(
                        c, f, e
                    ),
                    deduplicate=True,
                )
                global_duplicates = 0
            else:

                def progress_cb(c, _t, f, e=None):
                    progress_tracker.update(c, f, e)

                (moved, errors, duplicates, history) = file_mover.move_files(
                    files=files,
                    destination=destination_str,
                    dry_run=settings.get("dry_run", False),
                    progress_callback=progress_cb,
                )
                content_duplicates = 0
                global_duplicates = 0
            move_results = {
                "moved": moved,
                "errors": errors,
                "duplicates": duplicates,
                # Map duplicates to name_duplicates for UI
                "name_duplicates": duplicates,
                "content_duplicates": content_duplicates,
                "global_duplicates": global_duplicates,
                "history": history,
                "created_folders": [],
            }

        # Finish progress tracking
        progress_tracker.finish()

        # Update results
        results.update(move_results)

        # Save history if not dry run and there are history entries
        # (includes both moved files and content duplicates)
        if not settings.get("dry_run", False) and move_results["history"]:
            self.history_manager.save_history(move_results["history"], destination_str)

        # Check if aborted
        if abort_signal.is_set():
            results["aborted"] = True

        # Clean up empty directories if not dry run and not filtering by file type
        # Note: sort_by_type should still clean up empty source directories
        if (
            not settings.get("dry_run", False)
            and not settings.get("file_type_filter")
            and results["moved"] > 0
        ):
            # Import the function we need
            from folder_extractor.utils.file_validators import get_temp_files_list

            # Remove empty directories
            removal_result = self._remove_empty_directories(
                destination, get_temp_files_list()
            )
            results["removed_directories"] = removal_result["removed"]

            # Filter out created type folders from skipped list
            # (they're expected to have content)
            created_folder_names = set(results.get("created_folders", []))
            results["skipped_directories"] = [
                (name, reason)
                for name, reason in removal_result["skipped"]
                if name not in created_folder_names
            ]

        return results

    def _remove_empty_directories(
        self, path: Union[str, Path], temp_files: list
    ) -> Dict[str, Any]:
        """Remove empty directories after extraction.

        Args:
            path: Root path
            temp_files: List of temporary files to ignore

        Returns:
            Dictionary with 'removed' count and 'skipped' list of (path, reason)
        """
        path = Path(path)
        removed_count = 0
        skipped_dirs = []

        # Collect all subdirectories, sorted by depth (deepest first)
        directories = sorted(
            [d for d in path.rglob("*") if d.is_dir()],
            key=lambda x: len(x.parts),
            reverse=True,
        )

        for directory in directories:
            # Skip root directory (defensive - rglob('*') doesn't include root)
            if directory == path:  # pragma: no cover
                continue

            # Get directory contents
            try:
                dir_contents = list(directory.iterdir())
            except OSError as e:
                skipped_dirs.append((str(directory.name), f"Zugriffsfehler: {e}"))
                continue

            # Filter out temp files and hidden files if not included
            filtered_contents = []
            for item in dir_contents:
                if item.is_file():
                    if item.name in temp_files:
                        continue
                    if not settings.get(
                        "include_hidden", False
                    ) and item.name.startswith("."):
                        continue
                filtered_contents.append(item)

            # Check if directory is effectively empty (no files or subdirs)
            has_files = any(item.is_file() for item in filtered_contents)
            has_dirs = any(item.is_dir() for item in filtered_contents)

            if not has_files and not has_dirs:
                try:
                    # Delete hidden/temp files that were filtered out before rmdir
                    # But protect the history file!
                    for item in dir_contents:
                        if item not in filtered_contents and item.is_file():
                            # Never delete the history file
                            if item.name == HISTORY_FILE_NAME:
                                continue
                            with suppress(OSError):
                                item.unlink()

                    directory.rmdir()
                    removed_count += 1
                except OSError as e:
                    skipped_dirs.append((str(directory.name), f"Löschfehler: {e}"))
            else:
                # Directory is not empty - collect reason
                file_count = sum(1 for item in filtered_contents if item.is_file())
                dir_count = sum(1 for item in filtered_contents if item.is_dir())
                reasons = []
                if file_count > 0:
                    reasons.append(f"{file_count} Datei(en)")
                if dir_count > 0:
                    reasons.append(f"{dir_count} Unterordner")
                reason_str = f"enthält {', '.join(reasons)}"
                skipped_dirs.append((str(directory.name), reason_str))

        return {"removed": removed_count, "skipped": skipped_dirs}

    def undo_last_operation(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Undo the last operation.

        Args:
            path: Path where history is located

        Returns:
            Dictionary with undo results
        """
        path = Path(path)
        path_str = str(path)

        # Load history
        history_data = self.history_manager.load_history(path_str)

        if not history_data or "operationen" not in history_data:
            return {
                "status": "no_history",
                "message": MESSAGES["UNDO_NO_HISTORY"],
                "restored": 0,
            }

        # Get operations from history
        operations = history_data["operationen"]

        # Create operation for undo
        with ManagedOperation(self.state_manager, "undo") as op:
            restored = 0
            errors = 0

            # Create progress tracker
            progress_tracker = ProgressTracker()
            progress_tracker.start(len(operations))

            # Process history in reverse
            for _i, entry in enumerate(reversed(operations)):
                if op.abort_signal.is_set():
                    break

                try:
                    # Get original path and ensure parent directory exists
                    original_path = Path(
                        entry.get("original_pfad", entry.get("original_path"))
                    )
                    original_path.parent.mkdir(parents=True, exist_ok=True)

                    # Undo the move
                    self.file_operations.move_file(
                        entry.get("neuer_pfad", entry.get("new_path")),
                        str(original_path),
                    )
                    restored += 1

                    # Update progress
                    original_path_entry = entry.get(
                        "original_pfad", entry.get("original_path")
                    )
                    progress_tracker.increment(original_path_entry)
                    op.update_stats(files_processed=1, files_moved=1)

                except Exception as e:
                    errors += 1
                    original_path_entry = entry.get(
                        "original_pfad", entry.get("original_path")
                    )
                    progress_tracker.increment(original_path_entry, error=str(e))
                    op.update_stats(files_processed=1, errors=1)

            # Finish progress
            progress_tracker.finish()

            # Clear history after successful undo
            if restored > 0 and not op.abort_signal.is_set():
                self.history_manager.delete_history(path_str)

            # Clean up empty directories after undo (e.g., empty type folders)
            removed_dirs = 0
            if restored > 0 and not op.abort_signal.is_set():
                from folder_extractor.utils.file_validators import get_temp_files_list

                removal_result = self._remove_empty_directories(
                    path, get_temp_files_list()
                )
                removed_dirs = removal_result["removed"]

            return {
                "status": "success" if restored > 0 else "failed",
                "message": MESSAGES["UNDO_SUMMARY"].format(count=restored),
                "restored": restored,
                "errors": errors,
                "aborted": op.abort_signal.is_set(),
                "removed_directories": removed_dirs,
            }


class EnhancedExtractionOrchestrator:
    """Orchestrates the complete extraction workflow with state management."""

    def __init__(
        self,
        extractor: IEnhancedExtractor,
        state_manager: Optional[IStateManager] = None,
    ):
        """Initialize orchestrator.

        Args:
            extractor: Extractor implementation
            state_manager: State manager implementation
        """
        self.extractor = extractor
        self.state_manager = state_manager or get_state_manager()

    def execute_extraction(
        self,
        source_path: Union[str, Path],
        confirmation_callback: Optional[Callable[[int], bool]] = None,
        progress_callback: ProgressCallback = None,
        indexing_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Execute complete extraction workflow.

        Args:
            source_path: Source directory path
            confirmation_callback: Optional callback for user confirmation
            progress_callback: Optional callback for progress updates
            indexing_callback: Optional callback for indexing start/end events

        Returns:
            Dictionary with operation results
        """
        source_path = Path(source_path)

        # Start operation
        with ManagedOperation(self.state_manager, "extraction") as op:
            try:
                # Validate security
                self.extractor.validate_security(source_path)

                # Discover files
                files = self.extractor.discover_files(source_path)

                if not files:
                    return {
                        "status": "no_files",
                        "message": MESSAGES["NO_FILES_FOUND"],
                        "files_found": 0,
                    }

                # Get confirmation if callback provided
                if (
                    confirmation_callback
                    and not settings.get("dry_run", False)
                    and not confirmation_callback(len(files))
                ):
                    return {
                        "status": "cancelled",
                        "message": MESSAGES["OPERATION_CANCELLED"],
                        "files_found": len(files),
                    }

                # Reset timer after user confirmation - measure only actual work
                op.reset_start_time()

                # Note: Progress tracking is handled directly in extract_files
                # via the progress tracker callback, not through state manager listeners

                # Extract files
                results = self.extractor.extract_files(
                    files,
                    source_path,
                    op.operation_id,
                    progress_callback,
                    indexing_callback,
                )

                # Add metadata
                results["status"] = "success"
                results["files_found"] = len(files)
                results["operation_id"] = op.operation_id

                # Get final stats
                stats = self.state_manager.get_operation_stats(op.operation_id)
                if stats:
                    results["duration"] = stats.duration
                    results["success_rate"] = stats.success_rate

                return results

            except SecurityError as e:
                return {"status": "security_error", "message": str(e), "error": True}

            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Fehler: {str(e)}",
                    "error": True,
                }

    def execute_undo(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Execute undo operation.

        Args:
            path: Path where history is located

        Returns:
            Dictionary with undo results
        """
        path = Path(path)
        return self.extractor.undo_last_operation(path)
