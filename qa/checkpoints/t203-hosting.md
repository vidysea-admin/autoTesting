# Checkpoint: t203-hosting (cycle 0, single coordinator)

Verdict: qa/verdicts/t203-hosting.md (FAIL). Env: Windows 11 Home, worktree `.venv` (uv), tree = 47241bb8 (code 61585fc2), clean except this checkpoint, the verdict and `qa/issues.jsonl` rows AT-782..AT-789 (uncommitted: the shell was denied by the auto-mode classifier after the `ui-run.md` edit attempt).
Hashes: git HEAD 47241bb8; dependency lock `uv.lock` unchanged by the diff (Playwright 1.62.0). Docker: client 29.6.1 and Compose v5.2.0 only, daemon down.
Attribution: claude-sonnet-subagent checker (this file); sub-checker `ad3ebd6c28be70061` (conftest review, 3 experiments in copies expA/expB/expC); sub-checker `a404683fa562b6d73` (deploy files, 12 mutants in copies).

| Check | Command / scope | Result |
|---|---|---|
| Stress, cap and single flight | `probes/stress.py 40` (checker scratchpad), real threads, 12 submitters, 6 projects, 40 presses, measured inside the runner | 0 cap violations, 0 same-project violations, 0 stuck |
| Mutant cap `>=` to `>` | same harness, copy `m_nolimit` | 38/40 runs violated (p=0.95) |
| Mutant no lock | same harness, copy `m_nolock` | 0/40 (GIL hides it); 20 queue tests still pass |
| Race, widened window | `probes/race.py`, shipped vs `m_nolock` | shipped 10/10 exactly 1 running; mutant 10/10 two running |
| Mutants (one copy each, green before, red after) | strict removed; ceiling 65; single flight dropped; `finally` to `else`; memoised `_prepare_run`; reversed FIFO; INTERRUPTED to QUEUED | all 7 red on the named assertion; FIFO also red only on `test_admin_raising_the_limit...` (incidental) |
| Slot-release edge probes | `probes/edge.py` (copy-free, read-only import of the bound src) | E3 SystemExit recorded `done`; E4 unwritable queue path leaves entry `running`, no worker |
| conftest review | sub-checker: fixture removed (23 failed of 186), re-raise variant (186 passed), run-body-raises mutant (21 failed of 186; 3 old tests still pass) | fixture justified; 3 tests lose detection power |
| Deploy static | sub-checker: HO1-HO3, HO6, HO7, HO9-HO11, HO13, HO14, compose YAML | mutants killed M1-M3, M5-M9; survived M4, M7b, M8b, M12 |
| M4 re-run by me | copy `f_m4`, delete `**/.env.*` | green before, `1 passed` after (survives) |
| Compose by me | `docker compose -f docker/compose.prod.yml config`, copy `f_m4` | no domain: rc=1; `.env.example` as server.env: `ANTHROPIC_API_KEY: ""`, `AUTOTESTER_APPROVAL_KEY: ""` |
| Lint | `uv run ruff check src tests scripts` | All checks passed |
| Doctor | `uv run autotester doctor` | doctor: clean |
| Full suite | `uv run pytest -v` in the bound tree, output `scratchpad/suite2.log` | NOT COMPLETE at the time of writing: 27% reached, 1 failure (`tests/test_crawl_inventory_live.py` first test, pre-existing live-crawl file; run 1 ended at that file with `EXIT 1`). PIDs 9500, 29828, 38252 still running; the shell was denied so I could not stop them or read the end. The suite log is the only record |

Docker rows (build, compose up, HTTPS, supervision, restart persistence, `docker diff`, `docker history`): BLOCKED-CAPABILITY, not run.
Mode D browser check: not run (no hosted instance, shell denied).
Evidence reuse at the repair cycle: queue claims keep their results unless `ui/run_queue.py`, `schema/run_queue.py`, `store/server_settings.py` or `schema/server_settings.py` change; re-run the five FAILURES and `tests/test_hosting_deploy.py`, `tests/test_run_queue.py`, the 21 UI run test files and the conftest fixture.
