"""
File operations module.

Handles all file system operations including moving files,
generating unique names, and managing directories.
"""
import os
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict, Optional, Any
from abc import ABC, abstractmethod

from folder_extractor.config.constants import (
    NO_EXTENSION_FOLDER,
    FILE_TYPE_FOLDERS,
    HISTORY_FILE_NAME
)
from folder_extractor.utils.terminal import Color


class FileOperationError(Exception):
    """Base exception for file operation errors."""
    pass


class IFileOperations(ABC):
    """Interface for file operations."""
    
    @abstractmethod
    def move_file(self, source: str, destination: str, dry_run: bool = False) -> bool:
        """Move a single file."""
        pass
    
    @abstractmethod
    def generate_unique_name(self, directory: str, filename: str) -> str:
        """Generate a unique filename in the given directory."""
        pass
    
    @abstractmethod
    def remove_empty_directories(self, path: str, include_hidden: bool = False) -> int:
        """Remove empty directories recursively."""
        pass
    
    @abstractmethod
    def determine_type_folder(self, filename: str) -> str:
        """Determine the folder name for a file type."""
        pass


class FileOperations(IFileOperations):
    """Implementation of file operations."""
    
    def __init__(self, abort_signal=None):
        """Initialize file operations.
        
        Args:
            abort_signal: Threading event to signal operation abort
        """
        self.abort_signal = abort_signal
    
    def move_file(self, source: str, destination: str, dry_run: bool = False) -> bool:
        """
        Move a single file from source to destination.
        
        Args:
            source: Source file path
            destination: Destination file path
            dry_run: If True, don't actually move the file
        
        Returns:
            True if successful, False otherwise
        
        Raises:
            FileOperationError: If the move operation fails
        """
        if dry_run:
            return True
        
        try:
            # Try to move using rename (fastest)
            os.rename(source, destination)
            return True
        except OSError:
            # Fall back to copy and delete (works across filesystems)
            try:
                shutil.copy2(source, destination)
                os.remove(source)
                return True
            except Exception as e:
                raise FileOperationError(f"Failed to move file: {str(e)}")
    
    def generate_unique_name(self, directory: str, filename: str) -> str:
        """
        Generate a unique filename in the given directory.
        
        If a file with the given name already exists, appends _1, _2, etc.
        
        Args:
            directory: Directory to check for existing files
            filename: Original filename
        
        Returns:
            Unique filename that doesn't exist in the directory
        """
        if not os.path.exists(os.path.join(directory, filename)):
            return filename
        
        # Split name and extension
        name_parts = filename.rsplit('.', 1)
        if len(name_parts) == 2:
            base_name, extension = name_parts
            extension = '.' + extension
        else:
            base_name = filename
            extension = ''
        
        # Find unique name
        counter = 1
        while True:
            new_name = f"{base_name}_{counter}{extension}"
            if not os.path.exists(os.path.join(directory, new_name)):
                return new_name
            counter += 1
    
    def remove_empty_directories(self, path: str, include_hidden: bool = False) -> int:
        """
        Remove empty directories recursively.
        
        Args:
            path: Root path to start from
            include_hidden: Whether to consider hidden files
        
        Returns:
            Number of directories removed
        """
        removed_count = 0
        
        for root, dirs, files in os.walk(path, topdown=False):
            # Skip the root directory itself
            if root == path:
                continue
            
            # Check if directory is empty
            try:
                dir_content = os.listdir(root)
                
                # If not including hidden files, filter them out
                if not include_hidden:
                    dir_content = [item for item in dir_content 
                                 if not item.startswith('.')]
                
                # If directory is empty (or only has hidden files), remove it
                if not dir_content:
                    # Remove hidden files if not including them
                    if not include_hidden:
                        for item in os.listdir(root):
                            if item.startswith('.'):
                                item_path = os.path.join(root, item)
                                if os.path.isfile(item_path):
                                    os.remove(item_path)
                                elif os.path.isdir(item_path):
                                    shutil.rmtree(item_path)
                    
                    os.rmdir(root)
                    removed_count += 1
            except (OSError, PermissionError):
                # Skip directories we can't access
                pass
        
        return removed_count
    
    def determine_type_folder(self, filename: str) -> str:
        """
        Determine the folder name for a file based on its type.
        
        Args:
            filename: Name of the file
        
        Returns:
            Folder name for the file type
        """
        # Get file extension
        _, ext = os.path.splitext(filename.lower())
        
        # Look up in mapping
        if ext in FILE_TYPE_FOLDERS:
            return FILE_TYPE_FOLDERS[ext]
        elif ext:
            # Unknown extension - use uppercase extension without dot
            return ext[1:].upper()
        else:
            # No extension
            return NO_EXTENSION_FOLDER


