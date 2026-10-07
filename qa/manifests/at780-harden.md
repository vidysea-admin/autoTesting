# Manifest — at780-harden

**Unit:** AT-780 hardening follow-up. Closes the leaks, over-masking and ReDoS found by both blind checkers of `at780-pii` (`qa/verdicts/at780-pii.a.md`, `.b.md`).
**Contract:** `qa/contracts/reconcile.md` RC12, RC11, RC14; `core-invariants.md` C1/C2/C3.
**Date:** 2026-10-07
**Fix cycle:** 0
**Tier:** L (security)
**Base:** branch `wave/at780-pii` @ 13f37c3c; this branch `wave/at780-harden`
**Status:** ready-for-check
Policy-Version: proportional-verification/2026-10-07.7
Metrics: start=2026-10-07 end=2026-10-07 wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=16 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-07.7

## What changed

| Path | Change |
|---|---|
| `src/autotester/core/redact.py` (222 -> 260 lines) | `_EMAIL_RE` removed; new `_mask_emails` scans outward from each `@` (linear, Unicode-aware, plus addressing, dotless hosts). `_PHONE_RES` gains grouped/dotted/bracketed Indian mobile shapes and an Indian STD landline pattern; the international pattern takes a leading `(`. Name labels: `_NAME_WORD` adds fname/lname/mname/fullname/nombre and Devanagari naam; `mask_name_value` normalises `first_name` / `firstName`; `_PERSON_ROLE` adds dad/mom/mum/papa/... and Hindi roles; `_NOT_PERSON_NAME` / `_NOT_A_NAME_FIELD` extended (bank, business, plan, partner, service, scholarship, template, ..., "name of <org>", country, course, type, ..., Hindi org words). No secret-scrub function touched. |
| `tests/test_redact_pii.py` | +88 lines: email variants, non-emails with `@`, STD, grouped phones, 12-digit anchor, short numbers, new labels, over-masking labels, linear-time tests (200 KB, scaled by `timing_scale()`). |
| `tests/test_reconcile_pii.py` | +53 lines: PII in candidate title/route/controls, hardened shapes through the exact prompt, nested strings, new labels, non-person labels keep their value. |
| `stages/reconcile.py` | unchanged (296 lines). |

## Criteria

| # | Criterion | Test nodes |
|---|---|---|
| 1 | ReDoS: `mask_pii` linear; 200 KB adversarial input (no `@`, long alnum/digit/dot runs, `a@`*50k, one `@` mid-run, digit groups, parens, `+`digits) under `1.0 * timing_scale()` s | `test_redact_pii.py::test_mask_pii_is_linear_on_adversarial_input[*]` (9) |
| 2a | Non-ASCII/IDN emails masked | `::test_email_variants_are_masked_whole` (`josé@exämple.com`, `अनु@example.com`, `jane@münchen.de`); `test_reconcile_pii.py::test_hardened_pii_shapes_never_reach_the_prompt` |
| 2b | Plus addressing, dotless host (`user@localhost`); non-emails keep `@` text | `::test_email_variants_are_masked_whole`, `::test_non_emails_with_an_at_sign_survive`, `::test_many_emails_in_one_string` |
| 2c | Indian STD landlines | `::test_indian_std_landline_is_masked` |
| 2d | Dotted / grouped / bracketed phones, Indian spaced (no country code), Devanagari digits; 12-digit run not partially masked; short numbers survive | `::test_phone_written_with_dots_groups_or_brackets_is_masked`, `::test_a_twelve_digit_run_is_not_partially_masked`, `::test_short_numbers_survive_the_new_phone_patterns` |
| 3 | Name labels: नाम, पिता का नाम, fname, lname, first_name, firstName, Dad, Mother, Father, guardian | `::test_more_person_labels_mask_a_word_value`; `test_reconcile_pii.py::test_hardened_name_labels_are_masked_in_the_prompt` |
| 4 | No over-masking: Bank/Business/Plan/Course/University name, Student country/course/type, Name of university, Partner/Scholarship/Template name, consent checkbox, dashboard, Hindi university name, नामांकन | `::test_non_person_labels_are_not_masked`; `test_reconcile_pii.py::test_non_person_labels_keep_their_value_in_the_prompt` |
| 5 | Nested strings: candidate title/route/controls, narration, cues all masked | `test_reconcile_pii.py::test_pii_in_the_candidate_title_route_and_controls_is_masked`, `::test_nested_strings_in_every_part_of_the_prompt_are_masked` |

## Falsifications (throwaway copy under the session scratchpad, never the worktree; script `falsify.py`)

Each mutant run against `test_redact_pii.py` + `test_reconcile_pii.py` + `test_reconcile.py` (198 tests). All 16 killed.

| Mutant | Result |
|---|---|
| F1 restore the old quadratic email regex | killed (`alnum_run` linear test failed; only that param run, 111 s) |
| F2 email must be ASCII | 4 failed |
| F3 `+` not allowed in local part | 3 failed |
| F4 dotless host not masked | 2 failed |
| F5 drop the STD landline pattern | 9 failed |
| F6 drop the Indian grouped-mobile pattern | 13 failed |
| F7 drop Devanagari `नाम` label | 2 failed |
| F8a drop `first_name`/`firstName` normalisation | 4 failed |
| F8b drop fname/lname | 5 failed |
| F9 drop dad/mom roles | 4 failed |
| F10a bank/business/plan not excluded | 8 failed |
| F10b country/course/type not excluded for roles | 5 failed |
| F10c "name of <org>" not excluded | 2 failed |
| F11 mask the video dict only, not the candidate | 1 failed |
| F12 drop `(?!\w)` anchor on the 10-digit pattern | 1 failed |
| F13 drop Hindi university exclusion | 1 failed |

TDD proof: the new tests (linear tests deselected) against the old `redact.py` @ 13f37c3c: `62 failed, 104 passed, 9 deselected`.

## Commands run (worktree, single pytest process, `-p no:xdist`)

```
uv run pytest tests/test_redact_pii.py tests/test_reconcile_pii.py tests/test_reconcile.py tests/test_redact_encoding_coverage.py tests/test_redact_ignorable_perf.py tests/test_redact_obfuscation.py tests/test_redact_wrap_perf.py tests/test_timing_scale.py -p no:xdist
-> 341 passed in 39.81s
uv run pytest tests/test_redact_pii.py tests/test_reconcile_pii.py -p no:xdist
-> 175 passed in 0.91s   (9 linear tests at 200 KB each well under 1 s)
uv run ruff check src tests scripts
-> All checks passed!
uv run autotester doctor
-> doctor: clean
```

No full suite run (host short on RAM, suite lock held by another run).

## Known limits (not claimed)

- Heuristic masking: names in free text, obfuscated emails (`jane [at] x.com`, `a%40b.com`), `Nickname`/`Username` labels and bare `Textbox 1`-style labels are still not masked. A bare `Name` label masks any lettered value (conservative).
- Any run of ten digits still reads as a phone (unchanged, disclosed earlier).
- Process note: I killed all `python.exe` / `uv.exe` processes once to stop a runaway mutant run (F1 under the full 200 KB suite). That may have touched another session's Python process on this host.
