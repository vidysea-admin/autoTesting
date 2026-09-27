# Manifest — at611-cjk-perf (AT-611)

**Unit:** AT-611 (folded-secret scanning of CJK-heavy text still cost ~8.4 s/MB, only ~1.1x
faster than pre-AT-606, because the 4096-entry `lru_cache` on `_is_ignorable` thrashed once a
string's distinct code points exceeded it). Filed against the merged at599-606-redact-wrap-perf
work (`qa/verdicts/at599-606-redact-wrap-perf.md`, checker Mode A perf probe).

**Contract:** `qa/contracts/core-invariants.md` (project-wide; C2 line caps, C7 mutation duty).
**Fix cycle:** 1
**Dual check:** no
**Persona walk:** skip (backend-only)
**Issues addressed:** AT-611 (low, open → fixed here). Not flipped by me — `qa/issues.jsonl` is
the checker's write surface.
**Executor:** claude-opus-subagent

## Root cause (measured, not guessed)

Reproduced the checker's own numbers first, in-process against the merged master
(`Redactor.contains_folded` + `assert_no_raw_secrets`, 3 fake secrets, CJK Unified Ideographs
0x4E00-0x9FFF sampled uniformly): 100/250/500/1024 KB gave 2.6s/5.6s/10.5s/25.2s in a fresh
process on this box (noisier than the checker's 0.86/2.51/4.13/8.36s — this repo runs two loops
concurrently — but the same shape: linear, ~4-5x an ASCII input of the same size). A 1 MB CJK
corpus has ~20,992 distinct code points (measured directly) — almost exactly the entire CJK
Unified Ideographs block, and 5x the old cache's 4096-entry capacity. `_is_ignorable`
(`redact_fold.py:91`, `@functools.lru_cache(maxsize=4096)`) is called once per character of every
string `fold_credential` folds; once the working set of distinct characters exceeds the cache,
every call is a miss AND pays LRU eviction-list bookkeeping on top of the `unicodedata.category`
lookup the cache exists to avoid — strictly worse than no cache at all for this shape of input.

## Fix — a precomputed table, not a bigger cache

Tried three approaches empirically (fresh-process, best-of-3 each) before choosing:

| approach | CJK 1 MB (best of 3) | ASCII 1 MB (best of 3) | ratio |
|---|---|---|---|
| baseline (`lru_cache(maxsize=4096)`) | ~25s | ~3.0s | ~8x |
| `functools.cache` (unbounded lru_cache) | 7.28s | 2.88s | **2.53x** — at the edge of a 2.5x bound |
| precomputed BMP range table + `bisect` (chosen) | 7.10s | 5.12s | **1.39x** |

Unbounded caching alone already gives a large win (removes eviction overhead), but its ratio sat
right at the 2.5x bound on this noisy box — too little margin for a bound test that has to survive
"this repo runs two loops concurrently" (project CLAUDE.md). It also holds every distinct
character ever seen for the process lifetime with no ceiling (bounded in theory by all of Unicode,
~1.1M entries, but unmeasured in practice). The table approach gives more headroom and a fixed,
tiny footprint (21 ranges), so it is what shipped.

**`src/autotester/core/redact_wrap.py`** (had headroom; `redact_fold.py` was at the 300-line cap)
gains:
- `_DEFAULT_IGNORABLE` — moved here verbatim (not edited) from `redact_fold.py`, docstring
  unchanged except one cross-reference (`_is_ignorable` → `is_ignorable_char`).
- `_build_bmp_ignorable_ranges()` — a one-time table build (~30 ms, measured) that marks every
  Basic Multilingual Plane code point (0x0000-0xFFFF) that is category `Cf`/`Cc` or inside a
  `_DEFAULT_IGNORABLE` range, using a `bytearray` flag pass over the 17 explicit ranges FIRST and
  exactly one `unicodedata.category` call per code point after — not `any(...)` over the 17-tuple
  inside the hot loop, which measured 0.20s for the same 21-range result (7x slower than the
  bytearray-first order).
- `is_ignorable_char(ch)` (public, was `redact_fold._is_ignorable`) — for any BMP code point,
  answers with one `bisect.bisect_right` against the precomputed table: no `unicodedata` call, no
  cache, so a document with 20,000 distinct characters costs the same per character as one with
  20. Code points above the BMP (astral emoji, historic scripts, CJK Extension B+) fall back to
  the original direct computation (`category(ch) in ("Cf","Cc")` or `_DEFAULT_IGNORABLE` range
  check), uncached — rare in practice and not the path the CJK-heavy regression measured.

**`src/autotester/core/redact_fold.py`** — `_DEFAULT_IGNORABLE` and `_is_ignorable` removed
(moved out, not edited-then-deleted-elsewhere); `import functools` removed (no longer used
anywhere in this file); `fold_credential`'s `stripped = ...` line now calls `is_ignorable_char`
imported from `redact_wrap`. Net: 300 → 237 lines (well under the cap — the file shrank, it did
not grow).

**`docs/MAP.md`** — regenerated via `autotester map` (one row's summary line changed to match
`redact_wrap.py`'s widened module docstring; no `ARCHITECTURE.md` prose change).

**`tests/test_redact_ignorable_perf.py`** (new) — see below.

Result is byte-identical: `fold_credential`'s STRIP step still removes exactly the same set of
characters (proven by the equivalence test below over the full BMP, plus a stratified astral
sample); nothing about which characters are ignorable changed, only how fast the answer is
computed.

## What changed

- `src/autotester/core/redact_wrap.py` — 78 → 218 lines. Added: `_DEFAULT_IGNORABLE` (moved),
  `_build_bmp_ignorable_ranges`, `_BMP_IGNORABLE_RANGES`/`_BMP_IGNORABLE_STARTS`,
  `is_ignorable_char` (moved + rewritten). `contains_wrapped_encoding` (AT-599) untouched.
- `src/autotester/core/redact_fold.py` — 300 → 237 lines. Removed: `_DEFAULT_IGNORABLE`,
  `_is_ignorable`, `import functools`. Changed: import line now also pulls `is_ignorable_char`
  from `redact_wrap`; `fold_credential`'s strip step calls it; module docstring gains one sentence
  naming the move. `ASCII_CONFUSABLES`, `BIDI_OVERRIDES`, `MIN_FOLDED_LEN`, `fold_credential`,
  `_obfuscated_spellings`, `_contains_folded_secret` all otherwise untouched.
- `docs/MAP.md` — one row regenerated (`autotester map`).
- `tests/test_redact_ignorable_perf.py` (new, 145 lines) — equivalence test over the full BMP,
  9 stratified astral-code-point parametrized cases, and the CJK-heavy bound test.
- Not touched: `src/autotester/core/redact_encodings.py`, `src/autotester/core/redact.py` (owned
  by the parallel at598-607-encoding-coverage unit, per the brief).

## Verify — actual outputs

```
$ uv run pytest tests/test_redact_wrap_perf.py tests/test_redact_ignorable_perf.py
.............................                                            [100%]
29 passed in 50.28s
```

(18 existing AT-599/AT-606 tests + 11 new AT-611 tests = 29.)

```
$ uv run pytest tests/ -k redact
........................................................................ [ 72%]
...........................                                              [100%]
99 passed, 1859 deselected, 1 warning in 62.76s
```

(88 pre-existing redact tests + 11 new = 99. The 1 warning is the pre-existing, disclosed AT-561
`TraceWriter` fallback deprecation warning, unrelated to this unit.)

```
$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

(`doctor` first reported `stale-generated: docs/MAP.md` after the docstring changes; fixed by
`uv run autotester map`, re-run above shows clean.)

### Timings — before and after (fresh process, best-of-3, this box, concurrent second session)

| input | CJK-heavy (best of 3) | ASCII (best of 3) | ratio |
|---|---|---|---|
| BEFORE (master, `lru_cache(maxsize=4096)`) | ~24-25s | ~3.0s | ~8x |
| AFTER (this unit) | ~7.1-7.7s | ~5.1s (noisy run) / ~2.9s (quiet run) | 1.4x-2.5x, depending on concurrent machine load |

The bound test asserts ratio < 2.5x AND an absolute ceiling of 15s (loose on purpose — see the
test's own comment — this pins "not superlinear-cache-thrashing any more", not a tight target),
and was re-run 3 times consecutively to confirm stability (all green, see Capability coverage).

## Capability coverage (each claim → its isolating, single-hunk falsifying edit)

Both falsifications were done in a throwaway copy OUTSIDE the worktree
(`C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/dd410a44-7522-428c-9b91-fda96de822cd/scratchpad/at611-falsify/`),
never via `git stash`, never in this worktree. Baseline in that copy confirmed green first
(`29 passed` before either edit — no import shim needed: `is_ignorable_char` is a plain function,
not `_is_ignorable`'s old decorated form). Each edit's anchor was confirmed to match exactly once
and the file on disk was confirmed to actually change before trusting the result (core-invariants
C7). The copy was restored to the fixed state after each falsification; `git status`/`git diff`
in the worktree before and after both runs show no changes outside this unit's own edits — the
worktree itself was never touched by either falsification.

| claim | falsifying edit | test | before | after |
|---|---|---|---|---|
| CJK-heavy 1 MB stays under the same budget as ASCII (the speedup is real) | `redact_wrap.py`: reverted `is_ignorable_char`'s body to the original `unicodedata.category(ch) in ("Cf","Cc")` / `_DEFAULT_IGNORABLE`-range check, AND re-added `@functools.lru_cache(maxsize=4096)` on top of it (both anchors matched exactly once; file confirmed changed on disk) | `test_cjk_heavy_scan_stays_within_a_generous_multiple_of_ascii` | 11/11 passed | **FAILED**: `CJK-heavy 1 MB took 24.02s vs ASCII 3.06s (7.84x, expected under 2.5x)` — both the ratio and absolute assertions fail |
| The BMP range table is derived correctly, not a hand-widened duplicate (the zero-width/variation-selector class specifically) | `redact_wrap.py`: dropped the `(0xFE00, 0xFE0F)` variation-selector range from `_DEFAULT_IGNORABLE` (anchor matched exactly once; file confirmed changed on disk) | `test_is_ignorable_char_matches_original_over_the_full_bmp` | 11/11 passed | **FAILED**: `16 BMP mismatches, first: [65024, 65025, 65026, 65027, 65028]` — exactly the 16 code points in the dropped range (0xFE00-0xFE0F is 16 code points) |

**A note on the second falsification's first (wrong) attempt, disclosed rather than hidden:** the
first attempt dropped `(0x200B, 0x200F)` (zero-width space/joiners) instead, and the equivalence
test stayed green — because U+200B-U+200F are Unicode category `Cf`, so the table-build's
`unicodedata.category(...) in ("Cf", "Cc")` pass re-marks them ignorable regardless of whether
`_DEFAULT_IGNORABLE` also lists them; dropping a redundant entry changes nothing observable. This
also surfaced a real bug in the equivalence test's first draft: its reference implementation
imported `_DEFAULT_IGNORABLE` directly from `redact_wrap` — the very module being mutated — so
sabotaging that constant sabotaged the "ground truth" identically and the test could never have
caught a real mutation there. Fixed before shipping: the test now hardcodes an independent literal
copy of the original 17 ranges (`_REFERENCE_DEFAULT_IGNORABLE`) so it cannot be silently mutated in
lockstep with the code under test. The corrected second attempt used `(0xFE00, 0xFE0F)`
(variation selectors, category `Mn` — confirmed via `unicodedata.category(chr(0xFE00))` before
choosing it), which is NOT redundantly covered by the `Cf`/`Cc` branch, and killed the test as
shown in the table above.

## Live browser evidence

Not UI-touching. Changed paths: `src/autotester/core/redact_wrap.py`,
`src/autotester/core/redact_fold.py`, `docs/MAP.md` (regenerated),
`tests/test_redact_ignorable_perf.py` (new), `qa/manifests/at611-cjk-perf.md`.

## Known limits (disclosed, not claimed)

- The astral-plane (code point > 0xFFFF) path is not sped up — it keeps the original per-call
  `unicodedata.category` computation, uncached. This is deliberate (the checker's own repro and
  this unit's own corpus both draw from the BMP CJK Unified Ideographs block, ~21,000 code
  points), and disclosed rather than silently narrowed: a corpus built from CJK Extension B or
  further supplementary-plane blocks would not see this fix's speedup and could still show the
  pre-AT-611 cost shape on that specific path. Filing a follow-up is not done here (out of scope
  for a low-severity perf ticket whose own repro is BMP-only); noted for whoever next profiles
  astral-heavy input.
- The ratio bound (< 2.5x) and absolute ceiling (< 15s) are both loose by design, matching this
  repo's own stated tolerance for a "loaded Windows box" (brief) and this project's own note that
  two loops run concurrently. A tighter bound would flake here; this one still catches a return to
  the ~8x cache-thrashing ratio the falsification reproduced.
- `redact_encodings.py`'s existing docstring comment ("the real speed-up is `_is_ignorable`'s
  cache") becomes stale after this fix (there is no cache any more, a table) but that file is
  owned by the parallel at598-607-encoding-coverage unit per the brief's explicit constraint, so it
  is not edited here — disclosed instead of silently left inconsistent.
- `tests/test_redact_obfuscation.py:40`'s comment mentioning `_is_ignorable` by its old name is
  similarly stale (historical narrative, not code) and left untouched — out of this unit's stated
  scope, and correcting every historical cross-reference across the test suite was not asked for.

## Status: checked-PASS (cycle 1, qa/verdicts/at611-cjk-perf.md 1e439b7)