class HistoryManager:
    """Manages operation history for undo functionality."""
    
    @staticmethod
    def save_history(operations: List[Dict[str, Any]], directory: str) -> str:
        """
        Save operation history to file.
        
        Args:
            operations: List of operation records
            directory: Directory to save history file
        
        Returns:
            Path to the history file
        """
        history_file = os.path.join(directory, HISTORY_FILE_NAME)
        
        history_data = {
            "zeitstempel": datetime.now().isoformat(),
            "version": "1.0",
            "operationen": operations
        }
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)
        
        return history_file
    
    @staticmethod
    def load_history(directory: str) -> Optional[Dict[str, Any]]:
        """
        Load operation history from file.
        
        Args:
            directory: Directory containing history file
        
        Returns:
            History data or None if not found
        """
        history_file = os.path.join(directory, HISTORY_FILE_NAME)
        
        if not os.path.exists(history_file):
            return None
        
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    
    @staticmethod
    def delete_history(directory: str) -> bool:
        """
        Delete history file.
        
        Args:
            directory: Directory containing history file
        
        Returns:
            True if deleted, False if not found
        """
        history_file = os.path.join(directory, HISTORY_FILE_NAME)
        
        if os.path.exists(history_file):
            os.remove(history_file)
            return True
        
        return False


class FileMover:
    """High-level file moving operations."""
    
    def __init__(self, file_ops: IFileOperations, abort_signal=None):
        """
        Initialize file mover.
        
        Args:
            file_ops: File operations implementation
            abort_signal: Threading event to signal abort
        """
        self.file_ops = file_ops
        self.abort_signal = abort_signal
    
    def move_files(self, files: List[str], destination: str, 
                   dry_run: bool = False,
                   progress_callback=None) -> Tuple[int, int, int, List[Dict]]:
        """
        Move multiple files to destination.
        
        Args:
            files: List of file paths to move
            destination: Destination directory
            dry_run: If True, simulate the operation
            progress_callback: Optional callback for progress updates
        
        Returns:
            Tuple of (moved_count, error_count, duplicate_count, history)
        """
        moved = 0
        errors = 0
        duplicates = 0
        history = []
        
        for i, file_path in enumerate(files):
            # Check abort signal
            if self.abort_signal and self.abort_signal.is_set():
                break
            
            # Progress callback
            if progress_callback:
                progress_callback(i + 1, len(files), file_path)
            
            try:
                filename = os.path.basename(file_path)
                
                # Generate unique name if needed
                unique_name = self.file_ops.generate_unique_name(destination, filename)
                if unique_name != filename:
                    duplicates += 1
                
                dest_path = os.path.join(destination, unique_name)
                
                # Move file
                if self.file_ops.move_file(file_path, dest_path, dry_run):
                    moved += 1
                    
                    # Record in history
                    if not dry_run:
                        history.append({
                            "original_pfad": file_path,
                            "neuer_pfad": dest_path,
                            "original_name": filename,
                            "neuer_name": unique_name,
                            "zeitstempel": datetime.now().isoformat()
                        })
                
            except Exception as e:
                errors += 1
                if progress_callback:
                    progress_callback(i + 1, len(files), file_path, error=str(e))
        
        return moved, errors, duplicates, history
    
    def move_files_sorted(self, files: List[str], destination: str,
                         dry_run: bool = False,
                         progress_callback=None) -> Tuple[int, int, int, List[Dict], List[str]]:
        """
        Move files sorted by type into subdirectories.
        
        Args:
            files: List of file paths to move
            destination: Destination directory
            dry_run: If True, simulate the operation
            progress_callback: Optional callback for progress updates
        
        Returns:
            Tuple of (moved_count, error_count, duplicate_count, history, created_folders)
        """
        moved = 0
        errors = 0
        duplicates = 0
        history = []
        created_folders = set()
        
        for i, file_path in enumerate(files):
            # Check abort signal
            if self.abort_signal and self.abort_signal.is_set():
                break
            
            # Progress callback
            if progress_callback:
                progress_callback(i + 1, len(files), file_path)
            
            try:
                filename = os.path.basename(file_path)
                
                # Determine type folder
                type_folder = self.file_ops.determine_type_folder(filename)
                type_path = os.path.join(destination, type_folder)
                
                # Create type folder if needed
                if not os.path.exists(type_path) and not dry_run:
                    os.makedirs(type_path, exist_ok=True)
                    created_folders.add(type_folder)
                
                # Generate unique name
                unique_name = self.file_ops.generate_unique_name(type_path, filename)
                if unique_name != filename:
                    duplicates += 1
                
                dest_path = os.path.join(type_path, unique_name)
                
                # Move file
                if self.file_ops.move_file(file_path, dest_path, dry_run):
                    moved += 1
                    
                    # Record in history
                    if not dry_run:
                        history.append({
                            "original_pfad": file_path,
                            "neuer_pfad": dest_path,
                            "original_name": filename,
                            "neuer_name": unique_name,
                            "zeitstempel": datetime.now().isoformat()
                        })
                
            except Exception as e:
                errors += 1
                if progress_callback:
                    progress_callback(i + 1, len(files), file_path, error=str(e))
        
        return moved, errors, duplicates, history, list(created_folders)