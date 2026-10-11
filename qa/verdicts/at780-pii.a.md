# Verdict (checker A, blind dual check) — at780-pii

**Date:** 2026-10-07
**Policy:** proportional-verification/2026-10-07.7, tier L, security trigger (`core/redact.py`)
**Unit:** AT-780, branch `wave/at780-pii`, commit `1856e5c4`
**Cycle checked:** 0
**Verdict:** PASS (code, security probes, scoped tests); one open process item: the full suite is BLOCKED-PROCESS (see Tests and gates)

## Check plan (written first)

1. Read the diff (`origin/master...HEAD`: redact.py +63, reconcile.py 12 lines, 2 new test files) and judge each manifest criterion against the code.
2. Security: capture the exact prompt through the recording mock; probe `mask_pii`, `mask_pii_obj`, `mask_name_value` with adversarial input; confirm `_judged` is the only model call; confirm the scrub / `assert_no_raw_secrets` path is untouched and still runs last.
3. Affected tests: the three named files, every test importing `core.redact`, ruff, `autotester doctor`.
4. One full suite (security L), under `.work/suite.lock`.
5. Falsification: my own mutants in a throwaway copy (not the worktree), at least one per claim.

## Criteria

| Claim (manifest) | Evidence | Result |
|---|---|---|
| Email, +91, plain 10-digit, international, US phones masked in the exact prompt | `reconcile_fakes.judge_prompts` captured prompt; `test_pii_values_are_masked_in_the_exact_prompt` (5 params) pass; my e2e probe: `jane+promo@example.co.in`, `+91 (98765) 43210`, `98765 43210`, `Zoë Müller` (name field), `O'Brien-Smith` all masked to `<email>`/`<phone>`/`<name>` in `"value"` | holds |
| Name-field values masked | 4 label params pass; my probe: "Full Name", "Your name", "Applicant", "Name of the student", "Last name", "Student Name (as per 10th marksheet)" masked | holds |
| Email/phone in narration and cues masked | test passes; `mask_pii_obj` runs over the whole `video` and `other` dicts; probe with route `/app?e=jane@x.com&p=9876543210`, candidate title, cue: none present in prompt | holds |
| Non-PII survives | search term, "2024", "10", "Course name box", "Student ID box" kept; company/display/user/course name labels not masked | holds |
| RC11 determinism | pure functions, `sort_keys=True`; determinism test passes | holds |
| RC12 scrub unchanged | diff only adds functions to redact.py; `Redactor`, `assert_no_raw_secrets`, `fold_credential` untouched; in `_judged` the order is still `redactor.scrub(prompt)` then `assert_no_raw_secrets`, and masking happens earlier, in `build_judge_prompt`; `test_rc12_*` pass; placeholder guard in `mask_name_value` keeps `{{SECRET:K}}` intact | holds |
| `_judged` is the only model call | `grep` of reconcile.py: one `provider.judge` (line 122); `screen_identity.py` has "no provider"; `_judged` prompt comes only from `build_judge_prompt` (line 272) | holds |

Masking versus the issue's `fix_direction` (drop `value`): the issue's expected outcome says "no typed value leaves the machine". Masking cannot meet that literally; it meets the stated intent (no PII shapes to an external model) only for the shapes the heuristics recognise. The maker disclosed that Umesh chose this direction. I accept it as the unit's scope. The residual leaks below are outside what the maker claimed and are filed as PROPOSED-ISSUE, not FAIL. AT-780 should be closed on this PASS only with those proposals filed; the issue's literal "no typed value" outcome is not achieved.

## Adversarial probes (worktree code, run read-only)

Masked correctly: plus addressing `jane+tag@example.com`; upper-case email; `+91-98765-43210`; `+919876543210`; `[98765 43210]`; `tel:9876543210`; `+1.415.555.2671`; `+91 11 2345 6789`; PII in nested dict/list/tuple (`mask_pii_obj`); `Zoë Müller`; `O'Brien-Smith`; non-ASCII names under an English label.

Leaks (not masked), measured:

| Input | Result |
|---|---|
| `josé@exämple.com`, `अनु@example.com` (non-ASCII email) | unmasked, `_EMAIL_RE` is ASCII only |
| Indian landline `011-2345 6789`, `011 23456789`, `0120-4567890`, `022 2345 6789` | unmasked (confirmed through the full prompt for `011-2345 6789`) |
| `98765.43210`, `9876 543 210`, `98 76 54 32 10`, `(98765) 43210` | unmasked |
| Devanagari digits `०९८७६५४३२१०` | unmasked |
| Value typed into a Hindi-labelled name field (`नाम`, `छात्र का नाम`) | unmasked, confirmed through the full prompt (`राहुल शर्मा` reaches the prompt) |
| Name under `fname`, `Nombre`, `Dad`, `Textbox 1`, `First` | unmasked (disclosed limit: generic labels) |
| Obfuscated email `jane [at] example.com`, percent-encoded `a%40b.com` | unmasked |
| `(+91) 98765 43210` | masked but leaves a dangling `(` (cosmetic) |
| `1800 123 4567` toll-free | unmasked (not personal; fine) |

