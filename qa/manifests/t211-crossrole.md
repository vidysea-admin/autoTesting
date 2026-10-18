# Manifest - t211-crossrole (T-211, G11-5)

**Status:** checked-PASS (qa/verdicts/t211-crossrole.md a2f1d55e, cycle 0)
**Fix cycle:** 0
**Contract:** qa/contracts/multi-role-platform.md (MP13, MP14, MP15; invariants MPI1, MPI2, MPI3 held)
**Goal task:** T-211
**Authority:** D-104 (Approved-by: Umesh 2026-10-17: build G11 now)
**Dual check:** no (no auth, tenancy or data-write trigger: the runner drives an injected port and reads a clock; it stores nothing and holds no credential)
**Persona walk:** skip (no UI surface in this unit)
**Issues addressed:** none
**Executor:** claude-sonnet-subagent
**Base SHA:** 36a87037 (worktree .worktrees/t211-crossrole, branch wave/t211-crossrole; the T-209 head)
**Code SHA:** 4425f762

## Criteria (quoted verbatim from the contract)
- **MP13 - Role-tagged steps and timed assertions.** A scenario step names the role account that performs it; an assertion names observer role, channel (`ui | mailbox | api`), `present | absent` and within_s; the runner polls until within_s and records the observed time. Verify: fixture where B's view updates after 2 s passes at T=5 and fails at T=1. serves: intent#O18 - closes T-211
- **MP14 - Absence is evidence.** An `absent` assertion passes only after the full window elapsed with no match; a `present` assertion that never matched fails with the window and the last observation. Verify: both directions on the fixture. serves: intent#O18, intent#O3 - closes T-211
- **MP15 - Unbuilt oracles say so.** The oracle registry lists every G11 oracle by module name; a missing module is reported `not built` in the run summary, never omitted. Verify: registry test with one module absent. serves: intent#O20, intent#O4 - closes T-211
- **MPI1 - Leak evidence stores no third-party personal data.** (held: step actions, assertion targets and the recorded last observation refuse or withhold email/phone-shaped text; an oracle error is recorded by exception type only.)
- **MPI3 - One enums file, one editor.** `schema/multi_role_enums.py` is not in `git diff --name-only 36a87037..4425f762`.

## What changed
- `src/autotester/schema/role_step.py` (new, 58 lines): `RoleStep` (id, `role_id`, `action` in the existing `ReproVerb` vocabulary via `parse_repro_step`, personal-shape refused), `StepOutcome`, `StepState` (ok / failed / not_run).
- `src/autotester/schema/cross_role_assertion.py` (new, 83): `CrossRoleAssertion` (observer role, `AssertChannel`, `Expectation`, target, `within_s` in (0, 3600], `poll_interval_s` default 0.5, optional `after_step`), `Observation` (matched, short detail), `AssertionOutcome` (verdict, `observed_s`, window, last observation, reason), `AssertVerdict`.
- `src/autotester/schema/cross_role_scenario.py` (new, 75): `CrossRoleScenario` (roles, ordered steps, assertions; a step/assertion naming an unlisted role, a duplicate id or an unknown `after_step` fails at load) and `ScenarioResult` (steps, assertions, `oracle_summary`, findings, `passed`).
- `src/autotester/schema/oracle_context.py` (new, 109): the published oracle interface (docstring "HOW TO WRITE AN ORACLE"): `OracleContext` (in), `RoleSessionPort` Protocol (`perform`, `observe`; T-210 plugs in here), `OracleState` (`ran` / `not built` / `not run` / `errored`), `OracleStatus`, `OracleRunSummary` (validator: every `OracleName` exactly once).
- `src/autotester/stages/oracle_registry.py` (new, 97): `module_name`, `run_oracles(context, selected, importer)`, `oracle_statuses(importer)`; imports `autotester.stages.oracle_<name>` with `importlib` for all 13 `OracleName` values; absent module = `not built`, any other import failure / missing `run` / raise / wrong return = `errored` (exception type only).
- `src/autotester/stages/cross_role_runner.py` (new, 175): `Clock` Protocol, `SystemClock`, `poll_assertion`, `run_scenario(scenario, port, clock, *, project_slug, run_dir, platform_ids, oracles, importer)`.
- tests: shared helper module `cross_role_fakes` (FakeClock, FrozenClock, ScriptedPort, make_scenario) imported by the three test files; `tests/test_cross_role_runner.py` (12), `tests/test_oracle_registry.py` (12), `tests/test_cross_role_schema.py` (32 parametrised).
- falsified (unchanged): none. No T-207, T-209, T-210 file, `browser/session.py` or `stages/parallel_run.py` touched; `multi_role_session` is not imported.

