# Verdict A — t167-release-regression (T-167)  [dual check, coordinator A]
Date: 2026-10-11 · Cycle checked: 0 · Resume: 0 of 2 · Retry: 0 · Policy-Version: proportional-verification/2026-10-10.9
Checked: branch wave/t167-release-regression HEAD 667a0c64 (code 00fae668, base master 3a16616c). Bound to D:/autoTesting. Contract: qa/contracts/release-regression.md (unchanged on master since the build).

## Check plan
Tier L (dependency bump, concurrency/resume, approval gate; `dual-trigger: security consent.py:182` read: line 182 is `require_approval`). CLI-only, no UI file: no browser. Plan: criteria re-run, one falsification per criterion in throwaway copies, 4c diff read, gate-order probes, old-state resume probes, regression files, release-manager persona walk (sub-checker, CLI only), doctor/ruff/lock. Full suite: see below.

VERDICT: PASS
SCOREBOARD: 6/6 criteria met (RR1-RR6), invariants not enumerated in the contract
TIER: L (new dependency langgraph==1.2.14; checkpoint/resume; signed-approval gate before the graph)
FAILURES: none
CAPABILITY-COVERAGE: 6/6 reproduced (copies green first; evidence qa/evidence/t167-release-regression-a/mutants.log)
LIVE-BROWSER: not-applicable (CLI-only; no UI path changed)
ISSUES-WRITTEN: none (dual coordinator; PROPOSED-ISSUE lines below)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Evidence per criterion (my own runs; copies of `git archive 667a0c64`, PYTHONPATH to the copy)
- RR1: 22 passed in the copy (test_regression_trigger + test_cli_release). Falsify `reenter` also resetting `done` -> test_rr1_a_done_stage_is_not_redone... red on `rec.calls == 1` (2 == 1). Old-format state.json (no new fields, INGEST done, no checkpoint.json) resumes: INGEST not re-run, MODEL run once (probe p3). Corrupt/foreign-thread checkpoint.json raises, restored file resumes with no redo (p4).
- RR2: falsify delete `release_preflight` from `run_or_resume` -> forged-scope test red. Probes: forged scope never invokes the graph, calls no runner, creates no run dir (p1); approval withdrawn after the pause -> the answered resume is refused, no stage runs (p2); a release ledger resumed without its scope is refused (p5).
- RR3: falsify `is_trusted` without `flagged_bad` -> test_rr3_a_human_flagged... red. Good/bad/good test: third run's baseline is run1 (green in copy).
- RR4: add `Result.PASS` to release.py -> AI6-shape regex test red; second edit (issue detail hard-coded) -> test_rr4_every_result... red on `'failed' == '0/1'`.
- RR5: delete the `langgraph==` line -> rr5 test red on `assert lines`; unmodified: `autotester doctor` -> `doctor: clean`; `uv lock --check --offline` -> resolves, no change; ruff clean.
- RR6: iterate only `expected_flow_ids[:1]` -> both rr6 tests red (2 failed).
Regression: orchestrate, orchestrate_runners, cli_orchestrate, cli_orchestrate_resume, schema, store, consent, parallel_run_approval = 112 passed. No existing test file is modified in the diff.

