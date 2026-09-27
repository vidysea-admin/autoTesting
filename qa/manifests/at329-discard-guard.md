# Manifest — at329-discard-guard
**Contract:** qa/contracts/core-invariants.md (C7 — a test that claims a kill must be shown to die when the behaviour it names is reverted)
**Goal task:** none
**Date:** 2026-09-25
**Fix cycle:** 1 of 3
**Dual check:** no
**Issues addressed:** AT-329 (medium, open -> fixed)
**Executor:** claude-sonnet-5 (maker build subagent, inline — investigation found no code change needed)

## What changed
Nothing in this branch. Investigation (below) found the fix AT-329 asks for was already
committed, on an ancestor of `wave/at329-discard-guard` (branched from master tip
`bb4be39`), and never closed out in `qa/issues.jsonl`:

- `scripts/mutation_check.py:239-264` (`_discard`) — the guard is already the two-clause
  form `not root.is_relative_to(temp) or not root.name.startswith("mutation-check-")`, and
  the docstring at `_sandbox:220-224`/`_discard:240,252-256` already narrows the promise to
  "ownership by convention... not ownership by creation (AT-329)" — the exact optional
  narrowing the issue's `expected` text offered. Landed in `14ebf9b` (2026-09-11,
  "fix(qa): defend both clauses of the cleanup guard (AT-329, AT-332)").
- `tests/test_mutation_sandbox.py:153-180` —
  `test_cleanup_refuses_a_sandbox_shaped_name_outside_the_temp_dir`, isolating the
  UNDER-TEMP clause (the gap the issue named) by monkeypatching `tempfile.gettempdir` to a
  sibling directory so a `mutation-check-`-prefixed path is provably outside it — a path
  the prefix clause alone would accept, so only the under-temp clause explains the refusal.
  Also landed in `14ebf9b`, briefly regressed to autouse-disarmed in the same commit's
  sibling unit and restored non-autouse in `c9b42ee` (2026-09-16,
  "fix(AT-384/385): drop the autouse fixture that disarmed cleanup's prefix guard") —
  `c9b42ee`'s own message names AT-329 by number as the clause it was restoring.
- `qa/evidence/at311-mutation-check/mutations-self.json:157-174` already carries both
  per-clause self-mutation entries ("cleanup under-temp clause dropped (AT-329)",
  "cleanup prefix clause dropped (AT-329)"), and `self-run.txt:49,52` records both KILLED.

Both commits are ancestors of this unit's HEAD (`bb4be39`); `git status` in the worktree is
clean. There is nothing left for this unit to add or fix — the ledger row is stale, not the
code. Flipping `qa/issues.jsonl` is the checker's job, not the maker's, per this project's
adapter contract; this manifest documents the finding for the checker to act on.

## How to verify
- `uv run pytest tests/test_mutation_sandbox.py -k cleanup_refuses -o addopts="" --no-header`
  -> both isolation tests pass
- `uv run ruff check src tests scripts` -> clean
- `uv run autotester doctor` -> clean

## Actual outputs (this unit's run, worktree HEAD bb4be39)
```
collected 9 items / 7 deselected / 2 selected
tests\test_mutation_sandbox.py ..                                        [100%]
======================= 2 passed, 7 deselected in 0.27s =======================
```
```
All checks passed!
```
```
doctor: clean
```
Free RAM at run time: ~0.8 GB. Full non-browser suite NOT run (below the 3.5 GB ceiling);
declared gap. `tests/test_mutation_check.py`'s browser-launching tests were not touched and
not run (out of scope — this unit changed nothing there).

## Capability coverage
Independently re-proved in a throwaway copy (never the worktree; deleted after), because the
recorded self-run evidence predates this unit and a maker owes its own proof, not a citation:

| clause defended | falsifying edit (`scripts/mutation_check.py`, single hunk) | check that goes red |
|---|---|---|
| under-temp (`not root.is_relative_to(temp)`) | `if not root.is_relative_to(temp) or not root.name.startswith(...)` -> `if not root.name.startswith(...)` | `test_cleanup_refuses_a_sandbox_shaped_name_outside_the_temp_dir` — before: 2 passed; after: `Failed: DID NOT RAISE MutationError` on that test, sibling `test_cleanup_refuses_to_delete_anything_it_did_not_create` stayed green (1 failed, 1 passed) |
| prefix (`not root.name.startswith("mutation-check-")`) | `if not root.is_relative_to(temp) or not root.name.startswith(...)` -> `if not root.is_relative_to(temp)` | `test_cleanup_refuses_to_delete_anything_it_did_not_create` — before: 2 passed; after: `Failed: DID NOT RAISE MutationError` on that test, `test_cleanup_refuses_a_sandbox_shaped_name_outside_the_temp_dir` stayed green (1 failed, 1 passed) |

Reproduction: copied `scripts/mutation_check.py` + `tests/test_mutation_sandbox.py` (minus
`conftest.py`, which pulls in an unrelated helper not needed by these two pure-function
tests) to a scratch dir outside the repo, ran the worktree's own `.venv` interpreter
against the scratch copy with `-k cleanup_refuses`, applied one hunk at a time, reverted
between edits. Matches `qa/evidence/at311-mutation-check/self-run.txt:49,52`
("KILLED  cleanup under-temp clause dropped (AT-329)", "KILLED  cleanup prefix clause
dropped (AT-329)") — that recorded run and this unit's independent reproduction agree.

## Live browser evidence
LIVE-BROWSER: not-applicable — pure-function guard on a `Path`, no UI surface.

## Gaps
- Full non-browser suite not run (RAM ~0.8 GB, below the 3.5 GB ceiling for a full run).
- `qa/issues.jsonl` AT-329 row is left `open` — flipping it is the checker's job per this
  project's adapter contract, not the maker's; this manifest is the evidence for that flip.
- No `mutations-self.json`/`self-run.txt` update needed — both already carry the AT-329
  entries and a recorded KILLED result from a prior run (see above), and this unit's
  independent reproduction confirms they still hold at `bb4be39`.

## Status: checked-PASS (cycle 1, 8104397)
