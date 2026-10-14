# scripts-env-bounds

Status: checked-PASS
Fix cycle: 1
Branch: wave/scripts-env-bounds

## Change
- scripts/run_real_acceptance.py: calls `load_repo_env(root)` (same loader as CLI); new `--max-actions` / `--wall-clock`; prints the crawl bounds; url_only seams use them. check_crawl_approval.py already loaded the env (no change).
- stages/real_acceptance.py: `crawl_bounds()` = min(request or default, covering approval); `preflight(..., bounds)` checks the CRAWL row covers those bounds and prefers newest grant; widest-wall-clock covering row chosen.
- tests/test_real_acceptance.py: bounds fit approval, 1800 s row selected, key only in .env (subprocess).

## Verify
pytest tests/test_real_acceptance.py tests/test_consent.py (47 pass), ruff clean, doctor clean.
