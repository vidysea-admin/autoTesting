# Verdict - t199d-bug-wiring
Cycle checked: 1
Verdict: PASS

- Single path: `store.save_run` has exactly one caller in src (`stages/run_launcher.py::launch_run`), followed by `record_run_bugs`. UI run (routes_runs), queue, team Test press (routes_team_run), schedule tick (schedule_wiring) and CLI all reach runs via launch_run. Idempotent per run, fault logged and run kept, no SheetClient constructed in src (D-090).
- TB12 `sheet_sync.try_sync`, TB14 `tracker_binding` + schema: covered by tests, pass.
- Gate test: `test_the_gate_is_not_a_parameter` failed on master because of `requested_by_id` (T-201b). It is only copied into `Run.requested_by_id` (attribution), never read by any gate. Added to the allow-list with a comment (as for `requested_at`); assertion unchanged.
- Tests: 71 passed (bug_wiring, sheet_sync_tb12_tb14, tracker_auth, tracker_page, run_launcher*), 92 passed (team_run*, schedule wiring/tick/gate, cli_schedule). ruff clean, doctor clean.
