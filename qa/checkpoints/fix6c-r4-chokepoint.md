# Checkpoint: fix6c-r4-chokepoint (cycle 0, single checker)

Source: fae69506 (code 4c297ce8), base 58e13d6b. Relevant blobs: observe.py, role_probe.py, platform_links.py at 4c297ce8; tests unchanged. Environment: Windows 11, worktree .venv, Playwright Chromium. No build id, no data snapshot.
Attribution: claude-sonnet-subagent checker, verdict qa/verdicts/fix6c-r4-chokepoint.md.

| Check | Command / scope | Result |
|---|---|---|
| manifest set | pytest 7 files (chokepoint, network_assertions, observe, platform_links, role_session_port, role_session_port_login, multi_role_session) | 69 passed |
| importer set | pytest serial_scope, browser_unreadable, non-live test_explore*.py | 330 passed |
| ruff / doctor | browser/ + platform_links.py / autotester doctor | clean |
| falsification F1, F2 | isolated copy, appended violation per criterion | each red on its own test, restored green |
| diff read + probe | qa/evidence/fix6c-r4-chokepoint/probe_observer_hopwatch.py | guard identical, hooks released on detach |

Mandatory evidence: complete. Full suite: not run (no trigger).
