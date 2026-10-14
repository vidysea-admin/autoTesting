# Verdict: ui-production-approval

Cycle checked: 1
Verdict: FAIL
Commit: ca0ae0b3

## Passed
- Scoped tests (24: production approval, crawl approval, list, policy table), ruff, doctor clean; merge-tree vs master clean.
- Forged granted_by: no form field; signer is the session email (`_signer`); no session or Authorization header gives 403.
- Production forced server-side (`project.production or bool(production)`); non-production behaves as before (checkbox optional).
- CSRF: D-066 Origin guard middleware runs first on POSTs (exact-origin allowlist); no per-form token, relies on that guard. Acceptable.
- Missing key: 400, nothing written.
- Role escalation: access.approve held by Admin (@all), Sub-admin (@assigned), Developer (@own). Same populations held project.run before except custom groups with project.run but not access.approve (they lose crawl-approval grants; Tester never had either). Intended tightening, but a custom group must be re-granted.

## Blocking finding
1. No server-side caps on bounds. `wall_clock_s` only `>0 and finite`, `max_actions >0`, expiry only "in the future". A signed-in approver can sign a production approval with 600000000 s (19 years), a huge action count, and a year-9999 expiry. schema/approval.py itself notes the 600000000 s row exists and "nothing here rejects it". A UI grant must be bounded.
   Required fix: in `crawl_approval_submit`, reject wall_clock_s > 86400 (24h), expiry > now + 30 days, and a sane max_actions ceiling, each with a 400 and a test (including the production path).

## Verdict
FAIL until caps land. Re-check after Fix cycle 2.

---

# Cycle 2

Cycle checked: 2
Verdict: PASS
Commit: 354a55e8 (rebased on 4b7b5989)

- (a) Writers of approval rows: UI route and CLI `approve` both call `validate_grant_bounds` before signing. Other writers: `explore_consent` account-derived rows (granted_by ACCOUNT_GRANTOR, production forced False, never admitted for production projects, system-selected bounds) and dev scripts (`scripts/*proof*.py`, `agent_live_comparison.py`; hardcoded, not runtime paths). None is a human production grant path; no bypass. Residual note: account-derived rows are uncapped by this validator (non-production only).
- (b) Boundaries use strict `>`: exactly 2000 / 86400s / 30 days accepted, one past rejected (tested in test_grant_bounds_caps.py). CLI date-only 30th day is rejected (end of day), stricter, fine.
- (c) Test diffs: only granted_by field removed (now session), expiries made relative, 30 changed to 29 for the cap; no assertion weakened (granted_by assertion tightened to session email).
- (d) 42 scoped tests pass, ruff clean, doctor clean, merge-tree vs master clean.
