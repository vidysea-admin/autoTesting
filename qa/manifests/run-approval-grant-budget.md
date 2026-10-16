# Run-approval grant scope and probe budget

Status: ready-for-check
Fix cycle: 0
Risk: high (consent gate, security)
Base: c4d48ad109f1ef77f73ee9172866cc5feeca7063
Candidate: see the unit commit (`git log -1 --format=%H` on branch worktree-agent-a70bbe56d22416ba9)
Branch: worktree-agent-a70bbe56d22416ba9

## Issues addressed

- ISS-d063-grant-budget-1 (FIXED). `covering_approval` -> `_credential_approval` reused any
  account-derived row matching project/kind/target. It now reuses an account-derived row only
  when `row.scope` equals the freshly validated credential scope (the JSON of keys + domains
  that `validate_account_scope` returns), so a run for other credentials mints its own row. A
  credential-free run (no declared secrets, or none provisioned) already saw human rows only
  (AT-759, `human` list); a regression test now pins that.
- ISS-d063-grant-budget-2 (ALREADY FIXED, verified by test). `ui/app.py` installs the D-066
  Origin/Host guard (`origin_guard_middleware`) and the T-204 auth middleware ahead of every
  route, so a cross-site POST cannot edit base_url/domains/secrets or trigger a run. New test
  posts to the edit, secrets, run and crawl-approval routes with a foreign Origin: all 403, the
  project is unchanged, no approval is written. (Existing `test_ui_origin_guard.py` walks every
  state-changing route.) No code change for this issue.
- ISS-d063-grant-budget-3 / AT-675 (FIXED). `covering_approval(..., probes=0)` is a new keyword;
  `run_launcher.require_live_case_approval` passes `run_budget.probe_request(cases)` (2 per FILL
  step + 1 per ASSERT step, a floor) so a human row granting fewer probes is refused at
  preflight naming "probes N > approved M", before any browser opens. Runtime enforcement stays
  in `RunBudget` (unchanged). The UI grant form gains `max_probes` (default 4000, cap
  `MAX_GRANT_PROBES` = 40000 = MAX_GRANT_ACTIONS x PROBES_PER_ACTION, range-checked, secret
  scan applied).
- AT-570: already `verified` on the ledger (the gate lives in `stages/run_launcher.py`, reached
  from `trigger_run`); nothing to add. Not touched.

## HMAC-bound payload

Unchanged. `max_probes` and `scope` were already in `RunApproval._bound_payload`; no bound field
was added, so every existing signed row still verifies. A legacy row without `max_probes` loads
(default 0) and a row edited after signing fails `is_intact`/signature: both refuse, neither
crashes (test `test_legacy_and_edited_rows_fail_closed_without_a_crash`).

## Changed paths

- src/autotester/stages/explore_consent.py (scope-equality reuse; `probes` floor)
- src/autotester/stages/run_budget.py (`probe_request`)
- src/autotester/stages/run_launcher.py (passes probe floor; 299 lines)
- src/autotester/core/consent.py (`MAX_GRANT_PROBES`)
- src/autotester/ui/routes_crawl_approval.py (max_probes field + validation)
- tests/test_run_approval_grant_budget.py (new, 12 tests)
- qa/manifests/run-approval-grant-budget.md

## Consumers

`covering_approval` callers: run_launcher (UI + queue + tick), schedule_gate, release,
explore (`require_consent`), CLI explore. All keep `probes=0` default except run_launcher, so
only the human-grant LIVE_CASE preflight tightens. Existing on-disk human rows with
`max_probes=0` still cover case runs that have no FILL/ASSERT steps; runs with them need a
re-grant carrying probes (this is the intended fail-closed outcome).

## Contract clauses

core-invariants C12 (fail closed), consent.md CN5 (exact triple), CN10 (zero means zero),
CN11 (no transfer across scopes), D-018, D-068, D-088, AT-110 signing.

## Required checks

- pytest tests/test_run_approval_grant_budget.py (+ consent/launcher/ui-approval/origin suites)
- ruff check on changed paths; `autotester doctor` (clean)

## Follow-ups (not done)

- schedule_gate and release.py also call `covering_approval(LIVE_CASE)` with no probe floor; a
  probe-less human row passes their preflight (still stopped at runtime by `RunBudget`).
- The gate files qa/gates/d063-cn5-vs-cn11.md and d063-self-grant-csrf.md still need Umesh's
  ruling text reconciled; the issue rows stay open until the checker verifies.
