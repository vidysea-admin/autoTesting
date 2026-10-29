# Manifest - error-text-hardening

**Status:** ready-for-check
**Fix cycle:** 0
**Issues addressed:** findings F1, F2, F3 of `qa/verdicts/error-text-split-token.b.md` (typed U+E000 not blanked; pretty-printed newlines between blocks; 50k `<br>` stalls the read), plus Umesh's 2026-10-29 scope addition (letters-only case-insensitive secret floor 12 -> 8).
**Branch:** `fix/error-text-hardening` (worktree `D:/autoTesting/.claude/worktrees/errtext-harden`), on top of `fix/error-text-followups` @ `2c5eeb95`. Not merged, not pushed.

## Criteria (each pinned by a test; all written red first)
1. A typed value that itself holds U+E000 is blanked: typed `Alice\ue00099`, echoed the same, gives `No user [input] found`. (`test_h1_typed_value_holding_a_private_use_char_is_still_blanked`)
2. A pretty-printed newline (with indentation) between blocks is not a real space: `<p>Alice</p>\n<p>99</p>`, indented `<div>`s, `<ul>\n<li>`, and `Alice\n<br>\n99` for typed `Alice99` all give `No user [input] found`. (`test_h2_pretty_printed_newlines_between_blocks_are_not_a_real_space`, 4 cases)
3. A space with no newline next to a block is still real: `<p>Alice </p>\n<p>99</p>` stays `Seen Alice 99 here` (no over-masking). (`test_h2_a_space_without_a_newline_next_to_a_block_is_still_real`; the older `test_f6b_real_whitespace_next_to_a_separator_is_not_removed` is unchanged and green)
4. A hostile page cannot stall the read: 50,000 `x<br>` or `<p>x</p>` units finish under a 20 s bound and the over-cap excerpt is replaced whole by `[excerpt masked: over the scan limit]`, with no typed value in the output and the next alert still read. (`test_h3_fifty_thousand_separators_are_capped_and_masked_not_leaked`, 2 cases)
5. Below the cap nothing changes: a 3,000-separator message is still scanned and blanked (`[input] end a a a ...`), no mask. (`test_h3_below_the_cap_a_long_message_is_still_scanned_and_blanked`)
6. The caps are shared across a run: 30 alerts of 3,000 separators each do not leak and stay under the bound. (`test_h3_many_alerts_share_one_run_budget`)
7. A single message over the character cap (1.4M chars) is masked whole, never truncated. (`test_h3_an_oversized_message_is_masked_whole`)
8. (Umesh 2026-10-29) A letters-only secret of 8-11 chars (`sunshine`, `mypassword`, `password`) echoed in another case is masked; 7 letters (`welcome`) stays exact-case only; 12-letter and non-letter cases unchanged. (`test_letters_only_secret_of_eight_or_more_is_masked_in_another_case`, `test_letters_only_secret_under_eight_keeps_exact_case_only`)
9. Every earlier F1-F9, F6b, F7, F8 test and the redaction perf tests stay green unchanged.

## Change (edit in place)
- `src/autotester/browser/error_text.js` (171 -> 227 lines):
  - `partsOf(root)` (new, 37 lines) replaces the clone + per-node `replaceWith`/`prepend`/`append` loop: one iterative `TreeWalker` pass over the live subtree, no clone, no DOM mutation; `DROP` elements and their subtrees are skipped; a `null` part marks each `<br>`/block boundary. Caps `MAX_NODES` 20,000 and `MAX_CHARS` 1,000,000 per excerpt, `RUN_NODES` 60,000 and `RUN_CHARS` 3,000,000 per run; over a cap `messageText` returns `MASK` (fail-safe), and the main loop stops reading once the run budget is spent.
  - The U+E000 sentinel is removed (`SEP`), so U+E000 is ordinary text on both sides and a typed value holding it matches. This replaces the proposed "strip U+E000 from typed values" and also fixes the reverse side effect noted in F1 (an icon-font glyph in an alert was dropped).
  - `collapse(parts)`: a whitespace chunk holding `\r`/`\n` is source formatting (`fmt`); a space or tab without a newline is real. A run is an inserted gap when it touches a boundary and holds no real space.
- `src/autotester/core/redact.py:56`: `CI_MIN_LEN, CI_MIN_LETTERS = 8, 8` (293 lines, unchanged count).
- `tests/test_error_text_followups.py` (171 -> 252 lines), `tests/test_redact_case_insensitive.py` (rewrote the letters-only test into two).

## Tests run (one pytest at a time, 2 files per call, `-o addopts=`)
Red first (before the fix):
- `pytest tests/test_error_text_followups.py -k "h1 or h2"`: `5 failed, 2 passed` (h1 and 4 h2 cases red; the negative and the below-cap test green by design).
- Old JS restored for `-k h3`: `3 failed, 2 passed`; the 50k `x<br>` case took 36.64 s (over the 20 s bound), the 1.4M-char message leaked `filler` text.
- `pytest tests/test_redact_case_insensitive.py` at 12: `1 failed, 7 passed`.

Green after:
- `pytest tests/test_error_text_followups.py tests/test_assertion_error_text.py`: `51 passed` (62.51 s with Chromium start-up; each h3 case is well under 1 s of scan time)
- `pytest tests/test_redact_case_insensitive.py`: `8 passed`
- `pytest tests/test_redact_ignorable_perf.py tests/test_redact_wrap_perf.py`: `30 passed`
- `pytest tests/test_redact_pii.py tests/test_redact_obfuscation.py`: `195 passed`
- `pytest tests/test_redact_escaped.py tests/test_redact_encoding_coverage.py`: `58 passed`
- `pytest tests/test_execute_assertions.py tests/test_probe_floor_matches_runtime.py`: `31 passed`
- `pytest tests/test_observe.py tests/test_agent_credential_gate.py`: `93 passed`
- `uv run ruff check src tests scripts`: `All checks passed!`
- `uv run autotester doctor`: 2 violations, both `docs/SNAPSHOT.md` stale-generated / stale-committed (the same two as `error-text-split-token`; not touched by this unit).

## Known limits
- A hostile page over a cap gets its excerpt masked whole, so legitimate (huge) alert text is lost by design; the caps are far above any real alert.
- `RunApproval`, secrets and `.env` were not touched or read. Case-insensitive masking at 8 letters means a letters-only 8-11 char secret that equals an ordinary word also masks that word in evidence (cosmetic, accepted by Umesh).
- `run.nodes` counts every visited node, including nested alert elements scanned twice; the run budget bounds that.
