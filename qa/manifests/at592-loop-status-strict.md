# Manifest — at592-loop-status-strict

**Unit:** `autotester loop-status --strict` must exit non-zero whenever `qa/.last-tick` has ticks
but none of them is credible (every stamp is future-dated), the exact CORRUPT state
`report_lines` already renders — non-strict output and exit code unchanged.
**Contract:** no `qa/contracts/` file names `loop-status` (the only "loop" contract,
`qa/contracts/agent-loop.md`, is T-080's unrelated agent-fallback-retry loop). Judged against
`qa/contracts/core-invariants.md`'s general verify-with-real-output discipline; no criterion
number applies. Flagged for the checker to decide whether a `loop-status` contract is warranted.
**Date:** 2026-09-26
**Fix cycle:** 1 of 3
**Dual check:** no
**Persona walk:** skip (CLI only)
**Issues addressed:** AT-592
**Executor:** claude-sonnet-subagent

## The gap (AT-592, as filed)

`LoopStatus.asleep_now` (`src/autotester/loop_status.py`) only fires off the OPEN gap that
`find_gaps` returns, and `find_gaps` over an empty `credible` list (every raw tick excluded as
future-dated) returns `((), None)` — no gap for `asleep_now` to key off. So a tick log where
every stamp is dated after `now` made `--strict` exit 0, even though the very same run's
`report_lines` output was already printing `ticks: 1 · last: none credible — every stamp is dated
after now` plus a `CORRUPT: ... dated after now ... alive indefinitely (AT-399)` row. CI/session
hooks calling `--strict` were told the loop was fine while the tool's own text called it corrupt.
Filed by `checker-unit` off the at424-loop-status-future cycle-1 check
(`qa/verdicts/at424-loop-status-future.md`, which scoped its own PASS to rendering only and
explicitly deferred the `--strict` exit-code bug to this issue).

## What changed

- `src/autotester/loop_status.py:123-138` — new `LoopStatus.strict_unhealthy` property:
  `return self.asleep_now or (self.ticks > 0 and self.last_tick is None)`. Added after
  `retro_blind` (same class, same style of one-liner-with-a-docstring-explaining-why). Covers two
  cases: the loop is silently asleep right now (`asleep_now`, unchanged), OR there are ticks but
  none survived as credible (the AT-592 case `asleep_now` cannot see because it has no gap to
  reason about). `asleep_now` itself, `find_gaps`, `read_ticks`, `report_lines` and `status` are
  all unchanged — this is additive, not a rewrite of the existing gap arithmetic.
- `src/autotester/cli_loop.py:33-39` (`loop_status_cmd`) — the exit line changed from
  `raise typer.Exit(1 if (strict and report.asleep_now) else 0)` to
  `raise typer.Exit(1 if (strict and report.strict_unhealthy) else 0)`. Nothing else in the
  function changed: the printed report lines, the non-strict path, and the `--hours` option are
  byte-identical to before.
- `tests/test_loop_status_integrity.py` — 5 tests added (29 total across the two loop-status test
  files, up from 24):
  - `test_strict_unhealthy_is_true_when_every_stamp_is_future` (line 177) and
    `test_strict_unhealthy_is_false_on_a_healthy_log` (line 190) — property-level, using the
    module's existing `status(root, now=...)` fixed-clock pattern.
  - `test_cli_strict_exits_nonzero_on_an_all_future_tick_log` (line 213),
    `test_cli_strict_exits_zero_on_a_healthy_tick_log` (line 226), and
    `test_cli_non_strict_exit_code_on_the_corrupt_log_is_unchanged` (line 240) — CLI-level, via
    `typer.testing.CliRunner` against the real `autotester.cli.app`, using `AUTOTESTER_ROOT`
    (the project's existing override mechanism, same pattern as `tests/test_approve_cli.py`) and
    real wall-clock `datetime.now(UTC)` timestamps, since `loop_status_cmd` takes no `now=`
    parameter and always reads the real clock.
  - Added imports: `timedelta`, `pytest`, `typer.testing.CliRunner`, `autotester.cli.app`; module-
    level `runner = CliRunner()`; small `_cli_tick_log` and `cli_root` fixture helpers, mirroring
    the file's existing `_tick_log` helper.
- `docs/MAP.md` — not regenerated; no new module was added, only a property and a CLI condition,
  so `autotester map`'s output is unaffected (confirmed no diff would occur: no new file, no new
  top-level symbol module `map` tracks).

## How to verify (commands + actual outputs)

```
$ uv run pytest tests/test_loop_status.py tests/test_loop_status_integrity.py
.............................                                            [100%]
29 passed in 0.25s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

RAM-gated gap: the full suite (`uv run pytest`, no target) was **not** run this cycle — only the
two loop-status test files plus ruff/doctor, per the standing RAM-low instruction. Declared, not
hidden.

## Capability coverage (each claim -> its isolating falsification)

Falsified in a throwaway plain-file copy OUTSIDE the tracked worktree
(`cp -r <worktree> <scratchpad>/at592-falsify`, own `uv run`-managed venv — `uv run pytest` inside
that copy built its own `.venv` there, confirmed working before any mutation). Each edit is a
single hunk, applied, run, then reverted; the tracked worktree was never touched (`git status`
inside the worktree showed only the 3 intended files, both before and after this falsification
round — see "Actual outputs" below).

| claim | falsifying edit (single hunk, in the throwaway copy) | check | observed |
|---|---|---|---|
| `--strict` exits non-zero on an all-future log (the bug itself, driven through the real CLI) | `src/autotester/cli_loop.py:39` — `raise typer.Exit(1 if (strict and report.strict_unhealthy) else 0)` -> `raise typer.Exit(1 if (strict and report.asleep_now) else 0)` (the original, buggy condition) | `test_cli_strict_exits_nonzero_on_an_all_future_tick_log` | PASS before. FAIL after: `assert result.exit_code != 0` fails — `0 != 0` — reproducing the exact filed bug (exit 0 while output shows `CORRUPT`/`last: none credible`) |
| `LoopStatus.strict_unhealthy` itself covers the no-credible-tick case, not just `asleep_now` | `src/autotester/loop_status.py:138` — `return self.asleep_now or (self.ticks > 0 and self.last_tick is None)` -> `return self.asleep_now` | `test_strict_unhealthy_is_true_when_every_stamp_is_future`, `test_cli_strict_exits_nonzero_on_an_all_future_tick_log` | PASS before. FAIL after: both fail — `strict_unhealthy` collapses back to the old, insufficient `asleep_now` signal and misses the all-future case again |

Before/after (mutation 1, `cli_loop.py:39`):
```
--- before ---
    raise typer.Exit(1 if (strict and report.strict_unhealthy) else 0)
--- after ---
    raise typer.Exit(1 if (strict and report.asleep_now) else 0)
```
```
F.                                                                       [100%]
FAILED tests/test_loop_status_integrity.py::test_cli_strict_exits_nonzero_on_an_all_future_tick_log
AssertionError: ticks: 1 . last: none credible . every stamp is dated after now
    CORRUPT: 1 tick stamp(s) dated after now . excluded from the gap arithmetic ...
assert 0 != 0
```
Reverted; re-ran `-k cli_strict` -> `2 passed`.

Before/after (mutation 2, `loop_status.py:138`):
```
--- before ---
        return self.asleep_now or (self.ticks > 0 and self.last_tick is None)
--- after ---
        return self.asleep_now
```
```
FAILED tests/test_loop_status_integrity.py::test_strict_unhealthy_is_true_when_every_stamp_is_future
AssertionError: the new one must see it anyway
assert False is True
FAILED tests/test_loop_status_integrity.py::test_cli_strict_exits_nonzero_on_an_all_future_tick_log
AssertionError: ...
assert 0 != 0
2 failed, 3 passed
```
Reverted; re-ran the full pair of loop-status test files in the throwaway copy -> `29 passed in
0.42s`. Tracked worktree `git diff --stat` immediately after, confirming it was never touched:
```
src/autotester/cli_loop.py          |  5 ++-
src/autotester/loop_status.py       | 17 ++++++++
tests/test_loop_status_integrity.py | 86 ++++++++++++++++++++++++++++++++++++-
3 files changed, 106 insertions(+), 2 deletions(-)
```
(exactly the 3 files this unit intended to change, nothing from the falsification copy).

**Not separately falsified:** the two "keeps old behaviour" claims (healthy log -> exit 0 under
`--strict`; corrupt log -> exit 0 without `--strict`) are exercised by
`test_cli_strict_exits_zero_on_a_healthy_tick_log` and
`test_cli_non_strict_exit_code_on_the_corrupt_log_is_unchanged`, both of which passed against the
real fix without needing a dedicated falsification — they pin *unchanged* behaviour, which the two
rows above already prove is reachable only through the new `strict_unhealthy` gate (mutation 1
shows the strict path is live; the non-strict test never calls `strict_unhealthy` at all, since
`strict=False` short-circuits the `and` before it).

## Live browser evidence

Not UI-touching — CLI-only fix. Changed paths: `src/autotester/cli_loop.py`,
`src/autotester/loop_status.py`, `tests/test_loop_status_integrity.py`.

## Known limits / gaps (disclosed, not claimed)

- Full test suite not re-run this cycle (RAM-low standing instruction) — only
  `tests/test_loop_status.py` + `tests/test_loop_status_integrity.py`, ruff, and doctor.
- No `qa/contracts/` file names `loop-status`; judged against `core-invariants.md` generally.
  Flagged for the checker to decide whether a dedicated contract criterion is warranted, per this
  unit's brief (maker does not edit `qa/contracts/`).
- `docs/MAP.md` not regenerated — no new module, symbol-level content unaffected; noted rather
  than silently skipped.
- This fix intentionally does **not** extend `strict_unhealthy` to `anomalies.out_of_order` alone
  (out-of-order ticks with a credible `last_tick` and no open gap). AT-592's filed `expected`
  clause is specific to "ticks but no credible `last_tick`"; out-of-order corruption with a
  surviving credible tick was not in scope and is not covered by these tests. Flagged for the
  checker to decide whether that is a separate gap.

## Status: checked-PASS (cycle 1, qa/verdicts/at592-loop-status-strict.md c51dce5)
