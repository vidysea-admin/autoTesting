# Manifest — at599-606-redact-wrap-perf (AT-599 + AT-606)

**Unit:** AT-599 (an encoded needle split by a newline or MIME 76-char wrap is missed) + AT-606
(the folded-secret scan is superlinear: 518 KB took 11.8 s). Both filed against the merged
at347-352-356-redact-fold work (`qa/verdicts/at347-352-356-redact-fold.md`).

**Contract:** `qa/contracts/core-invariants.md` (project-wide; C5/C7 especially) and
`qa/contracts/browser-and-secrets.md` (B2/B4 — this is the security credential gate before every
model call).
**Fix cycle:** 2 of max 3
**Dual check:** no
**Persona walk:** skip (backend security, no UI surface)
**Issues addressed:** AT-599 (medium, open → fixed here), AT-606 (medium, open → fixed here).
Neither flipped by me — `qa/issues.jsonl` is the checker's write surface.
**Executor:** claude-sonnet-subagent

## Root cause (found by profiling, not guessed)

Profiled `Redactor.contains_folded` on a ~530 KB synthetic corpus in a throwaway copy before
touching any file (`cProfile`, full table in
`qa/evidence/at599-606-redact-wrap-perf/perf_and_mutation.log`). `_is_ignorable`
(`redact_fold.py:88`, unchanged logic) accounted for 86% of total time: it is called once per
character of every string `fold_credential` folds — the text itself, its reversal, and its
HTML-unescape, so ~1.59M Python-level calls for one 530 KB input — each doing an
`unicodedata.category` lookup plus a fresh `any(...)` generator scanning a 17-tuple ignorable-range
table. That work is O(1) per call but real text repeats the same few hundred distinct characters
far more than it grows, so the *character-by-character Python call overhead* is what scales badly,
not the underlying algorithm. `declared_secret_encodings` (`redact_encodings.py:78`) is a second,
smaller offender: a pure function of one secret string, recomputed from scratch on every single
scrub/gate call regardless of text size.

