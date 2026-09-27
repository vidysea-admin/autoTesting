# Manifest — at424-loop-status-future

**Contract:** qa/contracts/core-invariants.md (a structured anomaly must be rendered, not only
computed — same lesson as AT-366/AT-396/AT-399)
**Goal task:** none
**Date:** 2026-09-25
**Fix cycle:** 1 of 3
**Dual check:** no
**Issues addressed:** AT-424

## Why this unit

AT-424 (filed by the checker): `report_lines()` in `src/autotester/loop_status.py` returned early
whenever `report.last_tick is None`, printing the flat line `"loop-status: no ticks recorded"`
before any CORRUPT row could ever be appended. That guard is true in two different situations —
a genuinely empty log (`ticks == 0`), and a log where every stamp is future-dated (`ticks > 0` but
`credible` is empty because `status()` excludes future stamps from the gap arithmetic per AT-399).
The second case is exactly the literal AT-399 scenario (a tick log stamped ~6h ahead): `status()`
correctly computed `anomalies.future == 1`, but `report_lines()` never got far enough to render it,
so a corrupt log and an untouched project rendered the identical line.

## What changed

`src/autotester/loop_status.py:186-203` (`report_lines`):

- The early-return guard now keys off `report.ticks == 0` (nothing was parsed at all) instead of
  `report.last_tick is None`. A non-zero `ticks` with no credible survivor now falls through
  instead of short-circuiting.
- When `last_tick` is `None` but `ticks > 0`, the summary row now reads
  `"ticks: N · last: none credible — every stamp is dated after now"` (level `bad`) instead of
  calling `.isoformat()` on `None` (which would have raised).
- The trailing healthy-loop all-clear (`"loop-status: no gaps"`) is now gated on
  `report.last_tick is not None` in addition to `not report.gaps`, so a corrupt, credible-tick-free
  log does not also claim to be a clean loop in the same render.

No change to `status()`, `find_gaps()`, `Anomalies`, or the CLI exit-code logic in
`src/autotester/cli_loop.py` — AT-424's `expected` is scoped to rendering, and `asleep_now`
(the CLI's `--strict` exit-code source) was not part of the filed complaint.

`tests/test_loop_status_integrity.py` — three new tests appended after the existing
`test_the_corruption_is_printed_not_only_counted`:

- `test_an_all_future_log_is_not_reported_as_no_ticks_recorded` — the literal AT-424 repro: one
  stamp 8h ahead, asserts `last_tick is None` and `anomalies.any is True` (the precondition), then
  asserts the rendered output is not `["loop-status: no ticks recorded"]` and does contain the
  CORRUPT / "dated after now" rows.
- `test_a_truly_empty_log_still_reports_no_ticks_recorded` — guards against overcorrecting: zero
  parseable ticks must still render the original line.
- `test_an_all_future_log_does_not_also_claim_no_gaps` — a corrupt, credible-tick-free log must not
  also print the healthy-loop "no gaps" all-clear.

## Real verification performed (not simulated)

```
$ uv run pytest tests/test_loop_status.py tests/test_loop_status_integrity.py -v
tests\test_loop_status.py ...............                                [ 62%]
tests\test_loop_status_integrity.py .........                            [100%]
24 passed in 0.49s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

Red-first, on the original (pre-fix) code, in the bound worktree before any fix was applied:

```
$ uv run pytest tests/test_loop_status.py tests/test_loop_status_integrity.py -v
tests\test_loop_status.py ...............                                [ 62%]
tests\test_loop_status_integrity.py ......F..                            [100%]
FAILED tests/test_loop_status_integrity.py::test_an_all_future_log_is_not_reported_as_no_ticks_recorded
AssertionError: an all-future log must never render as an empty one
assert ['loop-status: no ticks recorded'] != ['loop-status: no ticks recorded']
1 failed, 23 passed in 0.94s
```

## How to verify

- `uv run pytest tests/test_loop_status.py tests/test_loop_status_integrity.py -v` → 24 passed
- `uv run ruff check src tests scripts` → All checks passed!
- `uv run autotester doctor` → doctor: clean
- Full suite (`uv run pytest`, no `-q`) NOT run this cycle — see Gaps below.

## Capability coverage table

Each row: claim → single-hunk falsifying edit applied in a throwaway copy outside the worktree
(`C:\Users\Lenovo\AppData\Local\Temp\claude\d--autoTesting\...\scratchpad\at424-cap`, a full `cp -r`
of the worktree including its `.venv`) → the check that goes red. No tracked worktree file was ever
edited to falsify or red-test; the worktree diff is exactly the two files listed above, before and
after.

| Claim | Falsifying edit | Check that goes red |
|---|---|---|
| An all-future log no longer renders as "no ticks recorded" | Reverted the guard: `if report.ticks == 0:` → `if report.last_tick is None:` | `test_an_all_future_log_is_not_reported_as_no_ticks_recorded` fails with `['loop-status: no ticks recorded'] != ['loop-status: no ticks recorded']` |
| A corrupt, credible-tick-free log does not also claim "no gaps" | Reverted the trailing guard: `if not report.gaps and report.last_tick is not None:` → `if not report.gaps:` | `test_an_all_future_log_does_not_also_claim_no_gaps` fails: `AssertionError: a corrupt, credible-tick-free log is not a clean loop` |
| A truly empty log still says "no ticks recorded" (no overcorrection) | Not separately falsified by edit — this is the pre-existing behavior path (`ticks == 0` still hits the same early return as before); covered by `test_a_truly_empty_log_still_reports_no_ticks_recorded`, which was green both before and after the fix (guards against a future regression, not this cycle's change) |

## LIVE-BROWSER: not-applicable

This unit is a pure rendering-logic fix in `loop_status.py`; no browser, no live product surface.

## Gaps

- Full `uv run pytest` (whole suite, not just `test_loop_status*.py`) was not run this cycle — free
  RAM measured at session start was ~1.05 GB, below the 3.5 GB floor the brief set for a full-suite
  run. Targeted tests (`tests/test_loop_status.py` + `tests/test_loop_status_integrity.py`, 24
  tests, the full set touching `loop_status.py`), `ruff check`, and `autotester doctor` all ran and
  are clean. The checker should re-run the full suite if free RAM allows.
- `src/autotester/cli_loop.py`'s `--strict` exit code (`asleep_now`) was left unchanged — for an
  all-future log, `asleep_now` is still `False` (no open gap, since `credible` is empty), so the
  CLI exit code does not reflect the corruption either. That is outside AT-424's filed `expected`
  (which is scoped to the false "no ticks recorded" render), but is a related residual worth the
  checker's judgment on whether it warrants its own follow-up issue.

## Status: checked-PASS (cycle 1, 729ecc5)
