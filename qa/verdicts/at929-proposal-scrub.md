# Verdict A - at929-proposal-scrub (repair check)
Cycle checked: 1
Date: 2026-10-17 (checker A, blind coordinator; bound to D:/autoTesting/.worktrees/at929-proposal-scrub)
Base 69ebfae7 (= git merge-base HEAD master); Repair base 248026de (ancestor of HEAD 4addd97e, verified); product head 2cb9e414.

## Check plan
Repair checker. Failed criterion C1 (AT-929: every proposal field scrubbed before store; the generate route bypassed it).
Plan: (1) read repair diff 248026de..HEAD in full + whole-unit diff scope; (2) grep every writer of case_proposals.jsonl in src/;
(3) re-run affected tests + ruff + doctor; (4) 1 falsification of the repaired path in copies outside the worktree;
(5) security read of the changed lines. No UI-visible change (stage-layer + route redirect/refusal page only): no Mode D. Policy proportional-verification/2026-10-15.12.

## Evidence
- Callers: `grep stage_case_proposals src` -> only expand.py:182 (inside stage_scrubbed_proposals) and its def project_store.py:131.
  stage_scrubbed_proposals callers: expand.py:189 (stage_and_review -> cli.py:223, routes_proposals.py:108,143) and routes_learn.py:233 (the generate route).
  Other writer of the file, review_case_proposal (project_store.py:149), is reached only via stage_and_review (expand.py:193), so `reviewed_by` is covered by the `--by` refusal; routes_proposals.py:76-80 also pre-refuses.
  No path stages a proposal unscrubbed.
- Tests (run by me in the worktree): `uv run pytest tests/test_expand_redaction.py tests/test_expand.py tests/test_expand_cli.py tests/test_ui_learn.py tests/test_ui_learn_guard.py` -> 68 passed (28 s).
  `uv run ruff check src tests scripts` -> All checks passed!; `uv run autotester doctor` -> doctor: clean.
- Diff scope (4c): repair diff touches only expand.py (new stage_scrubbed_proposals; stage_and_review reuses it), routes_learn.py (import + one call), tests. Whole-unit src/tests diff = those 3 files, all in the manifest's What changed; qa/ files are bookkeeping.
  Removed lines in whole unit: only the 2 raw `stage_case_proposals(propose_cases(spec))` call forms and the `propose_cases` import they replaced. No function, test, route or key deleted.
- Security read: error text in `_scrub_proposals` (expand.py:172,174) is static and never echoes the value; the route refusal page prints str(exc) (routes_learn.py:238) = that static text. The route test asserts SECRET not in response.text.
  Refusing (not masking) a --by or flow id equal to a stored secret leaves nothing unscrubbed in the store, which satisfies AT-929 expected text and its fix_direction ("or reject a --by value that matches a declared secret").
  Flow id cannot be masked: it is the FlowSpec link (proposal.require_current).

## Falsification (C1, repaired path), copies of `git archive HEAD` in scratchpad, worktree untouched
Both route tests named `test_the_generate_route_does_not_store_a_flow_name_secret_in_case_proposals_jsonl` and `..._refuses_a_flow_id_that_is_a_secret_and_stores_nothing`.
- Floor (revert the repaired hunk): routes_learn.py:233 back to `store.stage_case_proposals(propose_cases(spec))`. Green in copy first (2 passed), then RED on the named assertions ("'Hunter2-Zebra-4411' is contained here" in case_proposals.jsonl; and the flow-id test stores a file with the secret). Not an import error.
- Mutant (1): stage_scrubbed_proposals stages `propose_cases(spec)` unscrubbed. Green first, then 5 failed in tests/test_expand_redaction.py (both route tests + the 3 stage_and_review scrub tests), all on secret-in-file / DID NOT RAISE assertions.
Evidence of runs: scratchpad f1/f2 (session-local); commands reproducible as above.

## Result
SCOREBOARD C1 met. Invariants touched: core-invariants secret-redaction (stored artifact) holds on every writer.
PROPOSED-ISSUE: {"severity":"low","type":"wording","title":"routes_learn.py:236-241 refusal page for a staging ValueError always says 'Case proposals need human review' and points at `autotester expand --proposals`, which is misleading when the cause is a flow id/secret refusal; cosmetic","expected":"refusal body names the actual cause or the rename action"}

VERDICT: PASS
SCOREBOARD: 1/1 criteria met, core-invariants holds
TIER: L (security: secret redaction of staged proposals; dual-trigger src/autotester/stages/expand.py:181)
FAILURES: none
CAPABILITY-COVERAGE: 1/1 rows reproduced (repaired route path + stage_scrubbed_proposals mutant)
LIVE-BROWSER: not-applicable (changed paths: src/autotester/stages/expand.py, src/autotester/ui/routes_learn.py, tests/test_expand_redaction.py; no rendered output changed)
ISSUES-WRITTEN: none (dual coordinator; PROPOSED-ISSUE above)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The cycle-0 bypass (POST /cases/generate staging raw titles) is closed: the route now calls stage_scrubbed_proposals, the single path from propose_cases to case_proposals.jsonl, and every other writer reaches the store through it. Reverting the route hunk or the scrub makes the named route tests go red on the secret-in-file assertion.
Metrics: start=2026-10-17T16:46:00Z end=2026-10-17T16:55:00Z wall_min=9 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=540 mutants=1 defects_unit=0 defects_6c=0
