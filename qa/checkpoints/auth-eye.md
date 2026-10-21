# Checkpoint: auth-eye (cycle 0, single checker)

Source: a15a21c3c34d1930ec32d3b08b8e60e5002d184e (HEAD 0b9d3abb adds only the manifest). Base 47496209. Blobs: src/autotester/ui/auth_view.py and tests/test_ui_auth_surface.py per `git diff 47496209 HEAD`. Environment: Windows 11, worktree .venv, Playwright Chromium, local uvicorn :8765 (temp AUTOTESTER_ROOT). No deploy id, no data snapshot.
Attribution: claude-sonnet-subagent checker, cycle 0, verdict qa/verdicts/auth-eye.md.

| Check | Command / scope | Result |
|---|---|---|
| affected tests | uv run pytest tests/test_ui_auth_surface.py tests/test_ui_auth_host_and_consent.py, 36 collected | 36 passed |
| ruff | ruff check src tests scripts | pass |
| doctor | autotester doctor | clean |
| CSP | grep -rniE "content-security or script-src" src | no match |
| Mode D | qa/evidence/browser-auth-eye-2026-10-21-checker/report.json, /auth/login and /auth/signup | toggle flips, no submit, value kept, keyboard ok |
| falsification C1 (bare input), C1+C3 (type=submit), C2 (no toggle), C3 (external script) | copy at .work/tmp/ae-chk-fals, `-k eye` | base 2 passed, each mutant 2 failed, restored 2 passed |

Mandatory evidence: complete. Full suite: not run (S unit, no full-suite trigger).
