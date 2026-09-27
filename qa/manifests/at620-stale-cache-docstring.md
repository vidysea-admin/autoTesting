# Manifest — at620-stale-cache-docstring (AT-620)

**Unit:** AT-620 — `redact_encodings.py`'s `declared_secret_encodings` docstring still credited
`_is_ignorable`'s `lru_cache` as the real speed-up, but AT-611 removed that cache and moved the
(renamed) function to `redact_wrap.is_ignorable_char` (a bisect table lookup, no cache). Filed
against checker Mode A of at611-cjk-perf cycle 1 (equivalence lens), severity low.

**Contract:** `qa/contracts/core-invariants.md` (project-wide; C2 line/function caps, C7 verification).
**Fix cycle:** 1 of max 3
**Dual check:** no
**Persona walk: skip (backend docstring)**
**Issues addressed:** AT-620 (low, open → fixed here). Not flipped by me — `qa/issues.jsonl` is the
checker's write surface.
**Executor:** claude-opus-subagent

## What changed

Fixed in place — corrected the stale sentence only, no other docstring text reflowed or trimmed.

- **`src/autotester/core/redact_encodings.py`** (`declared_secret_encodings` docstring, was at
  line 202 in the issue's evidence, now line 202 after other AT-598/AT-606/AT-611/AT-617 history
  already ahead of it) — replaced:
  > `AT-606 cycle 1's `@lru_cache` here was unproven and retained raw secrets in memory, so cycle 2
  > drops it -- the real speed-up is `_is_ignorable`'s cache.`

  with:
  > `AT-606 cycle 1's `@lru_cache` here was unproven and retained raw secrets in memory, so cycle 2
  > drops it -- the speed-up now is `redact_wrap.is_ignorable_char`'s bisect table (AT-611).`

  First draft named the function plus "bisect lookup over its precomputed BMP range table" in full,
  which pushed `declared_secret_encodings` to 51/52 lines against the 50-line C2 cap (it was already
  at exactly 50 before this unit). Re-wrapped the same two lines to fit the correction without
  touching any of the surrounding, unrelated docstring paragraphs — net line count of the function
  unchanged (confirmed via `doctor: clean` on this check below).
- **`tests/test_redact_ignorable_perf.py`** (150 → 165 lines, under the 300-line cap) — new test
  `test_redact_encodings_docstring_does_not_credit_the_removed_lru_cache`: asserts
  `inspect.getsource(redact_encodings)` no longer contains `_is_ignorable`, and that
  `is_ignorable_char` (imported from `redact_wrap`, already imported in this file for the existing
  BMP-equivalence tests) is callable — so the test fails loudly both if the stale prose regresses
  AND if the real AT-611 rename itself ever regresses.

No other file touched. `uv run autotester map` regenerated `docs/MAP.md` byte-identical to what
was already committed — nothing to commit there.

## Other live references to `_is_ignorable` found (grep), not touched

`grep -rn "_is_ignorable" src tests`:

