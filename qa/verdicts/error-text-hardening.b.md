# Verdict - error-text-hardening (Checker B, adversarial; combined A+B seat)

**Unit:** `qa/manifests/error-text-hardening.md`, branch `fix/error-text-hardening`, head `b6f2208d` (base `2c5eeb95`)
**Cycle checked:** 0
**Verdict:** PASS (5 non-blocking findings: 2 test gaps, 1 residual by-design leak form, 2 info. No finding is a new leak of a typed value or `.env` secret that the base code did not already have.)

## Commands run (worktree, one pytest at a time, 2 files per call, `-o addopts=`)
- `pytest tests/test_error_text_followups.py tests/test_assertion_error_text.py`: 51 passed
- `pytest tests/test_redact_case_insensitive.py tests/test_redact_ignorable_perf.py`: 20 passed
- `pytest tests/test_redact_wrap_perf.py tests/test_execute_assertions.py`: 32 passed
- `git diff 2c5eeb95 HEAD --stat -- tests/test_redact_ignorable_perf.py tests/test_redact_wrap_perf.py`: empty (perf tests unchanged, criterion 9)
- `ruff check src tests scripts`: All checks passed. `autotester doctor`: 2 violations (the same two `docs/SNAPSHOT.md` ones as the previous unit; not touched here). `error_text.js` 227 lines, `redact.py` 293, `test_error_text_followups.py` 252 (limit 300); `partsOf` 36 lines (limit 50).

