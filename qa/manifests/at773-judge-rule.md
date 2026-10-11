# Manifest — at773-judge-rule (a failed deterministic assertion can never be graded PASS)

**Contract:** qa/contracts/grade.md G6 (added D-074 rule A); qa/contracts/execute.md E1 (amended D-074 rule A)
**Decision:** D-074(b) (Umesh, chat 2026-10-07; amends D-032 partially). D-032 point 4's "judge may weigh and overrule a recorded failed assertion" is the removed part.
**Issue:** AT-773 (high, correctness)
**Fix cycle:** 0 of max 2
**Dual check:** no (no security/auth/tenancy/prod-write trigger: the diff is `stages/grade.py` verdict logic plus tests only; it handles no credentials, adds no auth or tenant boundary, and writes nothing to production; the guard only ever downgrades a PASS, never upgrades)
**Persona walk:** skip (no UI route or screen)
**Executor:** claude-sonnet-subagent
**Branch:** wave/at773-judge-rule

## Acceptance criteria (verbatim, Umesh's decision recorded as D-074(b))
"a deterministic assertion that failed can NEVER become PASS. For such a run the judge may only return FAIL or INCONCLUSIVE."
Contract G6: "A judge `Judgment` of PASS for such a run is rejected and downgraded to `Result.INCONCLUSIVE` with a `note` naming the failed assertion ... A run with no failed assertion is unaffected."
Tests asked for: (a) ASSERTION_FAILED + judge PASS gives a final verdict that is not PASS; (b) judge PASS on a completed run still PASS; (c) judge FAIL on ASSERTION_FAILED gives FAIL.

## The rule implemented (one place: `stages/grade.py::_assertion_guard`, called from `grade()`)
If the judge's answer is PASS and the run's outcome is `ASSERTION_FAILED` OR the run carries any `assert <field>: unmet` evidence item, the final verdict is **INCONCLUSIVE** (not FAIL: the judge contradicted a recorded fact, so either the product or the expectation is wrong, and a human must say which). The note names the unmet assertion(s), D-074(b), G6 and the judge's scoreboard. A judge FAIL (with its failures) and a judge INCONCLUSIVE pass through unchanged. The guard never upgrades a result. A run with no failed assertion is untouched. Every caller (`run_and_grade_case`, `_resilient`, `grade_errored_result`, UI routes) goes through `grade()`, so there is no second place.

## What changed
- `src/autotester/stages/grade.py` — `_assertion_guard`, `_unmet_assertions`, `ASSERTION_RULE_NOTE`; the final `_verdict(...)` call in `grade()` uses the guarded result and note; `_outcome_verdict` and `grade` docstrings updated (they said the judge may overrule).
- `tests/test_grade_assertion_rule.py` (new, 6 tests): (a) PASS on ASSERTION_FAILED -> INCONCLUSIVE with note naming the unmet assertion; PASS on a COMPLETED run carrying `assert network: unmet` evidence -> INCONCLUSIVE; (b) PASS on COMPLETED -> PASS; met assertion + PASS -> PASS; (c) FAIL on ASSERTION_FAILED -> FAIL with its failures; INCONCLUSIVE stays INCONCLUSIVE. Each docstring names the real scenario (the T-122 Pathlynks login run).
- `tests/test_grade.py::test_assertion_failed_run_still_reaches_the_judge_but_can_never_pass` — the AT-549 test used to pin `PASS` for ASSERTION_FAILED + judge PASS; it now pins INCONCLUSIVE (the judge is still called, grader id still `mock`). **This changes an existing assertion as D-074/G6 require; the checker should read it as an authorized protected-test change.**
- Not changed: `skills/grade/SKILL.md` (prompt). `tests/test_prompt_skills.py::test_sk3` pins the grade prompt byte-for-byte against `tests/fixtures/golden_prompts/grade.md`, so a prompt line would need a golden-fixture edit; the contract asks only for the code guard, so the prompt hint is left as an optional follow-up. `docs/ARCHITECTURE.md` line 90 ("the grader alone still owns every verdict") is untouched: it needs a DECISIONS entry naming that section in Changes-authorized, and D-074 does not name it.
- Removed/renamed names: none (`git grep` not needed).

