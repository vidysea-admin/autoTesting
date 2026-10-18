# Checkpoint - t208-role-onboarding (coordinator A)
- 2026-10-18 cycle 0: cmd `pytest tests/test_role_onboarding.py tests/test_role_accounts_routes.py tests/test_ui_auth_policy_table.py` (34 collected), code sha 83c4c161, env worktree .venv py3.11 with TMP=D:/autoTesting/.work/tmp -> 34 passed. Checker: claude-sonnet-subagent (coordinator A), file qa/verdicts/t208-role-onboarding.md.
- Falsifications (copies under the scratchpad, discarded): MP4 fM4b red 7==8; MP5 fM5 red DID NOT RAISE; MP6 fM6 red at test line 170.
- Probes: rebind by project.edit-only -> 303 (P1); /secrets same actor -> 403; no value in logs/page/project.json; both-quote value 400 value-free.
