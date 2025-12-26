"""
AI resilience and retry configuration module.

Provides tenacity-based retry strategies for handling transient
failures in AI API calls (rate limits, server errors).
"""

from __future__ import annotations

import logging

from google.api_core.exceptions import (
    InternalServerError,
    ResourceExhausted,
    ServiceUnavailable,
)
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


def create_ai_retry_decorator(
    max_attempts: int = 5,
    multiplier: int = 1,
    min_wait: int = 2,
    max_wait: int = 30,
):
    """
    Create a retry decorator for AI API calls.

    Retries on:
    - ResourceExhausted (429 rate limit)
    - InternalServerError (500)
    - ServiceUnavailable (503)

    Strategy: Exponential backoff with configurable parameters.

    Args:
        max_attempts: Maximum number of retry attempts (default: 5)
        multiplier: Exponential backoff multiplier (default: 1)
        min_wait: Minimum wait time in seconds (default: 2)
        max_wait: Maximum wait time in seconds (default: 30)

    Returns:
        Configured tenacity retry decorator

    Example:
        @create_ai_retry_decorator()
        async def my_api_call():
            ...
    """
    return retry(
        retry=retry_if_exception_type(
            (ResourceExhausted, InternalServerError, ServiceUnavailable)
        ),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=multiplier, min=min_wait, max=max_wait),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


# Default retry decorator with standard settings
ai_retry = create_ai_retry_decorator()
