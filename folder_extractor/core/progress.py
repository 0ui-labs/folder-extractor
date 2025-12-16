"""
Progress tracking and reporting.

Provides progress tracking capabilities with callbacks
and integration with state management.
"""
import time
from typing import Optional, Callable, Any, Dict
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class ProgressInfo:
    """Information about current progress."""
    current: int
    total: int
    current_file: Optional[str] = None
    error: Optional[str] = None
    
    @property
    def percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total == 0:
            return 100.0
        return (self.current / self.total) * 100.0
    
    @property
    def is_complete(self) -> bool:
        """Check if operation is complete."""
        return self.current >= self.total


class IProgressTracker(ABC):
    """Interface for progress tracking."""
    
    @abstractmethod
    def start(self, total: int) -> None:
        """Start tracking progress."""
        pass
    
    @abstractmethod
    def update(self, current: int, current_file: Optional[str] = None,
              error: Optional[str] = None) -> None:
        """Update progress."""
        pass
    
    @abstractmethod
    def increment(self, current_file: Optional[str] = None,
                 error: Optional[str] = None) -> None:
        """Increment progress by one."""
        pass
    
    @abstractmethod
    def finish(self) -> None:
        """Finish tracking."""
        pass
    
    @abstractmethod
    def get_info(self) -> ProgressInfo:
        """Get current progress information."""
        pass


class ProgressTracker(IProgressTracker):
    """Progress tracker with callback support."""
    
    def __init__(self, callback: Optional[Callable[[ProgressInfo], None]] = None,
                 update_interval: float = 0.1):
        """Initialize progress tracker.
        
        Args:
            callback: Optional callback for progress updates
            update_interval: Minimum interval between callbacks (seconds)
        """
        self.callback = callback
        self.update_interval = update_interval
        self._current = 0
        self._total = 0
        self._current_file: Optional[str] = None
        self._last_error: Optional[str] = None
        self._last_update_time = 0.0
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None
    
    def start(self, total: int) -> None:
        """Start tracking progress."""
        self._current = 0
        self._total = total
        self._current_file = None
        self._last_error = None
        self._start_time = time.time()
        self._end_time = None
        self._last_update_time = 0.0
        
        # Initial callback
        self._notify_progress()
    
    def update(self, current: int, current_file: Optional[str] = None,
              error: Optional[str] = None) -> None:
        """Update progress."""
        self._current = min(current, self._total)
        self._current_file = current_file
        self._last_error = error
        
        # Check if we should notify
        current_time = time.time()
        if (current_time - self._last_update_time) >= self.update_interval:
            self._notify_progress()
            self._last_update_time = current_time
    
    def increment(self, current_file: Optional[str] = None,
                 error: Optional[str] = None) -> None:
        """Increment progress by one."""
        self.update(self._current + 1, current_file, error)
    
    def finish(self) -> None:
        """Finish tracking."""
        self._end_time = time.time()
        self._current = self._total
        self._notify_progress()  # Always notify on finish
    
    def get_info(self) -> ProgressInfo:
        """Get current progress information."""
        return ProgressInfo(
            current=self._current,
            total=self._total,
            current_file=self._current_file,
            error=self._last_error
        )
    
    def _notify_progress(self) -> None:
        """Notify callback of progress update."""
        if self.callback:
            info = self.get_info()
            self.callback(info)
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        if self._start_time is None:
            return 0.0
        
        if self._end_time is not None:
            return self._end_time - self._start_time
        
        return time.time() - self._start_time
    
    @property
    def estimated_remaining_time(self) -> Optional[float]:
        """Estimate remaining time in seconds."""
        if self._current == 0 or self._total == 0:
            return None
        
        elapsed = self.elapsed_time
        rate = self._current / elapsed if elapsed > 0 else 0
        
        if rate == 0:
            return None
        
        remaining_items = self._total - self._current
        return remaining_items / rate
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics."""
        return {
            'current': self._current,
            'total': self._total,
            'percentage': self.get_info().percentage,
            'elapsed_time': self.elapsed_time,
            'estimated_remaining': self.estimated_remaining_time,
            'average_rate': self._current / self.elapsed_time if self.elapsed_time > 0 else 0,
            'has_errors': self._last_error is not None
        }


class BatchProgressTracker(ProgressTracker):
    """Progress tracker with batch processing support."""
    
    def __init__(self, callback: Optional[Callable[[ProgressInfo], None]] = None,
                 update_interval: float = 0.1, batch_size: int = 100):
        """Initialize batch progress tracker.
        
        Args:
            callback: Optional callback for progress updates
            update_interval: Minimum interval between callbacks
            batch_size: Size of each batch
        """
        super().__init__(callback, update_interval)
        self.batch_size = batch_size
        self._batch_start = 0
        self._batch_errors = 0
    
    def start_batch(self) -> None:
        """Start a new batch."""
        self._batch_start = self._current
        self._batch_errors = 0
    
    def end_batch(self) -> Dict[str, Any]:
        """End current batch and return statistics."""
        batch_items = self._current - self._batch_start
        return {
            'items_processed': batch_items,
            'errors': self._batch_errors,
            'success_rate': ((batch_items - self._batch_errors) / batch_items * 100)
                           if batch_items > 0 else 0
        }
    
    def increment(self, current_file: Optional[str] = None,
                 error: Optional[str] = None) -> None:
        """Increment progress by one."""
        if error:
            self._batch_errors += 1
        super().increment(current_file, error)


class CompositeProgressTracker(IProgressTracker):
    """Composite progress tracker that delegates to multiple trackers."""
    
    def __init__(self, trackers: list[IProgressTracker]):
        """Initialize composite tracker.
        
        Args:
            trackers: List of progress trackers
        """
        self.trackers = trackers
    
    def start(self, total: int) -> None:
        """Start tracking progress."""
        for tracker in self.trackers:
            tracker.start(total)
    
    def update(self, current: int, current_file: Optional[str] = None,
              error: Optional[str] = None) -> None:
        """Update progress."""
        for tracker in self.trackers:
            tracker.update(current, current_file, error)
    
    def increment(self, current_file: Optional[str] = None,
                 error: Optional[str] = None) -> None:
        """Increment progress by one."""
        for tracker in self.trackers:
            tracker.increment(current_file, error)
    
    def finish(self) -> None:
        """Finish tracking."""
        for tracker in self.trackers:
            tracker.finish()
    
    def get_info(self) -> ProgressInfo:
        """Get current progress information."""
        # Return info from first tracker
        if self.trackers:
            return self.trackers[0].get_info()
        return ProgressInfo(current=0, total=0)