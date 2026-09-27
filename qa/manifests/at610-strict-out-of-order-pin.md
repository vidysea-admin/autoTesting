# Manifest — at610-strict-out-of-order-pin

**Unit:** Pin the AT-610 gate answer (A — keep report-only) with tests: write-order corruption
(`out_of_order > 0`) must never gate `loop-status --strict` on its own, and must still render its
CORRUPT row. No behaviour change — the code already implements answer A.
**Contract:** qa/contracts/loop-status.md LS3 (+ LS1).
**Gate:** qa/gates/at610-strict-out-of-order.md — answered 2026-09-26, A, keep report-only (Umesh
via AskUserQuestion in the maker session).
**Date:** 2026-09-26
**Fix cycle:** 1
**Dual check:** no
**Persona walk:** skip (CLI tooling)
**Issues addressed:** AT-610
**Executor:** claude-opus-subagent

## The decision (AT-610, as gated)

`loop_status.py` counts `out_of_order` over file order (around line 245/252), while liveness is
judged on the sorted credible ticks (around line 253/259). A tick file whose lines were written
out of chronological order therefore always renders a CORRUPT row, but `--strict` stays exit-0
whenever a credible recent tick survives — write-order corruption never hides an outage. Umesh
answered A: keep this report-only, pin it with tests, and let the checker add the contract
sentence (now qa/contracts/loop-status.md LS3, landed on master under D-047 while this unit was in
flight; merged into this branch — no conflicts, `docs/DECISIONS.md` and `qa/` only plus an
unrelated already-merged UI unit).

## What changed

- `src/autotester/loop_status.py` — `LoopStatus.strict_unhealthy` (property, ~line 123): no logic
  change. Added a docstring paragraph (pure addition, existing text untouched) citing
  `qa/gates/at610-strict-out-of-order.md` and recording that the property deliberately does not
  fire on `anomalies.out_of_order`.
- `tests/test_loop_status_integrity.py` — 3 tests added (32 total across the two loop-status test
  files, up from 29), under a new `# -- AT-610 --` section at the end of the file:
  - `test_out_of_order_ticks_with_a_credible_recent_tick_do_not_gate_strict` — object-level, using
    the file's existing `status(root, now=...)` fixed-clock pattern (the same tick shape as
    `test_out_of_order_ticks_are_reported_rather_than_silently_sorted`). Asserts
    `anomalies.out_of_order == 1`, `strict_unhealthy is False`, and that `report_lines` still
    renders `CORRUPT` / `out of chronological order`.
  - `test_cli_strict_zero_on_out_of_order_with_credible_tick` — CLI-level, via the file's existing
    `CliRunner`/`_cli_tick_log`/`cli_root` pattern. Two recent, real-clock ticks written out of
    order; asserts `--strict` exits 0 and `CORRUPT` is still in the output.
  - `test_cli_strict_nonzero_on_out_of_order_with_stale_tick` — CLI-level, same pattern, but the
    ticks are ~10-11 days old (out of order and genuinely stale). Asserts `--strict` still exits
    non-zero, so the report-only pin cannot mask a real outage.
- No change to `find_gaps`, `read_ticks`, `report_lines`, `status`, or `cli_loop.py` — the
  behaviour under test already matches answer A; this cycle only adds coverage and documentation.

## How to verify (commands + actual outputs)

