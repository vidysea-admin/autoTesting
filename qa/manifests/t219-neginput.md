# Manifest - t219-neginput (T-219, G11-5)

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** qa/contracts/multi-role-platform.md (MP32; invariants MPI1, MPI2, MPI3 held)
**Goal task:** T-219
**Authority:** D-104 (Approved-by: Umesh 2026-10-17: build G11 now; Umesh 2026-10-18: "build all remaining features")
**Dual check:** no (no auth, tenancy, production-write or security trigger: the oracle drives an injected port with synthetic values and stores nothing)
**Persona walk:** skip (no UI surface in this unit)
**Issues addressed:** none
**Executor:** claude-sonnet-subagent
**Base SHA:** cff3ffe6 (worktree .worktrees/t219-neginput, branch wave/t219-neginput; the T-211 head, stacked on T-209 36a87037 and T-207)
**Code SHA:** 62eba1e4

## Criteria (quoted verbatim from the contract)
- **MP32 - Negative input per role (T-219).** For each form flow, the INPUT_EMPTY, INPUT_BOUNDARY, INPUT_UNICODE_OVERSIZE and DOUBLE_SUBMIT cases that `stages/expand.py` already produces run once per role account whose permitted surface reaches the form; `expand.py` is not edited. A submission the product accepts in breach of a declared `FieldConstraints` rule, a rule enforced for one role and not another, or a double submit that creates two records is a finding naming the role, form, rule and class. Verify: a synthetic fixture form with a rule matrix (required, min and max length, pattern, numeric range), enforced for role A and skipped for role B, plus a non-idempotent submit; every matrix cell is asserted, and a mutation that drops the per-role loop turns the role-B cells red. serves: intent#O20, intent#O3 - closes T-219
- **MPI1 - Leak evidence stores no third-party personal data.** (held: a finding holds rule, field name, class and role only, never a submitted or valid value; a `valid_values` entry that looks like an email or phone is refused at load; an oracle error is reported by exception type only by the registry.)
- **MPI3 - One enums file, one editor.** `schema/multi_role_enums.py` is not in `git diff --name-only cff3ffe6..62eba1e4`.

## What changed
- `src/autotester/stages/oracle_negative_input.py` (new, 275 lines): `run(context)` (the T-211 oracle interface; bound by assignment `run = _run`, see judgement call 5), `load_forms`, `form_probes` / `field_probes` (deterministic violating values from each declared `FieldConstraints` rule), `probe_cells` (every probe once per role in `form.role_ids`, intersected with `context.role_ids`), `findings_from_cells`, `FormInputPort` Protocol (`fill_field`). It calls `stages/expand.py::applicable_classes(flow)` to decide which of the four input classes the flow is asked about (expand.py is read, not edited).
- `src/autotester/schema/negative_input_form.py` (new, 52): `NegativeInputForm` - reuses `schema/flowspec.py` `Flow` / `InputField` / `FieldConstraints`; adds roles that reach the form, URL template, submit / rejection / duplicate selectors and one valid value per field.
- `src/autotester/schema/negative_input_cell.py` (new, 42): `ProbeCell` (form, role, field, `InputRule`, `CaseClass`, `breached`) and the closed `InputRule` set (required, min_length, max_length, pattern, min, max, double_submit). Cells exist for passes too, so the whole matrix is assertable.
- tests: helper module `negative_input_fakes` (FakeFormPort with per-role enforced rules and per-role idempotence; its constraint checker is independent code), `tests/test_negative_input_oracle.py` (15 tests).
- Not touched: `stages/expand.py`, `stages/oracle_registry.py`, any T-207/T-209/T-211 file, `schema/multi_role_enums.py`, `schema/enums.py`, `schema/project.py`, `browser/session.py`.

