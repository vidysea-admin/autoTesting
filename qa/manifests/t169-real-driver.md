# Manifest - t169-real-driver

**Status:** ready-for-check
**Fix cycle:** 2
**Unit:** T-169 turnkey real-target driver (evidence for GR1-GR4)
**Branch:** wave/t169-real-driver
**Contract:** qa/contracts/generic-acceptance.md (GA, GR1-GR4)

## Changes
- stages/real_acceptance.py: preflight via require_project_approval (CRAWL for url_only, LIVE_CASE for both; production rule applies), drive_real wraps run_mode, writes qa/evidence/t169-real/<mode>/{evidence.json,comparison.json,checklist.md} (run id, verdict counts, INCONCLUSIVE breakdown, comparison), returns GR1-GR4 checklist; GR3 verdict and AT-281 thresholds left as human.
- scripts/run_real_acceptance.py: CLI; --dry-run checks approvals only.
- tests/test_real_acceptance.py: refusal without approval, both modes with mock seams + TestClient (no browser).
- docs/MAP.md regenerated.

## Verify
PYTHONPATH=<worktree>/src python -m pytest tests/test_real_acceptance.py tests/test_generic_acceptance.py ; ruff check src tests scripts ; autotester doctor

## Human run (once approvals exist)
PYTHONPATH=src python scripts/run_real_acceptance.py pathlynks --mode url_only
PYTHONPATH=src python scripts/run_real_acceptance.py pathlynks --mode teaching   (add --dry-run first)
Note: the pathlynks project must already be onboarded; teaching needs a video source registered; GR4 text in the contract is stale (UI runs now enforce LIVE_CASE approval).

## Fix cycle 2
- Evidence scrubbed before write (SecretStore redactor, mask_pii, URL credential params) and gated with Redactor.assert_clean; failure reasons scrubbed before truncation. Test: test_evidence_is_scrubbed_and_gated.
- GR4: test_ui_run_trigger_refuses_production_without_approval drives POST /projects/demo/run for a production project with no approval: 403, no BrowserSession.start, no approval minted. Checklist line cites it and the code path (trigger_run -> run_launcher.prepare_run -> require_live_case_approval).
- Tests for unsigned and production:false rows refused in preflight.
