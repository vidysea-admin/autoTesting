# Manifest - run-error-text-evidence

**Status:** checked-PASS
**Fix cycle:** 1
**Issues addressed:** `.work/inbox-1028.md` line 12 ("The login failure reason is only in a screenshot"): DOM evidence records the unmet assertions, not the visible error text ("Invalid credentials"); with image withholding (`mask_exceeds_limit`, limit 0.85) the case became INCONCLUSIVE though the failure is real and reproducible.
**Branch:** `fix/run-error-text-evidence` (worktree `D:/autoTesting/.claude/worktrees/error-text`, off e74664f8). Not merged, not pushed.

## Criteria (numbered; each is pinned by a test in `tests/test_assertion_error_text.py`)
1. When any field of an expected state is unmet, `assert_expected` records ONE extra DOM evidence row `error text on page (after an unmet assertion): '<text>' | ...`, with the step's `step_order`, appended to the session evidence. (`test_unmet_assertion_records_the_visible_alert_text_as_dom_evidence`, `test_run_case_assertion_failed_carries_the_error_text`)
2. The row is NOT an `assert ` row, so `stages/grade.py:93` and `stages/grade_images.py:78` (which count `assert ... unmet|met` rows) are unchanged. (same first test)
3. A fully met expectation records no row and never evaluates the page. (`test_met_assertion_records_no_error_text_and_never_reads_the_page`)
4. The row passes `session._record`, i.e. the project's Redactor: an `.env` value in the page text (`hunter2`) is masked. (`test_error_text_goes_through_the_redactor`)
5. A scrape failure, `None`, a non-list, or blank items add no row and raise nothing; the unmet assertion row is still there. (`test_scrape_failure_or_empty_result_is_silent`)
6. The excerpt is bounded: at most `MAX_ITEMS`=5 items, `MAX_ITEM_CHARS`=200 each, `MAX_TOTAL_CHARS`=600 for the body; duplicates and fragments contained in a longer message collapse. (`test_excerpt_is_bounded`, `test_duplicate_and_contained_fragments_collapse`)
7. Against a real Chromium page the extractor finds visible `role=alert`, `aria-live`, `*toast*`/`*error*`-class text; skips hidden (`display:none`, `visibility:hidden`) nodes; skips form wrappers (anything containing input/textarea/select). (`test_extractor_finds_visible_alerts_and_toasts`, `test_extractor_skips_hidden_elements_and_form_wrappers`)
8. (reworded, cycle 1, to the exact guarantee) The extractor never includes text the page holds in a control or an editable region: input/textarea/select/option, scripts, secret-masked nodes, `contenteditable` regions and iframes (with their fallback content) are removed from every excerpt, an element containing a control is skipped as a form wrapper, and every value of 3 or more characters held by any input or textarea on the page, password included, in the document or in an OPEN shadow root, is replaced by `[input]` when a server echoes it back into an alert. Typed values and page text are whitespace-normalised identically (runs of whitespace and newlines collapse to one space) and matched case-insensitively. Not covered, by design: values under 3 characters (F4, documented limit), values typed inside an iframe or a CLOSED shadow root (not reachable from this document; no text from those is read either), and a value the server echoes in a transformed form (encoded, reversed, partial). `.env` secrets are separately masked by criterion 10. (`test_extractor_never_echoes_filled_input_values`, `test_f1_*`, `test_f2_*`, `test_f3_*`)
9. No probe budget change: the new read runs only on the already-failed path, spends no probe, and still honours `budget.check()` hard stops; `tests/test_probe_floor_matches_runtime.py` is unchanged and green.
10. (cycle 1, F5) Every excerpt is scrubbed by the project's Redactor BEFORE the 200-char item cap and the 600-char body cap are applied, so a secret straddling a cap is masked whole; the scrub also matches a secret whose whitespace was collapsed by the extractor (a `.env` value holding consecutive spaces). The `session._record` scrub still runs afterwards. (`test_f5_*`)

## Files changed
- `src/autotester/browser/error_text.js` (new, 77 lines after cycle 1): one read-only `page.evaluate` IIFE returning visible alert/error/toast strings.
- `src/autotester/browser/error_text.py` (new, 83 lines after cycle 1): `clean`, `read`, `record_visible_error_text`; one job stated in the docstring. A new module because `assertions.py` was at 259/300 lines and `assert_expected` at 49/50 lines (a new file was the only way to stay inside the doctor caps; the JS lives beside it as `enumerate.js` does).
- `src/autotester/browser/assertions.py:128-186`: `assert_expected` now ends `return _with_error_text(session, evidence, step_order)` (function stays <= 50 lines); new `_with_error_text` calls `error_text.record_visible_error_text` only if an `assert ` row is unmet. File is 268 lines.
- `tests/test_assertion_error_text.py` (new): 18 tests after cycle 1 (10 original + 8 hardening; wiring on the shared `FakePage`, the extractor tests on a real Chromium page via `page.set_content`).
- `docs/MAP.md`: regenerated by `autotester map` (generated file, never hand-edited).

