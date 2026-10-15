# Verdict: at887-reachability
Cycle checked: 1
Result: FAIL (PII in path templates)

Pass: old summaries load (new lists default empty, tested); the warning only appends a string and never skips, removes or reorders a case; schema keeps extra="forbid" (Artifact base); no summary or pre-AT-887 summary gives no warning; report card escapes HTML. Query strings and fragments are stripped.

Blocking: url_template(fold_index=True) folds only numeric ids. Measured: /user/john.doe@x.com/p stays verbatim, and /reset/AbCdEf0123456789xyz stays verbatim. reached_paths, unreached_paths and the report card would persist emails and path-borne tokens. Required: fold email-like and long opaque segments (or filter them) in _split_paths and _first_route, plus a test.

Checks: 36 scoped tests pass; ruff clean; doctor clean; merge-tree with master clean.

## Cycle 2
Cycle checked: 2
Result: PASS (head 36ab41d8, checked detached)

Probes folded: /user/john.doe@x.com/p -> /user/{var}/p; /reset/AbCdEf0123456789xyz -> /reset/{var}; phone, UUID, JWT, 8+ digit runs -> {var}. Slugs stay readable (intro-to-python, supply-partners, long hyphenated blog slugs). safe_path is applied to stored reached/unreached paths and to the warning route, and the card renders those.
Regexes: all fullmatch or simple classes; 50k-char adversarial segments ran in under 0.07s, so linear. Emails/phones reuse core.redact.mask_pii.
Overlap (non-blocking): core/urls.py already folds uuid/ULID/hex>=16 to {id} before safe_path runs, so _UUID is partly redundant; JWT and base64ish detection are new. Not a violation.
Checks: 331 scoped tests pass, ruff clean, doctor clean, merge-tree clean vs master.
