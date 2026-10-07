# Manifest — t203-hosting (run queue, server settings, Docker/Ubuntu deploy, Windows notes)

## Status: ready-for-check

Goal task: T-203 · Branch: wave/t203-hosting · Base: origin/master 7782df41 (rebased in cycle 1; was 6f33ec8b) · Source: cycle 0 = 5eee9b6e (61585fc2 before the rebase), cycle 1 = the commit carrying this manifest
Policy-Version: proportional-verification/2026-10-06.6
Fix cycle: 1
Cycle checked before: 0 (FAIL, qa/verdicts/t203-hosting.md)
Tier: L, single checker (new module, schema, config, deploy files).
Executor: claude (maker build subagent). Contract: `qa/contracts/hosting.md` (HO1-HO38) plus D-071, D-072.
Cycle 0 summary: 24 files, +1609/-34 lines, 51 tests added (queue 20, UI queue 8, settings 11, config 5, deploy 7), affected set 213 passed, 15 mutations killed, 0 survived (one invalid mutant was replaced).

## Verification run (affected tests only, no full suite)

- `uv run pytest tests/test_ui_runs*.py tests/test_credential_run_approval.py tests/test_coverage_wiring.py tests/test_ui_credential_safety.py tests/test_ui_origin_guard.py tests/test_ui_healthz.py tests/test_ui.py tests/test_run_queue.py tests/test_ui_runs_queue.py tests/test_hosting_config.py tests/test_hosting_deploy.py tests/test_server_settings.py` = `213 passed, 1 warning`
- `uv run ruff check src tests scripts` = `All checks passed!`
- `uv run autotester doctor` = `doctor: clean` (docs/MAP.md regenerated with `autotester map`)
- Docker daemon is down on this machine: `docker build`, `compose up`, HTTPS and every BUILD-HOST / SERVER-GATED row are NOT verified. The compose file is checked structurally (parsed YAML) only.

## Fix cycle 1 (repair brief: AT-782..AT-786 blocking, AT-787 cheap)

Executor: claude (maker build subagent). Rebased onto origin/master 7782df41 with no conflicts.
Tier L unchanged. Not a docs-lane or test-lane merge: the fix touches product code and the
protected `tests/conftest.py` fixture, so the repair checker applies.

| Issue | Row | Fix (file) | Test (red before the fix, green after) |
|---|---|---|---|
| AT-782 | HO1 | test now asserts all six contract canaries plus the older six and `qa/evidence/`; matcher honours slash-containing directory rules (`tests/test_hosting_deploy.py`) | `test_dockerignore_keeps_secrets_and_project_state_out_of_the_image`, `test_the_canary_check_itself_notices_a_dropped_rule` |
| AT-783 | HO2, HO11 | `load_repo_env` treats an EMPTY inherited value as unset (`src/autotester/core/env.py` `load_repo_env`, one condition); DEPLOY.md step 3 says so. `.env.example` is still copied, since empty keys are now harmless | `tests/test_env_loading.py::test_an_empty_inherited_value_does_not_shadow_the_data_env_file` (red before: 1 failed) |
| AT-784 | HO11, HO13 | `docker/compose.prod.yml` `AUTOTESTER_DOMAIN` is `${AUTOTESTER_DOMAIN:-localhost}` (no `:?`); DEPLOY.md: removed the 6080 tunnel claim, Host allow-list described as shipping with AT-758 with `AUTOTESTER_ALLOWED_HOSTS` to be set, Origin guard described as it is (`ui/helpers.py _origin_allowed`), UFW-bypass note on step 8; `.env.example` comment corrected | `test_compose_needs_no_domain_unless_the_https_profile_is_used`, `test_deploy_guide_claims_only_what_the_compose_file_does` |
| AT-785 | HO18 | `ui/run_queue.py`: new `_persist()` logs a failed queue-file write and never raises, used by `submit`, `recover` and `_finish`, so every started entry is launched; `_work` catches `BaseException` (SystemExit, CancelledError), records `interrupted` with the exception class, re-raises | `tests/test_run_queue_resilience.py`: full-disk test (red before), exit and cancelled-task tests (red before) |
| AT-786 | HO38 | `tests/conftest.py _inline_run_queue`: runner crashes are re-raised out of the request; `RunRefused` stays quiet | `tests/test_ui_runs_queue.py::test_a_run_that_crashes_inside_the_suite_queue_fails_the_test_that_started_it`, `test_a_gate_refusal_inside_the_suite_queue_is_not_an_error`; the 3 named tests (`test_a_run_that_stays_on_known_routes_asks_for_nothing`, `test_a_run_on_a_project_with_no_flowspec_asks_for_nothing`, `test_ui_run_needs_no_human_approval_when_credentials_are_provisioned`) are in the affected set and green |
| AT-787 (cheap part) | HO3, HO17 | none in src: two shipped guards | `test_two_members_pressing_test_in_the_same_instant_cannot_both_claim_the_last_slot` (widened-window harness, `limit()` sleeps 50 ms inside the claim); `test_healthz_source_root_is_the_package_even_when_the_data_root_is_elsewhere` (fresh interpreter with `AUTOTESTER_ROOT` elsewhere) |

