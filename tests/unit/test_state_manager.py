"""
Unit tests for state manager module.
"""
import pytest
import time
import threading
from unittest.mock import Mock, MagicMock
from pathlib import Path
import json
import tempfile

from folder_extractor.core.state_manager import (
    StateManager, OperationStats, ManagedOperation,
    get_state_manager, reset_state_manager
)


class TestOperationStats:
    """Test OperationStats dataclass."""
    
    def test_init(self):
        """Test initialization."""
        stats = OperationStats(
            operation_type="extraction",
            start_time=1000.0
        )
        
        assert stats.operation_type == "extraction"
        assert stats.start_time == 1000.0
        assert stats.end_time is None
        assert stats.files_processed == 0
        assert stats.files_moved == 0
        assert stats.files_skipped == 0
        assert stats.errors == 0
        assert stats.aborted is False
    
    def test_duration(self):
        """Test duration calculation."""
        stats = OperationStats(
            operation_type="extraction",
            start_time=1000.0
        )
        
        # No end time
        assert stats.duration is None
        
        # With end time
        stats.end_time = 1010.5
        assert stats.duration == 10.5
    
    def test_success_rate(self):
        """Test success rate calculation."""
        stats = OperationStats(
            operation_type="extraction",
            start_time=1000.0
        )
        
        # No files processed
        assert stats.success_rate == 0.0
        
        # Some files processed
        stats.files_processed = 10
        stats.files_moved = 8
        assert stats.success_rate == 80.0
        
        # All files processed
        stats.files_processed = 10
        stats.files_moved = 10
        assert stats.success_rate == 100.0


