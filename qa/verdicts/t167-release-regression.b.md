# Verdict B - t167-release-regression (T-167) - coordinator B of a dual check
Checked sha: 667a0c64 (code 00fae668), git archive copy, own `uv sync`. Policy-Version: proportional-verification/2026-10-10.9. Cycle checked: 0. Resume: 0 of 2. Retry: 0.
Blind to coordinator A (its verdict, checkpoint and evidence not read). No side effects: no ledger rows, no goal close, no merge, no push.

## Plan
Tier L (dependency bump, resume/concurrency, approval gate; dual-trigger consent.py:182 present in the manifest). Checks: RR1..RR6 verify commands once; full diff master...wave/t167 read; security attacks on the approval, scope, checkpoint and baseline paths (evidence/t167-release-regression-b/attacks.py); one falsification per criterion in copies; ordering mutants for the builder's preflight question. No full suite (A owns it). No browser (CLI only). No model call.

VERDICT: FAIL
SCOREBOARD: 5/6 criteria clean; RR2 meets its stated Verify but the gate it adds is bypassable (F1)
TIER: L (dependency bump `langgraph==1.2.14`; checkpoint/resume; approval gate at consent.py:182)

FAILURES:
- [RR2/security] sev: medium - a pre-seeded `runs/<id>/scope.json` skips the "approval narrower than the release" refusal. `release.py::_frozen_or_new` returns any scope found on disk without re-costing it (`frozen = store.load_release_scope(run_id); if frozen is not None: return frozen`), and `orchestrate_gate.py::release_preflight` calls `require_approval(actions=scope.max_actions, wall_clock_s=scope.wall_clock_s)` with the numbers the file itself declares. Reproduced (attacks-output.txt A1a/A1b): with a signed approval of 1 action, an honest first call for a 3-case release is refused ("narrower"), but a hand-written scope.json declaring max_actions=1 for the same 3 plans reaches the pause and, after the human answer, runs all three cases. `test_rr2_an_approval_narrower_than_the_release_is_refused` pins only the honest path and `test_rr2_a_forged_scope...` only a bogus approval_id. Edits to scope.json AFTER the pause are caught (A6, fingerprint). Needs write access to the project data dir, the actor class the HMAC on approval rows (AT-110) defends against. Fix direction: in `release_preflight` recompute the cost of `scope.plans` from the store (the `_plan_cost` rule) and require the approval to cover max(declared, recomputed); add a test that pre-seeds an under-declared scope. issue: P1

