# login-carveout (read-only sub-checker, t179a repair cycle 1, coordinator A)
Code: HEAD (c489e201) guards.py + tools.py. Script: scripts/login-carveout/run_rows.py (rows.csv, raw_output.txt),
scripts/login-carveout/scope_probe.py (scope_probe_output.txt). `autotester.__file__` printed = inside HEAD copy.
Env: fake canaries (CANARY-user-7f3a9c / CANARY-pw-7f3a9c), fake AUTOTESTER_APPROVAL_KEY set by the script, temp data roots,
spies for execute.run_case and the session factory. 94 rows; every refused row: typed refusal, sessions 0, run_case 0, data root unchanged.
Every ok row: sessions 1, run_case 1, data root changed (result saved). No canary ever appeared in an outcome.

Rows that ran although my default expectation was "refused" (UNEXPECTED in rows.csv):
B4, B4b (two/three fill+submit sequences), B11/B12/B13 (the one submit CLICK may be any name that passes deny_reason: Place order, Save, Transfer funds),
B14 (Enter on locator "Search"), C14-C17 (declared credential typed into Search/Comment/Amount/Delete confirmation),
C18 (post-login Comment fill of APP_PASS + CLICK "Post comment"), D3 (second NAVIGATE with query in login case),
D5b (/account?action=delete&confirm=1), D5c (/transfer?to=eve&amount=100).
Everything else behaved as the code reads. See the final report for findings F1-F5.
