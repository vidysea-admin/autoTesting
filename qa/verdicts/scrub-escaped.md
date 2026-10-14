# Verdict: scrub-escaped (head f845fe51)
Cycle checked: 0
Verdict: FAIL

- (a) FAIL. Redactor.scrub leaves percent-encoded, double-encoded (%2540) and `&#64;` forms of a secret unchanged. Only mask_pii gained %40 email / %2B phone patterns (single-encoded).
- (b) Normal text mostly fine ("100%40 off" untouched). _ENC_EMAIL_RE masks any `x%40host.tld` run.
- (c) No code overlap with real_acceptance._scrub_urls, but the URL-secret scrub is still outside core/redact; one concept lives in two places. Flag.
- (d) AT-830 partly fixed (single-encoded email/phone). AT-928 fixed (failure_bundle files: 29 pass). ISS-t168-2 fixed in load_api. AT-939 NOT fixed (percent-encoded secret in network URL stays verbatim); the manifest does not claim it.
- (e) Ruff clean. merge-tree vs master clean. tests/test_redact_pii.py: 133 pass in 1.1s on master, but on the branch it stalls at test ~131 (an F in the combined run). _ENC_PHONE_RE nested quantifier backtracks (3000x "%20" costs 0.57s, quadratic). Regression; not isolated within the time cap. Doctor: 1 violation (langchain_ollama undeclared), looks pre-existing. unified_report tests unconfirmed.
Action: maker fixes the stall, adds encoded variants to Redactor.scrub for AT-939, moves the URL scrub into core/redact.
