"""
Enhanced extractor module with state management integration.

Coordinates file discovery, filtering, and moving operations
with integrated progress tracking and state management.
"""
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable, Union
from abc import ABC, abstractmethod

from folder_extractor.core.file_discovery import IFileDiscovery, FileDiscovery
from folder_extractor.core.file_operations import (
    IFileOperations, FileOperations, FileMover, HistoryManager
)
from folder_extractor.core.state_manager import (
    IStateManager, ManagedOperation, get_state_manager
)
from folder_extractor.core.progress import (
    ProgressTracker, ProgressInfo
)
from folder_extractor.config.settings import settings
from folder_extractor.utils.path_validators import is_safe_path
from folder_extractor.config.constants import MESSAGES


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
    def extract_files(self, files: List[str], destination: Union[str, Path],
                     operation_id: Optional[str] = None,
                     progress_callback: Optional[Callable[[int, int, str, Optional[str]], None]] = None) -> Dict[str, Any]:
        """Extract files to destination with operation tracking."""
        pass

    @abstractmethod
    def undo_last_operation(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Undo the last operation."""
        pass


class EnhancedFileExtractor(IEnhancedExtractor):
    """Enhanced file extractor with integrated state and progress tracking."""
    
    def __init__(self,
                 file_discovery: Optional[IFileDiscovery] = None,
                 file_operations: Optional[IFileOperations] = None,
                 state_manager: Optional[IStateManager] = None):
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
            raise SecurityError(
                MESSAGES["SECURITY_ERROR"].format(path=path_str)
            )
    
    def discover_files(self, path: Union[str, Path]) -> List[str]:
        """Discover files based on current settings."""
        path = Path(path)
        return self.file_discovery.find_files(
            directory=str(path),
            max_depth=settings.get("max_depth", 0),
            file_type_filter=settings.get("file_type_filter"),
            include_hidden=settings.get("include_hidden", False)
        )
    
    def extract_files(self, files: List[str], destination: Union[str, Path],
                     operation_id: Optional[str] = None,
                     progress_callback: Optional[Callable[[int, int, str, Optional[str]], None]] = None) -> Dict[str, Any]:
        """Extract files to destination with operation tracking.

        Args:
            files: List of files to extract
            destination: Destination directory
            operation_id: Optional operation ID for tracking
            progress_callback: Optional progress callback

        Returns:
            Dictionary with extraction results
        """
        destination = Path(destination)
        destination_str = str(destination)

        results = {
            "moved": 0,
            "skipped": 0,
            "duplicates": 0,
            "errors": 0,
            "created_folders": [],
            "history": []
        }
        
        # Get abort signal from state manager
        abort_signal = self.state_manager.get_abort_signal()
        
        # Create file mover with abort signal
        file_mover = FileMover(self.file_operations, abort_signal)
        
        # Create progress tracker
        def update_progress(info: ProgressInfo):
            # Update operation stats in state manager
            if operation_id:
                self.state_manager.update_operation_stats(
                    operation_id,
                    files_processed=1,
                    files_moved=1 if not info.error else 0,
                    errors=1 if info.error else 0
                )
            
            # Call external progress callback if provided
            if progress_callback:
                progress_callback(
                    info.current,
                    info.total,
                    info.current_file or "",
                    info.error
                )
        
        progress_tracker = ProgressTracker(callback=update_progress)
        progress_tracker.start(len(files))
        
        # Process files
        if settings.get("sort_by_type", False):
            # Move files sorted by type
            moved, errors, duplicates, history, created_folders = file_mover.move_files_sorted(
                files=files,
                destination=destination_str,
                dry_run=settings.get("dry_run", False),
                progress_callback=lambda c, t, f, e=None: progress_tracker.update(c, f, e)
            )
            move_results = {
                "moved": moved,
                "errors": errors,
                "duplicates": duplicates,
                "history": history,
                "created_folders": created_folders
            }
        else:
            # Move files flat
            moved, errors, duplicates, history = file_mover.move_files(
                files=files,
                destination=destination_str,
                dry_run=settings.get("dry_run", False),
                progress_callback=lambda c, t, f, e=None: progress_tracker.update(c, f, e)
            )
            move_results = {
                "moved": moved,
                "errors": errors,
                "duplicates": duplicates,
                "history": history,
                "created_folders": []
            }
        
        # Finish progress tracking
        progress_tracker.finish()
        
        # Update results
        results.update(move_results)
        
        # Save history if not dry run and files were moved
        if not settings.get("dry_run", False) and results["moved"] > 0:
            self.history_manager.save_history(move_results["history"], destination_str)
        
        # Check if aborted
        if abort_signal.is_set():
            results["aborted"] = True
        
        # Clean up empty directories if not dry run and not filtering by type
        if (not settings.get("dry_run", False) and 
            not settings.get("sort_by_type", False) and
            not settings.get("file_type_filter") and
            results["moved"] > 0):
            # Import the function we need
            from folder_extractor.utils.file_validators import get_temp_files_list
            
            # Remove empty directories
            removed_count = self._remove_empty_directories(destination, get_temp_files_list())
            results["removed_directories"] = removed_count
        
        return results
    
    def _remove_empty_directories(self, path: Union[str, Path], temp_files: list) -> int:
        """Remove empty directories after extraction.

        Args:
            path: Root path
            temp_files: List of temporary files to ignore

        Returns:
            Number of directories removed
        """
        path = Path(path)
        removed_count = 0

        # Collect all subdirectories, sorted by depth (deepest first)
        directories = sorted(
            [d for d in path.rglob('*') if d.is_dir()],
            key=lambda x: len(x.parts),
            reverse=True
        )

        for directory in directories:
            # Skip root directory (defensive - rglob('*') doesn't include root)
            if directory == path:  # pragma: no cover
                continue

            # Get directory contents
            try:
                dir_contents = list(directory.iterdir())
            except OSError:
                continue

            # Filter out temp files and hidden files if not included
            filtered_contents = []
            for item in dir_contents:
                if item.is_file():
                    if item.name in temp_files:
                        continue
                    if not settings.get("include_hidden", False) and item.name.startswith('.'):
                        continue
                filtered_contents.append(item)

            # Check if directory is effectively empty (only subdirs that were already removed)
            has_files = any(item.is_file() for item in filtered_contents)
            has_dirs = any(item.is_dir() for item in filtered_contents)

            if not has_files and not has_dirs:
                try:
                    directory.rmdir()
                    removed_count += 1
                except OSError:
                    pass

        return removed_count
    
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
                "restored": 0
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
            for i, entry in enumerate(reversed(operations)):
                if op.abort_signal.is_set():
                    break

                try:
                    # Undo the move
                    self.file_operations.move_file(
                        entry.get("neuer_pfad", entry.get("new_path")),
                        entry.get("original_pfad", entry.get("original_path"))
                    )
                    restored += 1

                    # Update progress
                    original_path_entry = entry.get("original_pfad", entry.get("original_path"))
                    progress_tracker.increment(original_path_entry)
                    op.update_stats(files_processed=1, files_moved=1)

                except Exception as e:
                    errors += 1
                    original_path_entry = entry.get("original_pfad", entry.get("original_path"))
                    progress_tracker.increment(
                        original_path_entry,
                        error=str(e)
                    )
                    op.update_stats(files_processed=1, errors=1)

            # Finish progress
            progress_tracker.finish()

            # Clear history after successful undo
            if restored > 0 and not op.abort_signal.is_set():
                self.history_manager.delete_history(path_str)

            return {
                "status": "success" if restored > 0 else "failed",
                "message": MESSAGES["UNDO_SUMMARY"].format(count=restored),
                "restored": restored,
                "errors": errors,
                "aborted": op.abort_signal.is_set()
            }


class EnhancedExtractionOrchestrator:
    """Orchestrates the complete extraction workflow with state management."""
    
    def __init__(self, extractor: IEnhancedExtractor,
                 state_manager: Optional[IStateManager] = None):
        """Initialize orchestrator.
        
        Args:
            extractor: Extractor implementation
            state_manager: State manager implementation
        """
        self.extractor = extractor
        self.state_manager = state_manager or get_state_manager()
    
    def execute_extraction(self, source_path: Union[str, Path],
                         confirmation_callback: Optional[Callable[[int], bool]] = None,
                         progress_callback: Optional[Callable[[int, int, str, Optional[str]], None]] = None) -> Dict[str, Any]:
        """Execute complete extraction workflow.

        Args:
            source_path: Source directory path
            confirmation_callback: Optional callback for user confirmation
            progress_callback: Optional callback for progress updates

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
                        "files_found": 0
                    }

                # Get confirmation if callback provided
                if confirmation_callback and not settings.get("dry_run", False):
                    if not confirmation_callback(len(files)):
                        return {
                            "status": "cancelled",
                            "message": MESSAGES["OPERATION_CANCELLED"],
                            "files_found": len(files)
                        }

                # Note: Progress tracking is handled directly in extract_files
                # via the progress tracker callback, not through state manager listeners

                # Extract files
                results = self.extractor.extract_files(
                    files, source_path, op.operation_id, progress_callback
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
                return {
                    "status": "security_error",
                    "message": str(e),
                    "error": True
                }

            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Fehler: {str(e)}",
                    "error": True
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