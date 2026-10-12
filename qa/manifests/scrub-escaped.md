# scrub-escaped
Status: ready-for-check
Fix cycle: 0
Issues: ISS-t168-damage-control-report-1, ISS-t168-damage-control-report-2, AT-830, AT-928

- report-1: already fixed on master (82ba1f1e scrubs the report object before render); existing DC4 tests in test_unified_report_secrets.py cover it. No code change.
- report-2: load_api returns Unavailable("no first-party network evidence was stored") when no NETWORK row exists (stages/unified_report.py); test in test_unified_report.py.
- AT-830: core/redact.py masks %40 emails and %2B phones; tests in test_redact_pii.py.
- AT-928: failure_bundle trace.jsonl scrubs the span object before json.dumps; tests/test_failure_bundle_escape.py.
- tests/test_attack_b.py exists only under qa/evidence; not run.
