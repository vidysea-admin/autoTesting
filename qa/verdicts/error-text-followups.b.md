# Verdict - error-text-followups (Checker B, adversarial)

**Unit:** `qa/manifests/error-text-followups.md`, branch `fix/error-text-followups`, head `58d9a7b2` (base `a6e03fa4`)
**Cycle checked:** 0
**Verdict:** PASS (5 non-blocking findings, none a leak of a `.env` secret)

## Commands run (worktree, one pytest at a time, `-o addopts=`)
- `pytest tests/test_error_text_followups.py tests/test_assertion_error_text.py`: 34 passed
- `pytest tests/test_redact_case_insensitive.py tests/test_redact_wrap_perf.py`: 25 passed
- `pytest tests/test_redact_ignorable_perf.py tests/test_redact_obfuscation.py`: 68 passed
- `pytest tests/test_execute_assertions.py tests/test_probe_floor_matches_runtime.py`: 31 passed
- `pytest tests/test_core.py tests/test_secrets.py`: 1 failed + 43 passed on the first run (failing test not captured), then 44 passed on each of 4 reruns. Not reproduced; treated as a load flake on a shared low-memory machine, unattributed (see F5).
- `ruff check src tests scripts`: All checks passed. `autotester doctor`: 2 violations, both `docs/SNAPSHOT.md` stale-generated / stale-committed (as the manifest says; not touched by this unit). Sizes: `redact.py` 293, `error_text.js` 128, `test_error_text_followups.py` 139 lines.

## Falsification (revert each fix, a test must go red)
Plugin `.work/jsvariant.py` swaps `error_text.SCRAPE_JS` / `redact._ci_eligible` in memory.
- Whole old JS (`a6e03fa4`): `test_error_text_followups.py` 13 failed, 3 passed (the 3 are the inline-markup, unrelated-text, and F9 wiring-independent negatives). F6 x3, F7 x2, F8 x8 red.
- F6 reverted alone (BLOCKS loop removed): exactly the 3 `test_f6_*` that need separators go red.
- F8 reverted alone (fold = `toLowerCase`): 5 of the 9 F8 cases red (NFC/NFD, sharp s, full-width); Kelvin cases stay green because `toLowerCase` already maps U+212A to `k`, so that pair is not independently pinned.
- F9 reverted (`_ci_eligible` -> False): 6 tests red (5 in `test_redact_case_insensitive.py` + `test_f9_env_secret_echoed_in_another_case_is_masked_in_the_row`).
- F7: pinned by the old JS run (both `test_f7_*` red there).

## Criteria
1. F6 PASS. 2. F7 PASS: 120k-char value, 31 items, 0.10 s; 1M-char value 0.8 s; 2M-char alert with a 3-char typed value 1.44 s (`.work/probe_js.py`). 3. F8 PASS (NFC/NFD, ss, Kelvin, full-width, ligature `fi`, dotted I, Hangul, emoji all blanked, probed). Overlapping typed values merge (`abcd`+`cdef` -> one `[input]`), contained values merge. 4. F9 PASS with caveats F2-F4. 5. PASS: every probed typed value absent except F1 below.

## F9 threshold judgement (8 non-letter-bearing / 12 letters-only)
Measured with `Redactor({"K": v}).scrub(...)`: `Dashboard` -> `DASHBOARD` untouched (exact case masked only); `password`/`mypassword` upper-cased stay visible; `Password1` (9, has a digit) -> `password1` and `PASSWORD1` masked; `correcthorse` (12) masked in any case; `user name` (9, has a space) masks the UI label `User Name`. The guard does keep ordinary single words safe, and does catch the F9 case (`pass word 9`). Accepted as a judgement call: the letters-only gap (8-11 chars, e.g. `mypassword`) is only reachable when a server upper/lower-cases the echo, and exact-case masking is unchanged. Passphrases with spaces qualify by the "non-letter" rule and so can mask a matching ordinary phrase; fail-safe, acceptable.

## Non-blocking findings
- F1 (low, regression of a transformed echo) `error_text.js:109-114` now inserts a space at every `td/p/div/br` boundary, so a typed value with NO space that a page splits across blocks no longer matches. Probe: typed `Alice99`, alert `<p>Alice</p><p>99</p>` or `Alice<br>99` or two `<td>`s: old JS output `[input]`, new JS output `No user Alice 99 found` (typed value visible). The old textContent join caught it; F6's fix trades one transformed case for another. Fix idea: also test the folded text built without separator spaces (second `blank` pass over `textContent`). Requires a page that splits a single token across blocks, so low.
- F2 (low) Python-side other-case match uses `re.I` (simple folding): a declared secret holding sharp s is not masked when echoed as `STRASSE-PW99` (`Redactor({"K":"Straße-pw99"})` leaves it visible). A Python/Java server `.upper()` produces exactly that form. The JS typed-value path handles it; `core/redact.py` does not. German-letter secrets only.
- F3 (cosmetic, non-idempotent) a secret whose value equals its own key name case-insensitively is re-matched inside its mask: `Redactor({"PATHLYNKS_USER":"pathlynks_user"}).scrub("hi pathlynks_user")` -> `hi [REDACTED]:[REDACTED]:PATHLYNKS_USER`, and each further scrub adds one more layer (read() applies scrub 3 times). No leak; manifest already notes the cosmetic risk, but the growth per pass is worth knowing.
- F4 (perf, low) CI pass costs about 3x on very large text: 8 eligible secrets over 2 MB x3: 0.36 s old vs 1.09 s new; 20,000 short strings 0.28 s vs 0.42 s. `test_redact_wrap_perf` and `test_redact_ignorable_perf` pass unchanged, so no gate regresses. A cheap prefilter (`value.lower() in text.lower()`) would restore speed.
- F5 (info) one unattributed failure in `test_core.py`+`test_secrets.py` on the first run, 44 passed on 4 reruns; no failing name captured. Maker may want to confirm on a quiet machine.

## Not a finding
`zwsp` inside a typed value, `marker-lookalike` (`put` inside `[input]`) are unchanged versus the old behaviour or an artifact of my probe's own check.
