# Verdict B (blind dual check) — at780-pii (AT-780)

**Checker:** coordinator B · **Commit checked:** 1856e5c4 on `wave/at780-pii` · **Policy:** proportional-verification/2026-10-07.7, tier L (touches `core/redact.py`)
**Cycle checked: 0**

## Check plan (written first)
1. Walk each manifest claim to the code lines and to a named test node.
2. Over-masking / correctness (my focus): replay `tests/fixtures/reconcile/frozen_sample.json` through `reconcile` with masking on and off (monkeypatch the two reconcile imports to identity = the "before" prompt) and diff the judge prompts and the saved bytes; probe `mask_name_value` with a label/value matrix and `mask_pii` with PII-lookalike strings.
3. ReDoS: time `mask_pii` (and each regex) on 5 KB-100 KB adversarial strings.
4. Confirm no existing redact function changed (diff is additions only: `redact.py` +63/-0).
5. Affected tests only (no full suite): `tests/test_redact_pii.py tests/test_reconcile_pii.py tests/test_reconcile.py tests/test_redact*.py`; ruff; `autotester doctor`.
6. Falsification: 13 mutants, each in a throwaway copy under the session scratchpad (never in the worktree), run against the two PII test files (+ `test_reconcile.py` for the placeholder mutant).

## Verdict: PASS

## Evidence
- **Criteria.** RC12 (no PII-shaped value reaches the prompt; secret scrub and refusal unchanged), RC11 (deterministic) and RC14 (design rules) are met.
  - `build_judge_prompt` (`reconcile.py` ~L92-107) masks the step value via `mask_name_value(s.target, s.value)`, then runs `mask_pii_obj` over `video` and `other` before `json.dumps`. `_judged` is the only provider call and uses this prompt (read).
  - Pinned by `test_reconcile_pii.py::test_pii_values_are_masked_in_the_exact_prompt`, `::test_name_field_value_is_masked`, `::test_pii_in_narration_and_cues_is_masked_too`, `::test_non_pii_values_survive_in_the_prompt` and `::test_masking_is_deterministic_rc11`, plus the existing `test_reconcile.py::test_rc11_*` and `test_rc12_*`.
- **Existing redact behaviour unchanged.** `git diff --stat`: `redact.py` +63 -0, with only additions plus the `__all__` entries. The existing redact suite, including the `test_redact_*` files, is green.
- **Tests, lint and doctor, run by me in the worktree.**
  - Affected pytest: `209 passed in 50.30s`.
  - `uv run ruff check src tests scripts`: `All checks passed!`
  - `uv run autotester doctor`: `doctor: clean`.
  - Sizes: `redact.py` 222 lines, `reconcile.py` 296 lines (within the 300-line cap).
- **Frozen-sample replay (matching signal).**
  - The frozen sample produces 2 judge prompts; 1 changes with masking. Only two `"value": "sample"` entries become `"<name>"`.
  - The saved output bytes (`dumped`) are identical before and after, and scoring (`score_screen`) runs before masking, so the bands and the match decisions cannot change.
  - Across all 40 step values in the sample, the only changes are `sample` placeholders under name-ish labels (First/Last/Full/Student name, Account Holder Name, Bank Name). No RC1-RC14 criterion is affected.
  - Course, university and company names, and button text such as "Sign in" and the select values, are untouched.
- **ReDoS: found, quadratic.** `_EMAIL_RE` backtracks quadratically on a long run of `[A-Za-z0-9._%+-]` with no `@`.

  | Input | Time |
  |---|---|
  | 5 KB | 0.02 s |
  | 20 KB | 0.4-0.8 s |
  | 100 KB (`"a"*100000`, `"1"*100000`, `"a."*50000`) | about 19 s |
  | 100 KB of ordinary words | 0.02 s |

  The four phone patterns are linear (about 1 ms on 20 KB). The 100 KB single-token strings are pathological and not realistic for narration or typed values. No RC1-RC14 criterion bounds redaction time, so it is PROPOSED-ISSUE, not FAIL. The project treated the same class as a bug before (AT-606, superlinear folded-secret scan).