## Judgement calls for the checker
1. **Two schema files beyond OG-NEGIN's single stage file.** The design rule (Pydantic shapes live in `schema/`, one model per file) needs `NegativeInputForm` and `ProbeCell`; both names are new and unique, so no other G11 group collides. `InputRule` is local to its schema file (MPI3: no new enum in the enums file).
2. **How the oracle gets its forms.** `OracleContext` carries no flow, so `run` reads `<run_dir>/negative_input_forms.json` (a list of `NegativeInputForm`). A missing file raises `NegativeInputPlanMissing`, so the registry reports `errored` (type name only), never a clean "no findings" that would hide an unprobed form.
3. **"Permitted surface reaches the form" is declared, not discovered:** `form.role_ids`. A run that lists accounts (`context.role_ids`) probes only the roles in both.
4. **Rejection / duplicate are two selectors.** `RoleSessionPort.observe` is a single `matched` bool. A violating submit counts as accepted (breach) when `rejection_target` does not match; a double submit is a breach when `duplicate_target` (a selector that matches only when a second record with the same content exists) matches. Re-observed once per probe, no polling (the port decides how long a look takes; `within_s` is a 1 s hint).
5. **`run = _run`, not `def run`.** `autotester doctor` flags a second top-level `run` as `duplicate-concept` (doctor.py defines one) and every oracle module must expose `run`; measured: a plain `def run` gives 3 violations, the assignment gives the 2 stale-generated ones. Suggestion for the doctor owner: exempt `stages/oracle_*.py` from that rule so the other 12 oracle units need no workaround.
6. **CORE-REQUEST: schema/oracle_context.py `RoleSessionPort` (T-211 owner)** - typing a field value. `RoleStep.action` is capped at 200 chars and cannot carry an oversize value, so this oracle needs `fill_field(role_id, field, value)` on the session port. It is declared locally as `FormInputPort` (runtime-checkable) and `probe_cells` raises `TypeError` for a port without it. T-210's `multi_role_session` must implement it (or `RoleSessionPort` gains it).
7. **Probe values are best-effort isolations.** The filler character is chosen to satisfy the field's own pattern so a length probe breaks only the length rule; a pattern with no breaking candidate yields no probe (untestable, not a pass). The unicode-oversize probe uses a unicode filler where the pattern admits one, else an ASCII filler at `2*max_length+1` (capped at 5000 chars). A numeric min/max probe is `min-1` / `max+1`.
8. **Finding shape.** `finding_class = NEGATIVE_INPUT` for all cells (priority comes from `finding_priority`, not set here); `count` is 1 (one accepted submission) or 2 (two records); the title names role, form, rule, field, class and, when another role held the same rule, `the rule held for role <ids>` (that is the "enforced for one role and not another" case, carried by the breached role's finding rather than a second finding).
9. `autotester doctor`: 2 violations, both stale-generated (docs/MAP.md, docs/SNAPSHOT.md); not hand-edited, the merge queue regenerates.

## Verification scope
Policy-Version: proportional-verification/2026-10-18.15
Tier: M (new shared-shape schema reads plus a stage module; no L trigger)
Round: 3 new src files + 2 test files, 1 criterion (+MPI1, MPI3), est 30 min
Owners: OG-NEGIN
Base / checked state: cff3ffe6 / 62eba1e4, clean tree
Gate answers: none apply (D-104 opens the build; no gate in qa/gates touches negative input).
Affected tests / full-suite trigger: none outside the new files (no existing module edited); the builder ran no full suite.
Tests[MP32]: tests/test_negative_input_oracle.py - the full 20-cell matrix (10 cells x role-a, role-b) asserted equal to an explicit expectation (role-a every rule held and idempotent, role-b required and min_length held, the other six cells and the double submit breached); 7 findings all for role-b, each naming role, form, rule, class and the roles that held the rule; double submit count 2; boundary values (min-1, max+1, "17", "100", unicode oversize); only expand.py's applicable classes are probed (no fill step -> double submit only; no duplicate selector -> none); a role the run has no account for is skipped; registry run reports `ran` with 7 findings; missing forms file -> `errored NegativeInputPlanMissing`; port without `fill_field` refused. The fake port lives in the helper module negative_input_fakes (imported, not collected).
Tests[MPI1]: tests/test_negative_input_oracle.py::test_mpi1_findings_never_hold_a_submitted_or_valid_value, ::test_the_form_schema_is_closed (personal-shaped valid value refused).
Tests[MPI3]: none - diff check: `git diff --name-only cff3ffe6..62eba1e4` lists only the 5 files above.
Falsification[MP32]: copy-mutant in scratchpad/t219-neginput (src + the two test files, run with PYTHONPATH on the copy, `--noconftest`): `for role_id in form_roles(form, context_roles):` -> `...[:1]:` (drops the per-role loop): 7 failed / 8 passed, role-b cells red - `test_mp32_every_cell_of_the_rule_matrix_is_asserted_for_both_roles` (assert 10 == 20), `test_mp32_role_a_is_clean_and_role_b_gets_one_finding_per_skipped_cell` (set() != {'role-b'}), `test_mp32_a_finding_names_role_form_rule_and_class`, the double-submit and registry tests; restored 15 passed, copy identical to the tree. Extra (guidance, not floor): breach polarity inverted (`not drv.seen(...)` -> `drv.seen(...)`): 5 failed; second submit of a double submit dropped: 4 failed; each restored.
Pre-check[MP32]: 62eba1e4 uv run --directory D:/autoTesting/.worktrees/t219-neginput pytest tests/test_negative_input_oracle.py -> 15 passed t=5 blobs=tests/test_negative_input_oracle.py:97b5983,tests/negative_input_fakes.py:e7c4aa1
Lint: 62eba1e4 `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> 2 violations, both stale-generated (judgement call 9).
Metrics: start=2026-10-19T00:00:00Z end=2026-10-19T00:40:00Z wall_min=40 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=unavailable mutants=3 defects_unit=0 defects_6c=0 tests=15 tests_min=1

## How to verify (commands + expected)
- `uv run pytest tests/test_negative_input_oracle.py` -> expected: 15 passed.
- `git diff --name-only cff3ffe6..62eba1e4` -> expected: the 5 files listed, nothing else.

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| MP32 | each probe runs once per role that reaches the form; a breach is a finding naming role, form, rule, class | tests/test_negative_input_oracle.py::test_mp32_every_cell_of_the_rule_matrix_is_asserted_for_both_roles | drop the per-role loop (`[:1]`) | green on tree (20 cells); red on mutant (10 != 20, role-b findings gone) |

## Live browser evidence
Not UI-touching - no surface changed: only schema and stage modules plus tests; no route, template or static asset.

## Status: ready-for-check
