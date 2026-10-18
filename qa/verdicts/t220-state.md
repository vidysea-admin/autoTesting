# Verdict - t220-state (T-220, MP33) - Mode A, tier M, single checker

Cycle checked: 0
Date: 2026-10-18
Code SHA checked: 31cbde82 (manifest commit b9a3f34a). Base cff3ffe6 = `git merge-base HEAD int/1017` (verified).
Policy-Version: proportional-verification/2026-10-18.15

VERDICT: PASS
SCOREBOARD: 1/1 criteria met (MP33), 3/3 invariants hold (MPI1, MPI2, MPI3)
TIER: M (new schema model + new stage module, no existing module edited; no L trigger in the changed non-test files)
FAILURES: none
CAPABILITY-COVERAGE: 1/1 rows reproduced
LIVE-BROWSER: not-applicable (src/autotester/schema/state_probe.py, src/autotester/stages/oracle_state_after.py, tests only; no route, template or asset)
ISSUES-WRITTEN: none (PROPOSED-ISSUE P1 below; no ledger row written because the worktree ledger tops at AT-1024 while int/1017 already holds AT-1212, so a new id here would collide at merge; the maker mints it)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Check plan
Single type (python oracle, injected port, no UI): no sub-checkers. Steps: contract read, diff-scope read in full, re-run the verify commands, one falsification per criterion in a copy outside D:/autoTesting, MPI3 diff check.

## Evidence (all run by this checker)
- Contract MP33 text in qa/contracts/multi-role-platform.md:88 is quoted verbatim in the manifest.
- `git diff --name-only cff3ffe6..31cbde82` -> exactly 5 files (schema/state_probe.py, stages/oracle_state_after.py, tests/state_after_fakes.py, tests/test_oracle_state_after.py, tests/test_state_probe_schema.py); numstat 0 deletions; `schema/multi_role_enums.py` absent -> MPI3 holds.
- `uv run --directory <worktree> pytest tests/test_state_probe_schema.py tests/test_oracle_state_after.py tests/test_oracle_registry.py` -> 44 passed (matches manifest). `ruff check src tests scripts` -> All checks passed.
- `autotester doctor` -> 2 violations, both stale-generated (docs/MAP.md, docs/SNAPSHOT.md). Same 2 on a `git archive cff3ffe6` base copy, so pre-existing and not caused by this unit; the other advisory lines are D-087 non-blocking.
- Diff-scope read (step 4c) of both src files in full: oracle drives reads only through `RoleSessionPort.observe/perform`; readings are integers or declared tokens (`_reduce`, `_show`), page text never copied (MPI1); oracle error carries type only via the registry; no credential, no network, no write path beyond the injected port. No removed code (0 deletions). Fixture is a synthetic two-role counter app (MPI2).
- Logic read: `_fault` reports unreadable first, then actor wrong/missing after, then reload mismatch (not_persisted when after was right, otherwise missing/wrong_size); a non-actor stale-until-reload page that is right on reload is clean; consistent with MP33 and manifest judgement calls 3, 4, 7.

## Falsification (floor: 1 per changed criterion; copy at scratchpad/cp1, git archive of 31cbde82, PYTHONPATH to the copy, confirmed `autotester.__file__` in the copy)
| Criterion | Edit | Green before | Red after (named assertion) | Restored |
|---|---|---|---|---|
| MP33 | reload-persistence branch `if not _changed(probe, b, r)` -> `if False` | 13 passed | 5 failed incl. test_each_fault_is_reported_and_the_correct_counter_is_not (reverted fault no longer reported), test_a_status_that_reverts_on_reload_is_not_persisted_and_cites_labels | 13 passed |
| MP33 | reader roles limited to the actor (`roles` filtered in `_probe_findings`) | 13 passed | 5 failed incl. test_each_fault_is_reported_and_the_correct_counter_is_not (actor-only fault lost) | 13 passed |
Both edits failed on assertions, not on import errors.

## Non-blocking observations
PROPOSED-ISSUE P1 (low): oracle_state_after.py:152 `port.perform(probe.action)` propagates, so one failing action loses every other probe's findings for the run (manifest judgement call 4, disclosed; registry reports `errored` with the exception type, covered by test_a_failing_action_propagates_and_the_registry_reports_the_type_only). Consider catching per probe and reporting an unreadable/errored finding so remaining probes still run. Also: T-210's real session must put the count/status in `Observation.detail` (judgement call 2); that is a T-210 port criterion, not this unit.

EXPLANATION: The oracle reads each reader role before, after and after a reload, and the synthetic fixture shows not-incremented, actor-only and reverted-on-reload each reported with all three readings while the correct counter stays clean; two independent mutants in a copy turn the named assertions red. The diff is five new files, touches no T-207 enums file, copies no page text, and passes ruff and the affected tests; the two doctor violations are pre-existing on the base.
Metrics: start=2026-10-18T20:12:00Z end=2026-10-18T20:26:00Z wall_min=14 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=840 mutants=0 defects_unit=0 defects_6c=0 slow=falsification-and-env-setup 7