Design note (AT-785): a failed queue-file write is logged and scheduling carries on in memory,
rather than rolling the press back. A press never leaves an entry `running` without a worker; the
cost is that a restart right after such a failure forgets the unwritten state. The alternative
(roll back and raise) would also have stranded older waiters with no kicker.

### Verification (affected tests only, no full suite; policy .7)

- Removed or renamed names: none (`_save` stays, `_persist` is added; no symbol, field or key removed), so no `git grep` expansion applies.
- `uv run pytest tests/test_ui_runs*.py tests/test_credential_run_approval.py tests/test_coverage_wiring.py tests/test_ui_credential_safety.py tests/test_ui_origin_guard.py tests/test_ui_healthz.py tests/test_ui.py tests/test_run_queue.py tests/test_run_queue_resilience.py tests/test_ui_runs_queue.py tests/test_hosting_config.py tests/test_hosting_deploy.py tests/test_server_settings.py tests/test_env_loading.py` = `229 passed, 1 warning`
- Importers of the changed `core/env.py` and every test that drives `/run` or `run_queue` (18 files from `git grep`, plus `tests/test_ui_credential_exemption_scope.py` and `tests/test_ui_error_pages.py`, `-m "not harness"`) = `196 passed, 1 warning`
- `uv run ruff check src tests scripts` = `All checks passed!`
- `uv run autotester doctor` = `doctor: clean`
- Pre-fix red run of the new tests (5 failed, 31 passed over the 5 touched files) confirmed the tests reproduce AT-783, AT-785 and AT-786 before the code changed.
- Docker daemon still down on this host: BUILD-HOST rows stay BLOCKED-CAPABILITY. `docker compose config` was not run by me; the compose change is guarded by a parsed-text test only.

### Falsification, cycle 1 (each in its own throwaway copy of the tree, bound tree never touched)

| Criterion / issue | Mutation | Before | After |
|---|---|---|---|
| HO1 / AT-782 | delete `**/.env.*` from `.dockerignore` | 1 passed | 1 failed |
| HO2 / AT-783 | `os.environ.get(key)` back to `key in os.environ` | 1 passed | 1 failed |
| HO11,13 / AT-784 compose | `${AUTOTESTER_DOMAIN:?set it}` restored | 1 passed | 1 failed |
| HO11 / AT-784 guide | re-add `http://localhost:6080` to DEPLOY.md | 1 passed | 1 failed |
| HO18 / AT-785 save | `_persist` calls `_save()` bare | 1 passed | 1 failed |
| HO18 / AT-785 abort | abort recorded `DONE` again | 2 passed | 2 failed |
| HO38 / AT-786 | fixture's re-raise disabled (`if False:`) | 1 passed | 1 failed |
| HO17 / AT-787 lock | `self._lock = contextlib.nullcontext()` | 1 passed | 1 failed |
| HO3 / AT-787 healthz | `_SRC_ROOT = repo_root()/src/autotester` | 1 passed | 1 failed |

