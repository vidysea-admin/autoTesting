# Verdict - t178-failure-bundle-fb4-fb5 - fix cycle 1 - seat B (blind dual check)

Cycle checked: 1
Sha checked: 297207ff (manifest commit; product c142f8f1; master 8791b76b merged at 2587a7b1). Head verified with `git rev-parse`.
Repair base: a7d3fa6c (ancestor of HEAD, verified). Policy-Version: proportional-verification/2026-10-10.9
Bound to: D:/autoTesting. Evidence: qa/evidence/t178-failure-bundle-fb4-fb5-r1-B/. Checkpoint: qa/checkpoints/t178-failure-bundle-fb4-fb5.r1.b.md

## Plan
Tier L (dual-trigger security src/autotester/stages/failure_bundle.py:211-212). Repair-scoped: failed list = {advice-site guard, tests/test_cli_advice_resolves.py::test_no_advice_site_can_vanish_unnoticed}. Repair = merge 2587a7b1 (master + the review block moved cli.py -> stages/expand.py::stage_and_review) + c142f8f1 (tests only). Steps: separate merge vs fix diff, differential base-vs-head on the moved human-approval path (CLI + in-process), FB4/FB5/CONTAIN/ADVICE verify re-run, falsification for the touched inputs (FB5, ADVICE), containment hunk diff.

VERDICT: PASS
SCOREBOARD: 5/5 criteria met (FB4, FB5, CONTAIN, ADVICE guard, C2/C5 unchanged), invariants touched: none broken
TIER: L (security dual trigger failure_bundle.py:211-212; unchanged by the repair)
FAILURES: none

## Repair diff (step 4c)
- c142f8f1 changes only tests/test_cli_advice_resolves.py (+3/-1): two EXPECTED_SITES entries `("cli.py","expand")`, `("ui/routes_learn.py","expand")`, count 21 -> 23. Nothing removed.
- Merge 2587a7b1 vs a7d3fa6c: master's content (cli_release, flow_plans etc. in paths.py, docstring wording) plus the move. Product move: cli.py:220 now calls `expand_stage.stage_and_review(store_, spec, approve, prune, by)`; expand.py:127-137 holds the identical stage / disjoint-guard / review / return-rows body. Only behavioural nuance: `list_case_proposals()` is now read on the plain-generate path too (old code read it only on the --proposals/--approve/--prune path); `stage_case_proposals` already reads the same file first, so no new failure mode (malformed-file scenario identical).
- Whole-unit file list (`git diff 8791b76b 297207ff --name-only`, 24 files) is all inside the manifest "What changed" list; none outside scope.
- Path containment: `git diff a7d3fa6c c142f8f1 -- stages/failure_bundle.py schema/failure_bundle.py tests/test_failure_bundle.py` is empty; lines 211-212 (`target = (root / f.name).resolve()` / `if not target.is_relative_to(root)`) untouched.
- Reachability: `grep` of src at 297207ff: `stage_and_review` has one caller (cli.py:220). It takes no provider and makes no model call, so it cannot skip the gate. The gate stays in `expand`/`expand_flow` -> `_reviewed_batch` -> `preflight_case_proposals` (expand.py:140-148); `expand(...)` without a store raises before any call (in-process: expand_nostore and store-without-approval both ValueError, 0 calls).

## Differential base a7d3fa6c vs head c142f8f1 (22 scenarios, mock provider counting calls, scratch project)
CLI `autotester expand` and in-process; harness `evidence/.../diff_harness.py`, result `base-vs-head-compare.txt`. Compared exit code, message text, call count, files written (rows, status counts, reviewers), with ids/timestamps/paths normalised.
Scenarios: no staging; --proposals twice; approve-all (24 calls); partial approve + prune (2 calls); partial approve no prune (2 calls per generate); prune-all-non-happy (0); happy pruned only (0, refused); approve-then-prune-one (23); prune after approve (0, refused); empty and whitespace `--by`; approve+prune same id; unknown id; stale spec (flow added after approval); malformed jsonl line; hand-forged `approved` row with no reviewer; other project's approvals copied in; unreviewed FlowSpec; no flowspec; provider unavailable.
Result: 21 of 21 comparable scenarios identical (exit, text, calls, files). The 22nd (`inproc`) differs only because base has no `stage_and_review`. No approval-less generation in any scenario (calls 0 whenever refused). Teeth check: the same harness reports 7 and 2 differing scenarios against mutants M1 and M2 below, so it can see the move go wrong.

