# Checkpoint - t125-catalog - coordinator A - cycle 4

Attribution: coordinator A checker (this file + qa/verdicts/t125-catalog.md). Environment: Windows 11, Python 3.11.15 (`.venv` of the bound worktree), uv.lock sha256 prefix 188681b3a300c36f, tests/conftest.py blob e5ff4b8402fd.
Code identity: HEAD 778b5f86815f301c5a8baf212c95bf3d0cbf7026, tree 1b7b1c37ab979982fd03c703cac3d7e2f7dc6c28. Blobs: stages/catalog.py 41283e8e40a6, ui/routes_runs.py 8cfb5b00f27e, ui/run_execution.py 21ff612e4eb7, stages/run_budget.py 0bfee7a2a1d4, ui/routes_catalog.py 9ed4f8bcecb5.
Worktree also carried uncommitted other-unit bookkeeping (.goal/goal.json, docs/DECISIONS.md, docs/FEATURES.jsonl, docs/SNAPSHOT.md); not part of the identity of T-125 code.

| Check | Command / scope | Result |
|---|---|---|
| Full suite | `uv run pytest` (PID 39436), bound worktree, collected 2299 outcomes | 3 failed, 2276 passed, 6 skipped, 14 xfailed in 3667.39s; all 3 baseline/load |
| Baseline re-runs | pristine `git archive bd2fe8f4`: test_redact_wrap_perf (x2), test_goal_contract_registration | same failures as the bound tree |
| Lint | `ruff check src tests scripts` | All checks passed |
| Doctor | `autotester doctor` (bound worktree, with uncommitted bookkeeping) | clean |
| Falsification | 22 isolated single-hunk mutants m01-m22 (`git archive HEAD` copy each) | all green-before / red-after / restored-green |
| Browser (headless Playwright library, seeded scratch root, build = worktree HEAD) | project page link click, catalog page, run page, unknown project | pass; 1 console error = intentional 404 |

Browser build id: uvicorn from worktree src at HEAD 778b5f86 (source unchanged since 52bba0b7). Data snapshot: scratch root `scratchpad/ui-root`, seeded by `scratchpad/seed_ui.py`.
Reuse rule: every field above unchanged required before reuse; a source change under src/ or tests/ voids the suite and mutant rows.

## Integration re-check (cycle 4-integration, 2026-10-07)

Attribution: coordinator A checker (qa/verdicts/t125-catalog.md; cycle-4 verdict archived as qa/verdicts/t125-catalog.r4-1.md). Environment: Windows 11, Python 3.11.15 (`.venv` of D:/autoTesting/.worktrees/t125-integrate), uv.lock sha256 prefix 0f25d574ae096863.
Code identity: HEAD 0cce70ac (contract-only commit on merge 6c0d57a1 / manifest 51a84edd; B's later 8992ced9 is qa-only), tree of src at 0cce70ac. Blobs: ui/routes_runs.py e58af87c0252, ui/run_execution.py 1fbecaf8bae7, stages/run_budget.py a4abf08f4a06 (== origin d4c369b0), stages/parallel_run.py 3c79a9d74320 (== origin), ui/app.py 40b1646921a6 (300 lines), tests/test_ui_runs_serial_entry_order.py 7b55a55278cd. Unchanged vs cycle-4 identity: stages/catalog.py 41283e8e40a6, ui/routes_catalog.py 9ed4f8bcecb5, ui/routes_report.py bef0ec2382, schema/catalog.py d6a16e6b4a, schema/run.py 444687afc2.

| Check | Command / scope | Result |
|---|---|---|
| Full suite | `uv run pytest` (uv PID 37804, python 43428), bound worktree, no -q/-x | 3 failed, 2621 passed, 5 skipped, 14 xfailed in 3038.99s; 2 baseline, 1 load-flake |
| Earlier suite attempt | uv PID 36192 / python 36600, started 18:12 | died silently, no summary, no result (BLOCKED-PROCESS cause: concurrent suites, ~3 GB free) |
| Load-flake confirm | `pytest tests/test_crawl_inventory_live.py` alone: clean d4c369b0 (PYTHONPATH copy) and HEAD | 2 passed in 357.95s / 2 passed in 278.73s |
| Lint / doctor | `ruff check src tests scripts`; `autotester doctor` | All checks passed; doctor: clean |
| Falsification | 17 mutants CT6(1)-(4), CN10, aggregate budget (sub-checker, copies cn-*) + 7 mutants of the protected test (copies tp-a..g) | all green-before / red-after |
| Browser (headless Playwright library, build = HEAD 0cce70ac archive) | project page link, catalog page, run page, unknown 404 | pass; 1 expected 404 console error |
| Kept by identity | CT1-CT5, CT7-CT9, AT-588 packs | inputs unchanged since the cycle-4 rows above |

Reuse rule: every field above unchanged required before reuse; a source change under src/ or tests/ voids the suite and mutant rows.
