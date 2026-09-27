# Verdict — at613-snapshot-live-features (AT-613)

**Date:** 2026-09-27
**Cycle checked:** 1
**Checker:** /checker session (bound to `d:/autoTesting`), unit code b8832fd4, manifest 07f2ec1d, base 0ecda92f

```
VERDICT: PASS
SCOREBOARD: 2/2 criteria met (living-ledger L5: newest live high-value features surface in the snapshot; regression test guards it), core invariants C2/C4/C7 hold
FAILURES: none
CAPABILITY-COVERAGE: 1/1 rows reproduced in the checker's own copy
LIVE-BROWSER: not-applicable (changed paths: src/autotester/ledger/render.py, tests/test_ledger.py, docs/SNAPSHOT.md, manifest; generator, no UI)
ISSUES-WRITTEN: none
EXECUTOR: claude-opus-subagent (checker: this session)
EXPLANATION: The shown high-value slice is now sorted newest-first by id, so a just-appended live feature is always among the HIGH_FEATURES_SHOWN rows. The regenerated SNAPSHOT.md now leads with F-059, F-058 and F-057, which were invisible before. The extended test goes red on exactly the new assertion when the old ascending sort is restored.
```

## What the checker re-ran

- `uv run ruff check src tests scripts` gave **All checks passed!**
- `uv run autotester doctor` gave **doctor: clean**. `render.py` is still 300 lines, and `docs/SNAPSHOT.md` is 44 lines, within the L5 limit of 60.
- `uv run pytest tests/test_ledger.py` gave **24 passed**.
- Full `uv run pytest` gave **1 failed, 1999 passed, 6 skipped, 32 xfailed** (12:55). The single failure is the AT-518 flake (`test_flake_probe_real_process…grandchild`, FileNotFoundError on child.pid), which also fails on master and is not charged to this unit.

## Capability row (checker's own copy, `scratchpad/at613-row1`, git archive HEAD plus docs/qa, PYTHONPATH pointed at the copy)

The copy was **green before**: `test_snapshot_rolls_up_high_features_past_the_cap` gave 1 passed. I then restored `sorted(high, key=lambda x: x.id)` and confirmed with grep that no `reverse=True` remained. It went **red after**: `AssertionError: assert 'F-010 **OTP via email link**' in '...'` at test_ledger.py:285. That is the new AT-613 assertion, not an import or setup failure.

## Diff scope (4c)

Four files changed, all listed in "What changed", and nothing was deleted or renamed.

**The module-docstring reflow the maker flagged** (render.py lines 1-9, from 6 lines to 5): I compared the old and new docstrings by their word sequences, and they are **identical**. The longest line is 99 characters. This is a whitespace-only change to prose in a file the manifest lists, and it was disclosed. 4c fails a unit only for removing or renaming existing code or config, or for touching an unlisted file, so this is **not a FAIL**.

It does go against the maker's own "do not reflow existing docstrings" brief. That rule belongs to the maker and does not appear in any contract criterion. It is noted here for the maker's process, not charged to the unit.

## Notes (not failures)

- **"Changed in the last N days" still admits only UPDATED/RETIRED events**, as the builder flagged. L5's text reads "updated/retired in last 30 days", so the current behaviour matches the contract. Adding LIVE events there would be a new requirement (a Umesh or maker scope call), not a defect.
- **The sort is by the id string.** `store.next_id` zero-pads to 3 digits, so the order stays correct up to F-999; at F-1000 a string sort would put it before F-999. The previous ascending sort had the same limit. This is too far off to file now; sorting on `int(id.split('-')[1])` would remove it.
- **The test's continuation line** (`feature=f"feat-{i}", reason="why"))`) keeps its old indent under the longer `newest = store.append_event(` call. This is cosmetic, and ruff accepts it.
- AT-613 moves open → fixed once this merge is an ancestor of master.
