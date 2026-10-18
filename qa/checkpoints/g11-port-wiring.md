# Checkpoint: g11-port-wiring (cycle 0, single checker)

Source: 5176c0d798a69d8e24cef9053bdc6fc7dc144e1b (wave/g11-port-wiring; code at 2e3c5c8e), base 5865cf92. Relevant blob hashes (manifest, not re-hashed): tests/role_port_run.py ce51ce52, tests/role_port_app.py a2029114, tests/test_role_session_port.py 47eb8ba5, tests/test_role_session_port_login.py a4a4a2cf. Environment: Windows 11, worktree .venv, headless Playwright Chromium. Local fixture app on a.localhost (no build id, no data snapshot).
Attribution: claude-sonnet-subagent checker, cycle 0, verdict qa/verdicts/g11-port-wiring.md.

| Check | Command / scope | Result |
|---|---|---|
| acceptance | uv run pytest tests/test_role_session_port.py tests/test_role_session_port_login.py (17 collected) | 17 passed, 108 s |
| falsify PW1..PW4 | copies of src+tests+scripts outside the tree, one named node each | each green before, red after (PW1 red on NavigationRefused instead of PlatformScopeError) |
| PW3 own canaries | copy with checker-chosen passwords/email/phone, 3 PW3 tests | 3 passed |
| PW4 never-attempted probe | qa/evidence/g11-port-wiring/probe_unattempted.py | api_error, request_budget, copy_lint, responsive ran with alice-only findings: FAIL |
| ruff | ruff check src tests scripts | pass |
| doctor | autotester doctor | 2 violations, SNAPSHOT staleness only |
| choke point | tests/test_actuator_chokepoint.py | red only on stages/platform_links.py (T-210), none in new files |

Mandatory evidence: complete. Full suite: not run (full-suite trigger: none).

## Cycle 1 (repair check, single checker, claude-sonnet-subagent)

Source: a08871ec (code fix 5d98051f; cycle-0 checked head d9c8f5ad). Repair diff d9c8f5ad..a08871ec: role_port_state.py (+RoleState.attempted, `_guard`, `_require_every_role`), role_session_port.py (`state.attempted = True` in `login`), tests/test_role_session_port_login.py (+1 test). Same environment as cycle 0.
Attribution: verdict qa/verdicts/g11-port-wiring.md (cycle 1); cycle-0 verdict kept at qa/verdicts/g11-port-wiring.r0-1.md.

| Check | Command / scope | Result |
|---|---|---|
| PW4 probe | `.venv/Scripts/python.exe -I qa/evidence/g11-port-wiring/probe_unattempted.py` (alice only logged in) | negative_input, state_after, api_error, request_budget, copy_lint, responsive all `errored RoleLoginFailed`; FINDINGS 0 (probe_unattempted.c1.out) |
| affected tests | `uv run pytest tests/test_role_session_port.py tests/test_role_session_port_login.py tests/test_actuator_chokepoint.py` | 19 passed, 1 failed (chokepoint red only on stages/platform_links.py, T-210, outside diff), 132 s (c1-pytest-summary.txt) |
| falsification PW4 | copy outside tree: `if any(st.attempted ...)` -> `if False` in `_guard`; the new test green before, red after on `'RoleNotSignedIn' == 'RoleLoginFailed'` (falsify_pw4_c1.red.txt) | red on the named assertion |
| RoleNotSignedIn greps | src + tests | one raise (`_guard`, use before any sign-in) and one test expecting it before any attempt (login test line 45), still green |
| ruff | `uv run ruff check src tests scripts` | All checks passed |

Mandatory evidence: complete. Full suite: not run (no trigger).
