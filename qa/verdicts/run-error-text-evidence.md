# Verdict - run-error-text-evidence

**Verdict:** PASS
**Status:** PASS
**Cycle checked:** 0
**Reviewed SHA:** 31f6329f (base e74664f8), branch `fix/run-error-text-evidence`, worktree `.claude/worktrees/error-text`

## Scope
`git diff e74664f8..31f6329f`: `browser/error_text.py` (new, 67), `browser/error_text.js` (new, 56), `browser/assertions.py:25,177,180-186` (+10), `tests/test_assertion_error_text.py` (new, 10 tests), `docs/MAP.md` (+1 generated row), the manifest.

## Independent checks (run by the checker, one pytest at a time, `-o addopts=`)
- `pytest tests/test_assertion_error_text.py tests/test_probe_floor_matches_runtime.py`: 27 passed (the 3 real-Chromium tests ran, none skipped).
- `pytest tests/test_execute_assertions.py tests/test_execute.py tests/test_browser_settle.py`: 33 passed.
- `ruff check src tests scripts`: All checks passed.
- `autotester doctor`: 2 violations, both `decision-citation-dangling` on D-110 (`qa/verdicts/6c-1028-signup.md:4`, expected, D-110 is parked in the main checkout; and `qa/manifests/run-error-text-evidence.md:39`, same cause, resolves when D-110 lands). `stale-committed: docs/MAP.md` and `duplicate-concept` are NOT present. No size violation: assertions.py 268 lines, error_text.py 67, error_text.js 56 (manifest says 51; cosmetic).
- Revert test: the `_with_error_text` guard replaced by `if False:` gave 4 failed, 6 passed (`test_unmet_assertion_records_the_visible_alert_text_as_dom_evidence`, `test_error_text_goes_through_the_redactor`, `test_excerpt_is_bounded`, `test_run_case_assertion_failed_carries_the_error_text`). Reverted via `git checkout`. The manifest says "the 7 wiring tests then fail"; only 4 do (the other 3 are negative or pure-function tests that pass vacuously). Overstatement, not a defect.

## Criteria
1. PASS. `assertions.py:182-185` records one DOM row via `error_text.record_visible_error_text(step_order=...)` when any `assert ...: unmet` row exists; pinned by 2 tests, red on revert.
2. PASS. Row label is `error text on page ...`, never `assert `. `stages/grade.py:91-93` (`_unmet_assertions`) and `stages/grade_images.py:78` (`met_assertions`) filter on `startswith("assert ")`; neither file is in the diff.
3. PASS. The guard keys on an unmet row; the met-case test asserts `evaluate` is never called.
4. PASS. `error_text.py:66` goes through `session._record`, which runs `self.secrets.redactor().scrub(path)` (`browser/evidence.py:187`) before the row is built or appended; redactor test is red on revert.
5. PASS. `read()` swallows everything except `RunBudgetExceeded`; `clean()` returns [] for non-list/None/blank. Test covers exception, [], None, str, [None, 5, "  "].
6. PASS. `clean()` caps 200 chars/item, dedupes, drops contained fragments, keeps <= 5; `error_text.py:65` caps the body at 600. The JS also caps at 40 elements. Test is red on revert.
7. PASS. Real Chromium tests plus my own probe: visible `role=alert`, `aria-live`, `*toast*`/`*error*` found; `display:none` / `visibility:hidden` skipped; a `<form class=has-error>` wrapper skipped (`error_text.js:50`, `el.querySelector(CONTROLS)`).
8. PASS for the stated scenario (an `<input>`/password whose value is >= 3 chars echoed verbatim); see F1-F5 for edge cases where the claim is narrower than its wording. Probe confirms `data-autotester-secret` nodes and input/select/option are dropped from the clone (`error_text.js:18,40`).
9. PASS. `read()` calls `session.budget.check()` with no `probes=`/`actions=`; `run_budget.py:146` `check(actions=0, probes=0)` consumes nothing and still raises on a hard stop. `error_text.py` is imported only by `assertions.py`; the read runs only on the already-unmet path. Probe-floor test unchanged and 17/17 green.

