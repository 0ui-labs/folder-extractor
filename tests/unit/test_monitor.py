"""Unit tests for file stability monitoring module.

Tests the StabilityMonitor class which determines when files
are fully written and ready for processing in watch mode.
"""

import logging
import threading
import time
from unittest.mock import patch

from folder_extractor.core.state_manager import StateManager


class TestStabilityMonitor:
    """Tests for StabilityMonitor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.state_manager = StateManager()
        # Import here to allow TDD - test file exists before implementation
        from folder_extractor.core.monitor import StabilityMonitor

        self.monitor = StabilityMonitor(self.state_manager)

    def test_init_stores_state_manager(self):
        """StabilityMonitor stores reference to state manager for abort checking."""
        assert self.monitor.state_manager is self.state_manager

    def test_file_ready_immediately_when_stable_and_unlocked(self, tmp_path):
        """File that is stable in size and not locked is immediately ready."""
        # Arrange: Create a file with fixed content
        test_file = tmp_path / "ready_file.txt"
        test_file.write_text("stable content")

        # Act
        start = time.time()
        result = self.monitor.wait_for_file_ready(test_file, timeout=5)
        elapsed = time.time() - start

        # Assert: File should be ready quickly (within 2 iterations)
        assert result is True
        assert elapsed < 3  # Should complete in ~2 seconds (2 stability checks)

    def test_file_growing_waits_until_stable(self, tmp_path):
        """File that is still being written to waits until size stabilizes."""
        test_file = tmp_path / "growing_file.txt"
        test_file.write_text("initial")

        # Track size checks - simulate growing then stable file
        call_count = [0]
        sizes = [100, 200, 300, 300, 300]

        original_stat = test_file.stat

        def mock_stat(*args, **kwargs):
            result = original_stat()
            # Create a new stat_result-like object with our custom size
            idx = min(call_count[0], len(sizes) - 1)
            call_count[0] += 1

            class FakeStat:
                st_size = sizes[idx]
                st_mode = result.st_mode
                st_ino = result.st_ino
                st_dev = result.st_dev
                st_nlink = result.st_nlink
                st_uid = result.st_uid
                st_gid = result.st_gid
                st_atime = result.st_atime
                st_mtime = result.st_mtime
                st_ctime = result.st_ctime

            return FakeStat()

        with patch.object(type(test_file), "stat", mock_stat):
            result = self.monitor.wait_for_file_ready(test_file, timeout=10)

        assert result is True
        assert call_count[0] >= 4  # At least 4 size checks needed

    def test_locked_file_waits_until_released(self, tmp_path):
        """File that is locked waits until lock is released."""
        test_file = tmp_path / "locked_file.txt"
        test_file.write_text("content")

        # Mock: file locked twice, then released
        lock_states = iter([True, True, False])

        with patch.object(
            self.monitor, "_is_file_locked", side_effect=lambda _: next(lock_states, False)
        ):
            result = self.monitor.wait_for_file_ready(test_file, timeout=10)

        assert result is True

    def test_timeout_when_file_never_stabilizes(self, tmp_path):
        """Returns False when file never stabilizes within timeout."""
        test_file = tmp_path / "unstable_file.txt"
        test_file.write_text("x")

        # Mock: file size keeps growing
        growing_size = [0]
        original_stat = test_file.stat

        def mock_stat(*args, **kwargs):
            growing_size[0] += 100
            real_stat = original_stat()

            class FakeStat:
                st_size = growing_size[0]
                st_mode = real_stat.st_mode
                st_ino = real_stat.st_ino
                st_dev = real_stat.st_dev
                st_nlink = real_stat.st_nlink
                st_uid = real_stat.st_uid
                st_gid = real_stat.st_gid
                st_atime = real_stat.st_atime
                st_mtime = real_stat.st_mtime
                st_ctime = real_stat.st_ctime

            return FakeStat()

        with patch.object(type(test_file), "stat", mock_stat):
            start = time.time()
            result = self.monitor.wait_for_file_ready(test_file, timeout=3)
            elapsed = time.time() - start

        assert result is False
        assert 2.0 < elapsed < 10  # Should timeout around 3 seconds (wide margin for CI)

    def test_abort_signal_stops_waiting(self, tmp_path):
        """Abort signal causes immediate return with False."""
        test_file = tmp_path / "abort_test.txt"
        test_file.write_text("content")

        # Start thread that triggers abort after short delay
        def trigger_abort():
            time.sleep(0.5)
            self.state_manager.request_abort()

        abort_thread = threading.Thread(target=trigger_abort)
        abort_thread.start()

        start = time.time()
        result = self.monitor.wait_for_file_ready(test_file, timeout=10)
        elapsed = time.time() - start

        abort_thread.join()

        assert result is False
        assert elapsed < 3  # Should abort well before 10 second timeout

    def test_nonexistent_file_returns_false_after_timeout(self, tmp_path):
        """Non-existent file returns False after timeout."""
        nonexistent = tmp_path / "does_not_exist.txt"

        start = time.time()
        result = self.monitor.wait_for_file_ready(nonexistent, timeout=2)
        elapsed = time.time() - start

        assert result is False
        assert elapsed >= 1.5  # Should wait close to timeout

    def test_is_file_locked_returns_true_on_permission_error(self, tmp_path):
        """Lock detection returns True when PermissionError occurs."""
        test_file = tmp_path / "permission_test.txt"
        test_file.write_text("content")

        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            result = self.monitor._is_file_locked(test_file)

        assert result is True

    def test_is_file_locked_returns_true_on_os_error(self, tmp_path):
        """Lock detection returns True when OSError occurs."""
        test_file = tmp_path / "os_error_test.txt"
        test_file.write_text("content")

        with patch("builtins.open", side_effect=OSError("File in use")):
            result = self.monitor._is_file_locked(test_file)

        assert result is True

    def test_is_file_locked_returns_false_on_unexpected_error(self, tmp_path, caplog):
        """Unexpected errors are logged and return False (fail-safe behavior)."""
        test_file = tmp_path / "unexpected_error_test.txt"
        test_file.write_text("content")

        with patch("builtins.open", side_effect=RuntimeError("Unexpected")):
            with caplog.at_level(logging.WARNING):
                result = self.monitor._is_file_locked(test_file)

        assert result is False  # Fail-safe: assume not locked
        assert "Unexpected error" in caplog.text

    def test_is_file_locked_returns_false_when_file_accessible(self, tmp_path):
        """Lock detection returns False when file can be opened."""
        test_file = tmp_path / "accessible_file.txt"
        test_file.write_text("content")

        # No mocking - actually try to open the file
        result = self.monitor._is_file_locked(test_file)

        assert result is False

    def test_multiple_files_can_be_monitored_sequentially(self, tmp_path):
        """Multiple files can be monitored one after another."""
        files = [tmp_path / f"file_{i}.txt" for i in range(3)]
        for f in files:
            f.write_text(f"content of {f.name}")

        results = []
        for f in files:
            results.append(self.monitor.wait_for_file_ready(f, timeout=5))

        assert all(results), "All files should be ready"

    def test_path_string_converted_to_path_object(self, tmp_path):
        """String paths are automatically converted to Path objects."""
        test_file = tmp_path / "string_path_test.txt"
        test_file.write_text("content")

        # Pass as string instead of Path
        result = self.monitor.wait_for_file_ready(str(test_file), timeout=5)

        assert result is True

    def test_zero_timeout_returns_immediately(self, tmp_path):
        """Zero timeout returns based on immediate state check."""
        test_file = tmp_path / "zero_timeout.txt"
        test_file.write_text("content")

        start = time.time()
        # With 0 timeout, should check once and return
        result = self.monitor.wait_for_file_ready(test_file, timeout=0)
        elapsed = time.time() - start

        # Should return very quickly (no waiting)
        assert elapsed < 0.5
        # Result depends on whether file passes immediate stability check
        assert isinstance(result, bool)