## Verification scope
Policy-Version: proportional-verification/2026-10-06.6
Tier: L — protected test change (`tests/test_grade.py::test_assertion_failed_run_still_reaches_the_judge_but_can_never_pass` pin changed as D-074/G6 require; ruled L by the cycle-0 checker) on a shared module (`stages/grade.py`); no security/auth/tenancy, no production write.
Owner approval: docs/DECISIONS.md D-084 item 1 (2026-10-11)
Base: master merged into the branch twice on 2026-10-11 (merge 0e9fa191, then 3322a04f; the only add/add conflicts were the checker's `qa/verdicts/at773-judge-rule.md` and `qa/checkpoints/at773-judge-rule.md`, resolved by taking master's newer files; the cycle-0 verdict is archived on master as `qa/verdicts/at773-judge-rule.r0-1.md`; no src/ or tests/ conflict). D-074 is on master at docs/DECISIONS.md:2218 as the contract's authority. Code (src/ + tests/) is unchanged by the merges: the branch's own diff against master is `stages/grade.py`, `tests/test_grade.py`, `tests/test_grade_assertion_rule.py`.

Pre-check: 3322a04f0d6fae7dc8af3c27453b465cefe34ff2 uv --directory D:/autoTesting/.worktrees/at773-judge-rule run pytest tests/test_grade_assertion_rule.py tests/test_grade.py tests/test_grade_evidence.py -p no:xdist -o addopts= -> 54 passed (criterion G6) t=20 blobs=src/autotester/stages/grade.py:3adecbc,tests/test_grade_assertion_rule.py:0810af0,tests/test_grade.py:7bc75db,tests/test_grade_evidence.py:2af58c0
Pre-check: 3322a04f0d6fae7dc8af3c27453b465cefe34ff2 uv --directory D:/autoTesting/.worktrees/at773-judge-rule run pytest tests/test_execute_assertions.py -p no:xdist -o addopts= -> 14 passed (criterion E1; and `git diff master...HEAD --stat -- src/autotester/stages/execute.py` is empty: execute.py untouched by this unit) t=31 blobs=src/autotester/stages/execute.py:482f72f,tests/test_execute_assertions.py:51fd826

## Evidence (run in the worktree, uv run; no full suite)
- `uv run pytest tests/test_grade_assertion_rule.py tests/test_grade.py tests/test_grade_evidence.py tests/test_run_case_pipeline.py tests/test_run_case_pipeline_resilient.py tests/test_execute_assertions.py tests/test_prompt_skills.py tests/test_report_export.py tests/test_regression_proof.py tests/test_network_assertions.py tests/test_ui_runs_serial_resilience.py tests/test_ui_runs_parallel_crash_recovery.py` -> `108 passed, 1 warning in 10.35s`
- Also green: `tests/test_script_replay.py` `15 passed in 204.56s` (slow file, ran on the first version of the guard; the later edit only widened the trigger to unmet-evidence), `test_ensemble_honesty` 8, `test_run_trace` 10, `test_migrate_stamp_legacy_rubrics` 11, `test_video_evidence` 2, `test_video_duration_cap` 3.
- `uv run ruff check src tests scripts` -> `All checks passed!`
- `uv run autotester doctor` -> `doctor: clean`

## Falsifications (copy of src+tests in the scratchpad; green before, red after, restored; restored copy `diff`-identical to the worktree file)
Base in the copy: `19 passed` (grade_assertion_rule + test_grade).
- F1 remove the guard (`if False:`): 3 FAILED — `test_judge_pass_on_an_unmet_login_assertion_is_never_pass`, `..._completed_run_carrying_unmet_assert_evidence_is_never_pass`, `test_grade.py::test_assertion_failed_run_still_reaches_the_judge_but_can_never_pass`.
- F2 guard ignores the outcome (downgrades every PASS): 4 FAILED — `test_met_assertions_do_not_trigger_the_guard`, `test_judge_pass_on_a_completed_run_still_passes`, `test_completed_run_judged_pass`, `test_verdict_round_trips_...`.
- F3 guard downgrades FAIL too: 1 FAILED — `test_judge_fail_on_an_assertion_failed_run_stays_fail_with_its_failures`.
- F4 guard drops the unmet-evidence trigger (outcome only): 1 FAILED — `..._completed_run_carrying_unmet_assert_evidence_is_never_pass`.
- F5 guard emits FAIL instead of INCONCLUSIVE: 3 FAILED (same set as F1).

Metrics: start=2026-10-07T00:00:00Z end=2026-10-07T00:00:00Z wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=5 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6

**Status:** ready-for-check
