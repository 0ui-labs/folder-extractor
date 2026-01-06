"""
Enhanced extractor module with state management integration.

Coordinates file discovery, filtering, and moving operations
with integrated progress tracking and state management.
"""

import shutil
import tempfile
from abc import ABC, abstractmethod
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from folder_extractor.core.archives import IArchiveHandler

from folder_extractor.config.constants import HISTORY_FILE_NAME, MESSAGES
from folder_extractor.config.settings import Settings
from folder_extractor.core.archives import SecurityError
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
    StateManager,
)
from folder_extractor.utils.path_validators import is_safe_path

# Type alias for progress callback: (current, total, filename, error) -> None
ProgressCallback = Optional[Callable[[int, int, str, Optional[str]], None]]


class ExtractionError(Exception):
    """Base exception for extraction errors."""

    ...


class IEnhancedExtractor(ABC):
    """Interface for enhanced file extraction with state management.

    Attributes:
        settings: Settings instance for configuration
    """

    settings: Settings

    @abstractmethod
    def validate_security(self, path: Path) -> None:
        """Validate that the path is safe for operations."""
        ...

    @abstractmethod
    def discover_files(self, path: Path) -> List[str]:
        """Discover files based on current settings."""
        ...

    @abstractmethod
    def extract_files(
        self,
        files: List[str],
        destination: Path,
        operation_id: Optional[str] = None,
        progress_callback: ProgressCallback = None,
        indexing_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Extract files to destination with operation tracking."""
        ...

    @abstractmethod
    def undo_last_operation(self, path: Path) -> Dict[str, Any]:
        """Undo the last operation."""
        ...


class EnhancedFileExtractor(IEnhancedExtractor):
    """Enhanced file extractor with integrated state and progress tracking."""

    def __init__(
        self,
        settings: Settings,
        file_discovery: Optional[IFileDiscovery] = None,
        file_operations: Optional[IFileOperations] = None,
        state_manager: Optional[IStateManager] = None,
    ):
        """Initialize enhanced extractor.

        Args:
            settings: Settings instance for configuration
            file_discovery: File discovery implementation (optional)
            file_operations: File operations implementation (optional)
            state_manager: State manager implementation
                (optional, creates default if None)
        """
        self.settings = settings
        self.file_discovery = file_discovery or FileDiscovery()
        self.file_operations = file_operations or FileOperations()
        self.state_manager = state_manager or StateManager()
        self.history_manager = HistoryManager()

    # -------------------------------------------------------------------------
    # Archive Detection and Handling
    # -------------------------------------------------------------------------

    # Supported archive extensions
    _ARCHIVE_EXTENSIONS = frozenset([".zip"])
    _TAR_EXTENSIONS = frozenset([".tar"])
    _COMPRESSED_TAR_SUFFIXES = [".tar.gz", ".tar.bz2", ".tar.xz"]
    _TAR_ALIASES = frozenset([".tgz", ".txz"])

    def _is_archive(self, filepath: Path) -> bool:
        """
        Check if a file is a supported archive based on its extension.

        Args:
            filepath: Path to the file to check

        Returns:
            True if the file is a supported archive format
        """
        path = filepath
        name_lower = path.name.lower()
        suffix_lower = path.suffix.lower()

        # Check ZIP files
        if suffix_lower in self._ARCHIVE_EXTENSIONS:
            return True

        # Check TAR aliases (e.g., .tgz)
        if suffix_lower in self._TAR_ALIASES:
            return True

        # Check compressed TAR files (e.g., .tar.gz, .tar.bz2)
        for compound_ext in self._COMPRESSED_TAR_SUFFIXES:
            if name_lower.endswith(compound_ext):
                return True

        # Check plain TAR files
        return suffix_lower in self._TAR_EXTENSIONS

    def _get_archive_handler(self, filepath: Path) -> "Optional[IArchiveHandler]":
        """
        Get the appropriate handler for an archive file.

        Args:
            filepath: Path to the archive file

        Returns:
            An IArchiveHandler instance if supported, None otherwise
        """
        from folder_extractor.core.archives import get_archive_handler

        return get_archive_handler(filepath)

    def _process_archives(
        self,
        files: List[str],
        destination: Path,
        operation_id: Optional[str],
        progress_callback: ProgressCallback,
        indexing_callback: Optional[Callable[[str], None]],
    ) -> Tuple[List[str], Dict[str, Any]]:
        """
        Process archive files: extract contents and prepare for normal processing.

        Args:
            files: List of file paths to process
            destination: Target directory for extracted files
            operation_id: Optional operation ID for tracking
            progress_callback: Callback for progress updates
            indexing_callback: Callback for indexing events

        Returns:
            Tuple of (remaining_files, archive_results)
            - remaining_files: Files that were not archives (to be processed normally)
            - archive_results: Statistics about archive processing
        """
        # Check if archive extraction is enabled
        if not self.settings.get("extract_archives", False):
            return files, {}

        archive_results = {
            "archives_processed": 0,
            "archive_errors": 0,
            "files_extracted": 0,
            "aborted": False,
            # Aggregated stats from recursive processing
            "moved": 0,
            "errors": 0,
            "duplicates": 0,
            "name_duplicates": 0,
            "content_duplicates": 0,
            "global_duplicates": 0,
            "history": [],
        }

        # Get abort signal
        abort_signal = self.state_manager.get_abort_signal()

        # Separate archives from regular files
        remaining_files = []
        archives_to_process = []

        for filepath in files:
            file_path = Path(filepath)
            if self._is_archive(file_path):
                archives_to_process.append(filepath)
            else:
                remaining_files.append(filepath)

        # Process each archive
        for archive_path in archives_to_process:
            # Check abort signal
            if abort_signal.is_set():
                archive_results["aborted"] = True
                # Add remaining archives back to files list
                remaining_files.extend(
                    archives_to_process[archives_to_process.index(archive_path) :]
                )
                break

            archive_path_obj = Path(archive_path)
            archive_name = archive_path_obj.name

            # Notify progress
            if progress_callback:
                progress_callback(
                    archive_results["archives_processed"],
                    len(archives_to_process),
                    f"Entpacke {archive_name}...",
                    None,
                )

            # Create temporary directory for extraction
            temp_dir = None
            try:
                temp_dir = tempfile.mkdtemp(prefix="folder_extractor_archive_")
                temp_path = Path(temp_dir)

                # Get appropriate handler
                handler = self._get_archive_handler(archive_path_obj)
                if handler is None:
                    # Should not happen since we checked _is_archive, but be safe
                    remaining_files.append(archive_path)
                    continue

                # Extract archive
                handler.extract(archive_path_obj, temp_path)

                # Discover extracted files
                extracted_files = self.file_discovery.find_files(
                    directory=temp_path,
                    max_depth=0,  # Unlimited depth within archive
                    include_hidden=self.settings.get("include_hidden", False),
                )

                if extracted_files:
                    archive_results["files_extracted"] += len(extracted_files)

                    # Recursively process extracted files (to destination)
                    # Applies same filters, deduplication, etc.
                    recursive_results = self.extract_files(
                        files=extracted_files,
                        destination=destination,
                        operation_id=operation_id,
                        progress_callback=progress_callback,
                        indexing_callback=indexing_callback,
                    )

                    # Aggregate results - ADD to existing values, don't overwrite
                    archive_results["moved"] += recursive_results.get("moved", 0)
                    archive_results["errors"] += recursive_results.get("errors", 0)
                    archive_results["duplicates"] += recursive_results.get(
                        "duplicates", 0
                    )
                    archive_results["name_duplicates"] += recursive_results.get(
                        "name_duplicates", 0
                    )
                    archive_results["content_duplicates"] += recursive_results.get(
                        "content_duplicates", 0
                    )
                    archive_results["global_duplicates"] += recursive_results.get(
                        "global_duplicates", 0
                    )
                    # Extend history list with entries from recursive processing
                    archive_results["history"].extend(
                        recursive_results.get("history", [])
                    )

                archive_results["archives_processed"] += 1

                # Delete archive if setting is enabled
                if self.settings.get("delete_archives", False):
                    Path(archive_path).unlink(missing_ok=True)

            except Exception as e:
                # Log error but continue with next archive
                archive_results["archive_errors"] += 1
                if progress_callback:
                    progress_callback(
                        archive_results["archives_processed"],
                        len(archives_to_process),
                        archive_name,
                        str(e),
                    )

            finally:
                # Always cleanup temp directory
                if temp_dir:
                    shutil.rmtree(temp_dir, ignore_errors=True)

        return remaining_files, archive_results

    def validate_security(self, path: Path) -> None:
        """Validate that the path is safe for operations."""
        if not is_safe_path(path):
            raise SecurityError(MESSAGES["SECURITY_ERROR"].format(path=path))

    def discover_files(self, path: Path) -> List[str]:
        """Discover files based on current settings."""
        files = self.file_discovery.find_files(
            directory=path,
            max_depth=self.settings.get("max_depth", 0),
            file_type_filter=self.settings.get("file_type_filter"),
            include_hidden=self.settings.get("include_hidden", False),
        )

        # Apply domain filter if set
        domain_filter = self.settings.get("domain_filter")
        if domain_filter:
            filtered_files = []
            for filepath in files:
                # Check if it's a weblink file
                file_path = Path(filepath)
                if file_path.suffix.lower() in [".url", ".webloc"]:
                    # Only include if domain matches
                    domain_matches = self.file_discovery.check_weblink_domain(
                        file_path, domain_filter
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
        destination: Path,
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

        # Process archives first (if enabled) - extract and recursively process contents
        files, archive_results = self._process_archives(
            files=files,
            destination=destination,
            operation_id=operation_id,
            progress_callback=progress_callback,
            indexing_callback=indexing_callback,
        )

        # Merge archive results into main results
        if archive_results:
            # Archive-specific stats
            results["archives_processed"] = archive_results.get("archives_processed", 0)
            results["archive_errors"] = archive_results.get("archive_errors", 0)
            results["files_extracted"] = archive_results.get("files_extracted", 0)
            if archive_results.get("aborted"):
                results["aborted"] = True

            # Add aggregated stats from archive extraction to main results
            results["moved"] += archive_results.get("moved", 0)
            results["errors"] += archive_results.get("errors", 0)
            results["duplicates"] += archive_results.get("duplicates", 0)
            results["name_duplicates"] += archive_results.get("name_duplicates", 0)
            results["content_duplicates"] += archive_results.get(
                "content_duplicates", 0
            )
            results["global_duplicates"] += archive_results.get("global_duplicates", 0)
            # Extend history with entries from archive processing
            results["history"].extend(archive_results.get("history", []))

        # If all files were archives and processed, we might have an empty list
        if not files:
            return results

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
        if self.settings.get("sort_by_type", False):
            # Create folder override callback for domain filter
            domain_filter = self.settings.get("domain_filter")
            folder_override: Optional[Callable[[Path], Optional[str]]] = None
            if domain_filter:
                # When domain filter is active, use domain as folder name for weblinks
                def _make_folder_override(
                    discovery: "IFileDiscovery",
                ) -> Callable[[Path], Optional[str]]:
                    def _folder_override(filepath: Path) -> Optional[str]:
                        if filepath.suffix.lower() in [".url", ".webloc"]:
                            domain = discovery.extract_weblink_domain(filepath)
                            if domain:
                                return domain
                        return None  # Use default folder determination

                    return _folder_override

                folder_override = _make_folder_override(self.file_discovery)

            # Move files sorted by type
            deduplicate = self.settings.get("deduplicate", False)
            global_dedup = self.settings.get("global_dedup", False)
            # Convert string paths to Path objects for core layer
            file_paths = [Path(f) for f in files]
            (
                moved,
                errors,
                duplicates,
                content_duplicates,
                global_duplicates,
                history,
                created_folders,
            ) = file_mover.move_files_sorted(
                files=file_paths,
                destination=destination,
                dry_run=self.settings.get("dry_run", False),
                progress_callback=lambda c, _t, f, e=None: progress_tracker.update(
                    c, f, e
                ),
                folder_override_callback=folder_override,
                deduplicate=deduplicate,
                global_dedup=global_dedup,
            )
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
            deduplicate = self.settings.get("deduplicate", False)
            global_dedup = self.settings.get("global_dedup", False)
            # Convert string paths to Path objects for core layer
            file_paths = [Path(f) for f in files]
            (
                moved,
                errors,
                duplicates,
                content_duplicates,
                global_duplicates,
                history,
            ) = file_mover.move_files(
                files=file_paths,
                destination=destination,
                dry_run=self.settings.get("dry_run", False),
                progress_callback=lambda c, _t, f, e=None: progress_tracker.update(
                    c, f, e
                ),
                deduplicate=deduplicate,
                global_dedup=global_dedup,
            )
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
        if not self.settings.get("dry_run", False) and move_results["history"]:
            self.history_manager.save_history(move_results["history"], destination)

        # Check if aborted
        if abort_signal.is_set():
            results["aborted"] = True

        # Clean up empty directories if not dry run and not filtering by file type
        # Note: sort_by_type should still clean up empty source directories
        if (
            not self.settings.get("dry_run", False)
            and not self.settings.get("file_type_filter")
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
        self, path: Path, temp_files: list
    ) -> Dict[str, Any]:
        """Remove empty directories after extraction.

        Args:
            path: Root path
            temp_files: List of temporary files to ignore

        Returns:
            Dictionary with 'removed' count and 'skipped' list of (path, reason)
        """
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
                    if not self.settings.get(
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

    def undo_last_operation(self, path: Path) -> Dict[str, Any]:
        """Undo the last operation.

        Args:
            path: Path where history is located

        Returns:
            Dictionary with undo results
        """
        # Load history
        history_data = self.history_manager.load_history(path)

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

                # Extract duplicate flags
                is_content_dup = entry.get("content_duplicate", False)
                is_global_dup = entry.get("global_duplicate", False)

                try:
                    # Get original path and ensure parent directory exists
                    original_path = Path(
                        entry.get("original_pfad", entry.get("original_path"))
                    )
                    original_path.parent.mkdir(parents=True, exist_ok=True)

                    # Handle duplicates differently: copy instead of move
                    if is_content_dup or is_global_dup:
                        # For duplicates, the original was deleted during extraction.
                        # We need to copy from the remaining file (neuer_pfad).
                        source_of_content = entry.get(
                            "neuer_pfad", entry.get("new_path")
                        )
                        source_path = Path(source_of_content)

                        if not source_path.exists():
                            raise FileNotFoundError(
                                f"Duplikat-Referenz nicht gefunden: {source_path}"
                            )

                        shutil.copy2(source_path, original_path)
                    else:
                        # Normal file: move back to original location
                        source_path = Path(
                            entry.get("neuer_pfad", entry.get("new_path"))
                        )
                        self.file_operations.move_file(
                            source_path,
                            original_path,
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
                self.history_manager.delete_history(path)

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
                (optional, creates default if None)
        """
        self.extractor = extractor
        self.state_manager = state_manager or StateManager()

    def execute_extraction(
        self,
        source_path: Path,
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
                    and not self.extractor.settings.get("dry_run", False)
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
                if op.operation_id is not None:
                    stats = self.state_manager.get_operation_stats(op.operation_id)
                else:
                    stats = None
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

    def process_single_file(
        self,
        filepath: Path,
        destination: Path,
        progress_callback: ProgressCallback = None,
    ) -> Dict[str, Any]:
        """Process a single file without directory discovery.

        This method is designed for watch mode where a single file is detected
        and should be processed immediately without scanning the entire directory.

        Args:
            filepath: Path to the single file to process
            destination: Destination directory for the file
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary with operation results
        """
        filepath = Path(filepath)
        destination = Path(destination)

        # Start operation
        with ManagedOperation(self.state_manager, "single_file") as op:
            try:
                # Validate security
                self.extractor.validate_security(destination)

                # Check if file exists
                if not filepath.exists():
                    return {
                        "status": "error",
                        "message": f"Datei existiert nicht: {filepath}",
                        "error": True,
                    }

                # Check abort signal before processing
                if op.abort_signal.is_set():
                    return {
                        "status": "aborted",
                        "message": "Operation abgebrochen",
                    }

                # Process single file directly - skip discovery
                results = self.extractor.extract_files(
                    files=[str(filepath)],
                    destination=destination,
                    operation_id=op.operation_id,
                    progress_callback=progress_callback,
                )

                # Add metadata
                results["status"] = "success"
                results["operation_id"] = op.operation_id

                return results

            except SecurityError as e:
                return {"status": "security_error", "message": str(e), "error": True}

            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Fehler: {str(e)}",
                    "error": True,
                }

    def execute_undo(self, path: Path) -> Dict[str, Any]:
        """Execute undo operation.

        Args:
            path: Path where history is located

        Returns:
            Dictionary with undo results
        """
        return self.extractor.undo_last_operation(path)
