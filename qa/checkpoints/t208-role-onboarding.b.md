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

# Checkpoint B - t208-role-onboarding (cycle 1, repair check)

Environment: win32, worktree .venv python; TMP/TEMP=D:/autoTesting/.work/tmp; AUTOTESTER_ROOT scratch per test; repo-root .env never touched.
Code: HEAD 8e2fc868, code SHA 7b81be9d (src/tests identical), repair base 64479541, base 722bf3df. Policy proportional-verification/2026-10-18.15. uv.lock/pyproject unchanged by the fix.
Original checker attribution: coordinator B, claude-sonnet-subagent, qa/verdicts/t208-role-onboarding.b.md (cycle 1)

| check | command / scope | result |
|---|---|---|
| step 3 | pytest tests/test_role_onboarding.py tests/test_role_accounts_routes.py tests/test_role_accounts_rescope.py tests/test_ui_auth_policy_table.py | 47 passed |
| neighbours | 6 files (credential_safety_project, env_editor, project_edit, onboard_pathlynks, multi_role_schema, onboard_a11y) | 104 passed, 1 skipped |
| lint | ruff check (5 changed py files); autotester doctor | pass; 2 known-disputed non-blocking |
| 4b MP4 | copy c1B_row1, routes_role_accounts.py `_restore(...)` -> pass; 2 rescope tests | green 2 -> red 2 (rescope.py:111, :129) |
| 4b MP5 | copy c1B_row2, role_onboarding.py:79 -> if False; 5 params | green 5 -> red 5 (DID NOT RAISE, test_role_onboarding.py:76) |
| 4b MP6 | copy c1B_row3, routes_role_accounts.py:254 -> if False; 3 params | green 3 -> red 3 (303 == 403, rescope.py:49,:70) |
| probes | qa/evidence/t208-role-onboarding.b/probe_b_c1.py, clean copy c1B_probe | 20 passed; observations Q1g, Q3b |
| 4c | git diff 64479541..7b81be9d --stat -- . ':!qa' | 5 files in scope, nothing removed |
