# Verdict - run-error-text-evidence

**Verdict:** PASS
**Status:** PASS
**Cycle checked:** 1
**Reviewed SHA:** 61be2b6f (cycle-1 diff `3ede657a..61be2b6f`), branch `fix/run-error-text-evidence`, worktree `.claude/worktrees/error-text`

## Scope
`git diff 3ede657a..61be2b6f`: `browser/error_text.js` (77 lines), `browser/error_text.py` (83), `tests/test_assertion_error_text.py` (18 tests, 8 new), manifest. `assertions.py` untouched this cycle (268 lines). Cycle-0 findings F1, F2, F3, F5 were asked to be fixed; F4 was kept as a documented limit; criterion 8 was reworded and criterion 10 added.

## Independent checks (checker-run, one pytest at a time, `-o addopts=`; imports confirmed to resolve to the worktree `src`)
- `pytest tests/test_assertion_error_text.py tests/test_probe_floor_matches_runtime.py`: 35 passed (real-Chromium tests ran, none skipped).
- `pytest tests/test_execute_assertions.py tests/test_execute.py tests/test_browser_settle.py`: 33 passed.
- `ruff check src tests scripts`: All checks passed.
- `autotester doctor`: 4 violations, all `decision-citation-dangling` on the parked decision (manifest :40/:65, the earlier verdict, the signup verdict); no size, stale-committed or duplicate-concept finding. File sizes OK (js 77, py 83, assertions.py 268).
- Revert test A, `assertions.py:184` guard forced False: 7 failed, 11 passed (the 4 wiring tests plus the 3 F5 tests that go through `assert_expected`). Restored with `git checkout`.
- Revert test B, `error_text.py` `read()` calling `clean(...)` without the scrubber (scrub only after the caps): exactly the 3 `test_f5_*` fail, 15 pass. Restored with `git checkout`. Worktree clean afterwards.

## Cycle-0 leak probes re-run (checker-written, real Chromium, scratchpad, not committed)
Direct runs of `error_text.SCRAPE_JS` + `clean`. All closed:
- F1 whitespace/newline: `"John  Smith"`, multi-line textarea, tab, NBSP-separated, padded value, all blanked to `[input]`.
- F2 case: `Alice99` echoed as `ALICE99`/`alice99` blanked; accented `Ünïcodé Ñame` echoed upper-case blanked.
- F3: value in an open shadow root blanked; nested open shadow roots three levels deep blanked; `contenteditable` (bare, `""`, `plaintext-only`, nested descendant) never read; iframe (srcdoc alert, fallback content) never read.
- F5: for every offset 150..204 a whitespace-bearing secret straddling the 200-char cap is fully masked; secret with consecutive whitespace masked as typed and collapsed; revert B proves the ordering is pinned.
- Regex specials in typed values (`a.b*c(d[e]+f?$^|\g{1}`, `((((`, `[[[`, `a|b|c`, `(?:x)+`, `$&$1`, literal backslashes): no regex error, all blanked.
- Text split across sibling nodes (`<span>Ali</span><span>ce99`, `<b>Al</b>ice<i>99</i>`, comment or `<script>` between): blanked (textContent joins them).
- Property-set value (`.value=` after load), `<select>` value, 300 inputs of 2000 chars + 40 alerts, 100 textareas of 20 KB: correct and fast (~0.01-0.02 s).

## Criteria
1-7, 9. PASS, unchanged since cycle 0 and re-verified by the green runs above.
8 (reworded). PASS: every claim in the new wording was probed above and holds; the "not covered, by design" list (under 3 chars, iframe or closed-shadow typed values, encoded/reversed/partial echo) is accurate. See F6 for one transformed-echo case the wording does not list.
10. PASS: `error_text.py` `_scrubber` + `clean(raw, scrub)` scrub before the 200-char cap, the 600 body cap then sees scrubbed text; whitespace-collapsed secrets matched; three tests pinned and red on revert.

## Non-blocking findings (low; none is a leak of a `.env` secret or a regression)
- F6 (low) `<br>` or block-level separators swallow the space: `error_text.js:62` builds text from `textContent`, so a multi-line textarea value `line1\nline2xx` echoed as `line1<br>line2xx` (nl2br) or as two `<p>`s becomes `line1line2xx`, which does not match the typed `line1 line2xx`, and survives. Probed: output `Bad: line1line2xx`. Same for a typed `Alice 99` echoed over a `<br>`. Fix idea: insert a space for `br` and block elements in the clone before `textContent`. This is a transformed echo of a non-secret typed value; the Redactor still masks `.env` secrets.
- F7 (low, fail-safe) a typed value of roughly 60,000+ characters makes `new RegExp(...)` (`error_text.js:57`) throw ("Invalid regular expression", measured: 30,000 ok, 60,000 throws), `page.evaluate` raises, `read()` swallows it and records NO error text for that page. No leak, but the diagnostic is silently lost. Fix idea: skip values over a few thousand chars, or wrap the regex build in try/catch and fall back to `split/join`.
- F8 (low, same class as the documented "transformed form") the `gi` flags use simple case folding only: NFC vs NFD (`café` vs `cafe\u0301`), `straße` vs `STRASSE`, and the Kelvin sign vs `k` are not matched. Needs a server that transforms the echo.
- F9 (low, pre-existing, outside this unit) the Redactor is case-sensitive for a secret printed in page text in another case (`PASS WORD 9` vs `pass word 9` stays visible). Core behaviour of `core/redact.py`, not changed here.

## One-concept / edit-in-place
No new file this cycle; `error_text.js` and `error_text.py` edited in place, functions within the 50-line cap, no duplicate concept.

## Residual / follow-up
- Maker scope limit stands: only the `assert_expected` path.
- Class-substring selectors can pick a visible non-error component; bounded and recorded as a plain fact (C7).
- Branch not merged, not pushed (per instruction).
