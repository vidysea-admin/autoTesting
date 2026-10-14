# Manifest - approval-prod-gate

**Status:** ready-for-check
**Fix cycle:** 2
**Unit:** T-145 blind-checker defects D1-D3 (approval traceability, production gate, redaction, clean-checkout done_check)
**Branch:** wave/approval-prod-gate
**Contract:** qa/contracts (RunApproval / explore consent); decisions D-018, D-068, D-088

## Changes
- schema/project.py: `Project.production` (machine-readable, default False). projects/pathlynks/project.json sets true; pathlynks-prepod unchanged (non-production).
- stages/explore_consent.py: a production project is covered only by a signed human-granted `production: true` row for the exact target and run kind. Account-derived and production:false rows are refused (never minted) with a named reason. `require_consent` now returns the approval.
- schema/crawl.py: `Crawl.approval_id`, `Crawl.approval_production`, set at the start gate in `run_crawl`.
- stages/explore_summary.py: `scrubbed()` passes nodes, edges and issues through the run's Redactor before disk (email included, ids preserved); `write()` saves the tracked `CrawlSummary` (schema/crawl_summary.py) to projects/<slug>/crawl_summaries/<crawl_id>.json when a crawl finishes. Full crawl artifacts stay gitignored.
- scripts/check_crawl_approval.py: verifies from the summary plus approvals.jsonl (clean-checkout safe): recorded id exists, intact, matches project/kind/target, covered the bounds at start, and production:true / not account-derived for production projects. Signature is verified when AUTOTESTER_APPROVAL_KEY is present and reported as NOT verified when it is not.
- tests/test_approval_prod_gate.py.

## Verify
uv run pytest tests/test_approval_prod_gate.py tests/test_explore_consent.py tests/test_explore.py tests/test_credential_run_approval.py tests/test_explore_secret_scrubbing.py ; uv run ruff check src tests scripts ; uv run autotester doctor

## Fix cycle 2 (D1-D4 of verdict cycle 1)
- core/consent.py: ONE function, `require_project_approval(project, ...)`: production project => signed human `production:true` row, exact target and kind, derived/false/unsigned/other-target refused with a named reason; otherwise unchanged. explore_consent.covering_approval now calls it (its private copy is gone).
- Paths now enforcing it: crawl/explore (covering_approval), release scope create (release.py via covering_approval), release re-check (orchestrate_gate.release_preflight, D2), UI case-run trigger (trigger_run -> run_launcher.prepare_run -> require_live_case_approval -> covering_approval; AT-570 already enforced there for every project, production adds the human-row rule), agents/guards.py crawl_approval and live_case_approval, stages/adversarial.py (also `production = production or project.production`).
- NOT changed, by design: stages/discover.py:49 gates a READ of a filesystem path outside the project (target is a path, not a live target; the scope carries a slug, not a Project). stages/ai_capture.py:96 takes a caller-stated `production` flag and a project slug string; not wired to Project.production here (open, noted for the checker).
- scripts/check_crawl_approval.py (D1): production project (declared or recorded) with no AUTOTESTER_APPROVAL_KEY, or an unverifiable signature, exits 1 with a named reason.
- explore_summary.safe_stop_reason (D4): enumerated code + <=80 char detail with URLs, paths and bracketed text removed.
- tests/test_approval_prod_gate_paths.py: per path x {derived, unsigned, production:false, other-target} refused, valid human production row allowed, non-production unaffected; forged-signature and no-key done_check; stop_reason hygiene.
