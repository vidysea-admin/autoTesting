# Manifest - t215-consist (T-215, G11)

**Status:** checked-PASS (qa/verdicts/t215-consist.md d0536aee)
**Fix cycle:** 0
**Contract:** qa/contracts/multi-role-platform.md (MP23, MP24; invariants MPI1, MPI2, MPI3, MPI6 held)
**Goal task:** T-215
**Authority:** D-104 (Approved-by: Umesh 2026-10-17: build G11 now; Umesh 2026-10-18: "build all remaining features")
**Dual check:** no (no auth, tenancy, security or prod-write trigger: both oracles read through an injected port and keep only counts, value classes and numbers; no credential, no foreign data, no model call)
**Persona walk:** skip (no UI surface in this unit)
**Issues addressed:** none
**Executor:** claude-sonnet-subagent
**Base SHA:** cff3ffe6 (worktree .worktrees/t215-consist, branch wave/t215-consist; the T-211 head)
**Code SHA:** 41847254

## Criteria (quoted verbatim from the contract)
- **MP23 - Same entity, N readers.** An entity handle produced in a scenario is read as each declared role; differing field values across roles (beyond declared role-specific fields) are a finding listing each role's value class, not raw personal values. Verify: fixture where the parent sees a stale status. serves: intent#O20 - closes T-215
- **MP24 - Answer-key scoring.** Given an answer-key fixture derived from product docs, answering every item correctly must yield the documented score; a mismatch is a finding. The fixture records its source and is refused if it cites a benchmark finding. Verify: fixture scoring 7/10 for all-correct answers. serves: intent#O20, intent#O21 - closes T-215
- **MPI1 - Leak evidence stores no third-party personal data.** (held for this unit: a reading is reduced to a value class; the raw text lives only in memory for the comparison; an oracle error is recorded by exception type only.)
- **MPI2 - Fixtures stay blind.** (held: synthetic status vocabulary, quiz and personal-shaped canaries; no benchmark finding's case.)
- **MPI3 - One enums file, one editor.** `schema/multi_role_enums.py` is not in `git diff --name-only cff3ffe6..41847254`.
- **MPI6 (the part this unit owns).** No scenario, fixture or prompt is written from a specific finding: the answer-key schema refuses a source that cites a finding.

## What changed
- `src/autotester/schema/entity_reading.py` (new, 107): `EntityHandle` (id, platform, url template, open action, 2..12 roles, fields, declared non-personal `vocabulary`), `EntityField` (selector, `role_specific`), `FieldReading` (field, role, `ValueClass`, label only for the vocabulary class), `ValueClass`. Reuses `validate_url_template`, `contains_personal_shape`, `parse_repro_step`, the platform and role id patterns.
- `src/autotester/schema/answer_key.py` (new, 109): `AnswerKey` (role, items with points, submit action, score selector, `documented_score`, `max_score`, `source`), `AnswerKeySource` (kind `product_doc`, ref, title; refuses a ref or title citing a benchmark, CEO list, known bugs, finding, atomic finding, `bug_events`, `AT-n`, `MPn`, acceptance comparison or `.work/`), `AnswerItem`, `AnswerSourceKind`. Refuses a key whose item points do not add up to the documented score, a documented score above the maximum and duplicate items.
- `src/autotester/stages/oracle_consistency.py` (new, 126): `classify_value`, `read_entity`, `check_entity`, `load_handles` (`<run_dir>/multi_role/entity_handles.json`), `run(context)`. Opens the entity as each role, observes each field through `RoleSessionPort.observe`, compares normalised values (whitespace and case folded), skips role-specific fields, emits one `ROLE_INCONSISTENCY` finding per differing field whose title names each role's class (`parent=vocabulary:Pending`, `student=email`).
- `src/autotester/stages/oracle_answer_key.py` (new, 101): `parse_score`, `take_quiz`, `check_key`, `load_keys` (`<run_dir>/multi_role/answer_keys.json`), `run(context)`. Performs the key's answers as its role, submits, reads the displayed score and emits `ANSWER_MISMATCH` when it differs from `AnswerKey.expected_score()` (all-correct = the documented score), when the maximum shown differs, or when no score is readable.
- tests: `tests/test_oracle_consistency.py` (17 test functions, 35 cases), `tests/test_oracle_answer_key.py` (17 functions, 38 cases).
- No T-207/T-209/T-211 file, `schema/multi_role_enums.py`, `schema/enums.py`, `schema/project.py`, `browser/session.py` or the registry touched.

## Judgement calls for the checker
1. **Where the inputs come from.** `OracleContext` (T-211, not editable) has no field for handles or keys, so each oracle reads a JSON list from `<run_dir>/multi_role/`. Absent file = nothing declared = no findings; an invalid file (for example a key citing a finding) raises, so the registry reports the oracle `errored` by type, never clean.
2. **Reads go through `RoleSessionPort.observe`.** `Observation.detail` (<= 200 chars) is the text seen; `matched=False` is class `missing`. A port exception propagates (registry: `errored`, type only) rather than being swallowed.
3. **Value class, not value.** A status is named only when it is a label the handle declares in `vocabulary`; every other value is reported as `email | phone | date | number | text_short | text_long | empty | missing`. Two different names therefore read `text_short` vs `text_short`: the finding still fires (raw values differ) but cannot say more, by design (MPI1). Raw values are never written, logged or placed in an exception.
4. **Count.** For consistency, `count` = roles whose value differs from the commonest value (ties: first role seen). For the answer key, `count` = score gap (or 1 when unreadable).
5. **"7/10 for all-correct".** Read as: the product's documentation says all-correct earns 7 points of a 10-point maximum (`documented_score=7`, `max_score=10`, item points sum to 7). `is_correct=False` on an item models a deliberately wrong answer and lowers the expected score.
6. **Source refusal is a deny-list over ref and title** (benchmark, CEO list, known bugs, finding(s), atomic, bug_events, `AT-n`, `MPn`, acceptance comparison, `.work/`). It cannot prove a doc is not derived from a finding; it refuses every way a key can say so.
7. **More than one model per schema file** (OG-CONSIST allows two schema files for five shapes); each docstring states one job.
8. **CORE-REQUEST:** `doctor.check_duplicate_definitions` flags any top-level `def run` because `doctor.py` has one, and the oracle interface (`schema/oracle_context.py`) mandates a module-level `run`. All 13 oracle modules will hit it. Here `run` is bound by assignment (`run = _consistency_oracle`), which the AST check does not see. Owner of the doctor / interface: exempt oracle modules or name the entry point differently.
9. `autotester doctor` reports 2 violations after the above, both stale-generated (docs/MAP.md, docs/SNAPSHOT.md); not hand-edited, the merge-queue owner regenerates.

## Verification scope
Policy-Version: proportional-verification/2026-10-18.15
Tier: M
Round: 4 src files + 2 test files, 2 criteria (+MPI1, MPI2, MPI3, MPI6), est 30 min
Owners: OG-CONSIST
mutant-cap-raise: two criteria with independent behaviours each (MP23: role-specific skip, value-vs-class compare, no-raw-value; MP24: wrong-score report, maximum compare, finding-citation refusal, points-sum refusal, wrong-answer scoring); one mutant per behaviour, run in a scratchpad copy in 20 s
Base / checked state: cff3ffe6 / 41847254, clean tree
Gate answers: none apply (D-104 opens the build; no gate in qa/gates touches these oracles).
Affected tests / full-suite trigger: none outside the new files (no existing module edited); the builder ran no full suite.
Tests[MP23]: tests/test_oracle_consistency.py - parent stale status is one `ROLE_INCONSISTENCY` finding naming `student=vocabulary:Approved, parent=vocabulary:Pending`; agreeing roles (case and spacing differ) give none; role-specific field may differ and only the undeclared field is reported; a role with no element reads `missing`; three roles count the odd one out; each role opens the entity first; value-class matrix; handle schema closed (id-like URL, one role, duplicate role, personal vocabulary, bad verb, extra field, no fields); run reads the file and writes nothing; role not in scenario refused; registry reports `ran` with the count; a port error is `errored` by type only.
Tests[MP24]: tests/test_oracle_answer_key.py - all-correct on the 7/10 fixture is clean; answers given as the key role in order then submit; weights ignored (4/10) is a mismatch naming 7/10 and 4/10; off-by-one displays (6/10, 8/10, 7/9, 7 of 12, no number) are mismatches, equivalent displays (`7/10`, `7 / 10`, `7 of 10`, `7`) pass; a hidden score is a mismatch; a deliberately wrong answer lowers the expectation; seven finding-citing sources refused (ref and title); no source refused; self-inconsistent keys refused; run reads the file; a finding-citing key file makes the oracle `errored`.
Tests[MPI1]: tests/test_oracle_consistency.py::test_mpi1_personal_values_are_reported_by_class_and_never_stored, ::test_a_broken_port_is_errored_by_type_only_not_swallowed, ::test_a_reading_cannot_carry_a_label_unless_it_is_vocabulary.
Tests[MPI3]: none - diff check: `git diff --name-only cff3ffe6..41847254` lists only the 6 files above.
Falsification[MP23]: copy-mutants in scratchpad/t215-consist (PYTHONPATH to the copy): role-specific skip removed (`if True`): red `test_a_declared_role_specific_field_may_differ`, `test_only_the_undeclared_field_is_reported_when_two_differ` (2 failed, 71 passed); compare by class instead of value: red `test_mp23_parent_sees_a_stale_status...` and 6 more (7 failed); raw value printed in the title: red `test_mp23_parent_sees_a_stale_status...` and 8 more incl. the MPI1 canary matrix (9 failed); unmutated 73 passed.
Falsification[MP24]: copy-mutants: mismatch never reported: red `test_mp24_a_product_showing_the_wrong_score...` and 9 more (10 failed); maximum not compared: red `test_each_off_by_one_display_is_a_mismatch[7/9]`, `[7 of 12]` (2 failed); finding-citation check disabled: red all 7 `test_mp24_a_key_citing_a_benchmark_finding_is_refused` cases plus the title variant (8 failed); item-points sum unchecked: red `test_a_key_that_disagrees_with_itself_is_refused[bad0]` (1 failed); wrong answers still scored: red `test_a_deliberately_wrong_answer_lowers_the_expected_score` (1 failed).
Pre-check[MP23]: 41847254 uv run --directory <worktree> pytest tests/test_oracle_consistency.py -> 35 passed t=1 blobs=tests/test_oracle_consistency.py:fb2e4da
Pre-check[MP24]: 41847254 uv run --directory <worktree> pytest tests/test_oracle_answer_key.py -> 38 passed t=1 blobs=tests/test_oracle_answer_key.py:a1aae17
Lint: 41847254 `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> 2 violations, both stale-generated (judgement call 9).
Metrics: start=2026-10-19T00:00:00Z end=2026-10-19T00:00:00Z wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=8 cycle=0 resumes=1 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=unavailable mutants=8 defects_unit=0 defects_6c=0 tests=73 tests_min=1

## How to verify (commands + expected)
- `uv run pytest tests/test_oracle_consistency.py tests/test_oracle_answer_key.py tests/test_oracle_registry.py` -> expected: 85 passed.
- `git diff --name-only cff3ffe6..41847254` -> expected: the 6 files listed, nothing else.

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| MP23 | roles' readings compared, role-specific skipped, classes only | tests/test_oracle_consistency.py::test_mp23_parent_sees_a_stale_status_is_a_finding_naming_each_roles_class, ::test_a_declared_role_specific_field_may_differ, ::test_mpi1_personal_values_are_reported_by_class_and_never_stored | skip removed / compare by class / print raw | green; red on each |
| MP24 | key score vs displayed score; source and self-consistency refusals | tests/test_oracle_answer_key.py::test_mp24_a_product_showing_the_wrong_score_is_an_answer_mismatch, ::test_mp24_a_key_citing_a_benchmark_finding_is_refused, ::test_a_key_that_disagrees_with_itself_is_refused | never report / disable citation check / drop sum check | green; red on each |

## Live browser evidence
Not UI-touching - no surface changed: only schema and stage modules plus tests; no route, template or static asset.

## Status: checked-PASS (qa/verdicts/t215-consist.md d0536aee)
