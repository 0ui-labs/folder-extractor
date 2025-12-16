"""
State management module.

Centralizes application state and provides thread-safe access.
"""
import threading
from typing import Optional, Any, Dict
from abc import ABC, abstractmethod


class IApplicationState(ABC):
    """Interface for application state management."""
    
    @abstractmethod
    def get_abort_signal(self) -> threading.Event:
        """Get the abort signal event."""
        pass
    
    @abstractmethod
    def request_abort(self) -> None:
        """Request operation abort."""
        pass
    
    @abstractmethod
    def clear_abort(self) -> None:
        """Clear abort request."""
        pass
    
    @abstractmethod
    def is_abort_requested(self) -> bool:
        """Check if abort was requested."""
        pass


class ApplicationState(IApplicationState):
    """Thread-safe application state container."""
    
    def __init__(self):
        """Initialize application state."""
        self._abort_signal = threading.Event()
        self._lock = threading.Lock()
        self._state: Dict[str, Any] = {}
    
    def get_abort_signal(self) -> threading.Event:
        """Get the abort signal event."""
        return self._abort_signal
    
    def request_abort(self) -> None:
        """Request operation abort."""
        self._abort_signal.set()
    
    def clear_abort(self) -> None:
        """Clear abort request."""
        self._abort_signal.clear()
    
    def is_abort_requested(self) -> bool:
        """Check if abort was requested."""
        return self._abort_signal.is_set()
    
    def set_value(self, key: str, value: Any) -> None:
        """Set a state value thread-safely."""
        with self._lock:
            self._state[key] = value
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a state value thread-safely."""
        with self._lock:
            return self._state.get(key, default)
    
    def update_values(self, values: Dict[str, Any]) -> None:
        """Update multiple state values atomically."""
        with self._lock:
            self._state.update(values)
    
    def clear(self) -> None:
        """Clear all state."""
        with self._lock:
            self._state.clear()
        self._abort_signal.clear()


class OperationContext:
    """Context for a single operation with its own state."""
    
    def __init__(self, app_state: IApplicationState):
        """Initialize operation context.
        
        Args:
            app_state: Application state container
        """
        self.app_state = app_state
        self.operation_data: Dict[str, Any] = {}
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
    
    @property
    def abort_signal(self) -> threading.Event:
        """Get abort signal from app state."""
        return self.app_state.get_abort_signal()
    
    def set_data(self, key: str, value: Any) -> None:
        """Set operation-specific data."""
        self.operation_data[key] = value
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Get operation-specific data."""
        return self.operation_data.get(key, default)
    
    def __enter__(self):
        """Enter operation context."""
        import time
        self.start_time = time.time()
        self.app_state.clear_abort()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit operation context."""
        import time
        self.end_time = time.time()
        # Could log operation duration here


# Global application state instance
_app_state: Optional[ApplicationState] = None


def get_app_state() -> ApplicationState:
    """Get or create the global application state."""
    global _app_state
    if _app_state is None:
        _app_state = ApplicationState()
    return _app_state


def reset_app_state() -> None:
    """Reset the global application state."""
    global _app_state
    if _app_state is not None:
        _app_state.clear()
    _app_state = ApplicationState()