# Checkpoint - land-t203-hosting (coordinator A, cycle 0) - claude-sonnet-subagent, verdict qa/verdicts/land-t203-hosting.md

Environment: Windows 11, Python 3.11.15, pytest 9.1.1 (-p no:xdist), worktree .venv; docker daemon down (npipe dockerDesktopLinuxEngine unreachable). Dependency lock: uv.lock of wave/land-t203-hosting (unchanged by the unit).
Code identity: fddbf469 (branch HEAD 05b8b7ba, manifest-only on top); base master 3a16616c; worktree clean (`git status --porcelain` empty) before and after.

| check | command / scope | collected | result |
|---|---|---|---|
| affected set | `uv --directory <wt> run pytest -p no:xdist` brief s.6 set + tests/test_ui_report.py test_ui_report_no_runs.py test_ui_sources.py | 297 | 297 passed, 190 s |
| lint | `ruff check src tests scripts`; `autotester doctor` | - | clean; clean |
| secret scan | `scripts/check_no_secrets.py docker .env.example` | 5 files | 0 leaks |
| own slot tests | scratch copy test_my_slots.py (threaded stress, crash/refuse/exit release, restart) | 4 | 4 passed; mutation -> 1 failed (named test) |
| HO17 | `>=` -> `>` in copy, tests/test_run_queue*.py | 24 | green 24; red 9 failed |
| HO2 | env.py `get(key)` -> `in os.environ`, tests/test_env_loading.py | 6 | green 6; red 1 failed |
| HO1 | drop `**/.env` from .dockerignore, tests/test_hosting_deploy.py | 10 | green 10; red 1 failed |
| ledger audit | prefix compare vs 3a16616c, 66f8b98c; collisions vs master (max AT-861) | 12 new rows | clean |
| persona walk | headless Chromium, 127.0.0.1:8123, root .work/checker-walk | - | see qa/evidence/browser-land-t203-hosting-2026-10-11-checker/ |

Build/service id for the browser check: uvicorn autotester.ui.app:app from the fddbf469 code tree. Data snapshot: scratch projects alpha/beta/gamma, seeded queue file.
Not run (named): full suite (owed to pre-push 6c; trigger: tests/conftest.py edited), Docker BUILD-HOST rows, Linux run, server rows.
