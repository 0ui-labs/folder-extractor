"""
Unit tests for progress tracking module.
"""
import pytest
import time
from unittest.mock import Mock, MagicMock

from folder_extractor.core.progress import (
    ProgressInfo, ProgressTracker, BatchProgressTracker,
    CompositeProgressTracker
)


class TestProgressInfo:
    """Test ProgressInfo dataclass."""
    
    def test_init(self):
        """Test initialization."""
        info = ProgressInfo(current=5, total=10)
        assert info.current == 5
        assert info.total == 10
        assert info.current_file is None
        assert info.error is None
    
    def test_percentage(self):
        """Test percentage calculation."""
        # Normal case
        info = ProgressInfo(current=5, total=10)
        assert info.percentage == 50.0
        
        # Complete
        info = ProgressInfo(current=10, total=10)
        assert info.percentage == 100.0
        
        # Empty
        info = ProgressInfo(current=0, total=0)
        assert info.percentage == 100.0
    
    def test_is_complete(self):
        """Test completion check."""
        # Not complete
        info = ProgressInfo(current=5, total=10)
        assert not info.is_complete
        
        # Complete
        info = ProgressInfo(current=10, total=10)
        assert info.is_complete
        
        # Over complete
        info = ProgressInfo(current=11, total=10)
        assert info.is_complete


class TestProgressTracker:
    """Test ProgressTracker class."""
    
    def test_basic_tracking(self):
        """Test basic progress tracking."""
        callback = Mock()
        tracker = ProgressTracker(callback=callback)
        
        # Start tracking
        tracker.start(total=10)
        
        # Check initial callback
        callback.assert_called_once()
        info = callback.call_args[0][0]
        assert info.current == 0
        assert info.total == 10
        assert info.percentage == 0.0
        
        # Update progress
        callback.reset_mock()
        tracker.update(5, "/path/to/file.txt")
        
        # Should have called callback
        callback.assert_called_once()
        info = callback.call_args[0][0]
        assert info.current == 5
        assert info.total == 10
        assert info.current_file == "/path/to/file.txt"
        assert info.percentage == 50.0
        
        # Finish
        callback.reset_mock()
        tracker.finish()
        
        # Should call callback on finish
        callback.assert_called_once()
        info = callback.call_args[0][0]
        assert info.current == 10
        assert info.is_complete
    
    def test_increment(self):
        """Test increment functionality."""
        tracker = ProgressTracker()
        tracker.start(total=5)
        
        # Increment
        tracker.increment("/file1.txt")
        info = tracker.get_info()
        assert info.current == 1
        assert info.current_file == "/file1.txt"
        
        # Increment with error
        tracker.increment("/file2.txt", error="Permission denied")
        info = tracker.get_info()
        assert info.current == 2
        assert info.current_file == "/file2.txt"
        assert info.error == "Permission denied"
    
    def test_rate_limiting(self):
        """Test callback rate limiting."""
        callback = Mock()
        tracker = ProgressTracker(callback=callback, update_interval=0.1)
        
        tracker.start(total=100)
        callback.reset_mock()
        
        # Rapid updates
        for i in range(10):
            tracker.update(i)
        
        # Should have limited callbacks
        # (exact count depends on timing, but should be less than 10)
        assert callback.call_count < 10
        
        # Wait and update again
        time.sleep(0.15)
        tracker.update(50)
        
        # Should have called again after interval
        last_call_count = callback.call_count
        assert last_call_count > 0
    
    def test_time_tracking(self):
        """Test time tracking features."""
        tracker = ProgressTracker()
        tracker.start(total=10)
        
        # Check elapsed time
        time.sleep(0.05)
        elapsed = tracker.elapsed_time
        assert elapsed > 0.04
        assert elapsed < 0.1
        
        # Update progress
        tracker.update(5)
        
        # Check estimated remaining
        remaining = tracker.estimated_remaining_time
        assert remaining is not None
        assert remaining > 0
        
        # Finish and check final time
        tracker.finish()
        final_elapsed = tracker.elapsed_time
        assert final_elapsed > elapsed
    
    def test_statistics(self):
        """Test statistics generation."""
        tracker = ProgressTracker()
        tracker.start(total=10)
        
        time.sleep(0.01)
        tracker.update(5, error="Test error")
        
        stats = tracker.get_statistics()
        assert stats['current'] == 5
        assert stats['total'] == 10
        assert stats['percentage'] == 50.0
        assert stats['elapsed_time'] > 0
        assert stats['average_rate'] > 0
        assert stats['has_errors'] is True
    
    def test_boundary_conditions(self):
        """Test boundary conditions."""
        tracker = ProgressTracker()
        
        # Empty progress
        tracker.start(total=0)
        info = tracker.get_info()
        assert info.percentage == 100.0
        assert tracker.estimated_remaining_time is None
        
        # Update beyond total
        tracker.start(total=10)
        tracker.update(15)
        info = tracker.get_info()
        assert info.current == 10  # Clamped to total


