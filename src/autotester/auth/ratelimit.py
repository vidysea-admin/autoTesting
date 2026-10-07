"""Login rate limit (AU5): 5 failures per account or 20 per client address inside a
10-minute window refuse further attempts, correct password included, until the window
passes. In memory: counters survive a request, not a restart. Time-based, never permanent.

Signup uses the same counters (`signup_limiter`): 10 attempts per client address per window,
because each signup costs a 64 MiB argon2 hash. The table is bounded: expired keys are
dropped, and past MAX_TRACKED_KEYS a new key is not tracked, so a flood of unique emails
cannot grow it without limit (the per-address counter still stops that address).
"""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable

MAX_FAILURES_PER_ACCOUNT = 5
MAX_FAILURES_PER_ADDRESS = 20
MAX_SIGNUPS_PER_ADDRESS = 10
WINDOW_SECONDS = 10 * 60
MAX_TRACKED_KEYS = 50_000


class LoginRateLimiter:
    """Sliding-window failure counters keyed by account email and client address."""

    def __init__(self, clock: Callable[[], float] = time.monotonic,
                 per_account: int = MAX_FAILURES_PER_ACCOUNT,
                 per_address: int = MAX_FAILURES_PER_ADDRESS) -> None:
        self._clock = clock
        self._limits = {"acct": per_account, "addr": per_address}
        self._lock = threading.Lock()
        self._failures: dict[str, deque[float]] = {}

    def _recent(self, key: str, now: float) -> deque[float]:
        """The live hits for `key`; an emptied key is dropped, never kept."""
        hits = self._failures.get(key)
        if hits is None:
            return deque()
        while hits and now - hits[0] >= WINDOW_SECONDS:
            hits.popleft()
        if not hits:
            del self._failures[key]
        return hits

    def _purge(self, now: float) -> None:
        for key in list(self._failures):
            self._recent(key, now)

    def blocked(self, email: str, address: str) -> bool:
        now = self._clock()
        with self._lock:
            return (len(self._recent(f"acct:{email}", now)) >= self._limits["acct"]
                    or len(self._recent(f"addr:{address}", now)) >= self._limits["addr"])

    def record_failure(self, email: str, address: str) -> None:
        now = self._clock()
        with self._lock:
            if len(self._failures) >= MAX_TRACKED_KEYS:
                self._purge(now)
            for key in (f"addr:{address}", f"acct:{email}"):
                if key in self._failures or len(self._failures) < MAX_TRACKED_KEYS:
                    self._failures.setdefault(key, deque()).append(now)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()


login_limiter = LoginRateLimiter()
signup_limiter = LoginRateLimiter(per_account=MAX_SIGNUPS_PER_ADDRESS,
                                  per_address=MAX_SIGNUPS_PER_ADDRESS)