- **Falsification (13 mutants; 11 killed, 2 survived).** The 11 killed by `test_redact_pii.py` + `test_reconcile_pii.py`:

  | Mutant | Result |
  |---|---|
  | M1 dict not recursed | 7 failed |
  | M2 lists not recursed | 7 failed |
  | M3 reconcile skips `mask_pii_obj` | 6 failed |
  | M4 raw value in prompt | 4 failed |
  | M5 placeholder guard dropped | 2 failed (run with `test_reconcile.py` as well) |
  | M6 no-letter guard dropped | 2 failed |
  | M7 `course` exclusion dropped | 2 failed |
  | M8 `id` exclusion dropped | 3 failed |
  | M9 role-only path off | 4 failed |
  | M12 phone masking removed | 14 failed |
  | M13 name mask on every label | 10 failed |

  Survivors: M10 (the `(?<![\w+])` and `(?!\w)` anchors on the 10-digit pattern removed) and M11 (an email with a dotless host such as `user@localhost` allowed). Neither anchor is pinned by a test.

## Findings that do not block
Over-masking, under-masking and test gaps, none of which touches an RC1-RC14 criterion:
- **Over-masking by label.** `mask_name_value` masks the value for these labels:
  - `Bank Name`, `Business name`, `Partner name`, `Service name`, `Plan name`, `Scholarship name`, `Template name`, `Agreement name`;
  - a bare `Name` ("Data Science"), `Name of university`;
  - role-only labels where the value is not a name: `Student country`, `Student course`, `Student type`, `Applicant type`, `Guardian consent checkbox`, `Counsellor dashboard`, `Parent` ("Mother").

  The `_NOT_PERSON_NAME` and `_NOT_A_NAME_FIELD` lists are open-ended denylists. The judge loses only the value text, never the label, route or controls, which carry the matching.
- **Under-masking.** `098765 43210` (0-prefix with a space), `9876 543 210`, 7-digit locals, and the `Username` and `Nickname` labels are not masked. The manifest already discloses that names are never guessed from free text.
- **Over-masking by shape.** A bare 10-digit id becomes `<phone>` (disclosed in the manifest).
- **Prompt.** The judge `SKILL.md` does not say what `<name>`, `<email>` and `<phone>` mean. They are self-explanatory, and the file only warns about `[REDACTED]`.
- **Issue closure.** AT-780's `fix_direction` (drop `value`) was replaced by the masking direction, as the manifest says. Close AT-780 against masking.

## PROPOSED-ISSUE lines
- PROPOSED-ISSUE: severity=medium, type=performance/security, feature=redact — `core/redact.py::_EMAIL_RE` is quadratic on long unspaced runs of `[A-Za-z0-9._%+-]` with no `@` (20 KB takes 0.4-0.8 s, 100 KB about 19 s). This is a ReDoS surface on crawled or model-supplied strings reaching `mask_pii_obj`. Expected: time linear in the input length. Fix direction: anchor the scan on `@` (find each `@`, then widen left and right with bounded or possessive scans), or cap the length of a string passed to `mask_pii`. Add a perf test in the style of `tests/test_redact_wrap_perf.py`.
- PROPOSED-ISSUE: severity=low, type=over-masking, feature=reconcile/redact — `mask_name_value` masks non-person values for labels such as Bank/Business/Partner/Service/Plan/Scholarship/Template name, a bare `Name`, and role-only labels such as `Student country/course/type`. Prefer an allowlist of person-name labels (first/last/full/middle/given/family/surname/holder/signature name) over an open denylist. Impact is limited to judge-prompt value text. Scoring and output bytes are unchanged on the frozen sample.
- PROPOSED-ISSUE: severity=low, type=test-gap, feature=redact — the mutants for the 10-digit phone anchors (M10) and the dotless-host email (M11) survive. Add tests that a 12-digit number is not partially masked and that `user@localhost` is (or is not) masked, to pin the intended behaviour.
- PROPOSED-ISSUE: severity=low, type=under-masking, feature=redact — phone shapes `098765 43210` and `9876 543 210` pass through unmasked. Optional.

Metrics: start=2026-10-07 end=2026-10-07 wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=13 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-07.7