## Judgement calls for the checker
1. **Window semantics.** The window starts when the assertion is first looked at and the last look is at `elapsed >= within_s` inclusive, so a view that updates at exactly `within_s` passes. `observed_s` is seconds into that window (rounded to ms). The `after_step` field (optional, not in the contract text) lets an assertion start after a named step; default is after the last step.
2. **An erroring observer cannot prove absence.** If any `observe` raised during an `absent` window the assertion FAILS ("absence is not proven"); for `present`, an error is just an unmatched look. Stricter than the contract text, in its spirit (MP14 "absence is evidence").
3. **Failed step.** A step that raises stops the scenario; later steps are `not_run` and every not-yet-decided assertion is `not_run` (reason names the step). Only the exception type is stored.
4. **No MultiRoleFinding from a failed assertion.** `FindingClass` (enums file, T-207's, MPI3) has no cross-role-assertion class, so failures are `AssertionOutcome`s on `ScenarioResult`; mapping to a finding class is the oracle units' job. If the checker wants one, CORE-REQUEST: schema/multi_role_enums.py add a class (T-207 owner).
5. **More than one model per schema file.** OG-CROSSROLE fixes six files, so related shapes share a file (assertion + observation + outcome; step + step outcome; oracle context + status + summary + the port Protocol; scenario + result). Each file's docstring states the one job.
6. **Poll bound.** The poll loop is bounded by `ceil(within_s / poll_interval_s) + 10`, so a clock that never advances ends in a failure (`absent` then fails "window did not elapse"), never a hang. `SystemClock` uses `time.perf_counter` (finer than `time.monotonic` on Windows, which sleeps shorter than its tick).
7. **Registry on the real tree.** All 13 oracle modules are absent today, so `oracle_statuses()` reports 13 x `not built`; as T-212..T-220 land their modules flip to `not run` / `ran` with no edit here.
8. `autotester doctor` reports 2 violations, both stale-generated (docs/MAP.md, docs/SNAPSHOT.md); not hand-edited, the merge-queue owner regenerates. Doc registration of the new modules needs a D-entry (contract "Out of scope").

## Verification scope
Policy-Version: proportional-verification/2026-10-18.15
Tier: L (timing: polling to `within_s`)
Round: 6 src files + 4 test files, 3 criteria (+MPI1, MPI3), est 55 min
Owners: OG-CROSSROLE
Base / checked state: 36a87037 / 4425f762, clean tree
Gate answers: none apply (D-104 opens the build; no gate in qa/gates touches the cross-role runner).
Affected tests / full-suite trigger: none outside the new files (no existing module edited); the builder ran no full suite.
Tests[MP13]: tests/test_cross_role_runner.py - B's view at +2 s passes at window 5 with `observed_s` 2.0 and fails at window 1 with the window and last observation; steps run in order with their roles; the loop sleeps on the fake clock to the full window (4 looks at 0,1,2,3 s); `after_step` start. tests/test_cross_role_schema.py - closed channel set, bad window / poll / target / role / extra field, step vocabulary and personal text, dangling role / step / duplicate ids.
Tests[MP14]: tests/test_cross_role_runner.py - absent passes only at the full window (clock >= 4), fails with the appearance time when it shows at 2 s, is not proven by an erroring observer, and cannot pass on a frozen clock; present-never-matched fails with window and last observation; a failed step leaves the assertion `not_run`.
Tests[MP15]: tests/test_oracle_registry.py - one module absent: all 13 listed, that one `not built`, the others `not run`; the real tree lists 13 with nothing broken; a different missing dependency is `errored` not `not built`; no `run` callable; selected oracles run with counts; a raising oracle is `errored` with the type only; wrong return type; the summary model refuses an omitted or duplicated oracle; the scenario result carries the summary; the oracle receives the live port, never serialised.
Tests[MPI1]: tests/test_cross_role_runner.py::test_observation_text_that_looks_personal_is_withheld_from_the_outcome, tests/test_oracle_registry.py (type-only error), tests/test_cross_role_schema.py (personal-shaped step / target refused).
Tests[MPI3]: none - diff check: `git diff --name-only 36a87037..4425f762` lists only the 10 files above (no `schema/multi_role_enums.py`, `schema/project.py`, T-207/T-209 file, `browser/session.py`, `stages/parallel_run.py`).
Falsification[MP13]: copy-mutants in scratchpad/t211-crossrole/mut (`elapsed >= within_s` -> `within_s * 10`): red `test_mp13_polls_until_the_window_not_sleeping_for_real` (1 failed, 55 passed); `observed_s` dropped from the passing present outcome: red `test_mp13_view_updating_after_2s_passes_at_window_5_and_records_observed_time` (1 failed); restored 56 passed.
Falsification[MP14]: copy-mutants: absent no longer requires the elapsed window (`if elapsed < within_s` -> `if False`): red `test_a_clock_that_never_advances_cannot_pass_an_absent_assertion` (1 failed); observer-error guard removed: red `test_mp14_absent_is_not_proven_by_an_observer_that_errored` (1 failed); restored 56 passed.
Falsification[MP15]: copy-mutants: `not built` entries dropped from the summary: red (many, the validator raises and `test_mp15_one_absent_module...`); same with the summary validator also disabled: red `test_mp15_one_absent_module_is_reported_not_built_and_not_omitted`, `test_mp15_the_real_tree_lists_all_thirteen...`, `test_the_summary_model_refuses_an_omitted_or_duplicated_oracle` (5 failed, 51 passed); unmutated control copy 56 passed.
Pre-check[MP13]: 4425f762 uv run --directory <worktree> pytest tests/test_cross_role_runner.py tests/test_cross_role_schema.py -> 44 passed t=1 blobs=tests/test_cross_role_runner.py:2521d1a,tests/test_cross_role_schema.py:85c5cdc
Pre-check[MP14]: 4425f762 uv run --directory <worktree> pytest tests/test_cross_role_runner.py -> 12 passed t=1 blobs=tests/test_cross_role_runner.py:2521d1a
Pre-check[MP15]: 4425f762 uv run --directory <worktree> pytest tests/test_oracle_registry.py -> 12 passed t=1 blobs=tests/test_oracle_registry.py:49d506c
Lint: 4425f762 `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> 2 violations, both stale-generated (judgement call 8).
Metrics: start=2026-10-18T11:00:00Z end=2026-10-18T11:50:00Z wall_min=50 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=6 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=unavailable mutants=6 defects_unit=0 defects_6c=0 tests=56 tests_min=1

## How to verify (commands + expected)
- `uv run pytest tests/test_cross_role_runner.py tests/test_oracle_registry.py tests/test_cross_role_schema.py` -> expected: 56 passed.
- `git diff --name-only 36a87037..4425f762` -> expected: the 10 files listed, nothing else.

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| MP13 | polls to within_s on an injected clock, records observed time | tests/test_cross_role_runner.py::test_mp13_view_updating_after_2s_passes_at_window_5_and_records_observed_time | drop `observed_s` / widen the window x10 | green on tree; red on both mutants |
| MP14 | absent passes only after the full window; error is not absence | tests/test_cross_role_runner.py::test_a_clock_that_never_advances_cannot_pass_an_absent_assertion, ::test_mp14_absent_is_not_proven_by_an_observer_that_errored | remove the elapsed-window check / the error guard | green; red on each |
| MP15 | all 13 oracles listed, absent = `not built` | tests/test_oracle_registry.py::test_mp15_one_absent_module_is_reported_not_built_and_not_omitted | omit `not built` rows (and disable the summary validator) | green; red (5 failed) |

## Live browser evidence
Not UI-touching - no surface changed: only schema and stage modules plus tests; no route, template or static asset.

## Status: checked-PASS (qa/verdicts/t211-crossrole.md a2f1d55e, cycle 0)
