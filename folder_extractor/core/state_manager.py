"""
Enhanced state management with operation tracking and statistics.

Provides centralized state management with thread-safety,
operation history, and performance metrics.
"""

import contextlib
import json
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


@dataclass
class OperationStats:
    """Statistics for a single operation."""

    operation_type: str
    start_time: float
    end_time: Optional[float] = None
    files_processed: int = 0
    files_moved: int = 0
    files_skipped: int = 0
    errors: int = 0
    aborted: bool = False

    @property
    def duration(self) -> Optional[float]:
        """Calculate operation duration."""
        if self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.files_processed == 0:
            return 0.0
        return (self.files_moved / self.files_processed) * 100


class IStateManager(ABC):
    """Interface for state management."""

    @abstractmethod
    def start_operation(self, operation_type: str) -> str:
        """Start a new operation and return its ID."""
        pass

    @abstractmethod
    def end_operation(self, operation_id: str) -> None:
        """End an operation."""
        pass

    @abstractmethod
    def update_operation_stats(self, operation_id: str, **kwargs) -> None:
        """Update operation statistics."""
        pass

    @abstractmethod
    def get_operation_stats(self, operation_id: str) -> Optional[OperationStats]:
        """Get statistics for an operation."""
        pass

    @abstractmethod
    def get_current_operation_id(self) -> Optional[str]:
        """Get the current operation ID."""
        pass

    @abstractmethod
    def request_abort(self) -> None:
        """Request abort of current operation."""
        pass

    @abstractmethod
    def is_abort_requested(self) -> bool:
        """Check if abort was requested."""
        pass

    @abstractmethod
    def clear_abort(self) -> None:
        """Clear abort request."""
        pass

    @abstractmethod
    def reset_start_time(self, operation_id: str) -> None:
        """Reset start time for an operation."""
        pass

    @abstractmethod
    def get_abort_signal(self) -> threading.Event:
        """Get the abort signal event."""
        pass


