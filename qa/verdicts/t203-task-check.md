# T-203 task-level check (independent) - NOT CLOSED

Checked master 208be7e0 on branch check/t203-task. Tests run: 146 passed (hosting_config/deploy/gaps, server_settings, ui_settings, run_queue*, windows_host, ui_runs_queue, team_run_queue_seam); 176 passed + 1 FAILED in schedule/intake/drive/report/policy set. `ruff check src tests scripts` clean. `autotester doctor` clean.

## Gap (blocks close)
- HO23 (scheduler never starts a browser; owned by T-200 but a hosting.md row) FAIL:
  `tests/test_schedule_tick.py:226` `test_the_scheduler_side_reaches_no_browser_or_pipeline_module_even_transitively` is red on master.
  Chain: `stages/schedule_wiring` -> `stages/schedule_owner` -> `autotester.auth` / `auth.config` -> `ui.helpers` -> `browser.session`
  (22 violations). Introduced by the T-200c HO24 owner guard (6409bb5e) importing auth, merged with T-204. The tick does not launch a
  browser at runtime, but the TS6 transitive-import guard is red and was not re-run after that merge. Fix: break `auth.config -> ui.helpers`
  (or have schedule_owner avoid the heavy import) so the guard is green; do not loosen the test.

## Rows
| row | status | evidence |
|---|---|---|
| HO1 | PASS (local); BUILD-HOST half DEFERRED (D-090 Docker rows) | test_hosting_config/deploy; land-t203-hosting mutation |
| HO2 | PASS (local scan) | check_no_secrets, env tests; inspect/logs DEFERRED |
| HO3 | PASS (healthz package path, tested); container DEFERRED | test_hosting_gaps |
| HO4 | PASS (local listing/restart); container DEFERRED | scripts/hosting_state_listing.py, t203b verdict |
| HO5, HO6, HO8 | DEFERRED/SERVER-GATED (Docker/Ubuntu, D-090) | no Docker here |
| HO7 | PASS (overlay: only loopback 8000); nmap SERVER-GATED | docker/compose.prod.yml |
| HO9 | PASS | drift tests in test_hosting_config |
| HO10, HO11, HO13, HO34, HO35, HO36 | DEFERRED (D-090) | |
| HO12 | PASS (local); probes SERVER-GATED | t203c-viewonly-ws verdict, merged 80c15ebb; policy table tests |
| HO14 | PASS | test_hosting_config |
| HO15 | PASS | test_server_settings, test_ui_settings |
| HO16-HO18 | PASS | test_run_queue*, test_ui_runs_queue |
| HO19 | PASS | _recheck_run_right, test_hosting_gaps |
| HO20 | PASS | test_run_queue |
| HO21 | PASS | test_hosting_gaps, policy table |
| HO22 | PASS | test_schedule_model |
| HO23 | FAIL | see Gap |
| HO24 | PASS (owner guard tests) | test_schedule_owner_guard |
| HO25 | PASS | test_ui_report*, policy table |
| HO26-HO29 | DEFERRED (D-093 item 2) | |
| HO30-HO33 | PASS (local) ; live Drive/1 GiB SERVER-GATED | test_ui_intake (413), test_ui_intake_drive, test_drive_link; Caddyfile:15 |
| HO37 | PASS | ruff and doctor clean |
| HO38 | PASS | affected existing tests green |
| HO39, HO40 | DEFERRED (D-093 item 1) | |
| HO41-HO46 | PASS | test_windows_host (9), serve_windows.ps1, DEPLOY.md Part B.1 |

## Gate ruling: qa/gates/t203-host-and-dns.md
Answered as deferred; does NOT block T-203 close. D-090 item 3: "the production host will be Ubuntu, with host and DNS provided
later. For now build and host on THIS Windows machine (no Docker here)". The gate file's own header: "Blocks: only the hosted check
of T-206 ... It does not block T-203's build." D-093 item 1 adds: "T-203 may close on this machine once its remaining non-deferred HO
criteria pass."
