# Checkpoint B - t208-role-onboarding (cycle 0)

Environment: win32, worktree .venv python, uv run --directory <wt>; TMP/TEMP=D:/autoTesting/.work/tmp; AUTOTESTER_ROOT scratch per test.
Code: HEAD 64479541, code SHA 83c4c161, base 722bf3df. Hashes (sha256 prefix): routes_role_accounts.py 0af1ebb6c191, role_onboarding.py 929974524924, policy.py b597f2ef1891. Lock: uv.lock unchanged by the diff.
Original checker attribution: coordinator B, claude-sonnet-subagent, qa/verdicts/t208-role-onboarding.b.md

| check | command / scope | result |
|---|---|---|
| step 3 | pytest tests/test_role_onboarding.py tests/test_role_accounts_routes.py tests/test_ui_auth_policy_table.py (34 collected) | 34 passed |
| neighbours | 14 auth/credential/env/project files | 210 passed, 1 skipped |
| lint | ruff check (7 py files); autotester doctor | pass; clean |
| 4b MP4 | copy row1, routes_role_accounts.py:185 -> pass; 3 tests | green 3 -> red 2 (KeyError) |
| 4b MP5 | copy row2, role_onboarding.py:103 -> if False; 2 tests | green 2 -> red 2 |
| 4b MP6 | copy row3, routes_role_accounts.py:216 -> pass; 1 test | green 1 -> red 1 (303 != 403) |
| probes | qa/evidence/t208-role-onboarding.b/probe_b_security.py in clean copy, 27 tests | 27 passed (P7, P8 observations printed) |
| 4c | git diff 722bf3df..83c4c161 --stat | 10 files in scope, nothing removed |
| affected set | shard_suite.py --affected --mode unit --list --candidates | exit 2 integration-required (dynamic globs) -> 6c |
| browser | maker evidence report.json + accounts-listing.png | judged, not re-driven |
