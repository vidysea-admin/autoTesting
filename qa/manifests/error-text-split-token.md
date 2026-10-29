# Manifest - error-text-split-token

**Status:** checked-PASS
**Fix cycle:** 0
**Issues addressed:** finding F1 of `qa/verdicts/error-text-followups.b.md`: the F6 change (a space at every `<br>`/block boundary) regressed a typed value with NO space that the page splits across blocks (typed `Alice99`; alert `<p>Alice</p><p>99</p>`, `Alice<br>99`, or two `<td>` cells). The old textContent join blanked it; the new output showed `No user Alice 99 found`.
**Branch:** `fix/error-text-followups` (worktree `D:/autoTesting/.claude/worktrees/error-text-f`), on top of `6c273c55`. Not merged, not pushed.

## Criteria (each pinned by a test in `tests/test_error_text_followups.py`)
1. A typed value with no space that the page splits across `<p>`, `<div>`, `<td>` or `<br>` is blanked: all four echoes give `No user [input] found`. (`test_f6b_unspaced_typed_value_split_across_blocks_is_blanked`, 4 cases)
2. The spaced echo (typed `Bob 77`, echoed over blocks) and the unspaced echo (`Alice99` over blocks, and inline `Alice99`) are all blanked in one message. (`test_f6b_spaced_and_unspaced_echoes_in_one_message_are_both_blanked`)
3. A real whitespace character next to a separator is not treated as inserted: `<p>Alice </p><p>99</p>` for typed `Alice99` stays `Seen Alice 99 here`. (`test_f6b_real_whitespace_next_to_a_separator_is_not_removed`; this one was green before the fix and pins that the fix does not over-mask)
4. Every existing F6, F7, F8, F9 and F1-F5 test stays green unchanged.

## Change (edit in place, `src/autotester/browser/error_text.js`, 128 -> 171 lines)
- `SEP` (`\uE000`) replaces the literal space inserted for `br`/`hr`/block boundaries; `collapse(raw)` does the whitespace collapse (same result as before) and also returns `gap[]`, true where a collapsed space came only from SEP.
- `blank(text, gap)` matches the typed values against `text` and against `text` with the `gap` spaces removed; `spansIn(view, map)` maps ranges of the unspaced view back to original offsets, so one `[input]` swallows the inserted separator space. Ranges still merge only when they overlap. Still `indexOf` only (no RegExp, F7 intact). Spans are appended by loop, not spread, so a huge span count cannot overflow the stack.

## Tests run (one pytest at a time, 2 files per call, `-o addopts=`)
Red first (before the JS change): `pytest tests/test_error_text_followups.py`: `5 failed, 17 passed` (the 4 split cases and the mixed-message case failed; the real-whitespace negative and all earlier tests passed).

Green after:
- `pytest tests/test_error_text_followups.py tests/test_assertion_error_text.py`: `40 passed`
- `pytest tests/test_execute_assertions.py tests/test_probe_floor_matches_runtime.py`: `31 passed`
- `uv run ruff check src tests scripts`: `All checks passed!`

## Known limits
- The unspaced view only drops spaces that were inserted at a separator; a typed value split across blocks AND containing a real space at the cut is matched by the spaced view as before.
- `\uE000` (private use) in page text would be read as a separator; no real page text uses it.
