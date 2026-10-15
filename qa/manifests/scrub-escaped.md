# scrub-escaped
Fix cycle: 1
Issues: ISS-t168-damage-control-report-1, ISS-t168-damage-control-report-2, AT-830, AT-928, AT-939

- report-1: already fixed on master (82ba1f1e scrubs the report object before render); existing DC4 tests in test_unified_report_secrets.py cover it. No code change.
- report-2: load_api returns Unavailable("no first-party network evidence was stored") when no NETWORK row exists (stages/unified_report.py); test in test_unified_report.py.
- AT-830: core/redact.py masks %40 emails and %2B phones; tests in test_redact_pii.py.
- AT-928: failure_bundle trace.jsonl scrubs the span object before json.dumps; tests/test_failure_bundle_escape.py.
- tests/test_attack_b.py exists only under qa/evidence; not run.

## Fix cycle 1 (answers verdict cycle 0)
- Redactor.scrub masks percent (x2), HTML-entity (decimal/hex/named) and plus spellings via decoded views with a segment map (core/redact_escaped.py). Closes AT-939.
- AT-830 finished: encoded email/phone masking is now linear scans (no regex backtracking); the quadratic _ENC_PHONE_RE is gone.
- URL-credential scrub moved to core/redact (scrub_url_credentials); real_acceptance._scrub_urls delegates.
- Tests: tests/test_redact_escaped.py (each encoding, 100 KB perf < 1 s). Scoped redact/failure_bundle/unified_report/real_acceptance: 343 pass; ruff and doctor clean. Branch wave/scrub-escaped-c1 (rebased on master; wave/scrub-escaped is checked out in another worktree).
Status: ready-for-check
