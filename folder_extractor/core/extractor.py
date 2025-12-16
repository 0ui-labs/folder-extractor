"""
Core extractor module.

Coordinates file discovery, filtering, and moving operations.
"""
import os
import threading
from typing import List, Tuple, Optional, Dict, Any, Callable
from abc import ABC, abstractmethod

from folder_extractor.core.file_discovery import IFileDiscovery, FileDiscovery
from folder_extractor.core.file_operations import (
    IFileOperations, FileOperations, FileMover, HistoryManager
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


class IExtractor(ABC):
    """Interface for file extraction operations."""
    
    @abstractmethod
    def validate_security(self, path: str) -> None:
        """Validate that the path is safe for operations."""
        pass
    
    @abstractmethod
    def discover_files(self, path: str) -> List[str]:
        """Discover files based on current settings."""
        pass
    
    @abstractmethod
    def extract_files(self, files: List[str], destination: str,
                     progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Extract files to destination."""
        pass
    
    @abstractmethod
    def undo_last_operation(self, path: str) -> int:
        """Undo the last extraction operation."""
        pass


class FileExtractor(IExtractor):
    """Main file extractor implementation."""
    
    def __init__(self, 
                 file_discovery: Optional[IFileDiscovery] = None,
                 file_operations: Optional[IFileOperations] = None,
                 abort_signal: Optional[threading.Event] = None):
        """
        Initialize file extractor.
        
        Args:
            file_discovery: File discovery implementation
            file_operations: File operations implementation
            abort_signal: Threading event for operation abort
        """
        self.abort_signal = abort_signal or threading.Event()
        self.file_discovery = file_discovery or FileDiscovery(self.abort_signal)
        self.file_operations = file_operations or FileOperations(self.abort_signal)
        self.file_mover = FileMover(self.file_operations, self.abort_signal)
    
    def validate_security(self, path: str) -> None:
        """
        Validate that the path is safe for operations.
        
        Args:
            path: Path to validate
        
        Raises:
            SecurityError: If path is not safe
        """
        if not is_safe_path(path):
            raise SecurityError(
                MESSAGES["SECURITY_ERROR"].format(path=path)
            )
    
    def discover_files(self, path: str) -> List[str]:
        """
        Discover files based on current settings.
        
        Args:
            path: Root path to search
        
        Returns:
            List of discovered file paths
        """
        return self.file_discovery.find_files(
            directory=path,
            max_depth=settings.max_depth,
            file_type_filter=settings.file_type_filter,
            include_hidden=settings.include_hidden
        )
    
    def filter_by_domain(self, files: List[str], domains: List[str]) -> List[str]:
        """
        Filter weblink files by domain.
        
        Args:
            files: List of file paths
            domains: Allowed domains
        
        Returns:
            Filtered list of files
        """
        if not domains:
            return files
        
        filtered = []
        for filepath in files:
            # Check if it's a weblink file
            if filepath.endswith(('.url', '.webloc')):
                if self.file_discovery.check_weblink_domain(filepath, domains):
                    filtered.append(filepath)
            else:
                # Non-weblink files are included
                filtered.append(filepath)
        
        return filtered
    
    def extract_files(self, files: List[str], destination: str,
                     progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Extract files to destination.
        
        Args:
            files: List of files to extract
            destination: Destination directory
            progress_callback: Optional progress callback
        
        Returns:
            Dictionary with extraction results
        """
        # Apply domain filter if set
        if settings.domain_filter:
            files = self.filter_by_domain(files, settings.domain_filter)
        
        # Determine extraction method
        if settings.sort_by_type:
            moved, errors, duplicates, history, created_folders = \
                self.file_mover.move_files_sorted(
                    files, destination, 
                    dry_run=settings.dry_run,
                    progress_callback=progress_callback
                )
            
            result = {
                "moved": moved,
                "errors": errors,
                "duplicates": duplicates,
                "history": history,
                "created_folders": created_folders
            }
        else:
            moved, errors, duplicates, history = \
                self.file_mover.move_files(
                    files, destination,
                    dry_run=settings.dry_run,
                    progress_callback=progress_callback
                )
            
            result = {
                "moved": moved,
                "errors": errors,
                "duplicates": duplicates,
                "history": history,
                "created_folders": []
            }
        
        # Save history if not dry run
        if not settings.dry_run and history:
            HistoryManager.save_history(history, destination)
        
        # Clean up empty directories if enabled
        if not settings.dry_run and not settings.file_type_filter:
            removed = self.file_operations.remove_empty_directories(
                destination, settings.include_hidden
            )
            result["removed_directories"] = removed
        else:
            result["removed_directories"] = 0
        
        return result
    
    def undo_last_operation(self, path: str) -> int:
        """
        Undo the last extraction operation.
        
        Args:
            path: Path where history file is located
        
        Returns:
            Number of files restored
        """
        # Load history
        history_data = HistoryManager.load_history(path)
        if not history_data or "operationen" not in history_data:
            return 0
        
        restored = 0
        operations = history_data["operationen"]
        
        # Restore files in reverse order
        for operation in reversed(operations):
            if self.abort_signal.is_set():
                break
            
            try:
                # Move file back to original location
                if os.path.exists(operation["neuer_pfad"]):
                    # Ensure original directory exists
                    os.makedirs(
                        os.path.dirname(operation["original_pfad"]), 
                        exist_ok=True
                    )
                    
                    # Move file back
                    self.file_operations.move_file(
                        operation["neuer_pfad"],
                        operation["original_pfad"]
                    )
                    restored += 1
            except Exception:
                # Continue with other files even if one fails
                pass
        
        # Delete history after successful undo
        if restored > 0:
            HistoryManager.delete_history(path)
        
        return restored


class ExtractionOrchestrator:
    """Orchestrates the complete extraction workflow."""
    
    def __init__(self, extractor: IExtractor):
        """
        Initialize orchestrator.
        
        Args:
            extractor: Extractor implementation
        """
        self.extractor = extractor
    
    def execute_extraction(self, 
                          source_path: str,
                          confirmation_callback: Optional[Callable] = None,
                          progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Execute complete extraction workflow.
        
        Args:
            source_path: Source directory path
            confirmation_callback: Callback for user confirmation
            progress_callback: Callback for progress updates
        
        Returns:
            Extraction results
        
        Raises:
            ExtractionError: If extraction fails
        """
        # Validate security
        self.extractor.validate_security(source_path)
        
        # Discover files
        files = self.extractor.discover_files(source_path)
        
        if not files:
            return {
                "status": "no_files",
                "message": MESSAGES["NO_FILES_FOUND"]
            }
        
        # Get confirmation if callback provided
        if confirmation_callback and not settings.dry_run:
            if not confirmation_callback(len(files)):
                return {
                    "status": "cancelled",
                    "message": MESSAGES["OPERATION_CANCELLED"]
                }
        
        # Extract files
        result = self.extractor.extract_files(
            files, source_path, progress_callback
        )
        
        result["status"] = "success"
        result["total_files"] = len(files)
        
        return result
    
    def execute_undo(self, path: str) -> Dict[str, Any]:
        """
        Execute undo operation.
        
        Args:
            path: Path where history is located
        
        Returns:
            Undo results
        """
        # Validate security
        self.extractor.validate_security(path)
        
        # Perform undo
        restored = self.extractor.undo_last_operation(path)
        
        if restored == 0:
            return {
                "status": "no_history",
                "message": MESSAGES["UNDO_NO_HISTORY"],
                "restored": 0
            }
        
        return {
            "status": "success",
            "message": MESSAGES["UNDO_SUMMARY"].format(count=restored),
            "restored": restored
        }