class TestBatchProgressTracker:
    """Test BatchProgressTracker class."""
    
    def test_batch_tracking(self):
        """Test batch-specific functionality."""
        tracker = BatchProgressTracker(batch_size=5)
        tracker.start(total=20)
        
        # Process first batch
        tracker.start_batch()
        for i in range(5):
            if i == 2:
                tracker.increment(error="Error on item 3")
            else:
                tracker.increment()
        
        # End batch and check stats
        batch_stats = tracker.end_batch()
        assert batch_stats['items_processed'] == 5
        assert batch_stats['errors'] == 1
        assert batch_stats['success_rate'] == 80.0
        
        # Process second batch (all successful)
        tracker.start_batch()
        for i in range(5):
            tracker.increment()
        
        batch_stats = tracker.end_batch()
        assert batch_stats['items_processed'] == 5
        assert batch_stats['errors'] == 0
        assert batch_stats['success_rate'] == 100.0
    
    def test_empty_batch(self):
        """Test empty batch handling."""
        tracker = BatchProgressTracker()
        tracker.start(total=10)
        
        tracker.start_batch()
        batch_stats = tracker.end_batch()
        
        assert batch_stats['items_processed'] == 0
        assert batch_stats['errors'] == 0
        assert batch_stats['success_rate'] == 0


class TestCompositeProgressTracker:
    """Test CompositeProgressTracker class."""
    
    def test_composite_tracking(self):
        """Test delegating to multiple trackers."""
        # Create sub-trackers
        tracker1 = Mock(spec=ProgressTracker)
        tracker2 = Mock(spec=ProgressTracker)
        
        # Set up return value for get_info
        mock_info = ProgressInfo(current=5, total=10)
        tracker1.get_info.return_value = mock_info
        
        # Create composite
        composite = CompositeProgressTracker([tracker1, tracker2])
        
        # Test start
        composite.start(10)
        tracker1.start.assert_called_once_with(10)
        tracker2.start.assert_called_once_with(10)
        
        # Test update
        composite.update(5, "/file.txt", "error")
        tracker1.update.assert_called_once_with(5, "/file.txt", "error")
        tracker2.update.assert_called_once_with(5, "/file.txt", "error")
        
        # Test increment
        composite.increment("/file2.txt")
        tracker1.increment.assert_called_once_with("/file2.txt", None)
        tracker2.increment.assert_called_once_with("/file2.txt", None)
        
        # Test finish
        composite.finish()
        tracker1.finish.assert_called_once()
        tracker2.finish.assert_called_once()
        
        # Test get_info (returns from first tracker)
        info = composite.get_info()
        assert info == mock_info
    
    def test_empty_composite(self):
        """Test composite with no trackers."""
        composite = CompositeProgressTracker([])
        
        # Should not crash
        composite.start(10)
        composite.update(5)
        composite.increment()
        composite.finish()
        
        # Get info returns empty
        info = composite.get_info()
        assert info.current == 0
        assert info.total == 0