```
$ uv run pytest tests/test_loop_status_integrity.py tests/test_loop_status.py
................................                                         [100%]
32 passed in 1.39s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

Run after merging master (f9b81f9, which carries the loop-status contract, D-047/D-048, and an
unrelated already-merged UI unit) into this branch — no full suite re-run this cycle, per the
unit's brief ("No full suite").

## Capability coverage (each claim -> its isolating falsification)

Falsified in a throwaway plain-file copy OUTSIDE the tracked worktree
(`C:/Users/Lenovo/AppData/Local/Temp/claude/.../scratchpad/at610-falsify/work` — a minimal copy of
`src/autotester/`, the two loop-status test files, `tests/conftest.py` and its two local helper
modules, and `pyproject.toml`; run with the worktree's own `.venv` interpreter and `PYTHONPATH`
pointed at the copy's `src/`, confirmed `32 passed` before any mutation). Each edit is a single
hunk, applied, run, then reverted; the tracked worktree was never touched (`git status --short`
inside the worktree showed only the 2 intended files, both before and after — see below).

| claim | falsifying edit (single hunk, in the throwaway copy) | check | observed |
|---|---|---|---|
| Out-of-order corruption alone does not gate `strict_unhealthy` / `--strict` | `src/autotester/loop_status.py` `strict_unhealthy` return: `return self.asleep_now or (self.ticks > 0 and self.last_tick is None)` -> `return (self.asleep_now or (self.ticks > 0 and self.last_tick is None) or self.anomalies.out_of_order > 0)` | `test_out_of_order_ticks_with_a_credible_recent_tick_do_not_gate_strict`, `test_cli_strict_zero_on_out_of_order_with_credible_tick` | PASS before. FAIL after: both fail — `strict_unhealthy` is `True`/`--strict` exits 1 (`assert True is False`, `assert 1 == 0`) purely off the write-order corruption, with no outage behind it |
| Out-of-order corruption is still counted and rendered (CORRUPT row), not silently dropped | `src/autotester/loop_status.py` `status()`: `out_of_order=sum(1 for earlier, later in pairwise(raw) if later < earlier),` -> `out_of_order=0,` | `test_out_of_order_ticks_with_a_credible_recent_tick_do_not_gate_strict` (report-rendering half), `test_cli_strict_zero_on_out_of_order_with_credible_tick`, `test_cli_strict_nonzero_on_out_of_order_with_stale_tick`, plus the pre-existing `test_out_of_order_ticks_are_reported_rather_than_silently_sorted` | PASS before. FAIL after: 4 tests fail — `CORRUPT` disappears from the rendered output entirely (`assert 'CORRUPT' in '...no gaps\n'` fails), including in the genuinely-asleep case |

Before/after (mutation 1, `strict_unhealthy`):
```
--- before ---
        return self.asleep_now or (self.ticks > 0 and self.last_tick is None)
--- after ---
        return (self.asleep_now or (self.ticks > 0 and self.last_tick is None)
                or self.anomalies.out_of_order > 0)
```
```
FAILED test_out_of_order_ticks_with_a_credible_recent_tick_do_not_gate_strict
AssertionError: write-order corruption alone does not gate --strict
assert True is False
FAILED test_cli_strict_zero_on_out_of_order_with_credible_tick
AssertionError: ticks: 2 . last: ...
  CORRUPT: 1 tick(s) written out of chronological order ...
assert 1 == 0
2 failed, 2 passed
```
Reverted; re-ran `-k out_of_order` -> `4 passed`.

Before/after (mutation 2, `status()` anomaly count):
```
--- before ---
        out_of_order=sum(1 for earlier, later in pairwise(raw) if later < earlier),
--- after ---
        out_of_order=0,
```
```
FAILED test_out_of_order_ticks_are_reported_rather_than_silently_sorted
FAILED test_out_of_order_ticks_with_a_credible_recent_tick_do_not_gate_strict
FAILED test_cli_strict_zero_on_out_of_order_with_credible_tick
FAILED test_cli_strict_nonzero_on_out_of_order_with_stale_tick
4 failed, 13 deselected
```
Reverted; re-ran the full pair of loop-status test files in the throwaway copy -> `32 passed in
1.54s`. Tracked worktree `git status --short` immediately after showed only:
```
 M src/autotester/loop_status.py
 M tests/test_loop_status_integrity.py
```
(the exact 2 files this unit intended to change, nothing from the falsification copy).

## Live browser evidence

Not UI-touching — CLI/test-only pin. Changed paths: `src/autotester/loop_status.py`,
`tests/test_loop_status_integrity.py`.

## Known limits / gaps (disclosed, not claimed)

- Full test suite not re-run this cycle, per the unit's own brief ("No full suite") — only the two
  loop-status test files, ruff, and doctor.
- The contract sentence itself is the checker's to add — it already landed as
  `qa/contracts/loop-status.md` LS3 while this unit was in flight (D-047), and this manifest cites
  it rather than editing it.
- The CLI-level tests for (a) and (c) use real wall-clock `datetime.now(UTC)`, matching the file's
  existing `test_cli_strict_exits_*` pattern, since `loop_status_cmd` takes no injectable `now=`.

## Status: checked-PASS (cycle 1, qa/verdicts/at610-strict-out-of-order-pin.md 11f1d4e)
