# Manifest — land-t203-hosting (re-land of the T-203 hosting slice as a local deployment, D-081 item 4)

## Status: ready-for-check

**Contract:** qa/contracts/hosting.md (HO1-HO38; scope per qa/briefs/land-t203-hosting.md section 3)
**Goal task:** T-203
**Date:** 2026-10-11
**Fix cycle:** 0
Branch: wave/land-t203-hosting · Base: master 3a16616c · Source: wave/t203-hosting code of 5eee9b6e + 9a644597 (checker PASS at 66f8b98c, qa/verdicts/t203-hosting.md); qa-only commits not carried
Code commit under check: fddbf469 (ebf2cf3d plus a renumber of issue ids in text only; the manifest is the only later change)
Executor: claude-sonnet-subagent (maker build subagent)

**Dual check:** no (no security|auth|tenancy|prod-write trigger; the auth/tenancy half is T-204)
**Persona walk:** required (tester: presses Run/Test and sees queued, running and the cap message; developer/sub-admin: reads the queue panel on the report page). Not done by the builder (belongs to the checker). Anonymous on loopback, scratch data root under .work/, seed a queued and a running entry. Re-walk after T-204 (login redirect).

## What changed
- 27 code/test/config files re-landed from the slice: run queue (`ui/run_queue.py`, `ui/run_queue_view.py`, `schema/run_queue.py`); server settings (`schema/server_settings.py`, `store/server_settings.py`); `core/env.py` empty-value fix; `docker/` Caddyfile, DEPLOY.md, compose.prod.yml, entrypoint.sh; `.env.example`, `Dockerfile`, `.gitattributes`; routes_live/report/sources/app; 8 test files; `tests/conftest.py` `_inline_run_queue` fixture only.
- `src/autotester/ui/routes_runs.py` (conflict): master's `cat = catalog(...)` plumbing kept, the branch's queue-only request kept. `cat` is now computed in `_prepare_run` (a snapshot taken when the queued run starts, after every gate re-ran) and carried in `_Prepared.cat` to `_execute_and_record`, which passes it to `_execute_with_trace` and uses it for `catalog_runnable_counts`. Master's request-path `run_id`/`run_dir` lines are gone (the queue entry id is the run id; `paths.run_dir(run_id)` is built in the executor).
- `src/autotester/ui/routes_runs.py::trigger_run` and `src/autotester/ui/run_queue.py::RunQueue.submit`: `submit` gained an optional `run_id`; `trigger_run` mints `run-<ulid>` only after `_prepare_run` passed and hands it in. Reason: the master test `tests/test_ui_runs_serial_entry_order.py::test_real_trigger_undersized_grant_refuses_all_stored_costs_before_run` patches `routes_runs.ulid` to fail if a refused press mints an id; without this it errors with AttributeError. The test is untouched.
- `src/autotester/ui/app.py` stays at 300 lines; `routes_report.py` 299. No relocation was needed.
- `qa/issues.jsonl`: 12 rows appended, renumbered AT-782..AT-793 (AT-772 skipped, already on master) to **AT-862..AT-873**. The brief's AT-824..835 collides with `integrate/combined` (AT-830..AT-840 in use), so the next free block after AT-840 was taken. Old ids cited in code/test docstrings updated (AT-862 canaries, AT-863 empty env, AT-864 compose domain/DEPLOY, AT-865 slot release, AT-866 conftest re-raise, AT-867 low items). Statuses are copied from the PASS commit; the checker owns status.
- `docs/MAP.md` regenerated (`autotester map`); `docs/SNAPSHOT.md` regenerated (`autotester snapshot`), because master's committed copy was stale (lacked D-081) and `doctor` flags it.