- **`src/autotester/core/redact_fold.py:14`** — `` `core/redact_wrap.py` also now holds
  `is_ignorable_char` (AT-611, was this module's `_is_ignorable`) `` — already correctly phrased in
  past tense as the rename record. Not stale.
- **`src/autotester/core/redact_fold.py:59, 129, 131`** — narrate the AT-351/AT-356 bug history
  (`` `_is_ignorable` is the corrected test``, etc.) using the name that function actually had *at
  that point in project history*, before the AT-611 rename. These are dated historical narrative,
  not a claim that `_is_ignorable` exists today — left alone; flagging here per instructions rather
  than silently skipping.
- **`tests/test_redact_ignorable_perf.py:2, 41`** — module docstring and
  `_original_is_ignorable`'s own docstring, both explicitly labelled as reproducing the **pre-AT-611**
  logic for comparison. Historical/intentional, not touched.
- **`tests/test_redact_obfuscation.py:40`** — a one-line comment referencing `_is_ignorable`;
  historical test comment per the brief's instruction to leave tests alone. Not touched, disclosed
  here.

Only `src/autotester/core/redact_encodings.py` had a claim that the function/cache still exists
under that name today — that's the one fixed.

## Verify — actual outputs

```
$ uv run pytest tests/ -k redact
........................................................................ [ 51%]
...................................................................      [100%]
139 passed, 1882 deselected, 1 warning in 34.33s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
ledger-row-stale: qa/manifests/at617-utf16-b64.md — AT-617 is still `open` although this unit PASSed
1 violation(s)

$ uv run autotester map
map: docs/MAP.md regenerated   # no diff — already current
```

(The 1 warning in the `-k redact` run is `starlette.testclient`'s pre-existing
`anyio.abc.BlockingPortal` deprecation notice, unrelated to this unit.)

**`ledger-row-stale` is pre-existing, not introduced by this unit.** This worktree branched from
`master` at `a95d1f1` (`merge wave/at617-utf16-b64 (checked-PASS cycle 1)`); `master` has since
advanced past that point with `ce1cb8c qa(checker): flip AT-617 fixed (merged a95d1f1)`, which
presumably updates `qa/issues.jsonl` to close AT-617. Confirmed identical
`qa/manifests/at617-utf16-b64.md` content between this worktree and current `master` (`diff` empty)
— the discrepancy is purely branch-point staleness relative to `qa/issues.jsonl`'s current state on
`master`, not anything this unit's diff touches. `qa/issues.jsonl` was not opened, edited, or
committed by this unit.

## Capability coverage (falsifying edit → named test goes red)

Falsified in a throwaway copy **outside** the worktree
(`C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/dd410a44-7522-428c-9b91-fda96de822cd/scratchpad/at620-falsify/`),
containing a standalone `check.py` (not the actual pytest test, since the real assertion needed the
installed package's import machinery) that applies the same "does `_is_ignorable` appear in the
module source" assertion directly against a copy of the fixed file and a copy with the stale
sentence manually reintroduced:

| claim | falsifying edit | check | before (fixed copy) | after (stale copy) |
|---|---|---|---|---|
| `redact_encodings.py`'s docstring no longer names `_is_ignorable` (AT-620) | reintroduced the stale sentence `` `_is_ignorable`'s cache `` into a copy of the corrected file | `check.py` (asserts `_is_ignorable` not in source) | **PASS** | **AssertionError: stale `_is_ignorable` reference found** |

The real pytest test (`test_redact_encodings_docstring_does_not_credit_the_removed_lru_cache`) makes
the identical assertion via `inspect.getsource` against the actual installed module, and was
confirmed passing in the `-k redact` run above (139 passed includes it, no failures). Not re-run
against a mutated copy of the real package in the worktree, per instruction to keep the sabotage row
in the throwaway scratch copy only — never `git stash`, no mutation of the worktree's own files.

## Live browser evidence

Not UI-touching. Changed paths: `src/autotester/core/redact_encodings.py`,
`tests/test_redact_ignorable_perf.py`, `qa/manifests/at620-stale-cache-docstring.md` (this file).

## Gaps

- **`ledger-row-stale` doctor warning present**, caused by this worktree's branch point predating a
  `qa/issues.jsonl` update already on `master` — not this unit's diff, disclosed above, will resolve
  on merge/rebase onto current `master`.
- **The falsification check ran against a hand-copied `check.py`, not the actual pytest test file**,
  because running the real test suite against a mutated copy would have required either mutating the
  worktree (disallowed) or reproducing the full package's import graph in the scratch dir (done for
  at617 previously, judged unnecessary overhead here for a docstring-only, single-string-literal
  assertion) — the assertion logic (`"_is_ignorable" not in source`) is identical in both places.
- **Historical `_is_ignorable` references in `redact_fold.py` and test files were reviewed and left
  alone** (see "Other live references" above) — a human reviewer may still want to judge whether the
  historical narrative in `redact_fold.py:59,129,131` reads clearly enough without the reader
  needing to know the AT-611 rename; left as-is since the brief scoped the fix to redact_encodings.py's
  stale claim only.

## Status: checked-PASS (cycle 1, qa/verdicts/at620-stale-cache-docstring.md a90a8961)
