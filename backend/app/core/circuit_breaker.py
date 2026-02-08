"""Circuit breaker pattern for external API calls."""

import logging
import time
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Simple circuit breaker with in-memory state.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failures exceeded threshold, requests are rejected
    - HALF_OPEN: Testing if service recovered (allows 1 request)
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0
        self._last_success_time: float = 0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info("circuit_breaker.half_open name=%s", self.name)
        return self._state

    def can_execute(self) -> bool:
        """Check if a request can pass through."""
        current_state = self.state
        if current_state == CircuitState.CLOSED:
            return True
        if current_state == CircuitState.HALF_OPEN:
            return True
        return False

    def record_success(self) -> None:
        """Record a successful call."""
        self._failure_count = 0
        self._last_success_time = time.time()
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            logger.info("circuit_breaker.closed name=%s", self.name)

    def record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "circuit_breaker.opened name=%s failures=%s",
                self.name,
                self._failure_count,
            )

    def get_status(self) -> dict[str, str | int | float]:
        """Get circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
        }


# Global circuit breakers for external services
anthropic_breaker = CircuitBreaker("anthropic", failure_threshold=3, recovery_timeout=60)
pohoda_breaker = CircuitBreaker("pohoda", failure_threshold=3, recovery_timeout=120)
imap_breaker = CircuitBreaker("imap", failure_threshold=5, recovery_timeout=60)
