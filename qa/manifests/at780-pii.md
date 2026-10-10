# Manifest — at780-pii

**Unit:** AT-780 — PII-shaped values (emails, phones, person names) are masked before the reconcile judge prompt reaches a model.
**Contract:** `qa/contracts/reconcile.md` RC12 (no secret and no original reaches a model; step values are named), RC11 (deterministic), RC14 (design rules); `core-invariants.md` C1/C2/C3.
**Issue addressed:** AT-780 (low). Umesh's direction supersedes the issue's `fix_direction` (drop `value`): keep the value but mask PII shapes, so the judge still sees the shape of a typed value.
**Date:** 2026-10-07
**Fix cycle:** 0
**Dual check:** no
**Tier:** L (changes `core/redact.py`, security-relevant)
**Base:** origin/master 7782df41, branch `wave/at780-pii`
**Status:** checked-PASS (reviewed at its own commit on base 7782df41; merged head re-check owed by land-integrate-combined)
Policy-Version: proportional-verification/2026-10-07.7
Metrics: start=2026-10-07 end=2026-10-07 wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=5 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-07.7

## What changed

| Path | Change |
|---|---|
| `src/autotester/core/redact.py` (222 lines) | Added `mask_pii(text)` (email -> `<email>`; international, Indian, 10-digit and US-dashed phones -> `<phone>`), `mask_pii_obj(obj)` (recursive), `mask_name_value(label, value)` (`<name>` only when the field label says person name and the value has a letter). No existing function changed. |
| `src/autotester/stages/reconcile.py` (296 lines) | `build_judge_prompt`: step `value` goes through `mask_name_value(target, value)`; then the whole `video` and `other` dicts through `mask_pii_obj` before `json.dumps`. So the prompt, then `redactor.scrub` and `assert_no_raw_secrets` in `_judged`, see only masked text. |
| `tests/test_redact_pii.py` (new) | Unit tests of the three functions. |
| `tests/test_reconcile_pii.py` (new) | Prompt-level tests with the recording `MockProvider` (`reconcile_fakes.judge_prompts`). |

Other model-bound paths in reconcile: none. `_judged` is the only `provider.judge` call and its prompt comes only from `build_judge_prompt`. Narration, cues, targets, route and candidate strings in that prompt are covered by `mask_pii_obj`. Names are never guessed from free text.

## Coverage

| Claim | Test node |
|---|---|
| Email, +91 / plain 10-digit / international / US phones masked in the exact prompt | `tests/test_reconcile_pii.py::test_pii_values_are_masked_in_the_exact_prompt` |
| Name-field values masked (first name, student name, parent, guardian) | `tests/test_reconcile_pii.py::test_name_field_value_is_masked` |
| Email/phone in narration and cues masked | `tests/test_reconcile_pii.py::test_pii_in_narration_and_cues_is_masked_too` |
| Search terms, "2024", "10", course name, student ID not masked | `tests/test_reconcile_pii.py::test_non_pii_values_survive_in_the_prompt`; `tests/test_redact_pii.py::test_non_pii_is_left_alone`, `::test_other_fields_and_non_word_values_are_not_masked` |
| RC11 determinism | `tests/test_reconcile_pii.py::test_masking_is_deterministic_rc11`; `tests/test_redact_pii.py::test_mask_pii_obj_recurses_and_is_deterministic`; existing `tests/test_reconcile.py::test_rc11_*` |
| RC12 secret scrub and refusal unchanged | `tests/test_reconcile.py::test_rc12_*` (all pass) |

## Verify (maker run, worktree)

| Command | Result |
|---|---|
| `uv run pytest tests/test_reconcile.py tests/test_reconcile_schema.py tests/test_reconcile_pii.py tests/test_redact_pii.py tests/test_redact_encoding_coverage.py tests/test_redact_ignorable_perf.py tests/test_redact_obfuscation.py tests/test_redact_wrap_perf.py tests/test_core.py tests/test_prompt_skills.py tests/test_portal_persona.py tests/test_discover.py tests/test_db.py tests/test_network_assertions.py` | `345 passed, 1 skipped` (before the 1-line import re-wrap in reconcile.py; the three reconcile/redact_pii files re-run after: `86 passed`) |
| `uv run ruff check src tests scripts` | `All checks passed!` |
| `uv run autotester doctor` | `doctor: clean` |

No full suite was run (scoped by brief).

## Falsification (throwaway copy under the session scratchpad, never the bound tree)

Suite: `tests/test_reconcile_pii.py` + `tests/test_redact_pii.py` (63 tests; 63 pass on the unmodified copy).

| Sabotage | Result |
|---|---|
| email substitution removed | 5 failed |
| phone substitution removed | 14 failed |
| name mask returns the value unchanged | 16 failed |
| name mask returns `<name>` for every value (over-mask) | 10 failed |
| phone pattern widened to any 2+ digits (over-mask) | 9 failed |
| restored | 63 passed |

## Known limits (disclosed)

- A bare 10-digit run (also 11 with a leading 0, 12 with 91) is treated as a phone number, so a 10-digit order id is masked too. It stays a stable placeholder, so matching is unaffected.
- A person's name typed into a field whose target does not say name/student/parent/guardian etc. is not caught; names in free text are not guessed by design.
- The issue's own fix_direction (drop `value`) was not taken; the checker may close AT-780 against Umesh's masking direction.
