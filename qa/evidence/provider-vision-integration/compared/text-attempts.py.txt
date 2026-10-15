"""Reserve physical requests across nested provider, repair and fallback scopes."""
from __future__ import annotations

import math
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from autotester.providers.base import ProviderError
from autotester.schema.provider_attempt import ProviderAttempt


class AttemptBudgetExhausted(ProviderError):
    """The shared physical-call count or elapsed deadline was exhausted."""


_SCOPES: ContextVar[tuple[AttemptBudget, ...]] = ContextVar("provider_attempts", default=())
_LOCK = threading.RLock()


class AttemptBudget:
    """A shared budget; copy_context propagates its identity to worker threads."""

    def __init__(self, max_calls: int, wall_clock_s: float | None = None) -> None:
        if isinstance(max_calls, bool) or not isinstance(max_calls, int) or max_calls < 0:
            raise ValueError("max_calls must be a nonnegative integer")
        if wall_clock_s is not None and (not math.isfinite(wall_clock_s) or wall_clock_s < 0):
            raise ValueError("wall_clock_s must be finite and nonnegative")
        self.max_calls = max_calls
        self.deadline = None if wall_clock_s is None else time.monotonic() + wall_clock_s
        self.attempts: list[ProviderAttempt] = []

    @property
    def used(self) -> int:
        return len(self.attempts)


@contextmanager
def attempt_budget(max_calls: int, wall_clock_s: float | None = None) -> Iterator[AttemptBudget]:
    """Nested budgets obey every enclosing cap; scope exit restores the caller."""
    budget = AttemptBudget(max_calls, wall_clock_s)
    token = _SCOPES.set((*_SCOPES.get(), budget))
    try:
        yield budget
    finally:
        _SCOPES.reset(token)


def reserve_attempt(provider: str, role: str, timeout_s: float) -> tuple[ProviderAttempt, float]:
    """Check every cap atomically BEFORE transport, sharing one safe receipt."""
    with _LOCK:
        scopes = _SCOPES.get()
        for scope in scopes:
            if scope.used >= scope.max_calls:
                raise AttemptBudgetExhausted("provider attempt budget exhausted: max_calls")
            if scope.deadline is not None:
                timeout_s = min(timeout_s, scope.deadline - time.monotonic())
        if timeout_s <= 0:
            raise AttemptBudgetExhausted("provider attempt budget exhausted: wall_clock_s")
        receipt = ProviderAttempt(provider=provider, role=role)
        for scope in scopes:
            scope.attempts.append(receipt)
        return receipt, timeout_s
