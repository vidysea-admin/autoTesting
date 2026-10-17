# Verdict (coordinator B) - at929-proposal-scrub
Cycle checked: 1
Verdict: PASS
Checker: B (blind dual-check coordinator), Mode A repair check, tier L (security, dual-trigger src/autotester/stages/expand.py:181)
Bound root: D:/autoTesting/.worktrees/at929-proposal-scrub | base 69ebfae7 (git merge-base HEAD master) | head 4addd97e (code at 2cb9e414) | repair base 248026de

## Check plan
Failed criterion C1 (AT-929) re-run; repair diff 248026de..HEAD read in full (src: expand.py +9/-2, routes_learn.py +2/-2; tests +28); whole-unit diff scanned for out-of-scope files; every caller of stage_case_proposals grepped; one falsification for the repaired path. Passed cycle-0 inputs (the 4 stage_and_review tests) re-run inside the same file.

## Criterion C1 - AT-929 "every field of case_proposals.jsonl that carries operator or target text passes Redactor.scrub before it is stored" - MET
- Callers of the writer: `grep -rn stage_case_proposals src` -> only project_store.py:131 (def) and expand.py:182 inside `stage_scrubbed_proposals` (expand.py:178-183). Its two callers: `stage_and_review` expand.py:189 (CLI expand --proposals/--approve/--prune and UI routes_proposals.py decision route) and routes_learn.py:233 (POST /projects/{slug}/cases/generate, was the bypass at 248026de). No third writer.
- Only other writer of the file: `review_case_proposal` project_store.py:149-157 (upsert reviewed row with `by`); sole caller expand.py:193, after `stage_scrubbed_proposals(store, spec, by)` has already refused a `by` equal to a stored secret (expand.py:169-170). reviewed_by therefore cannot carry a secret.
- title/rationale are scrubbed with id recomputed (expand.py:173-175); flow_id and `by` cannot be masked, so they are refused (builder refuses rather than masks; judged against the issue's own fix_direction "or reject a --by value that matches a declared secret": met). Refusal text is static ("the reviewer name matches a stored secret...", "a flow id matches a stored secret...") and does not echo the secret; the route renders it through the existing ValueError page (routes_learn.py:236-241), and the new route test asserts SECRET not in response.text.
- Security read of the changed lines: no new write path, no logging of values, no-op only when the project or secrets are absent (nothing to leak).

## Commands I ran (worktree, head 4addd97e)
- `uv run pytest tests/test_expand_redaction.py tests/test_expand.py tests/test_expand_cli.py tests/test_ui_learn.py tests/test_ui_learn_guard.py tests/test_provider_factory.py` -> 99 passed
- `uv run pytest tests/test_proposal_review_ui.py tests/test_ui_learn_vendor_echo.py` -> 9 passed (UI consumers of the changed route/stage)
- `uv run ruff check src tests scripts` -> All checks passed! ; `uv run autotester doctor` -> doctor: clean (expand.py 261, routes_learn.py 295, test file 264 lines; caps respected)

## Falsification (copy OUTSIDE the worktree: scratchpad fals929b, git archive HEAD, PYTHONPATH to the copy, import path verified)
- F1: `stage_scrubbed_proposals` made to stage `propose_cases(spec)` unscrubbed. Green before: 2 passed (`-k generate_route`). Red after: route tests fail on `assert 'Hunter2-Zebra-4411' not in ...case_proposals.jsonl` and 2x `DID NOT RAISE ValueError` (stage_and_review scrub tests).
- F2 (the repair itself): route reverted to `store.stage_case_proposals(propose_cases(spec))` with expand.py intact. Red: `test_the_generate_route_does_not_store_a_flow_name_secret_in_case_proposals_jsonl` and `test_the_generate_route_refuses_a_flow_id_that_is_a_secret_and_stores_nothing` FAILED, 2 failed 27 passed. The worktree was never edited; the copy is throwaway.

## Scope
Whole-unit diff vs base (non-qa): src/autotester/stages/expand.py, src/autotester/ui/routes_learn.py, tests/test_expand_redaction.py - all declared. No out-of-scope files; project_store.py, cli.py untouched.

PROPOSED-ISSUE: {"severity":"low","type":"process","title":"Stale unscrubbed rows already in an existing case_proposals.jsonl are retained: stage_case_proposals skips ids already present, and a scrubbed row has a different id, so older raw rows are not rewritten","evidence":"project_store.py:136,145 (existing ids kept); only affects files written before AT-929 landed; not a defect in the changed code","expected":"One-off migration or a doctor warning for pre-fix rows (candidate only)"}

Metrics: start=2026-10-17T16:40:00Z end=2026-10-17T16:56:00Z wall_min=16 agent_min=16 blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=960 mutants=0 defects_unit=0 defects_6c=0
