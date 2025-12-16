"""
Migration utilities for transitioning to new architecture.

Provides adapters and utilities to ensure backward compatibility
while transitioning to the new modular architecture.
"""
import threading
from typing import Optional, Dict, Any, Callable

from folder_extractor.core.state import (
    IApplicationState, ApplicationState, OperationContext
)
from folder_extractor.core.state_manager import (
    IStateManager, StateManager, get_state_manager
)
from folder_extractor.core.extractor import IExtractor, FileExtractor
from folder_extractor.core.extractor_v2 import (
    IEnhancedExtractor, EnhancedFileExtractor
)


class StateAdapter(IApplicationState):
    """Adapter to make new StateManager compatible with old IApplicationState."""
    
    def __init__(self, state_manager: Optional[IStateManager] = None):
        """Initialize adapter.
        
        Args:
            state_manager: State manager to adapt
        """
        self.state_manager = state_manager or get_state_manager()
    
    def get_abort_signal(self) -> threading.Event:
        """Get the abort signal event."""
        return self.state_manager.get_abort_signal()
    
    def request_abort(self) -> None:
        """Request operation abort."""
        self.state_manager.request_abort()
    
    def clear_abort(self) -> None:
        """Clear abort request."""
        self.state_manager.clear_abort()
    
    def is_abort_requested(self) -> bool:
        """Check if abort was requested."""
        return self.state_manager.is_abort_requested()


class ExtractorAdapter(IExtractor):
    """Adapter to make new EnhancedExtractor compatible with old IExtractor."""
    
    def __init__(self, enhanced_extractor: Optional[IEnhancedExtractor] = None,
                 state_manager: Optional[IStateManager] = None):
        """Initialize adapter.
        
        Args:
            enhanced_extractor: Enhanced extractor to adapt
            state_manager: State manager for operation tracking
        """
        self.enhanced_extractor = enhanced_extractor or EnhancedFileExtractor()
        self.state_manager = state_manager or get_state_manager()
        self._abort_signal: Optional[threading.Event] = None
    
    def validate_security(self, path: str) -> None:
        """Validate that the path is safe for operations."""
        self.enhanced_extractor.validate_security(path)
    
    def discover_files(self, path: str) -> list[str]:
        """Discover files based on current settings."""
        return self.enhanced_extractor.discover_files(path)
    
    def extract_files(self, files: list[str], destination: str,
                     progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Extract files to destination."""
        # Start an operation for tracking
        op_id = self.state_manager.start_operation("extraction")
        
        try:
            # If progress callback provided, wrap it
            if progress_callback:
                def wrapped_callback(current, total, filepath, error):
                    # Update state manager
                    self.state_manager.set_value("current_file", filepath)
                    if error:
                        self.state_manager.set_value("last_error", error)
                    
                    # Call original callback
                    progress_callback(current, total, filepath, error)
                
                # Use wrapped callback by setting up listener
                self.state_manager.add_listener("state_changed", 
                    lambda **kwargs: wrapped_callback(
                        self.state_manager.get_operation_stats(op_id).files_processed,
                        len(files),
                        kwargs.get('new_value') if kwargs.get('key') == 'current_file' else "",
                        kwargs.get('new_value') if kwargs.get('key') == 'last_error' else None
                    )
                )
            
            # Execute extraction
            results = self.enhanced_extractor.extract_files(
                files, destination, op_id
            )
            
            return results
            
        finally:
            # End operation
            self.state_manager.end_operation(op_id)
    
    def undo_last_operation(self, path: str) -> int:
        """Undo the last operation."""
        results = self.enhanced_extractor.undo_last_operation(path)
        return results.get("restored", 0)
    
    def set_abort_signal(self, signal: threading.Event) -> None:
        """Set abort signal (for compatibility)."""
        self._abort_signal = signal
        # Note: The new implementation uses state manager's abort signal


class MigrationHelper:
    """Helper class for migrating to new architecture."""
    
    @staticmethod
    def create_compatible_extractor(abort_signal: Optional[threading.Event] = None) -> FileExtractor:
        """Create a FileExtractor that uses new implementation internally.
        
        Args:
            abort_signal: Optional abort signal for compatibility
        
        Returns:
            FileExtractor instance using new implementation
        """
        # Create new enhanced extractor
        enhanced = EnhancedFileExtractor()
        
        # Wrap in adapter
        adapter = ExtractorAdapter(enhanced)
        
        # Create old-style extractor with adapter
        from folder_extractor.core.file_discovery import FileDiscovery
        from folder_extractor.core.file_operations import FileOperations
        
        # Return FileExtractor that will use our adapter
        # Note: This requires modifying FileExtractor to accept IExtractor
        # For now, return the adapter cast as FileExtractor
        return adapter  # type: ignore
    
    @staticmethod
    def migrate_settings() -> None:
        """Migrate settings to new state manager."""
        state_manager = get_state_manager()
        
        # Copy relevant settings to state manager
        from folder_extractor.config.settings import settings
        
        state_values = {
            "dry_run": settings.get("dry_run", False),
            "max_depth": settings.get("max_depth", 0),
            "include_hidden": settings.get("include_hidden", False),
            "sort_by_type": settings.get("sort_by_type", False),
            "file_type_filter": settings.get("file_type_filter"),
            "domain_filter": settings.get("domain_filter"),
        }
        
        state_manager.update_values(state_values)
    
    @staticmethod
    def create_operation_context() -> OperationContext:
        """Create an OperationContext using new state manager.
        
        Returns:
            OperationContext with state adapter
        """
        state_adapter = StateAdapter()
        return OperationContext(state_adapter)