## Verify commands re-run (one pytest process each, `-p no:xdist -p no:cacheprovider`)
- FB4: test_schema+test_store+test_pinned_regression+test_ui_runs -> 60 passed. Inputs untouched by the repair, recorded falsification kept (not repeated).
- FB5: test_expand+test_expand_cli+test_ui_learn+test_eval_compiler -> 61 passed.
- CONTAIN/C5: test_failure_bundle -> 23 passed. ADVICE: test_cli_advice_resolves -> 32 passed.
- Merge-affected: test_cli_surface 46, test_cli_harness_safety 4, test_ui_origin_guard 87, test_cli_release 4, test_pinned_regression 9, all passed. Pre-check lines reproduce (counts match the manifest).

## Falsification (each in its own copy of `git archive c142f8f1`, green before in the copy)
- FB5: `approved_batch` returns `status != "x"` (schema/case.py:173) -> test_five_nonhappy_proposals_prune_before_spend red `assert 5 == 2` and `assert 5 == 0` (expand.py test line 194). Before: 25 passed.
- ADVICE: delete `("cli.py","expand")` from EXPECTED_SITES -> test_no_advice_site_can_vanish_unnoticed red `new: [('cli.py','expand')]`. Before: 32 passed.
- Moved-path guidance mutants (above the floor): M1 `approved=True` in stage_and_review (prune becomes approve) and M2 remove the approve-and-prune guard both SURVIVE (25 passed): no test calls `--prune` or `stage_and_review` (`grep tests`: only test_expand_cli.py:144,146 use `--approve`). The test files are identical at a7d3fa6c, so this gap predates the repair; behaviour is correct (differential above). Not a FAIL under reviewer scope; PROPOSED-ISSUE P1.

CAPABILITY-COVERAGE: 2/2 repaired rows reproduced (FB5, ADVICE); FB4 and CONTAIN keep recorded rows (inputs untouched)
LIVE-BROWSER: not-applicable (repair changed no UI path; routes_learn.py/routes_runs.py unchanged since a7d3fa6c; persona walk is seat A's / not part of this repair-scoped check)
ISSUES-WRITTEN: none (dual coordinator)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The cycle-0 failure (unregistered `autotester expand --proposals` advice sites) is repaired: both sites are registered, the guard is green and goes red when a site is removed. The code move into stages/expand.py is behaviour-identical on 21 differential scenarios, makes no provider call, has one caller, and the approval gate is still in `expand` via `preflight_case_proposals`. I did not run the full suite (seat A owns it).
full-suite trigger: security class unit (seat A runs its own).

PROPOSED-ISSUE: {"severity":"low","feature":"failure-bundle","title":"No test pins the CLI review door: `autotester expand --prune` and the approve/prune disjointness guard in stages/expand.py::stage_and_review are untested; mutants `approved=True` and guard-removed survive test_expand_cli.py+test_expand.py","evidence":"tests grep: only --approve at tests/test_expand_cli.py:144,146; mutants in qa/evidence/t178-failure-bundle-fb4-fb5-r1-B/fals-m1-red.txt, fals-m2-red.txt","status":"open","found_by":"checker-unit","regression_check":null}

Metrics: start=2026-10-11T01:07:16Z end=2026-10-11T01:22:00Z wall_min=15 agent_min=15 blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-10.9 lane=normal check_s=884 mutants=2 defects_unit=0 defects_6c=0