## Falsification (each fix reverted in memory; JS variants in `.work/v/*.js` loaded by `.work/jsvariant_plugin.py` via `JSVARIANT`, scoped to `tests/test_error_text_followups.py -k "not f7 and not f8 and not f9"`, 21 tests)
| Variant | Result | Reading |
|---|---|---|
| `old` (whole JS from `2c5eeb95`) | 8 failed (h1, 4x h2, 2x h3 fifty-thousand, h3 oversized) | every new criterion is red on the old code |
| `v_nofmt` (newline whitespace read as real) | 4 failed (the 4 h2 cases) | criterion 2 pinned |
| `v_allgap` (every collapsed space removable) | 2 failed (f6b real-whitespace, h2 space-without-newline) | criterion 3 (no over-mask) pinned |
| `v_nocaps` (all four cap checks removed) | 3 failed (2x h3 fifty-thousand, h3 oversized) | criteria 4, 7 pinned |
| `v_truncate` (over the run cap return the parts read so far instead of null) | 3 failed (same three) | "mask whole, never truncate" pinned |
| `v_nocharcap` (MAX_CHARS off) | 1 failed (h3 oversized) | char cap pinned |
| `v_nojoined` (second, gap-removed pass off) | 10 failed (4 f6b, f6b mixed, 4 h2, h3 below-cap) | split-token still covered after dropping the sentinel |
| `v_gapfalse` (`gap.push(sep && !real)` -> `false`) | 10 failed (same set) | gap bookkeeping pinned |
| `v_nosep` (boundary `null` ignored) | 9 failed | separators pinned |
| `v_nonodecap` (MAX_NODES off) | 21 passed | NOT pinned (F1) |
| `v_norun` (RUN_NODES and RUN_CHARS off) | 21 passed | NOT pinned (F1); criterion 6's test passes without the run budget |
| `v_noblockclose` (no boundary after a block's children) | 21 passed | NOT pinned (F2) |
| `CI_MIN_LETTERS = 12` (plugin) on `tests/test_redact_case_insensitive.py` | 1 failed (`..._of_eight_or_more_is_masked_in_another_case`) | criterion 8 pinned; the 7-letter `welcome` test is unaffected |

## Criteria
1. PASS: typed `Alice99` echoed the same gives `No user [input] found`; also with the PUA char at a block cut (`<p>Alice</p><p>99</p>` -> `[input]`); typed `` -> `bad [input] val` (old JS: `bad val`, so the old output also dropped the glyph). An icon glyph in an alert is no longer dropped: `<i></i>Invalid credentials` -> `Invalid credentials` (old: `Invalid credentials`).
2. PASS: probes (`.work/probe.py`, 40+ cases, current vs old) all blank to `[input]`: `\n`, `\r\n` + indent, tab+newline, `Alice\n<br>\n99`, `<br><br>`, 3 blocks, nested divs, inline markup inside blocks, `<table>` with newlines, `<wbr>`, CSS `display:block` spans (adjacent text), a dropped `<script>`/`<noscript>` between the halves, upper-case echo split across blocks, and an open shadow-root input.
3. PASS: `<p>Alice </p>\n<p>99</p>` and `Alice&nbsp;<p>99</p>` stay unblanked (a real space). The older f6b negative is green unchanged.
4. PASS: 50,000 `x<br>` finishes in 0.08 s and 50,000 `<p>x</p>` in 0.23 s, each excerpt replaced whole by `[excerpt masked: over the scan limit]` and the next alert (`Other alert`) still read (old JS: 36.6 s per the manifest).
5. PASS: a 3,000-separator message below the cap is scanned and blanked (`h3_below_the_cap`; red under `v_nojoined`/`v_gapfalse`/`v_nosep`, so it exercises the scan).
6. PASS on behaviour, test is weak (F1): 30 alerts x 3,000 `x<br>` read 11 of 30 excerpts (the budget bites; `v_norun` reads all 30); no typed value in the output in either case.
7. PASS: 1.4M-char message masked whole; exactly 1,000,001 chars also masked; a 999,990-char single text node plus the typed value is scanned in 0.61 s and the value blanked.
8. PASS (see the CI row). `redact.py:56` is the only changed source line; `_ci_eligible` (`redact.py:103`) reads the constant at call time.
9. PASS: every earlier F1-F9/F6b/F7/F8 test and the perf tests are green and unchanged (51, 20 and 32 passed above).

## Other probes (adversarial, current JS)
- Sentinel removal did not reopen the split-token leak: all 4 `SPLITS`, the mixed spaced/unspaced message and the 3-block case are red under `v_nojoined`/`v_gapfalse` and green on the head. The code no longer writes U+E000, so it cannot introduce one into evidence.
- Caps hold for: 1.4M chars, 1,000,001 chars, 100k hidden `.error` elements (0.42 s, 1 visible alert read), 100-deep nested `.error` wrappers each holding 8,000 spans (0.20 s, no leak), 5,000 inputs + a 900k-char alert (0.97 s), 300 long textareas + 750k chars (2.45 s), a 120k-char typed value (0.12 s), 200 alerts x 400 `<br>` (0.17 s). No case reached 3 s. A 30,000-deep `<div>` chain and a 480-deep `div.error` chain crashed Chromium inside `page.set_content` before the script ran (same for old and new JS; not attributable to this unit).
- `run` is declared inside the IIFE, so the budget is per `page.evaluate`, not carried across calls.

## Non-blocking findings
- F1 (low, test gap) `MAX_NODES` (js:51) and the run budget `RUN_NODES`/`RUN_CHARS` (js:53-54, js:194-195, js:224) can be removed without any test going red (`v_nonodecap`, `v_norun`: 21 passed). `test_h3_many_alerts_share_one_run_budget` passes whether or not the budget exists (30 x 3,000 separators scans in 0.23 s unbounded). Behaviour is correct today (probe: 11 vs 30 excerpts read). Fix: a test where one excerpt is between ~10k and 20k nodes (per-excerpt cap), and one asserting that alerts after the budget is spent are not read (for example `len(joined.split(" | "))`).
- F2 (low, test gap) The boundary pushed after a block's children (js:198, js:203) is unpinned (`v_noblockclose`: 21 passed). Without it a typed value that holds a space is leaked when a block is followed directly by text: typed `Alice 99`, echo `<p>Alice</p>99` gives `No [input] here` on the head and `No Alice99 here` on the variant. Fix: add that case to the `SPLITS`-style tests.
- F3 (low, residual leak form, by design of criterion 3; identical output on the old JS) A single space with no newline between two blocks is read as a real space, so unspaced typed `Alice99` echoed as `<p>Alice</p> <p>99</p>` surfaces as `Alice 99` (not blanked). Browsers do not render that space. The likelier real-world forms (newline-formatted HTML, `<br>`) are fixed; this one needs minified or templated HTML with a bare space between blocks. A whitespace-only text node that sits between two boundaries could be treated as formatting without breaking the `<p>Alice </p>` negative (a trailing space inside a block).
- F4 (info, narrow behaviour change, not a `.env` secret regression) With the sentinel gone, a page that echoes the typed value with a U+E000 inserted (`Alice99`) is no longer blanked (old JS: `[input] x`, because it consumed U+E000 by accident). It now behaves like the zero-width space and soft hyphen interleavings, which neither version blanks (`Ali​ce99`, `Ali\xadce99` are identical in both). An invisible-char-interleaved echo is a pre-existing limit.
- F5 (info, availability trade-off, fail-closed) The run budget starves later alerts on pathological pages: 30 x 3,000 separators reads 11 of 30; 100 nested `.error` wrappers with 8,000 spans each reads 4 excerpts (old JS read 40). Nothing leaks; real alerts after a hostile block are not recorded. Acceptable given the manifest's stated caps.

## Not findings
Over-masking when `<p>Alice \n</p><p>99</p>` (newline inside the trailing space) is blanked: fail-safe. A block-level `DROP` element (`<div contenteditable>`) emits no boundary, so `Alice<div contenteditable>q</div>99` joins to `Alice99` and is blanked: fail-safe. A 7-letter letters-only secret keeps exact-case masking only (criterion 8, accepted by Umesh 2026-10-29). `RunApproval`, `.env` values and `AUTOTESTER_APPROVAL_KEY` were not read or touched.