Runner: scratchpad `falsify.py` (copy per mutant, `PYTHONPATH=<copy>/src`, worktree interpreter).

### Left open on purpose

- AT-788 (T-203 rows still open: HO4, HO5, HO6 non-root, HO8, HO10 linux evidence, HO12, HO15 page, HO19 `project.run`, HO21 scoping, HO34-HO36): rows stay open, T-203 stays pending. Not this cycle's work.
- AT-789 (`qa/contracts/ui-run.md` RU1 wording): contract, never edited by the maker; the checker amends it.
- AT-787 remainder (Caddyfile redirect/TLS test, startup mode log, queue kick for a raised cap, Caddy body limit vs `server.env`, per-key `.env.example` comments): low, owned by later units.
- Not run by me: the browser check of the queue panel (no hosted instance; Docker down). The cycle 0 verdict asks for it at the repair cycle, so the checker must run it against a local `uvicorn` instance.
- Full suite: none run by the builder (policy .7). Trigger recorded for the checker: `full-suite trigger: tests/conftest.py edit` (already run once in cycle 0 on the earlier tree).

Metrics: start=2026-10-07T18:58:00+05:30 end=2026-10-07T19:10:00+05:30 wall_min=12 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=9 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6

(The cycle 0 manifest follows, unchanged except the header lines.)

## Coverage table (hosting.md)