## Tests run (in the worktree, one pytest at a time, `-o addopts=`)
Tests were written before the implementation; I did not capture a separate red run (the first run was still importing when the implementation landed), so red-then-green is NOT claimed for this unit; the checker may demonstrate red by making `_with_error_text` a no-op (the checker measured 4 of the 10 original tests failing on that revert; the other 3 wiring tests are negative or pure-function).

`uv run pytest tests/test_assertion_error_text.py tests/test_execute_assertions.py tests/test_probe_floor_matches_runtime.py tests/test_execute.py tests/test_browser_settle.py -o addopts=`:
```
================== 60 passed, 1 warning in 121.97s (0:02:01) ==================
```
(no skips: the 3 real-Chromium tests ran.)

`uv run ruff check src tests scripts`:
```
All checks passed!
```
`uv run autotester doctor`: after the change 2 violations remain, neither from this unit: `stale-committed: docs/MAP.md` (clears once the regenerated MAP.md in this commit is committed) and `decision-citation-dangling: qa/verdicts/6c-1028-signup.md:4 cites D-110` (pre-existing; D-110 is parked in the main checkout). The `duplicate-concept: record` finding my first draft raised was fixed by renaming to `record_visible_error_text`.

## Known limits / for the checker
- Scope is the `assert_expected` path (steps with a declared `expected`). A case that fails by a thrown error with no declared expectation records no error text; not in this unit.
- Class-substring selectors (`*error*`, `*alert*`, `*warning*`) can pick up a visible non-error component that merely carries such a class; bounded by the caps above and recorded as a plain fact, never a verdict (C7).
- A typed value shorter than 3 characters is not blanked from echoed text (it would shred the message); `.env` secrets are still masked by the Redactor regardless of length.


## Cycle 1 - hardening of the checker's PASS-with-findings (`qa/verdicts/run-error-text-evidence.md`, F1-F5)
Tests first. Red run before any source change (`uv run pytest tests/test_assertion_error_text.py -o addopts= -rf`): 7 failed, 11 passed; the F5 total-cap test passed vacuously at first and was re-aimed (items of 198 chars so the secret begins at char ~597 of the body), after which all 8 hardening tests were red:
```
FAILED test_f1_typed_value_with_consecutive_whitespace_or_newline_is_blanked
FAILED test_f2_typed_value_echoed_in_another_case_is_blanked
FAILED test_f3_value_typed_in_an_open_shadow_root_is_blanked
FAILED test_f3_contenteditable_text_is_never_read_as_message_text
FAILED test_f3_text_inside_an_iframe_is_not_read
FAILED test_f5_secret_straddling_the_item_cap_is_scrubbed_before_the_cut
FAILED test_f5_secret_straddling_the_total_cap_is_scrubbed_before_the_cut
FAILED test_f5_secret_with_consecutive_whitespace_is_scrubbed
```
Fixes, edited in place: `browser/error_text.js` (`norm` shared by typed values and page text, case-insensitive escaped regex blanking, `controlsIn` walks open shadow roots, `EDITABLE` + `isContentEditable` skip, `iframe,frame,object,embed` dropped); `browser/error_text.py` (`_scrubber` + `clean(raw, scrub)` scrub before the item cap; `read` passes the scrubber; so the 600 body cap also only sees scrubbed text). F4 (< 3 chars) stays a documented limit. Cosmetic: the line counts above now match `wc -l`.

Green, after the fix (one pytest at a time, `-o addopts=`):
- `pytest tests/test_assertion_error_text.py tests/test_probe_floor_matches_runtime.py`: 35 passed (the real-Chromium tests ran).
- `pytest tests/test_execute_assertions.py tests/test_execute.py tests/test_browser_settle.py`: 33 passed.
- `ruff check src tests scripts`: All checks passed. `autotester map`: no diff. `autotester doctor`: 3 violations, all `decision-citation-dangling` on D-110 (the parked decision; resolves when D-110 lands); no size, stale-committed or duplicate-concept finding.

Known limit kept: iframe text is skipped, not read; a value typed inside an iframe or a closed shadow root cannot be collected, so only the Redactor protects against its echo.
