#!/bin/bash
# Part 1 runner: one pytest process over the auth files + origin guard, junit xml, grouped later by name.
W=D:/autoTesting/.worktrees/t204-team-login
S=C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/236a59b4-e0ec-4b2d-b22e-73d3059dd7f6/scratchpad/t204b-verify
cd $W
$W/.venv/Scripts/python.exe -m pytest -p no:xdist -p no:cacheprovider -rA --junitxml=$S/p1_auth.xml tests/test_ui_auth_login.py tests/test_ui_auth_accounts.py tests/test_ui_auth_groups.py tests/test_ui_auth_surface.py tests/test_ui_auth_escalation.py tests/test_ui_auth_hardening.py tests/test_ui_auth_cli_and_limits.py tests/test_ui_auth_survivors.py tests/test_ui_auth_host_and_consent.py tests/test_auth_deploy_files.py tests/test_ui_origin_guard.py > $S/p1_auth.log 2>&1
echo done1 > $S/p1_auth.done
