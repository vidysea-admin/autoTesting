# Verdict: scrub-escaped (b2e491c4, fix cycle 1)
Cycle checked: 1
Verdict: PASS

- Cycle 0 probes: single, double, HTML-entity and +/space variants of a secret now scrub to [REDACTED]:K, including inside a URL (AT-939 fixed). %40 email and %2B phone masked (AT-830 fixed).
- Over-scrub: "100%40 off", "sale 50% off", plain text untouched.
- Hang gone: 100 KB adversarial inputs 0.015-0.036 s; test_redact_pii 139 pass in 1.7 s (shell timeout 300 s).
- Duplicate: URL credential scrub lives in core/redact; real_acceptance._scrub_urls is a thin wrapper. No second regex.
- Scoped: test_redact_escaped 21 pass; failure_bundle(+escape), unified_report(+secrets) 49 pass; ruff clean; doctor clean; merge-tree vs master no conflicts.
- Minor residual (non-blocking): double-encoded PII shape "a%2540b.com" is not masked by mask_pii (only by Redactor for declared secrets).
