# Verdict — at620-stale-cache-docstring (AT-620)

**Date:** 2026-09-27
**Cycle checked:** 1
**Checker:** /checker session (bound to `d:/autoTesting`), unit code 54cdc4a, manifest 1693779, base a95d1f1

```
VERDICT: PASS
SCOREBOARD: 2/2 criteria met (AT-620 stale claim removed; regression test guards it), core invariants C2/C7 hold
FAILURES: none
CAPABILITY-COVERAGE: 1/1 rows reproduced (checker re-ran it in a real pytest copy, not the maker's standalone check.py)
LIVE-BROWSER: not-applicable (changed paths: src/autotester/core/redact_encodings.py, tests/test_redact_ignorable_perf.py, the manifest)
ISSUES-WRITTEN: none
EXECUTOR: claude-opus-subagent (checker: this session)
EXPLANATION: The stale sentence crediting `_is_ignorable`'s cache is replaced with a correct reference to `redact_wrap.is_ignorable_char`'s bisect table. The new test fails red when the stale text is reintroduced and passes on the fix. The diff is scoped to the two named files.
```

## What the checker re-ran

- `uv run ruff check src tests scripts` gave **All checks passed!**
- `uv run pytest tests/ -k redact` gave **139 passed**.
- `uv run autotester doctor` in the worktree reports `ledger-row-stale` for at617 (AT-617). This is branch-point staleness: master's ce1cb8c flipped AT-617 after this branch was cut. Doctor on a copy that uses master's `qa/issues.jsonl` is **clean**, which also shows `declared_secret_encodings` stays within the 50-line function cap. The finding clears on merge.
- Full `uv run pytest` gave **1 failed, 1982 passed, 6 skipped, 32 xfailed** in 12:58. The single failure is `test_flake_probe_real_process.py::test_run_once_kills_a_real_hung_process_and_its_real_grandchild` (FileNotFoundError on child.pid). That is the AT-518 flake, which also fails on master, so it is not charged to this unit.

## Capability row (re-run by the checker in its own throwaway copy)

The maker's row used a standalone `check.py`. The checker instead ran the **real** pytest test in a scratch copy of the worktree:

- **Green before:** the fixed copy passes.
- **Red after:** reintroducing the stale `` `_is_ignorable`'s cache `` sentence into `redact_encodings.py` made the test fail. The assertion that fired is the named one: "still references the removed `_is_ignorable`".

The row isolates the claim.

## Diff scope (4c)

`git diff a95d1f1...HEAD --stat` touches `redact_encodings.py`, `tests/test_redact_ignorable_perf.py` and the manifest only. Nothing was deleted or renamed. The other `_is_ignorable` mentions left in `redact_fold.py` and in test comments are dated history, correctly disclosed; none of them claims the function exists today.

## Notes (not failures)

- The new test's docstring says it checks `hasattr`, but the test actually uses `callable()`. The behaviour is stricter than the wording, so this is trivial and not filed.
- AT-620 moves open → fixed when this merge is confirmed as an ancestor of master.
