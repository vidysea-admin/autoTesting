# Manifest - error-text-followups

**Status:** ready-for-check
**Fix cycle:** 0
**Issues addressed:** findings F6-F9 of `qa/verdicts/run-error-text-evidence.md` (lines 35-38), the low, non-blocking items of the cycle-1 PASS.
**Branch:** `fix/error-text-followups` (worktree `D:/autoTesting/.claude/worktrees/error-text-f`, off master a6e03fa4, which already contains `fix/run-error-text-evidence`). Not merged, not pushed.

## Criteria (numbered; each pinned by a test)
1. (F6) A `<br>` or block-level boundary (`br,hr,p,div,li,ul,ol,dl,dt,dd,tr,td,th,table,section,article,header,footer,h1-h6,blockquote,pre,form,fieldset`, `error_text.js` `BLOCKS`) yields a space in the excerpt: a multi-line typed value echoed over `<br>` or as two `<p>` is blanked, and ordinary text on either side of a separator is not run together. Inline markup (`<b>`, `<i>`, `<span>`) still joins text nodes. (`test_f6_*` in `tests/test_error_text_followups.py`)
2. (F7) A typed value of any length cannot throw: `error_text.js` no longer builds a `RegExp`; it scans with `indexOf`. A 120,000-char textarea value echoed in an alert is blanked and the rest of the message and a second alert are still recorded (before: `Invalid regular expression`, `read()` swallowed it, nothing recorded). A long value that is not echoed does not hide other alerts. (`test_f7_*`)
3. (F8) Typed values and page text are compared by a Unicode folded key (NFKD, combining marks dropped, upper then lower case): NFC vs NFD, `\u00df` vs `SS`, the Kelvin sign vs `k` and full-width forms are blanked in both directions, to `[input]`, with the surrounding message intact; unrelated text is untouched. Matches are collected as ranges in the original text and merged only when overlapping, so adjacent echoes keep separate `[input]` markers and a short typed value (`inp`) can no longer re-match inside an earlier `[input]` marker. (`test_f8_*`, 9 cases)
4. (F9) `Redactor.scrub` (`core/redact.py`) also masks a declared secret echoed in another case, with the same `[REDACTED]:KEY` mask. Guard so ordinary words are never masked: the extra pass applies only to a value of at least `CI_MIN_LEN`=8 chars holding a non-letter, or at least `CI_MIN_LETTERS`=12 chars when letters only (`_ci_eligible`). Exact-case masking is unchanged and stays floorless (a 2-char secret is still masked as typed). `is_clean`, `assert_clean`, `assert_no_raw_secrets` are unchanged. (`tests/test_redact_case_insensitive.py`, 7 tests; wiring `test_f9_env_secret_echoed_in_another_case_is_masked_in_the_row`)
5. Typed values never reach evidence: every case above asserts the typed value (or a tell-tale part) is absent; the existing F1-F5 tests in `tests/test_assertion_error_text.py` (18) still pass unchanged.

## Files changed
- `src/autotester/browser/error_text.js` 77 -> 128 lines (edited in place): `BLOCKS` separator handling in `messageText`, `fold`/`foldMap`, `typed` stored folded, `blank()` replaces the `RegExp` loop (the old `escapeRe` and `blankers` are gone).
- `src/autotester/browser/error_text.py` (docstring line only, 84 lines).
- `src/autotester/core/redact.py:` 276 -> 293 lines: `CI_MIN_LEN`/`CI_MIN_LETTERS`, `_ci_eligible`, `Redactor._ci`, `Redactor._mask_for`, second pass in `Redactor.scrub` (function stays well under 50 lines).
- `tests/test_error_text_followups.py` (new, 139 lines) and `tests/test_redact_case_insensitive.py` (new, 60 lines). New files because `tests/test_assertion_error_text.py` is at 282/300 lines and the redact suite is one-topic-per-file (`test_redact_*.py`); the real-Chromium fixture and helpers are imported from `test_assertion_error_text.py`, not duplicated.

## Tests run (worktree, one pytest at a time, at most 2 files per call, `-o addopts=`)
Red first (before any source change): `tests/test_redact_case_insensitive.py`: 5 failed, 2 passed (the 2 are the negative/unchanged-behaviour tests). `tests/test_error_text_followups.py`: 14 failed, 2 passed (the 2 are the inline-markup and unrelated-text negatives).

Green after the change:
- `pytest tests/test_error_text_followups.py tests/test_assertion_error_text.py`: `34 passed`
- `pytest tests/test_redact_case_insensitive.py`: `7 passed`
- `pytest tests/test_execute_assertions.py tests/test_probe_floor_matches_runtime.py`: `31 passed`; `pytest tests/test_execute.py tests/test_browser_settle.py`: `19 passed`
- Redactor regression sweep: `test_redact_obfuscation + test_redact_escaped` 77 passed; `test_redact_encoding_coverage + test_redact_ignorable_perf` 49 passed; `test_redact_wrap_perf + test_redact_pii` 157 passed; `test_core + test_container_redaction` 85 passed, 1 skipped; `test_secrets + test_trace_numeric_secret` 35 passed; `test_failure_bundle_escape + test_report_export_secrets` 13 passed; `test_unified_report_secrets + test_run_trace` 17 passed; `test_grade_pii + test_failure_bundle` 28 passed.
- `uv run ruff check src tests scripts`: `All checks passed!`
- `uv run autotester doctor`: 2 violations, both `docs/SNAPSHOT.md` (`stale-generated` and `stale-committed`, a generated file that already differs from regeneration at the base commit; not touched by this unit). No size, duplicate-concept or dangling-citation finding from the files changed here. The whole suite was NOT run (machine low on memory); the checker should run the targeted files above.

## Known limits / for the checker
- A combining mark that follows a matched base letter in the page text (e.g. NFD `e` + U+0301) can remain next to the `[input]` marker; harmless, not the typed value.
- The fold drops accents, so a typed `cafe` also blanks an echoed `caf\u00e9`: deliberate over-masking (fail-safe).
- F9 guard is a judgement call recorded in criterion 4: a letters-only secret of 8-11 characters (for example `password`) is still masked only as typed, to avoid masking ordinary words such as a UI label; the checker may tighten or relax `CI_MIN_LEN`/`CI_MIN_LETTERS`. The case-insensitive pass could in theory re-match the key name inside an existing `[REDACTED]:KEY` mask when a secret equals that key text; cosmetic only.
- Typed values under 3 chars (F4) remain a documented limit.
