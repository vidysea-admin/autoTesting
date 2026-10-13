# Task-level verdict - T-203 hosted website (close-out, 2026-10-13)

Contract `qa/contracts/hosting.md`. Row-by-row evidence: `qa/verdicts/t203-task-check.md` (independent check of master 208be7e0).

VERDICT: PASS (local build on this Windows machine; Docker/Ubuntu/DNS rows deferred)

- The one FAIL in that check, HO23 (the scheduler side never reaches a browser), is closed: `hosted`, `_option`, `bind_host`,
  `bind_port`, `auth_disabled` moved verbatim to the pure `auth/loopback.py` (security checker PASS,
  `qa/verdicts/t200-walk-auth-refactor.md`), cutting the chain schedule_wiring -> schedule_owner -> auth.config -> ui.helpers ->
  browser.session. `tests/test_schedule_tick.py::test_the_scheduler_side_reaches_no_browser_or_pipeline_module_even_transitively`
  is green on the merged tree with no loosening (ALLOWED_OUTSIDE gained only the HO24 auth modules). Re-run after merge:
  test_hosting_config, test_hosting_deploy, test_hosting_gaps, test_server_settings, test_schedule_tick, test_ui_runs_queue: 125
  passed; schedule CLI/wiring/owner guard/routes and run_queue: 121 passed; ruff and doctor clean.
- All other non-deferred rows were PASS in the task check (HO1-HO4 local halves, HO7, HO9, HO12, HO14-HO22, HO24, HO25, HO30-HO33,
  HO37, HO38, HO41-HO46).
- DEFERRED, not judged: HO5, HO6, HO8, HO10, HO11, HO13, HO34-HO36 (Docker/Ubuntu, D-090); HO26-HO29 (email, D-093 item 2);
  HO39, HO40 (D-093 item 1); server-gated probes (nmap, live Drive 1 GiB).
- Gate `qa/gates/t203-host-and-dns.md`: answered as deferred (D-090 item 3, D-093 item 1); it blocks only T-206's hosted check, not
  this close.