CAPABILITY-COVERAGE: 6/6 rows reproduced in own copies (edits differ from the builder's; green-before in a pristine copy; red on the named assertion)
LIVE-BROWSER: not-applicable (CLI only; no UI path touched)
ISSUES-WRITTEN: none (dual coordinator; PROPOSED-ISSUE lines only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Evidence per criterion (own runs, copy of 667a0c64)
- RR1 met: `pytest tests/test_regression_trigger.py tests/test_cli_release.py tests/test_orchestrate.py` -> 29 passed; OR2/OR4 re-proved on the checkpointer (state.json deleted, only checkpoint.json remembers). Falsify: `reenter()` stops resetting failed stages -> `test_rr1_a_raise_is_failed_and_resume_re_enters_that_stage` red on `assert 1 == 2` (calls).
- RR2 met on its stated Verify (no approval -> refused before graph and run dir; approved -> `awaiting_human`; resume with no answer stays paused; decline runs nothing). Falsify: `_confirm` takes an automatic answer instead of `interrupt()` -> pause test red `assert 'done' == 'awaiting_human'`. Security finding F1 above.
- RR3 met: good/bad/good -> run3 baseline run1; rule named `latest_earlier_finished_unflagged_all_pass_release`. Own probes: latest of two good chosen (A3a), a later-dated run never chosen (A3b), unfinished/flagged/failing/missing-result records untrusted (A3c-e). Falsify: `< boundary` -> `> boundary` -> third-run test red `assert None == 'run1'`.
- RR4 met: both release modules free of `Result.`/`Verdict(`/grader import; record results equal the grader's verdicts. Falsify: `Result.PASS` added to release.py (the trigger module; the builder used release_compare) -> `rr4_release_modules[release]` red, [release_compare] still green.
- RR5 met: `grep -n langgraph pyproject.toml` -> line 17 `"langgraph==1.2.14"`; `autotester doctor` -> "doctor: clean"; ruff clean. Falsify: line replaced by a comment -> `test_rr5` red on the declaring-line assertion.
- RR6 met: one release.json, both failures with flow ids, f3 passed; planless flow `not_run`. Falsify: log loop limited to `expected_flow_ids[:1]` (the contract's "run only the first plan" sabotage) -> red, missing `('f3','c-f3')`.
- Regression set (orchestrate_runners, cli_orchestrate*, schema, store, consent, parallel_run_approval): 105 passed.

## Attacks tried (attacks-output.txt)
Honest narrow approval: refused. Pre-seeded under-declared scope: BREACH (F1). Approvals emptied after the pause: refused on resume. scope.json edited after the pause: refused. Truncated and foreign-thread checkpoint: refused. Decision on a fresh run, and replay after finish: refused. Non-release context on a release run: refused. Baseline picker (flagged, unfinished, later, failing, missing result): never chosen. A case that did not run counting as passed: not reachable (results must equal scope cases and issues be empty).
Builder's open question (preflight moved to just after `_compile`): NOT a real hole today. Copies with the preflight moved right after `_compile` (m7) and right before `save_release_scope` (m8) pass all 14 release and cli tests because nothing touches disk or invokes the graph between the top of `run_or_resume` and `save_release_scope` (FileCheckpointer construction and `get_state` are read-only). Moving it after `save_release_scope` (m9) is caught (run dir exists). Residual: the order is guarded only by outcome tests (low hardening item).

## Proposed issues
PROPOSED-ISSUE: {"severity":"medium","feature":"release-regression","title":"release_preflight trusts the scope file's own max_actions/wall_clock_s; a pre-seeded scope.json skips the narrower-approval refusal","evidence":"qa/evidence/t167-release-regression-b/attacks-output.txt A1b; stages/release.py _frozen_or_new, stages/orchestrate_gate.py release_preflight","type":"security"}
PROPOSED-ISSUE: {"severity":"low","feature":"release-regression","title":"A flow or case dropped from the FlowSpec/plans between releases vanishes from the diff: regressed, fixed, new_cases and issues all stay empty (A4)","evidence":"attacks-output.txt A4; release_compare._diff iterates only the current scope's cases"}
PROPOSED-ISSUE: {"severity":"low","feature":"release-regression","title":"--run-id is not validated: '../escaped' writes scope/checkpoint outside runs/ (needs a covering approval first); a rejected decision on a fresh run leaves scope.json behind","evidence":"attacks-output.txt A9, A7a; cli_release.py release_cmd, orchestrate.py run_or_resume"}
PROPOSED-ISSUE: {"severity":"low","feature":"release-regression","title":"No test pins preflight-before-first-write ordering by spying on disk writes (m7/m8 equivalent today)","evidence":"mutant copies m7/m8/m9"}
PROPOSED-ISSUE: {"severity":"low","feature":"release-regression","title":"After --decline-by the CLI prints 'finished - see release-log' although no release record exists (code read only, not run)","evidence":"cli_release.py _echo_state"}
Observation (not an issue): `start_release` reaches `covering_approval`, which under D-068 may mint a signed row for a credentialed project before the graph exists; `release_preflight` itself never mints. This matches the manifest's gate answer, but "this unit never mints" is true only of the preflight.

EXPLANATION: Every criterion's own verify passes and falsifies on assertion, and the baseline, did-not-run and checkpoint-integrity attacks all held. One reproducible gate bypass remains in the new approval code: the scope file, an unsigned local input, supplies the bounds the approval is checked against, so a pre-seeded scope defeats the narrower-than-release refusal. A small local fix plus a test; the repair check should re-run RR2 and the affected release tests.
Metrics: start=2026-10-10T19:59:21Z end=2026-10-10T20:15:00Z wall_min=16 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=9 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=940 mutants=3 defects_unit=1 defects_6c=0
Lane exit: not applicable (dual check, L).
