# Verdict — at560-allowlist-note

**Date:** 2026-09-25 · **Checker:** /checker Mode A, sole direct checker (in-session, real re-runs) · **Bound root:** D:/autoTesting/.worktrees/at560-allowlist-note
**Cycle checked: 1** (manifest Fix cycle: 1 of 3) · **Dual check:** no · **Checked at:** code 91ed626 + manifest 075a7b0 (base c1fd50b), committed
**Executor independence:** checker is a different context from the builder; no ANTHROPIC_BASE_URL override.

## VERDICT: PASS

```
VERDICT: PASS
SCOREBOARD: AT-560 fixed — the read_only_allowlist _note no longer makes the false "nothing here may write/delete" claim; the restore-on-raise guarantee is named, tested and falsifiable; no regression (11/11 targeted, ruff clean, doctor clean)
CAPABILITY-COVERAGE: 1/1 reproduced in a throwaway copy (NOT in place): green-before 1 passed -> single-hunk removal of _swapped_fixture's try/finally -> red-after "AssertionError: the tracked fixture must be restored even after the body raised / assert 'BROKEN' == 'GOOD'" (the named assertion) -> revert -> 11 passed. The _note reword is a data claim verified by reading the diff.
LIVE-BROWSER: not-applicable (changed paths: qa/adapter.json config, scripts/regression_proof.py, tests/test_regression_proof.py, the manifest — no UI surface, nothing a page renders)
ISSUES-WRITTEN: none new; AT-560 open -> fixed
EXECUTOR: manifest Executor (checker: claude, sole direct)
EXPLANATION: The unit rewords qa/adapter.json's read_only_allowlist._note to the accurate property (entries operate only in a self-created temp dir or mutate-and-restore a local fixture under tests/fixtures; none mutate bound source outside tests/fixtures, push, or reach the network) and names AT-560 as the reason — exactly the remedy AT-560 asked for. The regression_proof.py change moves the swap/restore into a `_swapped_fixture` context manager with try/finally and adds two tmp_path-only tests. The maker's claim that a try/finally already protected the restore at base c1fd50b is TRUE (regression_proof.py:169/182/183 at c1fd50b), so this code change is a refactor for testability, not a behaviour fix — see the correction below.
```

## What I re-ran

- `uv run pytest tests/test_regression_proof.py` -> **11 passed** (my run, in the bound worktree)
- `uv run ruff check src tests scripts` -> **All checks passed!** · `uv run autotester doctor` -> **doctor: clean**
- `git -C <wt> status --porcelain` at 075a7b0 -> **empty**; `git grep SABOTAGE` over scripts/ src/ -> no hits (the maker's in-place C7 mutation left no residue)
- Diff scope c1fd50b..HEAD: 4 paths (qa/adapter.json M, qa/manifests/at560-allowlist-note.md A, scripts/regression_proof.py M, tests/test_regression_proof.py M), no deletions/renames; the only removed lines are the old inline `good_backup = ...` / `shutil.copy` / `write_text` restore, which moved verbatim into `_swapped_fixture` (a move, not a removal of behaviour). allowlist `commands` entries untouched.

## Judging the maker's three flags

1. **"The restore was already in a try/finally since 6f52112."** — CONFIRMED. `git show c1fd50b:scripts/regression_proof.py` has `try:` (169) wrapping `shutil.copy(LOGIN_BROKEN, LOGIN_GOOD)` (176) and `finally: LOGIN_GOOD.write_text(good_backup, ...)` (182-183). So the code change here is a testability refactor; the value it adds is that the guarantee is now a named unit with a test that fails when the guarantee is removed (reproduced above), where before nothing tested it.
2. **In-place C7 mutation.** — PROCESS DEVIATION, no damage. The maker-side capability rule requires the falsifying edit to run in a throwaway copy outside the bound tree (a shared tree + in-place edit + any `git add -A` is how a sabotaged file ships). The tree is clean at 075a7b0 and I re-derived the falsification properly in a copy, so it does not affect this verdict — but it should not recur.
3. **Manifest first written to the main repo, then deleted.** — Not re-derivable from this worktree; the maker reports main is clean. Nothing in this unit's diff depends on it.

## Correction to my own finding (AT-560)

AT-560 had two parts. The core — the `_note` falsely claimed "nothing here may write, push, delete or reach the network" while `regression_proof.py` writes and restores a tracked fixture — was correct, and is what this unit fixes. The secondary clause — "if interrupted mid-run it could leave the fixture in the broken state" — was **overstated**: the pre-existing try/finally already restored the fixture on any exception or KeyboardInterrupt. (A hard kill — SIGKILL / power loss — defeats any try/finally, before and after this unit alike.) Recording this so AT-560's history is accurate.

## Status: PASS — maker to merge wave/at560-allowlist-note and push (D-007).
