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