class StateManager(IStateManager):
    """Enhanced state manager with operation tracking."""

    def __init__(self):
        """Initialize state manager."""
        self._lock = threading.RLock()
        self._abort_signal = threading.Event()
        self._current_operation_id: Optional[str] = None
        self._operations: Dict[str, OperationStats] = {}
        self._state: Dict[str, Any] = {}
        self._listeners: Dict[str, List[Callable]] = {}
        self._operation_counter = 0

    def start_operation(self, operation_type: str) -> str:
        """Start a new operation and return its ID."""
        with self._lock:
            # Generate unique operation ID with counter
            self._operation_counter += 1
            operation_id = (
                f"{operation_type}_{int(time.time() * 1000)}_{self._operation_counter}"
            )

            # Create operation stats
            stats = OperationStats(
                operation_type=operation_type, start_time=time.time()
            )

            # Store operation
            self._operations[operation_id] = stats
            self._current_operation_id = operation_id

            # Clear abort signal
            self._abort_signal.clear()

            # Notify listeners
            self._notify_listeners("operation_started", operation_id=operation_id)

            return operation_id

    def end_operation(self, operation_id: str) -> None:
        """End an operation."""
        with self._lock:
            if operation_id in self._operations:
                stats = self._operations[operation_id]
                stats.end_time = time.time()
                stats.aborted = self._abort_signal.is_set()

                # Clear current operation if it matches
                if self._current_operation_id == operation_id:
                    self._current_operation_id = None

                # Notify listeners
                self._notify_listeners(
                    "operation_ended", operation_id=operation_id, stats=stats
                )

    def update_operation_stats(self, operation_id: str, **kwargs) -> None:
        """Update operation statistics."""
        with self._lock:
            if operation_id in self._operations:
                stats = self._operations[operation_id]
                for key, value in kwargs.items():
                    if hasattr(stats, key):
                        if key in [
                            "files_processed",
                            "files_moved",
                            "files_skipped",
                            "errors",
                        ]:
                            # Increment counters
                            current = getattr(stats, key)
                            setattr(stats, key, current + value)
                        else:
                            setattr(stats, key, value)

    def reset_start_time(self, operation_id: str) -> None:
        """Reset the start time for an operation.

        Useful when user confirmation happens after operation start,
        to measure only the actual work time.
        """
        with self._lock:
            if operation_id in self._operations:
                self._operations[operation_id].start_time = time.time()

    def get_operation_stats(self, operation_id: str) -> Optional[OperationStats]:
        """Get statistics for an operation."""
        with self._lock:
            return self._operations.get(operation_id)

    def get_current_operation_id(self) -> Optional[str]:
        """Get the current operation ID."""
        with self._lock:
            return self._current_operation_id

    def request_abort(self) -> None:
        """Request abort of current operation."""
        self._abort_signal.set()
        self._notify_listeners("abort_requested")

    def is_abort_requested(self) -> bool:
        """Check if abort was requested."""
        return self._abort_signal.is_set()

    def clear_abort(self) -> None:
        """Clear abort request."""
        self._abort_signal.clear()

    def get_abort_signal(self) -> threading.Event:
        """Get the abort signal event."""
        return self._abort_signal

    def set_value(self, key: str, value: Any) -> None:
        """Set a state value."""
        with self._lock:
            old_value = self._state.get(key)
            self._state[key] = value
            if old_value != value:
                self._notify_listeners(
                    "state_changed", key=key, old_value=old_value, new_value=value
                )

    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a state value."""
        with self._lock:
            return self._state.get(key, default)

    def update_values(self, values: Dict[str, Any]) -> None:
        """Update multiple state values."""
        with self._lock:
            for key, value in values.items():
                self.set_value(key, value)

    def add_listener(self, event: str, callback: Callable) -> None:
        """Add an event listener."""
        with self._lock:
            if event not in self._listeners:
                self._listeners[event] = []
            self._listeners[event].append(callback)

    def remove_listener(self, event: str, callback: Callable) -> None:
        """Remove an event listener."""
        with self._lock:
            if event in self._listeners:
                self._listeners[event].remove(callback)

    def _notify_listeners(self, event: str, **kwargs) -> None:
        """Notify all listeners of an event."""
        listeners = self._listeners.get(event, [])
        for listener in listeners:
            with contextlib.suppress(Exception):
                listener(**kwargs)

    def get_all_operations(self) -> Dict[str, OperationStats]:
        """Get all operation statistics."""
        with self._lock:
            return self._operations.copy()

    def save_state(self, filepath: Path) -> None:
        """Save state to file."""
        with self._lock:
            state_data = {
                "state": self._state,
                "operations": {
                    op_id: asdict(stats) for op_id, stats in self._operations.items()
                },
                "timestamp": datetime.now().isoformat(),
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2)

    def load_state(self, filepath: Path) -> None:
        """Load state from file."""
        if not filepath.exists():
            return

        with self._lock:
            with open(filepath, encoding="utf-8") as f:
                state_data = json.load(f)

            self._state = state_data.get("state", {})

            # Reconstruct operation stats
            self._operations = {}
            for op_id, stats_dict in state_data.get("operations", {}).items():
                self._operations[op_id] = OperationStats(**stats_dict)

    def clear(self) -> None:
        """Clear all state."""
        with self._lock:
            self._state.clear()
            self._operations.clear()
            self._current_operation_id = None
            self._abort_signal.clear()
            self._operation_counter = 0


class ManagedOperation:
    """Context manager for operations with automatic tracking."""

    def __init__(self, state_manager: IStateManager, operation_type: str):
        """Initialize managed operation.

        Args:
            state_manager: State manager instance
            operation_type: Type of operation
        """
        self.state_manager = state_manager
        self.operation_type = operation_type
        self.operation_id: Optional[str] = None

    def __enter__(self):
        """Start the operation."""
        self.operation_id = self.state_manager.start_operation(self.operation_type)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End the operation."""
        if self.operation_id:
            self.state_manager.end_operation(self.operation_id)

    def update_stats(self, **kwargs) -> None:
        """Update operation statistics."""
        if self.operation_id:
            self.state_manager.update_operation_stats(self.operation_id, **kwargs)

    def reset_start_time(self) -> None:
        """Reset start time to now. Call after user confirmation."""
        if self.operation_id:
            self.state_manager.reset_start_time(self.operation_id)

    @property
    def abort_signal(self) -> threading.Event:
        """Get abort signal."""
        return self.state_manager.get_abort_signal()


def reset_state_manager() -> None:
    """Deprecated: No longer needed with dependency injection.

    Tests should create fresh StateManager() instances instead.
    """
    import warnings
    warnings.warn(
        "reset_state_manager() is deprecated. Create fresh StateManager() instances instead.",
        DeprecationWarning,
        stacklevel=2
    )
    pass
