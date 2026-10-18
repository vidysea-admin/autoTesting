# Manifest - t220-state (T-220, G11)

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** qa/contracts/multi-role-platform.md (MP33; invariants MPI1, MPI2, MPI3 held)
**Goal task:** T-220
**Authority:** D-104 (Approved-by: Umesh 2026-10-17: build G11 now; Umesh 2026-10-18: "build all remaining features")
**Dual check:** no (no security, auth, tenancy or production-write trigger: the oracle drives an injected port and stores no page text or credential)
**Persona walk:** skip (no UI surface in this unit)
**Issues addressed:** none
**Executor:** claude-sonnet-subagent
**Base SHA:** cff3ffe6 (worktree .worktrees/t220-state, branch wave/t220-state; the T-211 head)
**Code SHA:** 31cbde82

## Criteria (quoted verbatim from the contract)
- **MP33 - State consistency after an action (T-220).** A `StateProbe` (`schema/state_probe.py`, reusing `schema/flowspec.py::ExpectedState`) names a counter, list or status reader (selector or first-party API pattern), the expected delta and the reader roles. The oracle reads before the action, after it, and after a reload, as each reader role; a missing, wrong-sized or non-persistent change is a finding citing all three readings. Verify: a synthetic fixture with three faults (counter not incremented, incremented only for the actor, reverted on reload) and one correct counter; each fault is reported and the correct one is not. serves: intent#O18, intent#O20 - closes T-220
- **MPI1 - Leak evidence stores no third-party personal data.** (held: a reading is an integer or a declared-token label, never the page text; an oracle error is recorded by exception type only.)
- **MPI2 - Fixtures stay blind.** (held: the fixture is a synthetic two-role counter app, `tests/state_after_fakes.py`.)
- **MPI3 - One enums file, one editor.** `schema/multi_role_enums.py` is not in `git diff --name-only cff3ffe6..31cbde82`.

## What changed
- `src/autotester/schema/state_probe.py` (new, 100 lines): `StateProbe` (id, platform, `ReaderKind`, reader channel `ui|api` only, reader target, reader URL as a placeholder template, the actor `RoleStep`, reader roles, `expected_delta` for counter/list or `expected_state: ExpectedState` for status), plus `ReaderKind` and `StateFault` (missing / wrong_size / not_persisted / unreadable), both local because `multi_role_enums.py` is T-207's alone (MPI3).
- `src/autotester/stages/oracle_state_after.py` (new, 171): `check_state_after(context)` exposed as module `run` (the registry contract). Loads `<run_dir>/state_probes.json`; per probe: every reader role opens the reader URL, is read (before), the actor step runs once, every reader is read (after), every reader reloads and is read again; one `MultiRoleFinding` (class `state_not_persisted`, oracle `state_after`, P1 by `finding_priority`) per failing reader role, title citing the fault and `before= after= reload=`.
- tests: `tests/test_state_probe_schema.py` (19), `tests/test_oracle_state_after.py` (13), helper `tests/state_after_fakes.py` (scripted two-role app with modes correct / not_incremented / actor_only / reverted / double).
- falsified (unchanged): no T-207/T-209/T-211 file, `schema/enums.py`, `schema/project.py`, `browser/session.py` or the registry touched.

## Judgement calls for the checker
1. **Where probes come from.** `OracleContext` has no probe field and may not be edited here, so the oracle reads `<run_dir>/state_probes.json` (a list of `StateProbe`); an absent file is "nothing to check" (empty list), an invalid one raises and the registry reports `errored` with the type only. CORE-REQUEST: schema/oracle_context.py add an optional typed probes field if the checker prefers context over a file (T-211 owner).
2. **Readings through the existing port.** The oracle uses `RoleSessionPort.observe` with a `CrossRoleAssertion` (PRESENT, `target` = reader target, `within_s` 1) and `perform` of `goto <reader_url>` for loads and reloads. The contract for a counter/list reader is that `Observation.detail` carries the count text (first integer, up to 9 digits); for a status reader it is the visible text, reduced to the declared `visible_text` tokens (`none` if absent). T-210's real session must honour this; it is not merged yet.
3. **Non-actor staleness.** The actor's own in-place "after" reading must show the change. A non-actor reader's page may be stale until reload, so for that role the reload reading decides: stale-after but correct-on-reload is clean (test `test_a_stale_non_actor_page_that_is_right_after_reload_is_clean`). A non-actor whose after is right but reload is not is `not_persisted`.
4. **Unreadable is a finding.** A reader that does not match, raises, or has no integer is a `unreadable` finding (class `state_not_persisted`, no class exists for it), never a silent pass. An action (`perform`) that raises propagates, so the registry reports `errored` with the exception type; other probes' findings are lost in that case.
5. **Readings live in the title.** `MultiRoleFinding` has no readings field, so the three readings are in the (200-char) title as numbers or declared tokens. `count` is the size of the deviation (min 1).
6. **`run` is an alias.** The registry needs a module-level `run`, but `autotester doctor` rejects a function name defined in two modules (`doctor.py` already defines `run`, and all 13 oracles would). So the function is `check_state_after` and `run = check_state_after`. CORE-REQUEST: the other 12 oracle units will hit the same doctor rule; either use the alias or exempt `run` in `doctor.py::check_duplicate_definitions`.
7. **Status has no baseline requirement.** A status probe passes if after and reload satisfy `expected_state` (all `visible_text` shown, no `absent_text`), whatever the before reading was.
8. `autotester doctor` reports 2 violations, both stale-generated (docs/MAP.md, docs/SNAPSHOT.md); not hand-edited.

