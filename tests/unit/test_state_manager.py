"""
Unit tests for state manager module.
"""
import time
import threading
from unittest.mock import Mock
from pathlib import Path
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


class TestStateManagerEdgeCases:
    """Test edge cases and error handling for state manager."""

    def test_aborted_flag_can_be_set_directly(self):
        """Operation can be marked as aborted via update_operation_stats."""
        manager = StateManager()
        op_id = manager.start_operation("test")

        manager.update_operation_stats(op_id, aborted=True)

        stats = manager.get_operation_stats(op_id)
        assert stats.aborted is True

    def test_faulty_listeners_do_not_break_operations(self):
        """A listener that raises an exception does not prevent operations from completing."""
        manager = StateManager()
        successful_listener = Mock()

        def faulty_listener(**kwargs):
            raise RuntimeError("Listener error")

        # Add both listeners
        manager.add_listener("operation_started", faulty_listener)
        manager.add_listener("operation_started", successful_listener)

        # Operation should still complete and notify working listeners
        op_id = manager.start_operation("test")

        assert op_id is not None
        successful_listener.assert_called_once()

    def test_faulty_state_change_listener_does_not_prevent_state_update(self):
        """A faulty state_changed listener does not prevent state from being updated."""
        manager = StateManager()

        def faulty_listener(**kwargs):
            raise RuntimeError("Listener error")

        manager.add_listener("state_changed", faulty_listener)

        # State should still be set despite listener failure
        manager.set_value("key", "value")
        assert manager.get_value("key") == "value"

    def test_load_state_preserves_existing_state_on_missing_file(self):
        """Loading from a nonexistent file preserves existing state."""
        manager = StateManager()
        manager.set_value("existing", "value")

        manager.load_state(Path("/nonexistent/path/state.json"))

        assert manager.get_value("existing") == "value"

    def test_can_end_non_current_operation(self):
        """Operations can be ended out of order."""
        manager = StateManager()

        op_id_1 = manager.start_operation("first")
        op_id_2 = manager.start_operation("second")

        # End the first one (not the current)
        manager.end_operation(op_id_1)

        # Current operation unchanged
        assert manager.get_current_operation_id() == op_id_2

        # First operation properly ended
        stats = manager.get_operation_stats(op_id_1)
        assert stats.end_time is not None

    def test_update_stats_ignores_unknown_operations(self):
        """Updating stats for unknown operation is a no-op."""
        manager = StateManager()

        # Create a real operation to verify state is not corrupted
        real_op_id = manager.start_operation("real")
        manager.update_operation_stats(real_op_id, files_processed=10)

        # Update unknown operation
        manager.update_operation_stats("nonexistent_id", files_processed=5)

        # Unknown operation has no stats
        assert manager.get_operation_stats("nonexistent_id") is None

        # Real operation unaffected
        assert manager.get_operation_stats(real_op_id).files_processed == 10

    def test_end_unknown_operation_is_safe(self):
        """Ending an unknown operation does not affect existing operations."""
        manager = StateManager()

        op_id = manager.start_operation("test")

        manager.end_operation("nonexistent_id")

        # Existing operation still active
        assert manager.get_current_operation_id() == op_id
        assert manager.get_operation_stats(op_id).end_time is None


def test_global_state_manager_is_lazily_initialized():
    """get_state_manager creates a new instance on first access."""
    import folder_extractor.core.state_manager as sm

    sm._state_manager = None

    manager = get_state_manager()

    assert manager is not None
    assert isinstance(manager, StateManager)

    # Clean up
    reset_state_manager()


class TestEventListenerBehavior:
    """Test event listener registration and notification behavior."""

    def test_multiple_listeners_receive_same_event(self):
        """Multiple listeners registered for the same event all get notified."""
        manager = StateManager()

        listener1 = Mock()
        listener2 = Mock()

        manager.add_listener("test_event", listener1)
        manager.add_listener("test_event", listener2)

        manager._notify_listeners("test_event", data="test")

        listener1.assert_called_once_with(data="test")
        listener2.assert_called_once_with(data="test")

    def test_remove_listener_for_unregistered_event_is_safe(self):
        """Removing a listener for an event that was never registered does not affect other events."""
        manager = StateManager()
        registered_listener = Mock()

        manager.add_listener("real_event", registered_listener)

        # Remove from non-existent event
        manager.remove_listener("nonexistent_event", Mock())

        # Real event still works
        manager._notify_listeners("real_event")
        registered_listener.assert_called_once()


class TestManagedOperationSafety:
    """Test ManagedOperation handles edge cases safely."""

    def test_exit_without_enter_does_not_corrupt_manager(self):
        """Calling __exit__ without __enter__ leaves manager in valid state."""
        manager = StateManager()
        existing_op = manager.start_operation("existing")

        managed = ManagedOperation(manager, "test")
        # Deliberately skip __enter__
        managed.__exit__(None, None, None)

        # Manager state is not corrupted
        assert manager.get_current_operation_id() == existing_op

    def test_update_stats_without_enter_is_ignored(self):
        """Calling update_stats before __enter__ has no effect."""
        manager = StateManager()
        existing_op = manager.start_operation("existing")
        manager.update_operation_stats(existing_op, files_processed=10)

        managed = ManagedOperation(manager, "test")
        # Deliberately skip __enter__
        managed.update_stats(files_processed=5)

        # Existing operation unaffected
        assert manager.get_operation_stats(existing_op).files_processed == 10


class TestUpdateOperationStatsFiltering:
    """Test that update_operation_stats only updates known attributes."""

    def test_unknown_attributes_are_silently_ignored(self):
        """Passing unknown attribute names to update_operation_stats has no effect."""
        manager = StateManager()
        op_id = manager.start_operation("test")

        manager.update_operation_stats(op_id, unknown_attribute=123, another_fake=456)

        # Known attributes still at initial values
        stats = manager.get_operation_stats(op_id)
        assert stats.files_processed == 0
        assert stats.files_moved == 0
        assert stats.errors == 0

    def test_known_attributes_are_incremented(self):
        """Known counter attributes are incremented, not replaced."""
        manager = StateManager()
        op_id = manager.start_operation("test")

        manager.update_operation_stats(op_id, files_processed=5)
        manager.update_operation_stats(op_id, files_processed=3)

        stats = manager.get_operation_stats(op_id)
        assert stats.files_processed == 8  # 5 + 3, not 3