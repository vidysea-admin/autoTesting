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

# Cycle 1 (repair checker, single coordinator, 2026-10-07)

Tree: branch wave/t203-hosting, code 9a644597 (fix on 6be74d89, base 7782df41 = origin/master, so no merge diff). Env: Windows 11, worktree `.venv` (uv), Docker client only, daemon down. Free RAM 4.1 GB at suite start (machine shared with ~12 other pytest runs).
Attribution: claude-sonnet-subagent repair checker (this file); browser sub-checker a8f22cf47f5b1683d (findings in qa/evidence/browser-t203-hosting-2026-10-07-checker/); falsification runner scratchpad `falsify.py` (one copy per mutant, worktree interpreter, PYTHONPATH=<copy>/src).

| Check | Command / scope | Result |
|---|---|---|
| Affected tests | manifest set (22 files incl. test_run_queue_resilience, test_env_loading), bound tree | 228 passed, 1 skipped (live Chromium RAM gate, AT-576), 63-78 s, twice |
| Importers of the fix | 36 test files from `git grep "load_repo_env|core.env|run_queue|routes_runs|/run\b"`, `-m "not harness"` | 266 passed, 1 skipped |
| HO1 falsification | drop each of 7 `.dockerignore` rules (`**/.env`, `**/.env.*`, `**/projects/`, `**/profiles/`, `.work/`, `qa/evidence/`, `.git/`), copy per mutant | all 7: green before, `1 failed` after |
| HO2 | `or os.environ.get(key)` back to `key in os.environ` | `1 passed` -> `1 failed`; also fresh-interpreter probe: `ANTHROPIC_API_KEY=` and `AUTOTESTER_APPROVAL_KEY=` empty + `.env` with real values loads both, an explicit non-empty `GEMINI_API_KEY` still wins |
| HO11/HO13 compose | real `docker compose -f docker/compose.prod.yml config` in a scratch copy with `.env.example` as server.env: no domain rc=0, https profile rc=0 (`AUTOTESTER_DOMAIN: localhost`), 8000 published on 127.0.0.1, 6080 only `expose`; mutant `:?` restored rc=1 `required variable AUTOTESTER_DOMAIN is missing` | MET; test mutant `1 passed` -> `1 failed` |
| HO11/HO13 guide | re-add `http://localhost:6080`; "ships with AT-758" -> "is enforced by AT-758" | each `1 passed` -> `1 failed`. Claims read against code: `ui/helpers.py:195 _origin_allowed` reads `AUTOTESTER_ALLOWED_ORIGINS`; `ALLOWED_HOSTS` appears nowhere in src (also not on origin/master 7782df41); 6080 absent from `ports` |
| HO18 | mutants `_persist` bare `_save()`, abort recorded DONE, abort swallowed (no re-raise), `finally` to `else` | each red on its named test (2 params or 1) |
| HO18 probes | scratchpad probe785.py: real thread spawner with SystemExit, CancelledError, KeyboardInterrupt | each entry `interrupted` with class name, next waiter `done`, abort propagates |
| HO18 restart after failed write | same probe, writes fail after alpha running + beta queued are saved | in memory both done; after restart alpha `interrupted`, beta re-launched (AT-790, low). Once any later write succeeds the file is whole (probe B) |
| HO38 | crash injected in `_run_queued`, shipped conftest | the 3 named tests: 3 passed before, `3 failed` after. Same crash with the fixture's re-raise disabled: `3 passed` (the old weakness). New fixture test with re-raise disabled: red |
| Browser | sub-checker, Playwright, own tab, 127.0.0.1:8767, scratch data root, seeded queue, no run started | see verdict LIVE-BROWSER |
| Boot recovery | my own uvicorn (killed by its listening PID) on a scratch root with a `running` row, no request sent | file rewritten as `interrupted` at startup (lifespan `get_queue()`), so the sub-checker's "lazy on first report visit" remark is wrong |
| Lint, doctor | `uv run ruff check src tests scripts`, `uv run autotester doctor` | All checks passed; doctor: clean |
| Full suite | `uv run pytest --deselect tests/test_crawl_inventory_live.py`, suite lock acquired 19:29:29, log scratchpad/suite_c1.log | see verdict |
| Full suite (resume 1) | `uv run pytest --deselect tests/test_crawl_inventory_live.py`, bound tree 9a644597, log scratchpad/suite_c1.log, lock 19:29:29-20:04:36 | EXIT 1: `1 failed, 2707 passed, 5 skipped, 2 deselected, 14 xfailed in 2093.70s`; the one failure is `test_redact_wrap_perf` (3.24 s vs 3 s bound under host load), passes alone on the bound tree (6.2 s) and twice on base 7782df41 (6.8 s, 8.1 s); unit touches no redact code; AT-793 |
Final: PASS (slice), verdict qa/verdicts/t203-hosting.md addendum; no merge, no push (coordinator order).