## Verification scope
Policy-Version: proportional-verification/2026-10-18.15
Tier: M
Round: 5 files, 1 criterion, est 30 min - two new src files plus three new test files, one scripted-app fixture, no existing module edited
Owners: OG-STATE
Base / checked state: cff3ffe6 / 31cbde82, clean tree
Gate answers: none apply (D-104 opens the build; no gate in qa/gates touches a state oracle).
Affected tests / full-suite trigger: none outside the new files (no existing module edited); the builder ran no full suite.
Tests[MP33]: tests/test_oracle_state_after.py - each of the three faults reported and the correct counter clean; all three readings and the fault name cited; class, oracle, P1 and a replayable repro; exact perform order (load, read, act once, reload, read); wrong-sized change; stale non-actor page clean; status clean / reverted-on-reload with token labels; unreadable reader; page text never copied; no probe file / no port; failing action reported by the registry as the exception type only. tests/test_state_probe_schema.py - closed kinds, expectation matches kind, no mailbox channel, id-bearing URL and personal-shaped target refused.
Tests[MPI1]: tests/test_oracle_state_after.py::test_readings_are_numbers_only_never_the_page_text, ::test_a_status_that_reverts_on_reload_is_not_persisted_and_cites_labels, ::test_a_failing_action_propagates_and_the_registry_reports_the_type_only; tests/test_state_probe_schema.py (personal-shaped target refused).
Tests[MPI3]: none - diff check: `git diff --name-only cff3ffe6..31cbde82` lists only the 5 files above (no `schema/multi_role_enums.py`).
Falsification[MP33]: copy-mutants in scratchpad/t220-state (PYTHONPATH copy of src; control 13 passed): reload read replaced by the after reading: red 5 (`test_each_fault_is_reported_and_the_correct_counter_is_not`, `..._cites_all_three_readings...`, `..._replayable_repro`, `test_a_stale_non_actor_page...`, status-reverts); reader roles limited to the actor (per-role loop dropped): red 5 (`test_each_fault...`, `..._cites_all_three...`, `test_the_oracle_loads_every_reader...`, `test_the_registry_runs_this_module...`); any-change instead of exact expected delta: red 1 (`test_a_wrong_sized_change_is_a_finding`). (A fourth, before-reading hard-coded, was also red with 4 failures; not counted against the tier cap.)
Pre-check[MP33]: 31cbde82 uv run --directory <worktree> pytest tests/test_state_probe_schema.py tests/test_oracle_state_after.py tests/test_oracle_registry.py tests/state_after_fakes.py -> 44 passed t=6 blobs=tests/test_oracle_state_after.py:7daa398,tests/test_state_probe_schema.py:39ae7af,tests/state_after_fakes.py:46686b4
Pre-check[MPI1]: 31cbde82 uv run --directory <worktree> pytest tests/test_oracle_state_after.py tests/test_state_probe_schema.py tests/state_after_fakes.py -> 32 passed t=2 blobs=tests/test_oracle_state_after.py:7daa398,tests/test_state_probe_schema.py:39ae7af
Lint: 31cbde82 `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> 2 violations, both stale-generated (judgement call 8).
Metrics: start=2026-10-19T09:00:00Z end=2026-10-19T09:30:00Z wall_min=30 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=unavailable mutants=3 defects_unit=0 defects_6c=0 tests=44 tests_min=1

## How to verify (commands + expected)
- `uv run pytest tests/test_state_probe_schema.py tests/test_oracle_state_after.py tests/test_oracle_registry.py` -> expected: 44 passed.
- `git diff --name-only cff3ffe6..31cbde82` -> expected: the 5 files listed, nothing else.

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| MP33 | reads before / after / after reload per reader role; reports missing, wrong-sized, non-persistent | tests/test_oracle_state_after.py::test_each_fault_is_reported_and_the_correct_counter_is_not, ::test_a_wrong_sized_change_is_a_finding | reload read = after read; roles = actor only; exact delta -> any change | green on tree; red on each (5, 5, 1 failed) |

## Live browser evidence
Not UI-touching - no surface changed: only a schema module, a stage module and tests; no route, template or static asset.

## Status: ready-for-check
