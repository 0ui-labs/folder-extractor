"""
Unit tests for AI resilience and retry configuration module.

Tests cover:
- Retry decorator factory creation
- Default retry decorator behavior
- Exponential backoff configuration
- Exception type filtering

Note: These tests require google-generativeai which only works on Python 3.9+.
Tests are skipped if the dependency is not available.
"""

from __future__ import annotations

import asyncio

import pytest

# Skip all tests if google-generativeai is not installed (Python 3.8)
pytest.importorskip("google.api_core.exceptions")

from google.api_core.exceptions import (  # noqa: E402
    InternalServerError,
    ResourceExhausted,
    ServiceUnavailable,
)

from folder_extractor.core.ai_resilience import (  # noqa: E402
    ai_retry,
    create_ai_retry_decorator,
)


class TestCreateAIRetryDecorator:
    """Tests for create_ai_retry_decorator factory function."""

    def test_returns_callable_decorator(self):
        """Factory returns a usable decorator."""
        decorator = create_ai_retry_decorator()
        assert callable(decorator)

    def test_default_parameters_create_valid_decorator(self):
        """Default parameters produce a functional retry decorator."""
        decorator = create_ai_retry_decorator()

        @decorator
        def dummy_function():
            return "success"

        result = dummy_function()
        assert result == "success"

    def test_custom_max_attempts_is_respected(self):
        """Custom max_attempts limits retry count before re-raising original error."""
        call_count = 0

        # Use minimal wait times for faster tests
        decorator = create_ai_retry_decorator(max_attempts=3, min_wait=0, max_wait=0)

        @decorator
        def failing_function():
            nonlocal call_count
            call_count += 1
            raise ResourceExhausted("Rate limited")

        # With reraise=True, the original exception is raised after all attempts
        with pytest.raises(ResourceExhausted, match="Rate limited"):
            failing_function()

        assert call_count == 3

    def test_retries_on_resource_exhausted(self):
        """Decorator retries on ResourceExhausted (429) errors."""
        call_count = 0

        decorator = create_ai_retry_decorator(max_attempts=3, min_wait=0, max_wait=0)

        @decorator
        def eventually_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ResourceExhausted("Rate limited")
            return "success"

        result = eventually_succeeds()
        assert result == "success"
        assert call_count == 2

    def test_retries_on_internal_server_error(self):
        """Decorator retries on InternalServerError (500) errors."""
        call_count = 0

        decorator = create_ai_retry_decorator(max_attempts=3, min_wait=0, max_wait=0)

        @decorator
        def eventually_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise InternalServerError("Server error")
            return "success"

        result = eventually_succeeds()
        assert result == "success"
        assert call_count == 2

    def test_retries_on_service_unavailable(self):
        """Decorator retries on ServiceUnavailable (503) errors."""
        call_count = 0

        decorator = create_ai_retry_decorator(max_attempts=3, min_wait=0, max_wait=0)

        @decorator
        def eventually_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ServiceUnavailable("Service unavailable")
            return "success"

        result = eventually_succeeds()
        assert result == "success"
        assert call_count == 2

    def test_does_not_retry_on_value_error(self):
        """Decorator does not retry on non-retriable exceptions."""
        call_count = 0

        decorator = create_ai_retry_decorator(max_attempts=3, min_wait=0, max_wait=0)

        @decorator
        def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid input")

        with pytest.raises(ValueError, match="Invalid input"):
            raises_value_error()

        assert call_count == 1  # No retries

    def test_does_not_retry_on_runtime_error(self):
        """Decorator does not retry on RuntimeError."""
        call_count = 0

        decorator = create_ai_retry_decorator(max_attempts=3, min_wait=0, max_wait=0)

        @decorator
        def raises_runtime_error():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Runtime issue")

        with pytest.raises(RuntimeError, match="Runtime issue"):
            raises_runtime_error()

        assert call_count == 1  # No retries


class TestAIRetryDefaultDecorator:
    """Tests for the pre-configured ai_retry decorator."""

    def test_ai_retry_is_callable(self):
        """Default ai_retry decorator is callable."""
        assert callable(ai_retry)

    def test_ai_retry_decorates_sync_function(self):
        """ai_retry works with synchronous functions."""

        @ai_retry
        def sync_function():
            return "sync result"

        result = sync_function()
        assert result == "sync result"

    def test_ai_retry_decorates_async_function(self):
        """ai_retry works with asynchronous functions."""

        @ai_retry
        async def async_function():
            return "async result"

        result = asyncio.run(async_function())
        assert result == "async result"

    def test_ai_retry_retries_async_function_on_error(self):
        """ai_retry retries async functions on retriable errors."""
        call_count = 0

        # Use custom decorator with no wait for faster tests
        fast_retry = create_ai_retry_decorator(max_attempts=3, min_wait=0, max_wait=0)

        @fast_retry
        async def async_eventually_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ResourceExhausted("Rate limited")
            return "success"

        result = asyncio.run(async_eventually_succeeds())
        assert result == "success"
        assert call_count == 2


class TestRetryConfiguration:
    """Tests for retry configuration parameters."""

    def test_wait_parameters_accepted(self):
        """Wait parameters (multiplier, min_wait, max_wait) are accepted."""
        # Should not raise
        decorator = create_ai_retry_decorator(multiplier=2, min_wait=1, max_wait=60)
        assert callable(decorator)

    def test_all_parameters_can_be_customized(self):
        """All parameters can be passed to the factory."""
        # Should not raise
        decorator = create_ai_retry_decorator(
            max_attempts=10, multiplier=2, min_wait=1, max_wait=120
        )

        @decorator
        def dummy():
            return "ok"

        assert dummy() == "ok"
