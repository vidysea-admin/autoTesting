# Verdict - t167-release-regression - repair coordinator B (fix cycle 1)
Cycle checked: 1 · Resume: 0 of 2 · Retry: 0 · Policy-Version: proportional-verification/2026-10-10.9
Bound to D:/autoTesting · sha checked 102a4b91 (repair range 667a0c64..102a4b91, ancestor verified with git) · date 2026-10-10 (clock UTC)

## Plan (step 0)
Tier L (security gate: dual-trigger src/autotester/core/consent.py:182, dispatched floor kept). Single instrument: pytest in a
throwaway `git archive 102a4b91` copy with its own `uv sync`. Checks: (1) RR2 re-run with my own reproduction of the cycle-0
failure; (2) attack matrix on the repaired gate (A1-A9 below); (3) affected tests for the repair diff; (4) step 4c repair diff read in
full + whole-unit stat; (5) one falsification of my own, plus the builder's row re-run. No UI (CLI-only), no browser, no model call, no
full suite (the other coordinator owns it). RR3/RR4/RR5 input files are untouched by the repair, so they keep their recorded results.

## Verdict
VERDICT: PASS
SCOREBOARD: 6/6 criteria met (RR2 re-tested end to end; RR1/RR6 via their affected tests; RR3/RR4/RR5 input files untouched), invariants: none enumerated for this contract
TIER: L (approval gate; the repair edits stages/orchestrate_gate.py:25-50 and stages/release.py)
FAILURES: none
CAPABILITY-COVERAGE: 2/2 repaired-criterion rows reproduced (builder RR2 cycle-1 row: `actions = scope.max_actions` -> `DID NOT RAISE ApprovalRequired`, green before in the copy; my own wall-clock row below)
LIVE-BROWSER: not-applicable (CLI-only; no UI path in the repair diff)
ISSUES-WRITTEN: none (dual coordinator: PROPOSED-ISSUE lines only)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## RR2 reproduction (my own, throwaway project dir, not the builder's test)
3 flows x 1 real 5-step case = true cost 15 actions; signed live_case approval of 5 actions; hand-written scope.json with the real
plans but max_actions=1, wall_clock_s=8. Pause call, then `decision=YES`: both calls raise ApprovalRequired ("narrower than this run -
actions 15 > approved 5"); zero cases executed. Declared 5 actions / 40 s (equal to the approval, below true cost): refused too.
This is the cycle-0 failure shape, now closed.

## Attack matrix (can a case run that the signed approval does not cover? NO in every row)
- A1 fewer plans declared and the bound lowered consistently (f3 moved to unplanned): runs only when the approval covers the 2 declared
  plans (>= 10); approval 9 and 5 refused. Executed actions never exceeded the approval. (The dropped flow is reported "not run";
  that is the manifest's own PROPOSED-ISSUE, not an approval breach.)
- A2 plans naming ghost case ids: cost 1 each, no real case in the store runs; plans swapped to an expensive real case with bound 1: refused.
- A3 duplicate flow plans: scope fails to load (ValueError), nothing runs. Same case in every plan: counted once and executed once
  (scope.case_ids dedups the same way), executed 5 <= approval 5.
- A4 honest freeze, then a case hand-grown in cases.jsonl (same id, +40 steps) before the answered resume: refused, nothing ran.
- A5 scope.json bounds: bool true, 1.0, "1", 10**30, Infinity, 1e-9 -> refused (recomputed cost wins); 0, -5, 1.5, wall -1, wall 0, NaN
  -> scope rejected at load. Nothing ever executed beyond the approval.
- A6 approval wall clock 10 s vs a 120 s release (declared bound honest, or wall forged to 1 s): refused. Probes: the gate passes
  probes=0, as the existing `_require` path does; case runs spend actions only (tests/run_approval_fixture.py docstring), so no gap now.
- A7 approval for another target, another kind (crawl), another project, expired, unsigned, payload edited after signing (with and
  without the id field), nonexistent id: all refused, nothing ran.
- A8 scope edited between pause and answered resume: bound lowered only -> "release scope changed or is missing" (fingerprint);
  plans grown plus bound edited -> ApprovalRequired; nothing ran.
- A9 other entry points: `autotester release` CLI with a forged scope (exit 2, no checkpoint.json written), `run_or_resume` called
  directly with a forged ReleaseScope object (refused, run dir empty), `run_or_resume` with release_scope=None on a release run
  (refused by check_lineage before `graph.invoke`), approval_id swapped to a small approval after the pause (refused).
  All go through `release_preflight`.
Residual, not a finding: preflight and graph.invoke are not atomic; a store write in that window could change a case. The next resume re-costs.

## Step 4c (repair diff read in full; range 667a0c64..102a4b91)
orchestrate_gate.py +21/-6 (plans_cost moved from release.py; actions = max(declared, recomputed); wall = max(declared, actions*8)),
release.py +/-13 (imports plans_cost, drops _plan_cost), tests/test_release_gate.py +83 (new), manifest. Nothing removed that a criterion
needs (`_plan_cost` and the `FlowPlan` import moved, not dropped). Whole-unit stat shows no file outside the manifest's What-changed
beyond its declared new files. Affected tests: 102 passed (test_release_gate, test_regression_trigger, test_cli_release,
test_orchestrate, test_orchestrate_runners, test_cli_orchestrate, test_cli_orchestrate_resume, test_consent, test_parallel_run_approval);
`ruff check src` clean.

## Falsification (mine, red by assertion)
Copy mut2 (own rootdir/pyproject; first proved by a test that the copy imports its own src, after a first attempt silently used the
other tree's src through pyproject `pythonpath`): orchestrate_gate.py line 50 `wall_clock_s=max(scope.wall_clock_s,
actions * WALL_CLOCK_PER_ACTION_S)` -> `scope.wall_clock_s`. Named node (attack A6, wall forged to 1 s): green before in the copy,
red after on `assert out.startswith("refused")`, restored. The builder's own RR2 row (actions re-cost removed) also reproduced red.

## PROPOSED-ISSUE
PROPOSED-ISSUE: {"severity":"low","feature":"release-regression","title":"wall-clock re-cost in release_preflight (orchestrate_gate.py:50) is unpinned: removing it leaves tests/test_release_gate.py and test_regression_trigger -k rr2 green","evidence":"mutant in a throwaway copy: 8 passed; the coordinator B attack test goes red","type":"test-gap"}
PROPOSED-ISSUE: {"severity":"low","feature":"release-regression","title":"release gate passes probes=0 so an approval's max_probes is never compared; harmless while case runs spend actions only, revisit when T-174/T-203 wire a live executor","evidence":"orchestrate_gate.py:46-50","type":"observation"}

EXPLANATION: The repaired gate takes the larger of the scope's declared bound and a cost recomputed from the plans in the store on every call, so a hand-edited bound cannot lower the check, and edits to the plans change the fingerprint (and the cost) as well; I found no path by which a case runs that the signed approval does not cover. The human "yes" itself is not signed; that was outside this criterion.
Metrics: start=unavailable end=2026-10-10T20:50:00Z wall_min=30 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=1800 mutants=1 defects_unit=0 defects_6c=0
slow: attack harness build and the copy-import proof, about 15 min
