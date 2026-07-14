"""
circuit_breaker.py — Resilient API call wrapper using tenacity.

Wraps exchange API calls with retry logic and a simple circuit-breaker
pattern to prevent hammering a failing endpoint.
"""
import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# Default limits
_DEFAULT_MAX_ATTEMPTS = 5
_DEFAULT_MIN_WAIT = 1.0   # seconds
_DEFAULT_MAX_WAIT = 30.0  # seconds

# Circuit-breaker state (per named circuit)
_circuits: dict[str, "_CircuitState"] = {}


class _CircuitState:
    """Simple in-process circuit state for a named circuit."""

    THRESHOLD = 5        # consecutive failures before tripping
    RESET_TIMEOUT = 60.0 # seconds before trying again in OPEN state

    def __init__(self, name: str) -> None:
        self.name = name
        self.failure_count = 0
        self.last_failure_time: float = 0.0
        self.open = False

    def record_success(self) -> None:
        self.failure_count = 0
        self.open = False

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.THRESHOLD:
            if not self.open:
                logger.warning(
                    "[CircuitBreaker] Circuit '%s' OPENED after %d failures.",
                    self.name, self.failure_count,
                )
            self.open = True

    def is_open(self) -> bool:
        if not self.open:
            return False
        if time.monotonic() - self.last_failure_time > self.RESET_TIMEOUT:
            logger.info(
                "[CircuitBreaker] Circuit '%s' transitioning to HALF-OPEN.",
                self.name,
            )
            self.open = False  # Allow one probe attempt
            self.failure_count = 0
            return False
        return True


class CircuitOpenError(Exception):
    """Raised when a circuit is open and requests are being blocked."""


def get_circuit(name: str) -> _CircuitState:
    """Return (or create) the circuit state for the given name."""
    if name not in _circuits:
        _circuits[name] = _CircuitState(name)
    return _circuits[name]


def resilient(
    circuit_name: str,
    max_attempts: int = _DEFAULT_MAX_ATTEMPTS,
    min_wait: float = _DEFAULT_MIN_WAIT,
    max_wait: float = _DEFAULT_MAX_WAIT,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """Decorator: retry with exponential back-off + circuit breaker.

    Usage::

        @resilient("binance_api")
        async def fetch_klines(...):
            ...
    """
    def decorator(func: F) -> F:
        @retry(
            retry=retry_if_exception_type(exceptions),
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            reraise=True,
        )
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            circuit = get_circuit(circuit_name)
            if circuit.is_open():
                raise CircuitOpenError(
                    f"Circuit '{circuit_name}' is OPEN. Request blocked."
                )
            try:
                result = await func(*args, **kwargs)
                circuit.record_success()
                return result
            except CircuitOpenError:
                raise
            except Exception as exc:
                circuit.record_failure()
                logger.warning(
                    "[CircuitBreaker] '%s' failure #%d: %s",
                    circuit_name, circuit.failure_count, exc,
                )
                raise

        return wrapper  # type: ignore[return-value]

    return decorator