| Row | Status | Evidence |
|---|---|---|
| HO1 `.dockerignore` canary | MET | `test_dockerignore_keeps_secrets_and_project_state_out_of_the_image` (small matcher, pathspec is not a dependency) |
| HO2 no inline secret in compose; scan of `docker/` | MET | `test_no_secret_value_anywhere_under_docker_or_in_the_dockerfile` |
| HO3 `AUTOTESTER_ROOT=/data`; `/healthz` reads the package path | MET (static) | `routes_live.package_root()`, `test_hosting_config.py`, compose `AUTOTESTER_ROOT: /data` |
| HO6 hardening | PARTIAL | restart, init, `no-new-privileges`, limits, log rotation, healthcheck present and tested. Non-root user NOT built |
| HO7 no published 8000/8010/6080/5900 | MET | app on `${AUTOTESTER_BIND:-127.0.0.1}:8000` only, noVNC `expose` only, x11vnc `-localhost`; `test_prod_compose_publishes_...` |
| HO9 `.env.example` keys only, drift test | MET | `test_env_example_documents_every_key_the_code_reads`, `test_env_example_holds_no_secret_looking_value` |
| HO10 cross-platform | MET | CRLF-safe `*.sh text eol=lf`, `entrypoint.sh` LF, `C:\` placeholder removed, no Windows-only path in `src/` found; guide Part B |
| HO11 `docker/DEPLOY.md` in the prescribed order | MET (doc) | Ubuntu steps 1-10 plus Windows Part B. Not executed on a server |
| HO14 Playwright tag equals `uv.lock` | MET | `test_dockerfile_playwright_tag_equals_the_locked_version` |
| HO15 `ServerSettings` | PARTIAL | schema, store, precedence (saved > env > default) built and tested. The ADMIN PAGE is NOT built (needs `settings.manage`, T-204) |
| HO16 persisted queue returns at once, 429 cap | MET | `test_ui_runs_queue.py`, `test_run_queue.py` (persistence, cap, thread non-blocking test) |
| HO17 cap and single flight | MET | `test_never_more_than_the_limit_and_never_two_of_one_project_running` and neighbours |
| HO18 slot released, restart recovery | MET | crash test, `interrupted` recovery test, corrupt-file test; `get_queue()` called in `_lifespan` |
| HO19 gates re-checked at start | PARTIAL | credentials, provider and consent re-checked via `_prepare_run` (`refused` with reason). The `project.run` permission recheck is NOT built (T-204) |
| HO20 shared RAM planning lock | MET | `planning()`/`grant()` tests plus `test_a_second_run_plans_against_the_ram_the_first_one_already_holds` |
| HO21 visibility | PARTIAL | queue panel on the report page. Per-user scoping NOT built (T-204) |
| HO37 doctor and ruff | MET | lines above |
| HO38 no regression | MET for the affected set | 213 passed; no full suite by instruction |
| HO4, HO5, HO8, HO12, HO13, HO34, HO35, HO36 | NOT BUILT | supervisord (HO5), noVNC gate and `/auth/check` (HO12, T-204; Caddy answers 503 for `/novnc/*` meanwhile), backup script (HO36, unit 5, server-gated), server rehearsals (HO8/34/35) |
| HO22-HO33 | NOT BUILT | Group 10 (schedule, mail, video intake). SMTP and timezone keys are placeholders in `.env.example` |

## Falsification (throwaway mutation in the working tree, restored after, test run each time)

| Claim | Mutation | Result |
|---|---|---|
| single flight | drop `e.project not in busy` | killed |
| cap | `>=` to `>` | killed |
| slot release | `finally` to `else` | killed |
| reason has class name only | `str(exc)` | killed |
| restart recovery | running stays queued | killed |
| waiting cap / 429 | cap check disabled | killed |
| shared RAM | other runs' grants ignored | killed |
| not queued | run executed inline in `trigger_run` | killed |
| saved beats env | saved-value branch removed | killed |
| HO1 | `**/.env` removed from `.dockerignore` | killed |
| HO7 | `6080:6080` published; app on `8000:8000` | both killed |
| HO6/HO3 | whole repo mounted instead of data dir | killed |
| HO14 | Dockerfile tag 1.61.0 | killed |
| HO9 | `AUTOTESTER_NOVNC_URL` removed from `.env.example` | killed |

Noted: my first "compose publishes noVNC" mutant was invalid (added an unknown key) and survived; it was replaced by the two real ones above.

## Deviations and things the checker should look at

1. **Guide path.** The brief said `docs/deploy-ubuntu.md`; the contract (HO11) says `docker/DEPLOY.md`. Contract followed (also avoids a CLAUDE.md router row for a docs file).
2. **Protected change `tests/conftest.py`**: one autouse fixture installs an in-memory queue whose spawner runs jobs inline, so about 12 existing synchronous UI run tests (62 `/run` calls) keep their meaning. The queue's own scheduling is tested separately with a manual spawner.
3. **`ui/app.py` hook** (declared exception): one line in `_lifespan`, `routes_runs.get_queue()`, plus 2 docstring lines folded into 1 to stay at 300 lines. T-125 also edits this file; expect a trivial merge.
4. **`ui/routes_runs.py`**: the `judge = LangChainFallbackProvider()` line (T-202's) is untouched, now inside `_prepare_run`. A textual conflict with T-202 is still possible because the surrounding function was split.
5. **One concept, one place (T-125).** The queue limits runs across the server; `stages/parallel_run.py` still owns per-run case width and `run_budget.py` the per-run budget. Neither file was edited. Only bridge: queue RAM grants feed the existing `plan_parallel_run(free_ram_mb=...)` seam. When T-125 lands, re-check that bridge.
6. **`ui/routes_report.py` is exactly 300 lines**; any T-125 addition there will need a split.
7. **Cap semantics:** at most 3 presses waiting per project; the 4th gets HTTP 429 (a chosen number, change `MAX_WAITING_PER_PROJECT`).
8. **Live view through Caddy is closed (503) until T-204**; on a trusted network use an SSH tunnel.
9. `QueueEntry.position` description says "derived, never stored" but the field is written as 0 in the file; harmless, noted.
10. Commit attribution uses Sonnet 5.5 (the model that built it), not the Opus 5.5 line in the brief.
11. Windows: guide Part B (NSSM or Task Scheduler, firewall, `AUTOTESTER_ALLOWED_HOSTS`, HTTPS via reverse proxy). Not tried on a Windows server.
