# ui-production-approval

Status: ready-for-check
Fix cycle: 1
Branch: wave/ui-production-approval

## Change
- UI approval form (`POST /projects/{slug}/crawl-approval`): kind select (crawl, live_case), production checkbox forced on for a production project (server also forces it), bounds and expiry kept.
- `granted_by` is the signed-in session email (no form field); no session, or an Authorization header, gives 403.
- Route policy row moved from project.run to access.approve (`auth/policy.py`, pin test updated).
- Missing signing key fails closed with the key message (400, nothing written).

## Files
src/autotester/ui/routes_crawl_approval.py, routes_credentials.py, auth/policy.py,
tests/test_ui_production_approval.py (new), test_ui_crawl_approval*.py, test_ui_auth_policy_table.py

## Verify
scoped ui approval tests, ruff, doctor clean.
