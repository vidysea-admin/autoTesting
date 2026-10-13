# Manifest - approval-prod-gate

**Status:** ready-for-check
**Fix cycle:** 1
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