## Verification scope
Policy-Version: proportional-verification/2026-10-10.9
Tier: L (concurrency: run_queue slot accounting and lock; config: compose.prod.yml, .env.example; env loading: core/env.py; protected-file edit: tests/conftest.py)
Base / checked state: master 3a16616c + ebf2cf3d, clean tree
Gate answers: qa/gates/t203-host-and-dns.md:13 `Answered (local-machine part only): 2026-10-10 - host locally for now - D-081`; line 11 (real server host and DNS) still open and blocks only HO34-HO36, not this unit. D-081 item 4. No Docker-dependent row is claimed.
Affected tests / full-suite trigger: the brief section 6 set plus tests/test_ui_report.py, tests/test_ui_report_no_runs.py, tests/test_ui_sources.py (routes_report and routes_sources changed). The full suite is owed by the checker.
Renumber note: after ebf2cf3d the coordinator found master's ledger runs to AT-861, so the 12 rows moved from AT-841..AT-852 to AT-862..AT-873 (same order, +21) in `qa/issues.jsonl`, the docstrings and comments of the files listed above, and this manifest. fddbf469 changes only ids in text: no behaviour and no issue status. The tagged Pre-check lines below ran on ebf2cf3d; only the untagged line below was re-run on fddbf469. Id map: AT-841..852 -> AT-862..873 (the earlier text above that says AT-841..AT-852 refers to the ids as renumbered in ebf2cf3d; read them +21).
Pre-check: fddbf469 uv run pytest -p no:xdist tests/test_env_loading.py tests/test_hosting_config.py tests/test_hosting_deploy.py tests/test_run_queue_resilience.py tests/test_ui_runs_queue.py -> 38 passed, 1 warning in 46.73s t=55 (the five test files whose docstrings changed; ruff and doctor also re-run on fddbf469: clean)
Pre-check[HO1]: ebf2cf3d uv run pytest tests/test_hosting_deploy.py -> 10 passed in 0.35s t=6 (LOCAL half; BUILD-HOST half BLOCKED-CAPABILITY, Docker daemon down)
Pre-check[HO2]: ebf2cf3d uv run pytest tests/test_env_loading.py -> 6 passed in 31.00s t=42 (LOCAL empty-env shadow and scan half; docker inspect/logs BLOCKED-CAPABILITY)
Pre-check[HO3]: ebf2cf3d uv run pytest tests/test_hosting_config.py tests/test_ui_healthz.py -> 13 passed, 1 warning t=13 (healthz package root only; container run BLOCKED-CAPABILITY)
Pre-check[HO7]: ebf2cf3d uv run pytest tests/test_hosting_deploy.py tests/test_hosting_config.py -> 18 passed, 1 warning t=10 (LOCAL overlay half; nmap/ss SERVER-GATED)
Pre-check[HO9]: ebf2cf3d uv run pytest tests/test_hosting_deploy.py tests/test_hosting_config.py -> 18 passed (same run as HO7) t=10
Pre-check[HO10]: ebf2cf3d uv run pytest tests/test_hosting_config.py tests/test_ui_healthz.py -> 13 passed t=13 (Windows half; the Linux half qa/evidence/t203-linux-run.md does not exist: PARTIAL, BLOCKED-CAPABILITY)
Pre-check[HO11]: ebf2cf3d uv run pytest tests/test_hosting_deploy.py tests/test_hosting_config.py -> 18 passed t=10 (guide-vs-code tests only; literal follow-through on Ubuntu is BLOCKED-CAPABILITY/SERVER-GATED: PARTIAL)
Pre-check[HO13]: ebf2cf3d uv run pytest tests/test_hosting_deploy.py tests/test_hosting_config.py -> 18 passed t=10 (config tests; redirect/TLS/HSTS and the startup mode log are SERVER-GATED; AT-867 notes COOKIE_SECURE/HOSTED are read nowhere in src yet: PARTIAL)
Pre-check[HO14]: ebf2cf3d uv run pytest tests/test_hosting_config.py tests/test_ui_healthz.py -> 13 passed t=13
Pre-check[HO15]: ebf2cf3d uv run pytest tests/test_server_settings.py -> 35 passed in 0.26s t=3 (model, store, validation, audit, precedence; the settings.manage page waits for T-204: PARTIAL, not claimed)
Pre-check[HO16]: ebf2cf3d uv run pytest tests/test_run_queue.py tests/test_run_queue_resilience.py tests/test_ui_runs_queue.py tests/test_ui_runs.py -> 24 passed in 1.03s (queue files) + 16 passed, 1 warning t=20 (UI files): the press returns the redirect before the run executed; persisted entry; restart recovery
Pre-check[HO17]: ebf2cf3d uv run pytest tests/test_run_queue.py tests/test_run_queue_resilience.py -> 24 passed in 1.03s t=6 (cap, per-project single flight, same-instant last-slot claim)
Pre-check[HO18]: ebf2cf3d uv run pytest tests/test_run_queue.py tests/test_run_queue_resilience.py -> 24 passed in 1.03s t=6 (normal finish, exception, SystemExit, CancelledError, full disk, interrupted on restart)
Pre-check[HO19]: ebf2cf3d uv run pytest tests/test_ui_runs_live_case_approval.py tests/test_credential_run_approval.py tests/test_coverage_wiring.py tests/test_ui_credential_safety.py tests/test_ui_runs_serial_entry_order.py -> 75 passed, 1 warning in 101.68s t=114 (the queued run re-checks credentials/provider/consent through the same `_prepare_run`; the `project.run` permission recheck needs T-204: PARTIAL)
Pre-check[HO20]: ebf2cf3d uv run pytest tests/test_run_queue.py tests/test_run_queue_resilience.py -> 24 passed in 1.03s t=6 (planning lock and grants under a faked RAM probe; real numbers at HO8, BLOCKED-CAPABILITY)
Pre-check[HO21]: ebf2cf3d uv run pytest tests/test_ui_runs_queue.py tests/test_ui_report.py tests/test_ui_report_no_runs.py -> 29 passed, 1 warning in 31.35s t=41 (requested_by and trigger recorded and shown; per-user scoping needs T-204: PARTIAL)
Pre-check[HO37]: ebf2cf3d uv run ruff check src tests scripts -> All checks passed!; uv run autotester doctor -> doctor: clean
Pre-check[HO38]: ebf2cf3d uv run pytest <brief section 6 set> tests/test_ui_report.py tests/test_ui_report_no_runs.py tests/test_ui_sources.py -> 297 passed, 1 warning in 67.93s t=80 (no existing assertion edited; the one failure of the first run, `test_real_trigger_undersized_grant_refuses_all_stored_costs_before_run`, was a real merge defect fixed in source, see What changed)
Metrics: unavailable

