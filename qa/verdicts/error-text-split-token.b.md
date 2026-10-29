# Verdict - error-text-split-token (Checker B, adversarial; combined A+B seat)

**Unit:** `qa/manifests/error-text-split-token.md`, branch `fix/error-text-followups`, head `48bd6b73` (base `6c273c55`)
**Cycle checked:** 0
**Verdict:** PASS (3 non-blocking findings; none is a regression of a `.env` secret and none is a leak the old code did not already have, except F1 which needs a typed value containing U+E000)

## Commands run (worktree, one pytest at a time, 2 files per call, `-o addopts=`)
- `pytest tests/test_error_text_followups.py tests/test_assertion_error_text.py`: 40 passed
- `pytest tests/test_execute_assertions.py tests/test_probe_floor_matches_runtime.py`: 31 passed
- `pytest tests/test_observe.py tests/test_run_failure_artifacts.py`: 15 passed
- `pytest tests/test_agent_credential_gate.py tests/test_drive_verify.py`: 101 passed (both cite `error_text`)
- `ruff check src tests scripts`: All checks passed. `autotester doctor`: 2 violations, both `docs/SNAPSHOT.md` stale-generated / stale-committed (same two as the earlier verdict; not touched by this unit). `error_text.js` 171 lines, `test_error_text_followups.py` 171 lines (limit 300).

## Falsification (each fix reverted in memory via `.work/jsvariant.py` + `JSVARIANT=<file>`, `tests/test_error_text_followups.py`)
| Variant (file in `.work/v/`) | Result |
|---|---|
| `v1_old` whole JS from `6c273c55` | 5 failed, 17 passed (the 4 split cases + the mixed message) |
| `v2_nojoined` second pass disabled (`if (joined.length !== text.length)` -> `if (false)`, js:115) | same 5 red |
| `v3_gapfalse` (`gap.push(!real)` -> `false`, js:139) | same 5 red |
| `v5_mapoff` (`map[to-1]+1` -> `map[to-1]`, in `spansIn`) | same 5 red (the blank would leave the last char) |
| `v6_nosepcollapse` (SEP read as real whitespace, js:137) | same 5 red |
| `v4_gaptrue` (every collapsed space marked removable, over-masking) | exactly 1 red: `test_f6b_real_whitespace_next_to_a_separator_is_not_removed` |

So every new test pins a distinct piece of the change, including the negative (no over-mask).

## Criteria
1. PASS: the four echoes (`<p>`, `<br>`, `<td>`, `<div>`) give exactly `No user [input] found` (test run + falsified above). Extra probes (`.work/chk_split_cases.py`, current vs old JS): 3 blocks (`Alice`/`99`/`x`), inline markup inside a block (`<p>Al<b>ice</b></p><p>99</p>`), nested divs, `<hr>`, `<ul><li>` pair, emoji pair split (`😀😀`/`PW1` for typed `😀😀pw1`), sharp-s fold split (`STRASSE`/`99` for typed `Straße99`), astral chars before the span (offset mapping across surrogate pairs): all blanked, all LEAK with the old JS.
2. PASS: spaced and unspaced echoes in one message both blanked; an overlapping pair (`Alice99` unspaced + `ce 99`) merges into one `[input]` (`zz [input] zz`).
3. PASS: `<p>Alice </p><p>99</p>` stays `Seen Alice 99 here`; `v4_gaptrue` makes it red, so the test is real.
4. PASS: all F1-F9 tests green unchanged (40 passed above).

## U+E000 can never appear in recorded evidence
By construction: the only writers of U+E000 are `n.replaceWith(SEP)` / `n.prepend(SEP); n.append(SEP)` on the CLONE (js:154-155). Everything then goes through `collapse(clone.textContent)`, and `collapse` consumes every `SEP` with `continue` before anything is appended to `text` (js:137); `blank` only slices `text` and appends the literal `[input]` (js:106-128). So neither `text` nor the return value can hold U+E000, including a U+E000 that was already in the page's own text (it is indistinguishable and is consumed the same way). Probe: 20 cases (incl. `Ali&#xE000;ce99`, `Invalid&#xE000;credentials`, a typed value holding U+E000, block-nested variants), `` found in the output of 0 cases. The Python side (`error_text.clean`) never sees it. The clone is discarded, so the live page is not mutated.

## Non-blocking findings
- F1 (low, narrow regression) A typed value that itself contains U+E000 is no longer blanked. Probe: typed `Alice99`, alert text `Alice99`: old JS `zz [input] zz`, new JS `zz Al ice99 zz` (the typed value leaks, with a space where the PUA char was). Cause: `collapse` strips/treats E000 in the page text (js:137) but `typed` is built from `foldMap(norm(el.value))` (js:77) without the same treatment, so the strings no longer line up. Needs a password or name holding one specific private-use code point, so contrived; fix is to drop `SEP` from typed values in the same loop (`norm(el.value).split(SEP).join('')`) and add a test. Side effect in the other direction (not a leak): a page icon-font glyph U+E000 in an alert is now dropped/read as a space (`<i></i>Invalidcredentials` -> `Invalid credentials`; U+E001 etc. are kept).
- F2 (info, known limit, NOT a regression: identical output with the old JS) a typed value with a real space echoed without it (`Alice 99` echoed `Alice99`) is not blanked; real source whitespace between blocks (`<p>Alice</p>\n<p>99</p>` for typed `Alice99`) or `&nbsp;` at the cut is a genuine space, so not blanked (this is criterion 3 by design). The manifest's "known limits" cover the first; the second (pretty-printed HTML between blocks) is not listed and is the likelier real-world form of a split echo.
- F3 (info, perf) Cost of the new path is bounded: 2M chars with no gaps 2.07 s vs 1.53 s old; 120k `<p>` pairs 0.93 s vs 0.81 s; 40 alerts x ~25k chars with gaps 3.46 s vs 2.39 s. No blow-up. A separate pre-existing cost: 20k `<br>` lines take 4.4 s in BOTH old (`6c273c55`) and new JS and 50k+ exceed 50 s in the new JS; the cost is the live-DOM `replaceWith`/`prepend` loop from F6 (js:152-156), not this unit. Worth a follow-up cap or a text-walk instead of DOM mutation, but out of this unit's scope.

## Not findings
Over-masking of unrelated adjacent blocks that happen to concatenate to a typed value (`<li>Alice</li><li>99</li>` with typed `Alice99`) is blanked: fail-safe, matches intent. `SEP` is never present on the live page (clone only).
