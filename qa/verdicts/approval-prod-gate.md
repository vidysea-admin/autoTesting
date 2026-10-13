# Verdict - approval-prod-gate

Cycle checked: 1
Verdict: FAIL
Checker: independent security review of wave/approval-prod-gate (b6336876). Tests: 62 passed (prod_gate, explore_consent, explore, credential_run_approval, secret_scrubbing); ruff clean; doctor clean.

## Probes
1. Enforced production gate (project.production): crawl/explore (stages/explore.py:263 via cli_crawl) and release scope creation (stages/release.py:64, covering_approval). NOT enforced: UI case runs (ui/routes_runs trigger_run has no approval check, AT-570 open); orchestrate_gate.py:46 (re-check omits production, so a hand-edited scope.json naming a production:false or derived row passes); agents/guards.py:65,72; stages/adversarial.py:108; stages/discover.py:49. The unit does not claim these, but the manifest does not say so either.
2. production is not settable via UI: routes_project_edit.py:213 model_copy touches name/base_url/domains only; new projects default False (ui/app.py:161). Flipping is a raw project.json edit: no admin check, no audit entry. A new slug pointing at a production URL is non-production by default (declared, not inferred).
3. Only pathlynks was a production target in tree; it is set true. Other prod-looking projects (erp, vidysea-erp at www.vidysea.com/erp) stay False: they silently remain ungated. Needs Umesh's call.
4. CrawlSummary: ids, approval id, bounds, counters only. stop_reason (<=200 chars, scrubbed) can carry page text or a URL; minor.
5. DEFECT: scripts/check_crawl_approval.py:73-78 passes a production project with "signature NOT verified" when the key is absent; row.is_intact is a content hash, forgeable by anyone who can edit approvals.jsonl. Must fail closed for production projects.
6. Redaction: planted email masked in nodes/edges/issues, ids preserved (test_crawl_artifacts_mask_the_test_account_email).

## Required fixes
- D1: fail closed (exit 1) when project.production or summary.project_production and no key.
- D2: pass production through orchestrate_gate.py:46 (and state which other paths remain open).