class TestStateManager:
    """Test StateManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = StateManager()
    
    def test_operation_lifecycle(self):
        """Test operation start and end."""
        # Start operation
        op_id = self.manager.start_operation("extraction")
        
        assert op_id is not None
        assert op_id.startswith("extraction_")
        assert "_1" in op_id or "_2" in op_id  # Contains counter
        assert self.manager.get_current_operation_id() == op_id
        
        # Get stats
        stats = self.manager.get_operation_stats(op_id)
        assert stats is not None
        assert stats.operation_type == "extraction"
        assert stats.start_time > 0
        assert stats.end_time is None
        
        # End operation
        time.sleep(0.01)  # Ensure some time passes
        self.manager.end_operation(op_id)
        
        # Check stats updated
        stats = self.manager.get_operation_stats(op_id)
        assert stats.end_time is not None
        assert stats.end_time > stats.start_time
        assert self.manager.get_current_operation_id() is None
    
    def test_update_operation_stats(self):
        """Test updating operation statistics."""
        op_id = self.manager.start_operation("extraction")
        
        # Update counters
        self.manager.update_operation_stats(op_id, files_processed=5)
        self.manager.update_operation_stats(op_id, files_moved=3)
        self.manager.update_operation_stats(op_id, errors=1)
        
        stats = self.manager.get_operation_stats(op_id)
        assert stats.files_processed == 5
        assert stats.files_moved == 3
        assert stats.errors == 1
        
        # Increment counters
        self.manager.update_operation_stats(op_id, files_processed=2)
        stats = self.manager.get_operation_stats(op_id)
        assert stats.files_processed == 7
    
    def test_abort_handling(self):
        """Test abort request handling."""
        assert not self.manager.is_abort_requested()
        
        # Request abort
        self.manager.request_abort()
        assert self.manager.is_abort_requested()
        
        # Get abort signal
        signal = self.manager.get_abort_signal()
        assert signal.is_set()
        
        # Clear abort
        self.manager.clear_abort()
        assert not self.manager.is_abort_requested()
        assert not signal.is_set()
    
    def test_state_values(self):
        """Test state value storage."""
        # Set single value
        self.manager.set_value("key1", "value1")
        assert self.manager.get_value("key1") == "value1"
        assert self.manager.get_value("nonexistent", "default") == "default"
        
        # Update multiple values
        self.manager.update_values({
            "key2": "value2",
            "key3": 123
        })
        assert self.manager.get_value("key2") == "value2"
        assert self.manager.get_value("key3") == 123
    
    def test_event_listeners(self):
        """Test event listener functionality."""
        mock_listener = Mock()
        
        # Add listener
        self.manager.add_listener("operation_started", mock_listener)
        
        # Start operation (should trigger listener)
        op_id = self.manager.start_operation("test")
        mock_listener.assert_called_once_with(operation_id=op_id)
        
        # Remove listener
        self.manager.remove_listener("operation_started", mock_listener)
        mock_listener.reset_mock()
        
        # Start another operation (should not trigger)
        self.manager.start_operation("test2")
        mock_listener.assert_not_called()
    
    def test_state_change_listener(self):
        """Test state change notifications."""
        mock_listener = Mock()
        self.manager.add_listener("state_changed", mock_listener)
        
        # Set value (should trigger)
        self.manager.set_value("test_key", "test_value")
        mock_listener.assert_called_once_with(
            key="test_key",
            old_value=None,
            new_value="test_value"
        )
        
        # Set same value (should not trigger)
        mock_listener.reset_mock()
        self.manager.set_value("test_key", "test_value")
        mock_listener.assert_not_called()
    
    def test_save_and_load_state(self):
        """Test state persistence."""
        # Set up some state
        op_id = self.manager.start_operation("extraction")
        self.manager.update_operation_stats(op_id, files_processed=10, files_moved=8)
        self.manager.end_operation(op_id)
        self.manager.set_value("last_path", "/test/path")
        
        # Save state
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            self.manager.save_state(temp_path)
            
            # Create new manager and load state
            new_manager = StateManager()
            new_manager.load_state(temp_path)
            
            # Check state restored
            assert new_manager.get_value("last_path") == "/test/path"
            
            # Check operations restored
            loaded_stats = new_manager.get_operation_stats(op_id)
            assert loaded_stats is not None
            assert loaded_stats.files_processed == 10
            assert loaded_stats.files_moved == 8
        
        finally:
            temp_path.unlink(missing_ok=True)
    
    def test_clear(self):
        """Test clearing all state."""
        # Set up state
        op_id = self.manager.start_operation("test")
        self.manager.set_value("key", "value")
        self.manager.request_abort()
        
        # Clear
        self.manager.clear()
        
        # Check everything cleared
        assert self.manager.get_current_operation_id() is None
        assert self.manager.get_operation_stats(op_id) is None
        assert self.manager.get_value("key") is None
        assert not self.manager.is_abort_requested()
    
    def test_thread_safety(self):
        """Test thread-safe operations."""
        results = []
        errors = []
        
        def worker(worker_id):
            try:
                for i in range(10):
                    # Start operation
                    op_id = self.manager.start_operation(f"worker_{worker_id}")
                    
                    # Update stats
                    self.manager.update_operation_stats(op_id, files_processed=1)
                    
                    # Set value
                    self.manager.set_value(f"worker_{worker_id}_value", i)
                    
                    # End operation
                    self.manager.end_operation(op_id)
                    
                    results.append((worker_id, i))
            except Exception as e:
                errors.append(e)
        
        # Run multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Check results
        assert len(errors) == 0
        assert len(results) == 50  # 5 workers * 10 iterations
        
        # Check all operations recorded
        all_ops = self.manager.get_all_operations()
        assert len(all_ops) == 50


class TestManagedOperation:
    """Test ManagedOperation context manager."""
    
    def test_context_manager(self):
        """Test basic context manager usage."""
        manager = StateManager()
        
        with ManagedOperation(manager, "test_op") as op:
            # Check operation started
            assert op.operation_id is not None
            assert manager.get_current_operation_id() == op.operation_id
            
            # Update stats
            op.update_stats(files_processed=5, files_moved=3)
            
            # Check abort signal available
            assert op.abort_signal is not None
        
        # Check operation ended
        assert manager.get_current_operation_id() is None
        stats = manager.get_operation_stats(op.operation_id)
        assert stats.end_time is not None
        assert stats.files_processed == 5
        assert stats.files_moved == 3
    
    def test_exception_handling(self):
        """Test operation ends even with exception."""
        manager = StateManager()
        op_id = None
        
        try:
            with ManagedOperation(manager, "test_op") as op:
                op_id = op.operation_id
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Check operation still ended
        assert manager.get_current_operation_id() is None
        stats = manager.get_operation_stats(op_id)
        assert stats is not None
        assert stats.end_time is not None


def test_global_state_manager():
    """Test global state manager functions."""
    # Reset first
    reset_state_manager()
    
    # Get instance
    manager1 = get_state_manager()
    manager2 = get_state_manager()
    
    # Should be same instance
    assert manager1 is manager2
    
    # Test it works
    manager1.set_value("test", "value")
    assert manager2.get_value("test") == "value"
    
    # Reset
    reset_state_manager()
    manager3 = get_state_manager()
    
    # Should be new instance
    assert manager3 is not manager1
    assert manager3.get_value("test") is None