AT-599 is a separate, correctness (not perf) gap in the same mechanism: `declared_secret_encodings`
needles are literal, case-significant substrings of an encoded secret — exactly what makes them
immune to adjacent characters (AT-352 cycle 2) — but that same literalness means a needle broken by
a `\n`/`\r\n` (deliberately mid-token, or by MIME's fixed 76-character line wrap) no longer appears
as one contiguous substring, so the exact search cannot see it.

## Fix cycle 2 (answers the checker's 2 FAIL lines)

**FAIL 1 (AT-599, medium) — whitespace inside base64-alphabet runs still evaded detection.**
The checker's repro: a declared secret's base64 encoding split at offset 10 by a newline was
caught, but split by a space or by a newline-plus-4-space-indent was not, because
`redact_wrap.py`'s regex only ever matched `\r\n|\r|\n` — never a bare space, tab, or the
indentation after a folded header line. Fixed in `src/autotester/core/redact_wrap.py`: the
module-level `_LINE_BREAK_RE = re.compile(r"\r\n|\r|\n")` is replaced with
`_WHITESPACE_RE = re.compile(r"\s+")`, and the cheap early-exit is now
`if not _WHITESPACE_RE.search(text): return False` (previously `"\n" not in text and "\r" not
in text`). `\s` matches space, tab, `\n`, `\r`, `\f`, `\v` — everything the module's own docstring
names ("whitespace inside base64-alphabet runs") plus the two forms the checker's matrix actually
exercised (space, newline+indent). No other line in the function changed. Tests added: space-split,
tab-split, and newline+4-space-indent-split, each through both `contains_folded` and
`assert_no_raw_secrets` (6 new tests), plus one more explicit space-separated-prose negative test
alongside the existing wrapped-prose one (see Capability coverage below for the falsifying repro).

**FAIL 2 (LOW) — `lru_cache` on `declared_secret_encodings` had no killing test row and retained
raw secrets.** The checker's own capability-coverage table (cycle 1, row 4: encodings cache only)
already showed removing just this cache leaves every test green, including the perf bound — the
measured 7x speed-up is entirely `_is_ignorable`'s cache in `redact_fold.py`. Per the brief
("Drop the lru_cache … Keep the `_is_ignorable` cache only if a test kills its removal; otherwise
disclose it"): `_is_ignorable`'s cache IS killed by a test (cycle-1 row 3: that cache alone gives
6.04s against the 3s bound — a real regression), so it stays, unchanged, in `redact_fold.py`
(not touched this cycle — `redact_fold.py` is exactly 300/300 and off-limits). The
`declared_secret_encodings` cache has no killing row, so it is removed outright in
`src/autotester/core/redact_encodings.py`: the `@functools.lru_cache(maxsize=256)` decorator line is
deleted, and the now-unused `import functools` is removed with it. Re-measured after removal (see
Before/after timing below): the 500 KB bound test still passes at 0.63s, indistinguishable from the
0.619s recorded with the cache present — no perf regression, confirming the checker's row-4 finding
that this cache bought nothing measurable while holding up to 256 raw secret values in memory for
the process lifetime.

## What changed

- **`src/autotester/core/redact_wrap.py`** — cycle 2: `_LINE_BREAK_RE` (`r"\r\n|\r|\n"`) replaced
  with `_WHITESPACE_RE` (`r"\s+"`); early-exit changed to `_WHITESPACE_RE.search(text)`; docstrings
  (module + function) rewritten to describe whitespace, not line breaks, and to record the cycle-1
  checker repro that motivated the widening. Still 77 lines, well under the 300-line cap.
  Cycle 1 (unchanged this cycle): `contains_wrapped_encoding()` strips separators from `text` and
  re-runs the exact-encoding needle search (`declared_secret_encodings`) against the unwrapped copy.
  Split out rather than inlined into `redact_fold.py` because that file was already at 292 of its
  300-line C2 cap before this unit (same reason `redact_encodings.py` was split out of it in AT-352
  cycle 2 — a distinct concern, own docstring, own tests).
- **`src/autotester/core/redact_fold.py`** — **untouched this cycle** (still exactly 300/300; the
  hard constraint on this unit is no added lines here). Cycle 1 gave it: `:18` `import functools`;
  `:26` `from autotester.core.redact_wrap import contains_wrapped_encoding`; `:90`
  `@functools.lru_cache(maxsize=4096)` on `_is_ignorable` (AT-606, kept — see FAIL 2 above);
  `:295` `_contains_folded_secret`'s extra OR branch calling `contains_wrapped_encoding` (AT-599).
- **`src/autotester/core/redact_encodings.py`** — cycle 2: `@functools.lru_cache(maxsize=256)`
  decorator removed from `declared_secret_encodings`; `import functools` removed (now unused);
  docstring's AT-606 note rewritten to record the removal and why (see FAIL 2 above). 133 lines,
  under the 300-line cap; `declared_secret_encodings` itself is 51 lines (`autotester doctor`
  confirms clean, function-length rule included).
- **`tests/test_redact_wrap_perf.py`** — cycle 2 adds 7 tests: 3 detection pairs (space-split,
  tab-split, newline+4-space-indent-split, each through `contains_folded` and
  `assert_no_raw_secrets`, 6 tests) plus 1 explicit space-separated-prose negative test
  (`test_space_separated_benign_prose_has_no_false_positive`). File docstring updated to name the
  cycle-2 gap. 209 lines total, under the 300-line cap.
  Cycle 1 (unchanged this cycle): split out of `tests/test_redact_obfuscation.py` (already at 290 of
  its own 300-line cap); 8 AT-599 detection tests (mid-token newline × {base64, hex} × {`\n`,
  `\r\n`} where applicable, plus real MIME 76-char wrapping via `base64.encodebytes`), 1
  benign-wrapped-prose negative test, and 2 AT-606 perf tests (absolute bound, growth ratio).

No other file touched. `docs/MAP.md` regenerated (`autotester map`) after cycle 2's edits, because
`doctor` flagged it stale again (the same regeneration cycle 1 already did — no new concept row,
same reasoning as cycle 1: `redact_wrap.py` is an internal implementation detail of the existing
"secret redaction" concept, not a new one).

## Verify — actual outputs

```
$ uv run pytest tests/test_actuator_chokepoint.py tests/test_cli_orchestrate.py tests/test_core.py \
    tests/test_coverage.py tests/test_db.py tests/test_execute.py tests/test_ids.py \
    tests/test_network_assertions.py tests/test_onboard_pathlynks.py \
    tests/test_parallel_run_evidence_namespace.py tests/test_portal_persona.py \
    tests/test_prompt_skills.py tests/test_redact_obfuscation.py tests/test_redact_wrap_perf.py \
    tests/test_run_pathlynks_first_cases.py tests/test_run_trace.py tests/test_secrets.py \
    tests/test_source_adapters_drive.py tests/test_ui_error_pages.py tests/test_ui_runs_parallel_trace.py
218 passed, 1 skipped, 6 warnings in 4.95s
```

(Every test file under `tests/` whose contents mention "redact" — confirmed via
`grep -rl redact tests/*.py`, 20 files including `test_ids.py` itself (it mentions "redact" only in
a comment about its own split-out history) — plus `test_core.py`, both named explicitly in the
brief. The 1 skip and 6 warnings are pre-existing and unrelated — AT-561's disclosed `TraceWriter`
fallback warning in `test_run_trace.py`, not touched by this unit.)

```
$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

### Cycle 2 — actual outputs (this fix cycle)

```
$ uv run pytest tests/test_redact_wrap_perf.py
..................                                                       [100%]
18 passed in 2.74s
```

18 = the 11 tests cycle 1 had (test count corrected from the cycle-1 manifest's "8 AT-599 detection
+ 1 negative + 2 perf" = 11) plus cycle 2's 7 new tests (3 detection pairs = 6, plus 1 negative).

```
$ uv run pytest tests/ -k "redact"
........................................................................ [ 85%]
............                                                             [100%]
84 passed, 1822 deselected, 1 warning in 4.85s
```

```
$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

(`doctor` initially flagged `function-too-long: redact_encodings.py:76 declared_secret_encodings is
57 lines > 50` after the FAIL-2 docstring note documenting the cache removal was first drafted at
its full explanatory length; the note was tightened across a few passes (57 -> 53 -> 52 -> 51 -> 50
lines of function body) until `doctor` came back clean, shown above. `docs/MAP.md` was regenerated
via `autotester map` after these edits, since `doctor` flagged it stale from the docstring/import
changes; no `ARCHITECTURE.md` prose change, same as cycle 1.)

### Full suite (extra verification beyond the brief's required commands)

```
$ uv run pytest tests/
1868 passed, 6 skipped, 32 xfailed, 15 warnings in 664.75s (0:11:04), exit 0
```

1868 = cycle 1's full-suite baseline (1861 passed) + 7 new cycle-2 tests, 0 failed. The 15 warnings
are the same pre-existing, disclosed AT-561 `TraceWriter` fallback warnings as cycle 1 (9 more than
cycle 1's 6, all the identical warning text at different call sites — not new, not touched by this
unit).

### Before/after timing (AT-606)

Same 500 KB corpus (`tests/test_redact_wrap_perf.py::_make_corpus`, fixed seed), same 5 secrets,
`contains_folded` + `assert_no_raw_secrets` combined:

| state | 500 KB combined call |
|---|---|
| BEFORE (both `@lru_cache` decorators removed, reproducing the pre-fix code exactly) | **4.19s** |
| AFTER (this unit's code) | **0.619s** |

Cold-process (fresh interpreter per row, no warm-cache carryover), `contains_folded` alone, AFTER:

| size | time | ratio vs previous row |
|---|---|---|
| 250 KB | 0.353s | — |
| 500 KB | 0.670s | 1.90x for 2x size |
| 1000 KB | 1.504s | 2.25x for 2x size |

Full profiling table and methodology: `qa/evidence/at599-606-redact-wrap-perf/perf_and_mutation.log`.

### Cycle 2 re-measure after removing `declared_secret_encodings`'s `lru_cache`

Same 500 KB corpus and bound test, cache removed (this cycle's actual committed code):

```
$ uv run pytest tests/test_redact_wrap_perf.py --durations=0
0.63s call     tests/test_redact_wrap_perf.py::test_redact_scan_stays_under_a_generous_bound_on_a_500kb_corpus
1.32s call     tests/test_redact_wrap_perf.py::test_redact_scan_time_roughly_doubles_not_quadruples_with_input_size
18 passed in 2.01s
```

0.63s vs the 0.619s recorded in cycle 1 with the cache present — the difference is noise (both well
under the 3s bound), not a regression. Honest disclosure: `declared_secret_encodings` is called once
per widened secret per scrub/gate call regardless of the cache, and its own work (a handful of
`base64`/`hex` calls on one short string) is microseconds — cheap enough that even every call
recomputing it from scratch does not show up against `_is_ignorable`'s dominant, now-cached cost.
This matches the checker's own row-4 finding (cycle 1): removing only this cache left every test
green, including the perf bound.

## Capability coverage (each claim → its isolating, single-hunk falsifying edit)

| claim | falsifying edit | test | before | after |
|---|---|---|---|---|
| A wrapped encoded needle (mid-token newline or MIME wrap) is caught by `contains_folded`/`assert_no_raw_secrets` (AT-599) | `redact_fold.py:295` `if contains_wrapped_encoding(text, widened_secrets, MIN_FOLDED_LEN): return True` → `if False:  # AT-599 SABOTAGE\n        return True` | `tests/test_redact_wrap_perf.py` (8 AT-599 detection tests) | 11 passed | **8 failed** (all 8 AT-599 detection tests, by name), 3 unrelated tests (negative + 2 perf) stayed green |
| The 500 KB scan stays under a generous bound (AT-606) | `redact_fold.py:90` remove `@functools.lru_cache(maxsize=4096)`, and `redact_encodings.py:77` remove `@functools.lru_cache(maxsize=256)` (anchors matched exactly once each, both files changed) | `test_redact_scan_stays_under_a_generous_bound_on_a_500kb_corpus` | 1 passed (0.619s) | **FAIL**: `500 KB scan took 4.19s, expected under 3s` |
| **Cycle 2** — a needle split by whitespace OTHER than a line break (space, tab, newline+indent) is caught, not only a line-break split (AT-599) | `redact_wrap.py:32` `_WHITESPACE_RE = re.compile(r"\s+")` → reverted to cycle 1's `re.compile(r"\r\n\|\r\|\n")` (anchor matched exactly once, in a throwaway copy under `C:/Users/Lenovo/AppData/Local/Temp/claude/.../scratchpad/at599-falsify/`, never in this worktree — the worktree's committed file was never touched) | standalone repro calling `contains_wrapped_encoding` directly with a fake secret (`FakeSecretValue-12345`) base64-split at offset 10, mirroring the checker's own cycle-1 matrix | fixed code: `newline: caught=True`, `space: caught=True`, `newline+4sp indent: caught=True` | **reverted (sabotaged) code: `newline: caught=True`, `space: caught=False`, `newline+4sp indent: caught=False`** — reproduces the checker's exact cycle-1 finding byte for byte |

Cycle 1's two edits were reverted after the run; `diff` against the worktree's committed files
exits 0 (byte-identical) for all four touched files. Cycle 2's falsifying edit was made and reverted
entirely inside the throwaway scratch copy (never in the worktree), then the scratch copy was
deleted; `git status`/`git diff --stat` in the worktree before and after the falsification run show
no unexpected changes to `redact_wrap.py` — only the intended cycle-2 fix diff.

**INCONCLUSIVE, disclosed per core-invariants.md C7:** the same AT-606 mutation above did NOT kill
`test_redact_scan_time_roughly_doubles_not_quadruples_with_input_size` at its own sizes (250 KB /
500 KB) — the large/small ratio was ~2.04x even with both caches removed, so growth stays close to
linear in that specific window on this machine even for the pre-fix code. The sibling bound test's
kill is what shows this test file is not vacuous; the ratio test is kept because the brief asks for
it and it remains a real assertion (it would fire on a return to the checker's originally measured
49x-for-10x-size magnitude of superlinearity), just not independently proven-killed by this one
mutation at this size window. Not reported as "the test is vacuous" — the property C7 forbids
inferring from a single zero-failure result.

**No isolating falsification for the benign-wrapped-prose negative test**
(`test_line_wrapped_benign_prose_has_no_false_positive`) — its job is to show the fix does NOT fire
on ordinary line-wrapped text, and the only mutation that would meaningfully break it is loosening
`contains_wrapped_encoding`'s exact-substring match into something fuzzier, which is not a change
this unit makes anywhere. Same shape as the "revert_op: none" rows other manifests in this repo
record for pure guard/negative tests (e.g. `qa/manifests/at521-finish-the-q-sweep.md`). Cycle 2's
`test_space_separated_benign_prose_has_no_false_positive` shares the identical reasoning and is
NOT falsified by the whitespace-widening revert in the Capability coverage table above -- that
revert only narrows the regex back to line breaks, and the space-only prose has none, so it hits
the SAME early-exit (`return False`) under both the fixed and the reverted code, proving nothing
about the widening either way. The only mutation that would meaningfully break this negative test is
the same one that would break the other: loosening the exact-substring match itself, which this unit
does not do anywhere.

## Live browser evidence

Not UI-touching. Changed paths: `src/autotester/core/redact_wrap.py` (new),
`src/autotester/core/redact_fold.py`, `src/autotester/core/redact_encodings.py`,
`tests/test_redact_wrap_perf.py` (new), `docs/MAP.md` (regenerated),
`qa/manifests/at599-606-redact-wrap-perf.md`,
`qa/evidence/at599-606-redact-wrap-perf/perf_and_mutation.log`.

## Known limits (disclosed, not claimed)

- **AT-598** (double base64 encoding and UTF-16 hex not covered) and **AT-607** (a raw secret of 7
  or fewer characters gets no encoding protection by design; an 8-character secret misses base32
  only at alignment offset 1) both stay open and out of scope — neither is touched by this unit.
- The AT-606 fix targets the specific hot path profiling identified (`_is_ignorable` and
  `declared_secret_encodings`); it does not restructure `fold_credential`'s NFKD-decompose-then-
  strip-`Mn` pass or `_obfuscated_spellings`' percent-decode loop, which the profile showed were not
  the dominant cost on this corpus. A corpus with very different character diversity (e.g. many
  distinct non-ASCII code points, defeating the `lru_cache`'s hit rate) would see a smaller speed-up
  than the ~7x measured here, though still no worse than the pre-fix baseline.
- `contains_wrapped_encoding` (AT-599) strips whitespace unconditionally across the whole text
  (cycle 2 widened this from line breaks only), not only inside runs that already look
  base64/hex/base32-shaped, because a wrapped needle by definition does not look encoded yet on
  either side of the split. The false-positive risk this could reopen is bounded, not eliminated by
  construction: it needs the exact needle bytes (still an 8+ character case-significant substring of
  a real secret's computed encoding) to reappear right at a whitespace join by coincidence, which
  `test_line_wrapped_benign_prose_has_no_false_positive` and cycle 2's
  `test_space_separated_benign_prose_has_no_false_positive` each probe once but do not exhaustively
  rule out for every possible text. Widening the strip from line-breaks-only to all of `\s+` widens
  this same bounded, not-eliminated risk proportionally (more join points now merge), but does not
  change its nature.
- The ratio-based perf test's mutation status is INCONCLUSIVE at its own two sizes, as disclosed
  above in Capability coverage — it is a real, brief-requested assertion, not a proven-killed one.
- **Resolved this cycle, not a residual:** the checker's LOW finding that `declared_secret_encodings`'s
  `lru_cache` retained raw secret values in process memory with no measured benefit is fixed by
  removing that cache outright (see FAIL 2 above) — not disclosed as a remaining limit.
- Split-across-two-scrub-calls and `%XX` URL-encoding (not a declared encoding) remain uncaught, per
  the cycle-1 verdict's own note ("inherent / not claimed") — inherent to a single-call,
  declared-encoding search and not claimed by either AT-599 or AT-606; out of scope for this unit.

## Status: checked-PASS (cycle 2, qa/verdicts/at599-606-redact-wrap-perf.md 969de22)
