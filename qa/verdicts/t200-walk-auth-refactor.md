# Verdict: t200-walk-auth-refactor (independent security check)

Branch check/t200-walk head 1a87daf1 against merge-base 9b332b2b. Checker: independent.

**Verdict: PASS**

- Moved bodies (hosted, _option, bind_host, bind_port, auth_disabled) in auth/loopback.py are
  byte-identical to the removed ones in auth/config.py; the only addition is a one-line docstring.
  HOSTED_ENV, DISABLED_ENV, _LOOPBACK moved with them. auth.config re-exports all of them
  (identity asserted in tests/test_auth_loopback.py); the five importers (accounts, app,
  auth_middleware, intake_gate_auth, routes_auth) still import from auth.config and resolve.
- AU17: auth_disabled() is honoured only when not hosted AND bound to loopback. Covered by
  test_auth_loopback.py: loopback ok; hosted+env-set -> False; 0.0.0.0/10.0.0.5/:: -> False;
  no switch -> False. No case needed adding.
- owner_guard skips only when auth_disabled(); with auth ON it fails closed (HO24).
- ALLOWED_OUTSIDE in the TS6 closure test gained only schedule_owner, auth, auth.access, auth.db,
  auth.defaults, auth.loopback. Nothing browser-related.
- AUTOTESTER_AUTH_DISABLED=1 is set only in test fixtures (test_cli_schedule root fixture,
  schedule_fakes.loopback_single_user), via monkeypatch.
- Other changes reviewed: wait_for_tick_runs (tracked non-daemon-equivalent threads, joined by the
  tick command, not on --dry-run; covered by test_tick_waits_for_runs and a CLI test); schedule
  card preview/inline refusal/credentials link; policy rows for /schedule use schedule.manage and
  are pinned in the AU14 table; 403 names the key only, not the user. No findings.
- Merged tree: test_cli_schedule, test_schedule_tick, test_tick_waits_for_runs, test_auth_loopback,
  test_schedule_wiring, test_schedule_owner_guard, test_schedule_routes, test_run_queue (121
  passed), test_ui_auth_policy_table and escalation (23 passed), ruff clean, doctor clean.
