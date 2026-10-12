# Manifest — at651-exact-host-secrets

Status: ready-for-check
Fix cycle: 0
Issues addressed: AT-651
Decision: D-087 item 1 (docs/DECISIONS.md) — each environment is a separate project; secret host scope is an EXACT host match; no `environments` schema concept.

## What changed
- `src/autotester/browser/secrets.py::_host_matches` now compares normalised hosts for equality (lowercase, one trailing dot ignored). The suffix branch is gone. `SecretRef.include_subdomains` is still accepted (schema untouched) but no longer widens matching; there was no other intentional subdomain allowlist. All callers (secrets, consent, schedule_gate) get exact matching through this one function.
- `projects/pathlynks/project.json`: no change needed. Every secret already scopes an exact host (`dev-new.vidysea.com` for counsellor, `pathlynks.vidysea.com` for user); only `allowed_domains` has bare `vidysea.com`, which is navigation scope, not secret scope.
- Test fixtures that relied on suffix matching now name the exact host (test_browser.py, test_browser_navigation_secrets.py, test_onboard_pathlynks.py).

## Tests (tests/test_browser_navigation_secrets.py)
Prod secret refused on dev-new.vidysea.com, pathlynks.vidysea.com.evil.com, other subdomain, bare parent, child, prefix lookalike; allowed on exact host with case and trailing-dot normalisation; mutation test shows a suffix match would let a child host through.

## Adding a prepod environment (per D-087)
Create a separate project, e.g. `pathlynks-prepod`, with its own base_url, allowed_domains, secrets scoped to `dev-new.vidysea.com`, and approvals. Not created now.