## Rulings on the six points
1. Dependency: authorised by D-041 `Changes-authorized` ("pyproject.toml: langgraph ... added only within T-167") and RR5. uv.lock diff is 109 pure additions in 4 hunks: langgraph 1.2.14, langgraph-checkpoint 4.2.0, langgraph-prebuilt 1.1.0, langgraph-sdk 0.4.6, ormsgpack 1.12.2, plus the root requires-dist lines. Nothing existing changed.
2. New modules: brief section 5 says the new-file set is "unknown until the builder decides; each needs a C3 justification for the cap" and names schema/release.py, orchestrate_checkpoint.py and "a release-trigger module". orchestrate_gate.py (orchestrate.py at 295/300), cli_release.py (cli_orchestrate.py at 258) and release_compare.py (one job: record + baseline) carry module docstrings stating a one-job split; accepted. Low note: the manifest gives no explicit C3 line for release_compare.py.
3. Approval gate: `release_preflight` is the first statement of `run_or_resume`; `start_release` also calls `covering_approval` before any ctx or file exists. Moves to just after `_compile`, and to after `check_lineage` (before `save_release_scope`), survive all tests, and I proved them behaviourally identical (p1 green in both copies: graph.invoke 0 calls, 0 runner calls, no run dir). Compile/get_state/load are reads, so no stage can run. Any move past `save_release_scope` (the builder's "just before invoke") goes red. Deleting it goes red. I found no public path where a run stage executes without a valid, signed, covering approval short of editing files on disk. Residual: see PROPOSED-ISSUE P1.
4. `autotester release` stops at EXECUTE with a message. RR1-RR6 Verify clauses are fixture-based with injected runners and the real `grade()`; none needs a live runner; d081 authorises no live T-167 run. Met without the live path.
5. Existing orchestrate: 112 regression tests green; old state.json resumes; bad checkpoints are refused loudly (see RR1). `_run_stage` (private) changed signature; its only callers are inside orchestrate.py.
6. Persona walk (release manager, CLI, throwaway root, no network): evidence/persona-walk-release-manager.md. Refusal writes nothing and prints a working grant command; minted run id is shown; pause/decline/approve flow runs. Findings are usability, not criterion failures (rated by me, not the sub-checker): see P3-P5.

## Full suite
NOT RUN, by maker instruction (the branch will receive a new commit; the suite is owed on the later sha). I had queued it, waited 13 min on the machine lock, started it at 01:44 (2886 tests collected), and stopped only my own process tree when told; the lock is released. No suite result is claimed. The suite is still owed.

## PROPOSED-ISSUE lines
PROPOSED-ISSUE: {"severity":"medium","feature":"release-regression","title":"release_preflight checks the approval against scope.max_actions only; it never re-derives cost from the scope's plans, so a scope that understates its cases passes the gate (probe p6: 3 cases executed under an approval of 1 action)","evidence":"src/autotester/stages/orchestrate_gate.py:23-33; qa/evidence/t167-release-regression-a/test_probe_t167.py::test_p6","status":"open","found_by":"checker-unit"}
PROPOSED-ISSUE: {"severity":"medium","feature":"release-regression","title":"No product code writes a FlowPlan (only store.save_flow_plan exists), so a real `autotester release` reports every flow `not run`; RR6 'each completed flow leaves a plan' has no producer","evidence":"grep save_flow_plan|FlowPlan( src -> store only","status":"open","found_by":"checker-unit"}
PROPOSED-ISSUE: {"severity":"medium","feature":"release-regression","title":"CLI: the pause prints only stage names (no flows, case/action counts, build, unplanned flows) so --approve-by is blind; approve exits 0 at 'stopped at execute' with no next step; decline says 'finished' and points to a release-log that does not exist; answering an already-answered release prints a raw ValueError traceback","evidence":"persona-walk-release-manager.md steps 2,4,5; src/autotester/cli_release.py:_echo_state","status":"open","found_by":"checker-unit"}
PROPOSED-ISSUE: {"severity":"low","feature":"release-regression","title":"A resume silently uses the frozen scope: a later plan or different --git-sha is ignored with no notice; orphan paused runs when --run-id is omitted; exit codes 1 vs 2 inconsistent","evidence":"persona walk step 7/8","status":"open","found_by":"checker-unit"}
PROPOSED-ISSUE: {"severity":"low","feature":"release-regression","title":"test_rr2_no_approval... monkeypatches `_compile` but is satisfied by start_release's own covering_approval, so it does not test run_or_resume's gate; only the forged-scope test does. Docstring history (AT-228, AT-132/137) was condensed in cli.py and paths.py","evidence":"tests/test_regression_trigger.py:146-157; git diff 3a16616c..00fae668 cli.py core/paths.py","status":"open","found_by":"checker-unit"}

Metrics: start=2026-10-10T19:59:16Z end=2026-10-10T20:18:00Z wall_min=19 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=10 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=1120 mutants=4 defects_unit=0 defects_6c=0
(lock wait of 13 min overlapped other work, so it is not counted as idle blocked time; 10 mutations = 6 floor + 4 beyond: rr2b/rr2c/rr2d probes and rr4b; all in isolated copies.)
