"""Redis-based rate limiter for Claude API calls.

Enforces CLAUDE_MAX_TOKENS_PER_HOUR and CLAUDE_MAX_CONCURRENT_CALLS
from application config using Redis counters.
"""

from __future__ import annotations

import time

import structlog
from redis import Redis

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


class RateLimitExceeded(Exception):
    """Raised when Claude API rate limit is exceeded."""

    def __init__(self, reason: str, retry_after: int = 60) -> None:
        self.reason = reason
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded: {reason}")


class ClaudeRateLimiter:
    """Redis-based rate limiter for Claude API usage.

    Uses:
    - Sliding window counter for tokens per hour (``claude:tokens:{hour}``)
    - Counter for concurrent calls (``claude:concurrent``)

    Methods:
        acquire(estimated_tokens): Check limits before API call, increment concurrent.
        release(): Decrement concurrent counter after call completes.
        record_usage(actual_tokens): Record actual token usage after call.
    """

    _TOKEN_KEY_PREFIX = "claude:tokens"
    _CONCURRENT_KEY = "claude:concurrent"
    _WINDOW_SECONDS = 3600  # 1 hour

    def __init__(self) -> None:
        settings = get_settings()
        redis_url = str(settings.REDIS_URL)
        self._redis = Redis.from_url(redis_url, decode_responses=True)
        self._max_tokens = settings.CLAUDE_MAX_TOKENS_PER_HOUR
        self._max_concurrent = settings.CLAUDE_MAX_CONCURRENT_CALLS

    def _token_key(self) -> str:
        """Current hour token counter key."""
        hour = int(time.time()) // self._WINDOW_SECONDS
        return f"{self._TOKEN_KEY_PREFIX}:{hour}"

    def acquire(self, estimated_tokens: int = 2000) -> bool:
        """Check rate limits and acquire a concurrent slot.

        Args:
            estimated_tokens: Estimated tokens for the upcoming call.

        Returns:
            True if acquired successfully.

        Raises:
            RateLimitExceeded: If token or concurrent limit is exceeded.
        """
        # Check token limit
        token_key = self._token_key()
        current_tokens = int(self._redis.get(token_key) or 0)

        if current_tokens + estimated_tokens > self._max_tokens:
            remaining = self._max_tokens - current_tokens
            logger.warning(
                "claude_rate_limit.tokens_exceeded",
                current=current_tokens,
                estimated=estimated_tokens,
                max=self._max_tokens,
                remaining=remaining,
            )
            raise RateLimitExceeded(
                f"Token limit: {current_tokens}/{self._max_tokens} used, need {estimated_tokens}",
                retry_after=60,
            )

        # Check concurrent limit
        concurrent = int(self._redis.get(self._CONCURRENT_KEY) or 0)
        if concurrent >= self._max_concurrent:
            logger.warning(
                "claude_rate_limit.concurrent_exceeded",
                current=concurrent,
                max=self._max_concurrent,
            )
            raise RateLimitExceeded(
                f"Concurrent limit: {concurrent}/{self._max_concurrent}",
                retry_after=10,
            )

        # Increment concurrent counter
        self._redis.incr(self._CONCURRENT_KEY)
        self._redis.expire(self._CONCURRENT_KEY, self._WINDOW_SECONDS)

        logger.debug(
            "claude_rate_limit.acquired",
            concurrent=concurrent + 1,
            tokens_used=current_tokens,
        )
        return True

    def release(self) -> None:
        """Release a concurrent slot after API call completes."""
        current = int(self._redis.get(self._CONCURRENT_KEY) or 0)
        if current > 0:
            self._redis.decr(self._CONCURRENT_KEY)

    def record_usage(self, actual_tokens: int) -> None:
        """Record actual token usage after API call.

        Args:
            actual_tokens: Actual tokens consumed by the call.
        """
        token_key = self._token_key()
        pipe = self._redis.pipeline()
        pipe.incrby(token_key, actual_tokens)
        pipe.expire(token_key, self._WINDOW_SECONDS)
        pipe.execute()

        logger.debug(
            "claude_rate_limit.usage_recorded",
            tokens=actual_tokens,
        )

    def get_usage(self) -> dict:
        """Get current usage stats.

        Returns:
            dict with tokens_used, tokens_limit, concurrent, concurrent_limit.
        """
        token_key = self._token_key()
        return {
            "tokens_used": int(self._redis.get(token_key) or 0),
            "tokens_limit": self._max_tokens,
            "concurrent": int(self._redis.get(self._CONCURRENT_KEY) or 0),
            "concurrent_limit": self._max_concurrent,
        }


# Module-level singleton (lazy init)
_limiter: ClaudeRateLimiter | None = None


def get_rate_limiter() -> ClaudeRateLimiter:
    """Get or create the singleton rate limiter.

    Returns:
        ClaudeRateLimiter instance.
    """
    global _limiter  # noqa: PLW0603
    if _limiter is None:
        _limiter = ClaudeRateLimiter()
    return _limiter
