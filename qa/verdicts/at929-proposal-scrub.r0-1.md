# Verdict A - at929-proposal-scrub
Date: 2026-10-17 · Cycle checked: 0 · Bound to: D:/autoTesting/.worktrees/at929-proposal-scrub · Base 69ebfae7 (git merge-base HEAD master) · Head b5d83803 (+01797fdb manifest)
Policy-Version: proportional-verification/2026-10-15.12 · Dual check coordinator A (blind)

## Check plan
Logic + security change (secret scrub of stored proposals). Checks: manifest verify commands, step 4c diff read, one falsification for C1 in a copy outside the worktree, writer enumeration for case_proposals.jsonl (criterion says "every field").

VERDICT: FAIL
SCOREBOARD: 0/1 criteria met (AT-929), core-invariants C5 not held for this artifact, 0 other invariants touched
TIER: L (security: secret redaction of stored proposals; dual-trigger src/autotester/stages/expand.py:181)
FAILURES:
- [AT-929] sev: medium · A second writer of case_proposals.jsonl stores the flow name raw, so "every field ... passes Redactor.scrub before it is stored" is not met · fix direction: scrub at the store write (ProjectStore.stage_case_proposals, project_store.py:131, which the issue names: "the store layer never calls Redactor.scrub"), or route src/autotester/ui/routes_learn.py:233 through the same scrub · issue: P1
  Evidence: routes_learn.py:233 (read by me) is `store.stage_case_proposals(propose_cases(spec))` inside POST /projects/{slug}/cases/generate, bypassing `_scrub_proposals`, which the builder wired only into `stage_and_review` (expand.py:181). I ran evidence/at929-proposal-scrub/repro_generate_bypass.py.txt in a git-archive copy of HEAD b5d83803 (copy outside the worktree): project with declared secret ST_PASS, approved FlowSpec whose flow name contains the secret, POST /cases/generate. Result: 1 failed, `'Hunter2-Zebra-4411' is contained here: "title":"Sign in Hunter2-Zebra-4411 - happy"`, and the same in every double_submit/etc. row's title. Route replied HTTP 400 (review gate, later in the route) but the raw rows were already written to case_proposals.jsonl, because staging happens before the gate at routes_learn.py:233-234. The builder's own UI-facing path is therefore still unscrubbed.
CAPABILITY-COVERAGE: 1/1 rows reproduced (the manifest row is real but only isolates the stage_and_review path, not "every field/every writer")
LIVE-BROWSER: not-applicable (changed paths: src/autotester/stages/expand.py, tests/test_expand_redaction.py)
ISSUES-WRITTEN: none (dual coordinator)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The builder's scrub works on the CLI/proposals-UI path stage_and_review: the 4 new tests pass and the falsification is real. But AT-929's expected text covers every stored field of case_proposals.jsonl and names the store layer, and the Generate-cases route writes the same file through the unscrubbed `store.stage_case_proposals`. Refusing a `--by` or flow id equal to a secret, rather than masking it, is acceptable under the issue's own fix direction ("or reject a --by value that matches a declared secret"); error text does not echo the secret (test asserts it; I read it at expand.py:171,174).

## Evidence (all run by me)
- `uv run pytest tests/test_expand_redaction.py` -> 27 passed (one earlier concurrent run had 2 WinError 5 rename failures from a parallel run; 14 re-run alone and the 52-test combined run passed)
- `uv run pytest tests/test_expand_redaction.py tests/test_expand.py tests/test_expand_cli.py` -> 52 passed in 59.6s (27 + 25 as the manifest expects)
- `uv run ruff check src tests scripts` -> All checks passed!; `uv run autotester doctor` -> doctor: clean
- Falsification C1 (copy at scratchpad cpA, outside worktree): the 4 AT-929 nodes green (4 passed) before; after replacing the `if secrets is None:` guard with `if True:` (always return rows) -> red on the named assertions: `assert 'Hunter2-Zebra-4411' not in ...` and `Failed: DID NOT RAISE ValueError` x2; ordinary-reviewer test stays green. Real, assertion-level red.
- Step 4c diff scope: 2 files (expand.py +17/-1, tests +57), both listed in What changed; nothing removed except the one `rows = propose_cases(spec)` line replaced.
- Bypass repro: see FAILURES.

PROPOSED-ISSUE: {"feature":"failure-bundle","severity":"medium","type":"security","title":"AT-929 scrub covers only stage_and_review; ui/routes_learn.py:233 generate_cases stages propose_cases(spec) raw into case_proposals.jsonl (flow name with a declared secret stored verbatim, before the review gate)","expected":"Every writer of case_proposals.jsonl scrubs title/rationale (scrub in ProjectStore.stage_case_proposals, or share _scrub_proposals)","evidence":"qa/evidence/at929-proposal-scrub/repro_generate_bypass.py.txt"}
PROPOSED-ISSUE: {"feature":"failure-bundle","severity":"low","type":"quality","title":"stage_and_review scrub uses scrub(by) != by to detect a secret; the review route's _refuse_unsafe_submission and CLI could share one helper (note only, no defect shown)"}

Metrics: start=2026-10-17T12:55:00Z end=2026-10-17T16:32:00Z wall_min=45 agent_min=unavailable blocked_min=100 suite_runs=0 repeat_runs=0 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=2700 mutants=1 defects_unit=1 defects_6c=0
