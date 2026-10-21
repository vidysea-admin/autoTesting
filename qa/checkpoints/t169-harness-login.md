# Checkpoint - t169-harness-login, coordinator A, cycle 0 (own evidence only)

Head 4ff07564 (code state a271a187; diff a271a187..HEAD is the manifest only). Base 8956c9bc. Env: Windows, worktree .venv python, uv; policy proportional-verification/2026-10-19.17.

| Check | Command / scope | Inputs | Result |
|---|---|---|---|
| C1 tests | uv run pytest tests/test_ui_settings.py tests/test_ui_env_labels.py (12) | routes_settings.py, env.py, test blobs at HEAD | 12 passed |
| C3 tests | uv run pytest tests/test_hosting_deploy.py (15) | .env.example | 15 passed |
| C2 tests | uv run pytest tests/test_real_acceptance.py tests/test_acceptance_isolation.py (23) | run_real_acceptance.py | 23 passed |
| extra candidates | pytest test_env_loading, test_ui_auth_own_origin, test_approval_signing, test_auth_deploy_files, test_ui_auth_policy_table, test_ui_auth_surface (125) | reference-hit list from shard_suite --candidates | 125 passed |
| falsification C1/C2/C3 | copies row1..3 (git archive HEAD subset), named tests green-before, mutated, red-after | qa/evidence/t169-harness-login-A/falsification.txt | 3/3 green then red |
| ruff / doctor | ruff check src tests scripts; autotester doctor | HEAD | clean |
| Mode D | uvicorn 127.0.0.1:8317, AUTOTESTER_ROOT temp, Playwright | HEAD | qa/evidence/browser-t169-harness-login-2026-10-21-checker/report.json |
| probe | dotenv_values vs parse_env round trip of set_env_value output | env.py, env_editor.py | 11 of 13 ok; `${HOME}` and literal backslash-n altered by dotenv |

Evidence dirs: qa/evidence/t169-harness-login-A/ and qa/evidence/browser-t169-harness-login-2026-10-21-checker/.