## Falsification (each in a throwaway copy of the tree under `.work/`, since deleted; the bound tree was never touched)
- Falsify[HO19 catalog plumbing]: in the copy, removed the `catalog_runnable_counts=...` kwarg from `_execute_and_record`'s `save_run` -> `tests/test_ui_runs_serial_entry_order.py` = `2 failed, 19 passed`; unmutated copy = `21 passed`.
- Falsify[HO16 id minted after the gates]: in the copy, minted `run-<ulid>` before `_prepare_run` in `trigger_run` -> `tests/test_ui_runs_serial_entry_order.py::test_real_trigger_undersized_grant_refuses_all_stored_costs_before_run` = `1 failed`; real tree passes.
- Not re-falsified (not changed by this unit): HO1/HO2/HO17/HO18 mutations were run by the cycle-1 checker (qa/verdicts/t203-hosting.md).

## Not claimed / still open on purpose
- BLOCKED-CAPABILITY (Docker daemon down): HO1 BUILD-HOST, HO2 inspect/logs, HO3 container, HO4, HO5, HO6, HO8, HO10 Linux run. SERVER-GATED: HO7 nmap, HO11 follow-through, HO12, HO13 TLS, HO34-HO36 (real host and DNS still open, qa/gates/t203-host-and-dns.md:11).
- Waiting for T-204: HO15 `settings.manage` page, HO19 `project.run` recheck, HO21 per-user scoping (all PARTIAL above).
- Open issues carried, status untouched: AT-867 (low tests), AT-868 (open rows list), AT-869 (qa/contracts/ui-run.md RU1 wording, the checker amends), AT-870 (restart after a failed queue write may re-run an entry), AT-871 (long reason overflows the queue panel), AT-872, AT-873.
- Persona walk and browser evidence: owed by the checker (no browser opened by the builder).
