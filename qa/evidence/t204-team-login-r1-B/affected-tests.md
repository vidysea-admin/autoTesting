# t204-team-login repair check r1-B: affected tests (head 6ea9b688)

Each file run as its own pytest process: `.venv/Scripts/python.exe -m pytest -p no:xdist -o addopts= <tests/FILE.py> -q -p no:cacheprovider --rootdir <worktree> --basetemp <scratch>` (exit code 0 + summary line = green).

| command (file) | exit | collected | passed | failed | skipped | wall s |
|---|---|---|---|---|---|---|
| tests/test_ui_auth_envkeys.py | 0 | 23 | 23 | 0 | 0 | 152 |
| tests/test_ui_auth_refusal_audit.py | 0 | 4 | 4 | 0 | 0 | 21 |
| tests/test_ui_auth_surface.py | 0 | 31 | 31 | 0 | 0 | 59 |
| tests/test_cli_advice_resolves.py | 0 | 31 | 31 | 0 | 0 | 87 |
| tests/test_env_loading.py | 0 | 6 | 6 | 0 | 0 | 30 |
| tests/test_ui_auth_escalation.py | 0 | 22 | 22 | 0 | 0 | 15 |
| tests/test_ui_auth_groups.py | 0 | 33 | 33 | 0 | 0 | 10 |
| tests/test_ui_auth_accounts.py | 0 | 13 | 13 | 0 | 0 | 11 |
| tests/test_ui_auth_hardening.py | 0 | 19 | 19 | 0 | 0 | 19 |
| tests/test_ui_auth_login.py | 0 | 21 | 21 | 0 | 0 | 10 |
| tests/test_ui_auth_cli_and_limits.py | 0 | 6 | 6 | 0 | 0 | 6 |
| tests/test_ui_auth_survivors.py | 0 | 4 | 4 | 0 | 0 | 7 |
| tests/test_ui_auth_host_and_consent.py | 0 | 13 | 13 | 0 | 0 | 7 |
| tests/test_auth_deploy_files.py | 0 | 3 | 3 | 0 | 0 | 4 |
| tests/test_ui_origin_guard.py | 0 | 95 | 95 | 0 | 0 | 15 |
| tests/test_credential_run_approval.py | 0 | 25 | 25 | 0 | 0 | 7 |
| tests/test_permission_coverage.py | 0 | 15 | 15 | 0 | 0 | 22 |
| tests/test_ui_env_editor.py | 0 | 11 | 10 | 0 | 1 | 5 |
| tests/test_ui_project_intake.py | 0 | 15 | 15 | 0 | 0 | 6 |
| tests/test_ui_error_pages.py | 0 | 12 | 12 | 0 | 0 | 8 |
| tests/test_ui_credential_exemption_scope.py | 0 | 7 | 7 | 0 | 0 | 6 |
| tests/test_ui_credential_exemption.py | 0 | 4 | 4 | 0 | 0 | 5 |

Total: 22 files, 412 passed, 0 failed.

- ruff check on the 6 changed src files + 4 changed test files: All checks passed (exit 0).
- `.venv/Scripts/autotester.exe doctor`: `doctor: clean` (exit 0). (`python -m autotester` has no __main__; the console script was used.)
- Repair diff aa6fec2e..6ea9b688 tests: 4 files (test_cli_advice_resolves, test_ui_auth_envkeys, test_ui_auth_refusal_audit, test_ui_auth_surface). `git diff --name-only aa6fec2e 0b8a26b2 -- src tests` is empty (master merge brought no src/tests).
- Extra files found by Grep for imports of core.env / ui.credential_guard / auth.config / ui.routes_admin beyond the named list: test_ui_error_pages, test_ui_credential_exemption_scope (both run, green); test_ui_credential_exemption added as an adjacent file (green).
- No failures, so no base-comparison run was needed.
