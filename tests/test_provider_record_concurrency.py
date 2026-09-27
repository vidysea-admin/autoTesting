"""AT-569: `Provider.record()` must be thread-safe.

T-173's parallel run route shares ONE judge `Provider` across N worker
threads grading concurrently (`ui/routes_runs.py::_run_cases_in_parallel`).
`record()`'s accumulate-then-append (`entry.calls += 1` on a shared
`ProviderUsage` row, and the not-matched -> append path for a brand new
role) is a classic unlocked read-modify-write race: two threads can both
read the same starting value before either writes back (a lost increment),
or both see no matching row and each append their own (a duplicate role
row) — either way the run's own cost report under-reports or double-counts.
"""

from __future__ import annotations

import threading

from autotester.providers.mock import MockProvider

_TRIALS = 50
"""Repeated independent races, each with a fresh provider: the lock makes
every trial deterministic (all pass, always); without it a single trial is
flaky (observed ~1-in-8 passes by chance), so requiring ALL trials to hit
exact totals makes an unlocked record() red reliably (chance of every trial
accidentally passing is negligible) without ever flaking green when locked."""


def _hammer(provider: MockProvider, n_threads: int, calls_per_thread: int, role: str) -> None:
    barrier = threading.Barrier(n_threads)

    def worker() -> None:
        barrier.wait()  # every thread's first record() races the others
        for _ in range(calls_per_thread):
            provider.record(role, input_tokens=3, output_tokens=2)

    threads = [threading.Thread(target=worker) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def test_record_from_many_threads_loses_no_increments_and_makes_no_duplicate_row() -> None:
    """A `threading.Barrier` lines every worker up so all N threads' FIRST
    `record()` call races for the same brand-new "judge" role at once (the
    duplicate-row shape), then each keeps hammering the now-shared row for
    many more iterations (the lost-increment shape). Both must be exact, on
    every one of `_TRIALS` independent trials."""
    n_threads, calls_per_thread = 50, 40
    total_calls = n_threads * calls_per_thread
    for trial in range(_TRIALS):
        provider = MockProvider(model="mock")
        _hammer(provider, n_threads, calls_per_thread, "judge")

        assert len(provider.usage) == 1, (
            f"trial {trial}: expected exactly one 'judge' row, got {len(provider.usage)} "
            f"(a duplicate row means two threads both took the not-matched->append "
            f"branch for the same role)"
        )
        row = provider.usage[0]
        assert row.role == "judge"
        msg = f"trial {trial}: lost increments ({row.calls} != {total_calls})"
        assert row.calls == total_calls, msg
        assert row.input_tokens == total_calls * 3
        assert row.output_tokens == total_calls * 2


def test_record_of_two_roles_from_many_threads_keeps_each_roles_totals_exact() -> None:
    """Two roles hammered concurrently by the same provider instance must
    never cross-contaminate each other's counts (each role's own row is a
    separate accumulate-then-append race, guarded by the same lock)."""
    n_threads = 40
    calls_per_thread = 25
    for trial in range(_TRIALS):
        provider = MockProvider(model="mock")
        barrier = threading.Barrier(n_threads)

        def worker(idx: int, provider: MockProvider = provider, barrier=barrier) -> None:
            role = "judge" if idx % 2 == 0 else "agent"
            barrier.wait()
            for _ in range(calls_per_thread):
                provider.record(role, input_tokens=1, output_tokens=1)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert {row.role for row in provider.usage} == {"judge", "agent"}, f"trial {trial}"
        by_role = {row.role: row for row in provider.usage}
        assert by_role["judge"].calls == (n_threads // 2) * calls_per_thread, f"trial {trial}"
        assert by_role["agent"].calls == (n_threads // 2) * calls_per_thread, f"trial {trial}"
