"""
Unit tests for core/state.py module.
"""
import threading
import time
import pytest

from folder_extractor.core.state import (
    ApplicationState,
    OperationContext,
    get_app_state,
    reset_app_state,
)


class TestApplicationState:
    """Tests for ApplicationState class."""

    def test_init(self):
        """Test ApplicationState initialization."""
        state = ApplicationState()
        assert state._abort_signal is not None
        assert isinstance(state._abort_signal, threading.Event)
        assert state._state == {}

    def test_get_abort_signal(self):
        """Test getting abort signal."""
        state = ApplicationState()
        signal = state.get_abort_signal()
        assert isinstance(signal, threading.Event)
        assert signal is state._abort_signal

    def test_request_abort(self):
        """Test requesting abort."""
        state = ApplicationState()
        assert not state.is_abort_requested()
        state.request_abort()
        assert state.is_abort_requested()

    def test_clear_abort(self):
        """Test clearing abort."""
        state = ApplicationState()
        state.request_abort()
        assert state.is_abort_requested()
        state.clear_abort()
        assert not state.is_abort_requested()

    def test_is_abort_requested(self):
        """Test checking abort status."""
        state = ApplicationState()
        assert state.is_abort_requested() is False
        state._abort_signal.set()
        assert state.is_abort_requested() is True

    def test_set_value(self):
        """Test setting a value."""
        state = ApplicationState()
        state.set_value("key1", "value1")
        assert state._state["key1"] == "value1"

    def test_get_value(self):
        """Test getting a value."""
        state = ApplicationState()
        state._state["key1"] = "value1"
        assert state.get_value("key1") == "value1"
        assert state.get_value("nonexistent") is None
        assert state.get_value("nonexistent", "default") == "default"

    def test_update_values(self):
        """Test updating multiple values."""
        state = ApplicationState()
        state.update_values({"key1": "value1", "key2": "value2"})
        assert state._state["key1"] == "value1"
        assert state._state["key2"] == "value2"

    def test_clear(self):
        """Test clearing state."""
        state = ApplicationState()
        state.set_value("key1", "value1")
        state.request_abort()
        state.clear()
        assert state._state == {}
        assert not state.is_abort_requested()

    def test_thread_safety(self):
        """Test thread-safe operations."""
        state = ApplicationState()
        results = []
        results_lock = threading.Lock()

        def writer():
            for i in range(100):
                state.set_value(f"key_{i}", i)

        def reader():
            for i in range(100):
                value = state.get_value(f"key_{i}")
                with results_lock:
                    results.append((f"key_{i}", value))

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should complete without deadlock or error
        # Verify reader collected results (values may be None if read before write)
        assert len(results) == 100
        for key, value in results:
            assert key.startswith("key_")
            # Value is either None (read before write) or the correct integer
            if value is not None:
                key_num = int(key.split("_")[1])
                assert value == key_num


class TestOperationContext:
    """Tests for OperationContext class."""

    def test_init(self):
        """Test OperationContext initialization."""
        app_state = ApplicationState()
        ctx = OperationContext(app_state)
        assert ctx.app_state is app_state
        assert ctx.operation_data == {}
        assert ctx.start_time is None
        assert ctx.end_time is None

    def test_abort_signal_property(self):
        """Test abort_signal property."""
        app_state = ApplicationState()
        ctx = OperationContext(app_state)
        assert ctx.abort_signal is app_state.get_abort_signal()

    def test_set_data(self):
        """Test setting operation data."""
        app_state = ApplicationState()
        ctx = OperationContext(app_state)
        ctx.set_data("key1", "value1")
        assert ctx.operation_data["key1"] == "value1"

    def test_get_data(self):
        """Test getting operation data."""
        app_state = ApplicationState()
        ctx = OperationContext(app_state)
        ctx.operation_data["key1"] = "value1"
        assert ctx.get_data("key1") == "value1"
        assert ctx.get_data("nonexistent") is None
        assert ctx.get_data("nonexistent", "default") == "default"

    def test_context_manager_enter(self):
        """Test context manager enter."""
        app_state = ApplicationState()
        app_state.request_abort()

        ctx = OperationContext(app_state)
        result = ctx.__enter__()

        assert result is ctx
        assert ctx.start_time is not None
        assert not app_state.is_abort_requested()  # Should be cleared

    def test_context_manager_exit(self):
        """Test context manager exit."""
        app_state = ApplicationState()
        ctx = OperationContext(app_state)
        ctx.__enter__()
        ctx.__exit__(None, None, None)

        assert ctx.end_time is not None
        assert ctx.end_time >= ctx.start_time

    def test_context_manager_with_statement(self):
        """Test using context manager with 'with' statement."""
        app_state = ApplicationState()

        with OperationContext(app_state) as ctx:
            assert ctx.start_time is not None
            ctx.set_data("operation", "test")
            time.sleep(0.01)  # Small delay

        assert ctx.end_time is not None
        assert ctx.end_time > ctx.start_time
        assert ctx.get_data("operation") == "test"

    def test_context_manager_with_exception(self):
        """Test context manager handles exceptions."""
        app_state = ApplicationState()

        with pytest.raises(ValueError):
            with OperationContext(app_state) as ctx:
                raise ValueError("Test error")

        # end_time should still be set
        assert ctx.end_time is not None


class TestGlobalState:
    """Tests for global state functions."""

    def setup_method(self):
        """Reset state before each test."""
        reset_app_state()

    def test_get_app_state(self):
        """Test getting global app state."""
        state = get_app_state()
        assert isinstance(state, ApplicationState)

    def test_get_app_state_singleton(self):
        """Test that get_app_state returns same instance."""
        state1 = get_app_state()
        state2 = get_app_state()
        assert state1 is state2

    def test_reset_app_state(self):
        """Test resetting global app state."""
        state1 = get_app_state()
        state1.set_value("test", "value")
        state1.request_abort()

        reset_app_state()

        state2 = get_app_state()
        # Should be a new instance
        assert state2 is not state1
        # State should be cleared
        assert state2.get_value("test") is None
        assert not state2.is_abort_requested()

    def test_reset_app_state_clears_existing(self):
        """Test reset clears existing state before creating new."""
        state = get_app_state()
        state.set_value("key", "value")

        reset_app_state()

        new_state = get_app_state()
        assert new_state.get_value("key") is None


def test_get_app_state_creates_when_none():
    """Test that get_app_state creates new instance when _app_state is None (line 131)."""
    import folder_extractor.core.state as state_module

    # Force _app_state to None
    state_module._app_state = None

    # Get state (should create new one)
    state = get_app_state()

    assert state is not None
    assert isinstance(state, ApplicationState)

    # Clean up
    reset_app_state()
