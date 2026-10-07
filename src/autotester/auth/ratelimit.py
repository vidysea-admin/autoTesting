"""Login rate limit (AU5): 5 failures per account or 20 per client address inside a
10-minute window refuse further attempts, correct password included, until the window
passes. In memory: counters survive a request, not a restart. Time-based, never permanent.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable

MAX_FAILURES_PER_ACCOUNT = 5
MAX_FAILURES_PER_ADDRESS = 20
WINDOW_SECONDS = 10 * 60


class LoginRateLimiter:
    """Sliding-window failure counters keyed by account email and client address."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._failures: dict[str, deque[float]] = {}

    def _recent(self, key: str, now: float) -> deque[float]:
        hits = self._failures.setdefault(key, deque())
        while hits and now - hits[0] >= WINDOW_SECONDS:
            hits.popleft()
        return hits

    def blocked(self, email: str, address: str) -> bool:
        now = self._clock()
        with self._lock:
            return (len(self._recent(f"acct:{email}", now)) >= MAX_FAILURES_PER_ACCOUNT
                    or len(self._recent(f"addr:{address}", now)) >= MAX_FAILURES_PER_ADDRESS)

    def record_failure(self, email: str, address: str) -> None:
        now = self._clock()
        with self._lock:
            self._recent(f"acct:{email}", now).append(now)
            self._recent(f"addr:{address}", now).append(now)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()


login_limiter = LoginRateLimiter()