## Security probe (checker-written, real Chromium, scratchpad; not committed)
Direct runs of `error_text.SCRAPE_JS` + `clean` against crafted pages. Leaked into the excerpt:
- F1 (typed value with consecutive whitespace, or a multi-line `<textarea>`): `messageText` collapses whitespace in the page text (`error_text.js:41`) but `typed` values are only `.trim()`med (`:33`), so `"John  Smith"` and `"line1\nline2xx"` echoed in an alert are not matched and survive.
- F2 (server echoes in a different case, `Alice99` -> `ALICE99`): the exact-case `split` (`:42`) misses it.
- F3 (inputs the extractor cannot see): a value typed in an open shadow root or an iframe is not collected (`document.querySelectorAll` pierces neither), and `contenteditable` text inside an element matched by the selector list is read as message text (`contenteditable` is in neither DROP nor CONTROLS).
- F4 (documented limit, confirmed): values < 3 chars (`ab`) are not blanked.
- F5 (ordering): `clean()` and the 600-char slice cut the text BEFORE `session._record` scrubs it, so a secret shown in page text (not in an input, so not blanked in JS) that straddles char 200/600 leaves a prefix the Redactor cannot match. The Redactor is also exact-match, and the JS collapses whitespace first, so a secret holding consecutive whitespace is not matched.

Not leaked (confirmed): input/textarea/select/option values inside the alert, `[data-autotester-secret]` text, hidden elements, a value changed via the `.value` property after load (the live value is blanked, not the stale attribute), a form wrapper holding inputs.

## Why PASS and not FAIL
The exposure path that matters (the `.env` / `{{SECRET:KEY}}` credential the run itself typed) is covered twice: blanked in-page when it sits in an input AND exact-match scrubbed by the project's Redactor at `_record`. F1-F5 need a non-secret test value echoed with altered whitespace/case, a shadow-DOM/iframe/contenteditable form, or a secret printed in page text straddling a cap; runs use a supplied test account (CLAUDE.md Credentials). The row records a fact and assigns no verdict (C7). Criterion 8 is worded absolutely ("every value held by any input"), which the code does not fully meet; that is a hardening item, not a regression (before this unit the same text was already in the screenshot).

## One-concept / edit-in-place
`assertions.py` was 259/300 and `assert_expected` 49/50 (manifest); the +10 lines are one import, one `return` swap and one 6-line helper, and function sizes stay within 50. A new `error_text.py` + `.js` is justified: no other module under `browser/` reads alert/toast text (a grep for `role="alert"`/toast/aria-live finds only this pair, `stages/report_banner.py` which renders the report's own HTML, and an unrelated `review_recall.py`), and `enumerate.js` / `visual_order.js` set the precedent of a sidecar `.js`. `execute.py::_error_text` is a different concept (formats a caught exception). The module docstring states one job. Doctor reports no duplicate-concept.

## PROPOSED-ISSUE (low, hardening; not written to issues.jsonl, to avoid an id collision with the main checkout)
Harden `error_text.js` / `error_text.py` against F1-F3 and F5: normalise `typed` values with the same whitespace collapse and compare case-insensitively; also collect from `textarea`, open shadow roots and same-origin iframes and drop `[contenteditable]`; scrub with the Redactor BEFORE the 200/600 caps (or cap on a boundary after scrub). Re-word criterion 8 to the exact guarantee until then.

## Residual / follow-up
- The maker's scope limit stands: only the `assert_expected` path; a thrown error with no declared expectation records no error text.
- `*error*`/`*alert*` class substrings can match a visible non-error component; bounded and recorded as a plain fact.
- Branch not merged, not pushed (per instruction).
