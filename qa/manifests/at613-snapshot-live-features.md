# Manifest — at613-snapshot-live-features (AT-613)

**Unit:** AT-613 — `autotester snapshot` could never show a newly live feature:
`ledger/render.py::_feature_lines` sorted the high-value live slice ascending by id and showed the
first `HIGH_FEATURES_SHOWN=8` (the OLDEST), and "Changed in the last N days" only admitted
UPDATED/RETIRED events. F-057/F-058/F-059 (live, high, 2026-09-26) were invisible in
`docs/SNAPSHOT.md`, the file the session-start hook injects. Filed by checker-sweep Mode B, medium.

**Contract:** `qa/contracts/living-ledger.md` L5 (lean snapshot, injected) — "live features (`high`
with reason, ...)" must actually surface what is live; `qa/contracts/core-invariants.md` C2
(line/function caps).
**Fix cycle:** 1 of max 3
**Dual check:** no
**Persona walk: skip** (generator, no UI)
**Issues addressed:** AT-613 (medium, open → fixed here). Not flipped by me —
`qa/issues.jsonl` is the checker's write surface, untouched.
**Executor:** claude-opus-subagent

## What changed

Chose one coherent rule (smallest change, per the brief): **the shown high-value slice is
newest-first by id** — ids are assigned sequentially (`store.next_id`), so a just-appended live
feature is always in the top `HIGH_FEATURES_SHOWN` instead of being pushed out by older rows. Did
not also touch the "Changed in the last N days" LIVE-event filter — the newest-first shown slice
alone already satisfies the test contract ("a just-appended live high-value feature appears in the
rendered snapshot"), and touching both would have meant two independent behavior changes for one
bug; named as a Gap below for a human call on whether LIVE should also join UPDATED/RETIRED there.

- **`src/autotester/ledger/render.py`** (`_feature_lines`, was 300/300 lines already — AT-590):
  - `shown = sorted(high, key=lambda x: x.id)` → `sorted(high, key=lambda x: x.id, reverse=True)`
    (the one-line fix).
  - Added a one-line docstring to `_feature_lines` naming the rule (AT-613), per instruction.
  - To fit the docstring under the 300-line cap without moving any code to another module,
    re-wrapped the module's own top docstring (lines 1-9, pure prose, no logic) from 6 lines to 5
    by filling to the ~100-col width instead of wrapping short — text is byte-identical, only the
    line breaks moved. Net file length: 300 → 300 (unchanged). Considered moving a helper to
    another module instead (per the brief's fallback), but nothing here is a "cohesive helper" —
    the fix is a single sort-key change, so re-wrapping an existing comment was the smaller,
    non-structural option and one concept (feature-line rendering) stays in one place.
- **`tests/test_ledger.py`** (274 → 297 lines, under the 300-line cap): extended the existing
  `test_snapshot_rolls_up_high_features_past_the_cap` (which already appends
  `HIGH_FEATURES_SHOWN + 2` live high-value features) rather than adding a new function — it already
  had the exact setup needed. Added: capture the last-appended event as `newest`, and
  `assert f"{newest.id} **{newest.title}**" in text`. This fails under the old ascending-by-id sort
  (the newest row is never in the shown-8) and passes under the fix. Chose to extend this test
  instead of writing a standalone one because a brand-new test function's mandatory 2 blank-line
  PEP8 separation would not fit inside `tests/test_ledger.py`'s existing 6-line slack under the
  300-line cap (294 lines pre-fix); reusing the existing setup keeps the file at 297.
- **`docs/SNAPSHOT.md`** regenerated via `uv run autotester snapshot` — the shown high-value slice
  now leads with F-059/F-058/F-057/F-056/... (newest-first) instead of F-002/F-003/F-004/...
  (oldest-first); F-057/F-058/F-059 are now visible, closing the bug directly.
- **`docs/MAP.md`**: `uv run autotester map` regenerated it byte-identical to what was already
  committed — nothing to commit there.

No other file touched.

## Verify — actual outputs

```
$ uv run pytest tests/test_ledger.py -k "snapshot or ledger or render"
........................                                                 [100%]
24 passed in 0.51s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester map
map: docs/MAP.md regenerated   # no diff — already current

$ uv run autotester snapshot
snapshot: 44 lines written

$ uv run autotester doctor
doctor: clean
```

Targeted tests only, per instruction — full suite (`uv run pytest` with no `-k`) not run for this
unit. Ran `map` before `snapshot`/`doctor` since AT-590/MAP staleness is doctor-enforced too; both
came back clean.

## Live browser evidence

Not UI-touching — a docs/ledger generator fix. Changed paths: `src/autotester/ledger/render.py`,
`tests/test_ledger.py`, `docs/SNAPSHOT.md`, this manifest.

## Capability coverage (falsifying edit → named test goes red)

Falsified in a throwaway copy of the whole worktree, **outside** it, at
`C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/dd410a44-7522-428c-9b91-fda96de822cd/scratchpad/at613-falsify/repo/`
(a full `cp -r` of the worktree, not a hand-built stub, since the render/store/schema import graph
is small but real — reproducing it by hand was unnecessary given the copy was free). Never used
`git stash`; the real worktree's files were never mutated for this exercise.

| claim | falsifying edit | check | before (fixed copy) | after (sabotaged copy) |
|---|---|---|---|---|
| AT-613: a just-appended live high-value feature is never pushed out of the shown slice | reverted `shown = sorted(high, key=lambda x: x.id, reverse=True)` back to `sorted(high, key=lambda x: x.id)` (the pre-fix ascending sort) in the copy only | `uv run pytest tests/test_ledger.py -k test_snapshot_rolls_up_high_features_past_the_cap` | **1 passed** | **1 failed** — `AssertionError: assert 'F-010 **OTP via email link**' in '...'` (the newest row, F-010, is absent; the old oldest-8-by-id order shows F-002..F-009 instead) |

Confirmed GREEN in the copy first (with the fix intact), then reverted the fix in the copy and
confirmed RED on exactly the named assertion, then stopped touching the copy.

## Gaps

- **"Changed in the last N days" still excludes LIVE events** (only admits UPDATED/RETIRED,
  `render.py`'s `recent` filter). Not touched — the newest-first shown-slice fix alone already
  satisfies AT-613's test contract, and the brief asked for one coherent rule, not both. A human
  may still want LIVE events to also appear under "Changed in the last N days" for symmetry with
  UPDATED/RETIRED; flagging rather than silently expanding scope.
- **The module-top docstring in `render.py` was re-wrapped** (6 lines → 5, same text) purely to
  make room for `_feature_lines`'s new one-line docstring under the 300-line cap. This is a
  whitespace-only change to unrelated prose, disclosed here per the anti-drift edit-in-place
  discipline rather than done silently.
- Not re-run against the full test suite (`uv run pytest` with no filter) — targeted tests only,
  per instruction.

## Status: checked-PASS (cycle 1, qa/verdicts/at613-snapshot-live-features.md b528a994)
