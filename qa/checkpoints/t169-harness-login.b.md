# Checkpoint t169-harness-login (coordinator B) - cycle 0, head 4ff07564, base 8956c9bc
Attribution: checker coordinator B (claude-sonnet-subagent), verdict qa/verdicts/t169-harness-login.b.md

## Completed checks (evidence identity)
- C1/C2/C3 tests: `uv run pytest tests/test_ui_settings.py tests/test_ui_env_labels.py tests/test_real_acceptance.py tests/test_acceptance_isolation.py tests/test_hosting_deploy.py` -> 50 passed. Code hashes (sha256 prefix): routes_settings.py 8bb3abfa5d96, core/env.py 701ad8e76ecd, run_real_acceptance.py bad73eab45e3, .env.example 87fbad7c6f4c, test_ui_settings.py a8545f9d574a, test_real_acceptance.py 872b712ccdc4, test_hosting_deploy.py f252d20dba80. Lock hash uv.lock d7ff32b5ab4a. Env: Windows 11, repo .venv python, TMP=D:/autoTesting/.work/tmp.
- Falsification C1/C2/C3 in 3 isolated copies of `git archive HEAD` (green-before 8 passed in copy, PYTHONPATH pinned to the copy and verified): M1 `_WRITE_ONLY = frozenset()` -> 2 failed; M2 `HARNESS_KEYS[:1]` in the script -> 2 failed (missing1, missing2); M3 password line deleted from .env.example -> 1 failed.
- Mode D: server 127.0.0.1:8791 (build = HEAD 4ff07564, data snapshot = empty temp root), evidence qa/evidence/browser-t169-harness-login-2026-10-21-checker-b/report.json.
- `ruff check src tests scripts` -> All checks passed; `autotester doctor` -> clean.