Performance: `mask_pii` is quadratic on long runs without `@`: 20k chars of `a` = 0.65 s, 100k chars = 16.6 s; 50k digits = 4.3 s. Narration and cues are short in practice, so not a FAIL.

## Tests and gates (I ran these)

| Command | Result |
|---|---|
| `uv run pytest tests/test_redact_pii.py tests/test_reconcile_pii.py tests/test_reconcile.py` | `86 passed` |
| `uv run ruff check src tests scripts` | `All checks passed!` |
| `uv run autotester doctor` | `doctor: clean` |
| Importers of `core.redact` | covered by the full suite below |
| Scoped run of all 16 test files that import `core.redact` or sit on the redact path (`test_core`, `test_db`, `test_discover*`, `test_network_assertions`, `test_portal_persona`, `test_prompt_skills`, `test_redact_*` incl. both perf tests, `test_report_export_secrets`, `test_run_pathlynks_first_cases`, `test_run_trace`, `test_source_adapters_drive`, `test_reconcile_schema`) | `316 passed, 1 skipped` (the two redact perf-baseline tests passed on this run) |
| Full `uv run pytest` (security L requirement) | **BLOCKED-PROCESS.** `.work/suite.lock` was held the whole 15-minute window (19:37 to 19:52 IST) by `checker t203-hosting cycle 1 suite`, started 19:29:29 and still held at 19:53. I never took the lock and ran no full suite. A lock-holder or a later checker must run it; any failure there that traces to this diff (it touches only `core/redact.py` additions, `stages/reconcile.py`, two new test files) reopens this verdict. |

## Falsification (throwaway copy of `git archive HEAD`, never the worktree)

Run on the three files above (86 tests; 86 pass unmodified).

| Mutant | Result |
|---|---|
| remove `mask_pii_obj` in `build_judge_prompt` | 6 failed (killed) |
| remove `mask_name_value` call | 4 failed (killed) |
| `mask_pii_obj` no dict recursion | 7 failed (killed) |
| `mask_pii_obj` no list/tuple recursion | 7 failed (killed) |
| drop `has_placeholder`/`MASK` guard | 2 failed (killed) |
| drop `_NOT_PERSON_NAME` exclusion | 4 failed (killed) |
| remove international phone pattern | 5 failed (killed) |
| mask only `video`, not the candidate `other` dict | 86 passed (SURVIVED, no test puts PII in a candidate title/route/control) |
| email regex without `+` in local part | 86 passed (SURVIVED; leaves `jane+<email>` in the prompt, assertions only check the whole raw string, and plus addressing is not in the test inputs) |
| remove the Indian spaced-phone pattern | 86 passed (SURVIVED; `98765 43210` without +91 is not in any test; the other patterns cover the tested inputs) |

The three survivors are test-strength gaps, not code defects: the code behaves correctly on each (I probed them directly above).

## PROPOSED-ISSUE

- PROPOSED-ISSUE (low, data-boundary): `_EMAIL_RE` is ASCII-only, so non-ASCII local parts or domains (`josé@exämple.com`) reach the judge prompt. Fix: use `[^\s@<>()\[\],;:"']+@[^\s@]+\.[^\s@]+` style Unicode-aware pattern.
- PROPOSED-ISSUE (low, data-boundary): Indian STD landlines with separators (`011-2345 6789`, `0120-4567890`), dotted `98765.43210`, grouped `9876 543 210`, and `(98765) 43210` are not masked; for an Indian student product these are likely values. Add a landline/grouped-digit pattern (9 to 12 digits after stripping separators, bounded) and Devanagari digits.
- PROPOSED-ISSUE (low, data-boundary): `mask_name_value` recognises English labels only; a value typed into a Hindi label (`नाम`, `छात्र का नाम`) or `fname`/`Nombre`/`Dad` reaches the prompt. Add common Hindi/transliterated labels, and consider masking any `value` whose label is not on an allow-list of known non-personal fields.
- PROPOSED-ISSUE (low, test-strength): add tests that put PII in the candidate title/route/controls (kills the "mask video only" mutant), assert plus-addressed emails leave no `jane+` fragment, and cover `98765 43210` without a country code.
- PROPOSED-ISSUE (low, perf): `mask_pii` is quadratic on long unbroken runs (100k chars = 16.6 s). Bound input length or anchor the email scan on `@` occurrences.
- PROPOSED-ISSUE (info): narration (`said`) is never name-masked by design; a spoken name that survives the verbatim-quote check goes to the judge. Record this as an accepted limit in RC12.

Metrics: start=2026-10-07T19:15+05:30 end=2026-10-07T19:56+05:30 wall_min=41 agent_min=unavailable blocked_min=15 suite_runs=0 repeat_runs=1 mutations=10 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-07.7
