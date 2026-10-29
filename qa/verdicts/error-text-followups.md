# Verdict - error-text-followups

**Verdict:** PASS
**Status:** PASS
**Cycle checked:** 0
**Reviewed SHA:** 58d9a7b2 (diff `a6e03fa4..58d9a7b2`), branch `fix/error-text-followups`, worktree `.claude/worktrees/error-text-f`
**Checker:** A (contract). Source findings: F6-F9 of `qa/verdicts/run-error-text-evidence.md` lines 35-38.

## Independent checks (checker-run, one pytest at a time, `-o addopts=`, imports resolve to the worktree `.venv`)
- `pytest tests/test_error_text_followups.py tests/test_assertion_error_text.py`: 34 passed (real Chromium ran, none skipped).
- `pytest tests/test_redact_case_insensitive.py tests/test_redact_wrap_perf.py`: 25 passed.
- `pytest tests/test_redact_ignorable_perf.py tests/test_redact_obfuscation.py`: 68 passed.
- `pytest tests/test_execute_assertions.py tests/test_probe_floor_matches_runtime.py`: 31 passed. `pytest tests/test_execute.py tests/test_browser_settle.py`: 19 passed.
- `uv run ruff check src tests scripts`: All checks passed.
- `uv run autotester doctor`: 2 violations, both `docs/SNAPSHOT.md` (`stale-generated`, `stale-committed`); the file is not in the diff (`git diff --stat a6e03fa4 HEAD` lists 6 files, none SNAPSHOT), so it predates the branch. 369 advisory decision-citation findings are non-blocking. No size, duplicate-concept or docstring finding. Sizes: `redact.py` 293, `error_text.js` 128, new tests 139 and 60.
- Whole suite not run (machine low on memory); targeted files only.

## Criteria
1. F6 PASS. `error_text.js:43-44` BLOCKS list matches the manifest; `:109-114` replaces `br`/`hr` with a space and pads other blocks. Tests `test_f6_*` (4) pass. Own probe: `<td>Alice</td><td>99</td>` and `<pre>ab\ncd\nef</pre>` echoes become `[input] bad` / `x [input] y`; inline `<b>Al</b>ice99` is still joined and blanked.
2. F7 PASS. No `RegExp` remains in `error_text.js` (`blank()` at `:84-104` uses `indexOf`, advancing by `v.length`, no infinite loop). 120,000-char value test passes with the second alert kept. Own perf probe: 40 alerts of 20k chars with a 20k-char textarea and 3 short values scraped in 0.57 s.
3. F8 PASS. `fold` (`:49`) = NFKD, marks dropped, upper then lower; `foldMap` (`:50-65`) keeps original offsets per folded unit, including surrogate pairs (emoji probe blanked). Spans merge only when overlapping (`:96-98`), adjacent stay separate; the `inp` vs `[input]` test passes. 7 parametrised forms plus negative and adjacency tests pass. Own probes also pass: duplicate typed values, overlapping typed values (`abcdef`/`defghi` in `abcdefghi` gives one marker), open shadow-root input with an upper-case echo, SVG text, typed value made only of combining marks (folds to empty, skipped by the `>= MIN_VALUE` check, no crash, no over-blank).
4. F9 PASS with a recorded judgement (see F-A). `redact.py:54-56` constants, `:101-104` `_ci_eligible`, `:134-135` compiled patterns (`re.escape`, `re.I`), `:138-146` `scrub` second pass. `is_clean` (`:161`), `assert_clean` (`:177`), `assert_no_raw_secrets` (`:254`) are untouched in the diff. Replacement uses a lambda, so a backslash or `\g<0>` in a secret is not a template (probe: `x\1y\g<0>zz` masked cleanly); regex metacharacters are escaped (probe `a.b*c+d(e)[f]\g` masked in upper case). Exact-case masking stays floorless (`test_exact_case_masking_is_unchanged_and_floorless`). Ordinary-word guard: `Passing PASS pass` with secret `pass` gives `Passing PASS [REDACTED]:K`; `password`/`Password PASSWORD` unchanged; `Summer2026` masks only `SUMMER2026` and `summer2026`, not `Summer sale`.
5. PASS. Every F6-F8 test asserts the typed value or a tell-tale part is absent, and the rows were asserted equal to `Account [input] is locked` style strings. `test_assertion_error_text.py` (18) unchanged and green. Typed-value non-leak holds in all probes above.

## Performance
`test_redact_wrap_perf`, `test_redact_ignorable_perf`, `test_redact_obfuscation` all pass. Own probe: `Redactor` with 4 secrets (3 CI-eligible) over a 2.3 MB text scrubs in 0.23 s; a 2.2 MB adversarial near-match string (`tr0ub4dor&3` x 200,000) in 0.26 s. The CI pass is one compiled linear `re.sub` per eligible secret with an escaped literal, so no backtracking risk and the cost is one extra scan per secret.

## Judgement: F9 thresholds (8 with a non-letter, 12 letters only)
Reasonable, not blocking. False-mask side: guard holds (above). Miss side, residual and fail-open only for a secret that a server re-cases:
- a letters-only secret of 8-11 chars (for example `sunshine`) echoed in another case is not masked;
- a secret of 3-7 chars containing a digit (for example `abc123`) echoed in another case is not masked.
Both match the manifest's stated limit. Test-account passwords are normally 8+ with a digit or symbol, so the common case is covered.

## Non-blocking findings (low; none is a regression or a leak of a typed value)
- F-A (low, residual): the two miss cases above. Option for the maker or Umesh: lower `CI_MIN_LETTERS` to 8 (cost: a letters-only 8-11 char secret that equals an ordinary word would also mask that word in evidence, cosmetic) or leave as is. No change required for PASS.
- F-B (low): the Python CI pass uses `re.I` only, so the Unicode forms folded on the JS side (NFD, sharp s vs SS) are not matched for a `.env` secret; `contains_folded` covers detection but `scrub` does not mask those. Same class as before F9, outside this unit.
- F-C (cosmetic, already disclosed): the CI pass could re-match the key text inside an existing `[REDACTED]:KEY` mask when a secret equals that key name.
- F-D (informational): a base letter followed by a combining mark in page text can leave the mark next to `[input]` (disclosed); a block element splitting the middle of a typed word (`Al<div>ice</div>`) is not blanked, a contrived transformed echo.

## Verdict
PASS for cycle 0. F6, F7, F8, F9 are closed as scoped. The branch is not merged or pushed (instruction: no merge, no push).
