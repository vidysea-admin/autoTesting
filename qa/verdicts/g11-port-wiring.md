# Verdict - g11-port-wiring cycle 1 (repair check)

Cycle checked: 1
Date: 2026-10-19 (checker, single, claude-sonnet-subagent; bound to D:/autoTesting/.worktrees/g11-port-wiring)
Policy-Version: proportional-verification/2026-10-18.15
Checked state: HEAD a08871ec (code fix 5d98051f); cycle-0 checked head d9c8f5ad. Cycle-0 verdict: qa/verdicts/g11-port-wiring.r0-1.md

## Check plan
Repair scope: the failed criterion PW4 (AT-1335) plus the impact of the repair diff on PW1-PW3 (the diff adds `RoleState.attempted` and changes `_guard` to raise RoleLoginFailed once any role attempted a sign-in). Tier L unchanged, single checker. Steps: probe re-run, repair-diff read in full, affected tests, one falsification for PW4, RoleNotSignedIn grep, ruff.

VERDICT: PASS
SCOREBOARD: 4/4 criteria met (PW1-PW4); invariants MPI1, MPI3, MPI5 untouched by the repair
TIER: L
FAILURES: none
CAPABILITY-COVERAGE: 1/1 floor row reproduced (one falsification for the repaired criterion, in a copy outside the tree)
LIVE-BROWSER: qa/evidence/g11-port-wiring/probe_unattempted.c1.out (headless Chromium, local fixture app only)
ISSUES-WRITTEN: none new; AT-1335 marked fixed. AT-1336 and AT-1337 (low) stay open and unchanged.
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The cycle-0 probe now prints negative_input, state_after, api_error, request_budget, copy_lint and responsive all `errored RoleLoginFailed` with FINDINGS 0, where it printed 7 findings from the working half. The repair is exactly what AT-1335 asked: `_require_every_role` (role_port_state.py:102-105) also treats a role on a platform with a declared sign-in that is not signed in as broken, and `_guard` (role_port_state.py:90-93) raises RoleLoginFailed ("never attempted") once any role has attempted a sign-in, so negative_input and state_after now give the same reason as the whole-run oracles. Use before any sign-in still raises RoleNotSignedIn (test line 45, still green). The 19 affected tests pass, which covers PW1-PW3 (the added `attempted = True` at role_session_port.py:82 is set before the existing login logic and changes nothing on the success path).

## Evidence (what I ran myself)
- PW4 probe: `.venv/Scripts/python.exe -I qa/evidence/g11-port-wiring/probe_unattempted.py` on a08871ec -> six oracles `errored RoleLoginFailed`, `FINDINGS 0 []` (qa/evidence/g11-port-wiring/probe_unattempted.c1.out).
- Repair diff read in full: `git diff d9c8f5ad..a08871ec` = role_port_state.py, role_session_port.py (+1 line), test_role_session_port_login.py (+23, one new test, no existing assertion edited), manifest. Whole-unit scope unchanged (no oracle, enums or other-unit schema file).
- Affected tests: `uv run pytest tests/test_role_session_port.py tests/test_role_session_port_login.py tests/test_actuator_chokepoint.py` -> 19 passed, 1 failed in 132 s; the failure is test_no_direct_page_or_playwright_access_outside_browser_package, red only on stages/platform_links.py:120,149-156,184 (T-210, not in this diff; same red as cycle 0) (c1-pytest-summary.txt).
- RoleNotSignedIn grep over src and tests: one raise (role_port_state.py:93, use before any sign-in) and one test expecting it (test_role_session_port_login.py:45); nothing else depends on it.
- Falsification (PW4, floor of 1): copy at scratchpad check-g11-pw-c1/copy (PYTHONPATH confirmed to the copy), `if any(st.attempted for st in self._states.values()):` -> `if False:` in `_guard`; `test_pw4_a_role_whose_sign_in_was_never_attempted_errors_every_oracle` green before, red after on `assert 'RoleNotSignedIn' == 'RoleLoginFailed'` for negative_input; copy restored (cmp identical) (falsify_pw4_c1.red.txt).
- `uv run ruff check src tests scripts` -> All checks passed.

## Note
The cycle-0 verdict proposed folding PW1-PW4 into qa/contracts/multi-role-platform.md under T-210 at PASS. Not done in this commit (the dispatch scope was verdict, checkpoint, evidence and issues); the contract maintainer step is still open for the next checker sweep.

Metrics: start=2026-10-19T04:05:00Z end=2026-10-19T04:25:00Z wall_min=20 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=1 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=1200 mutants=0 defects_unit=0 defects_6c=0
