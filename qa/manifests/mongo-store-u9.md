# Manifest - mongo-store-u9

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** `qa/contracts/mongo-store.md` (ACTIVE 2026-10-29), unit U9. **Criticality:** normal (U9 row has no dual mark; it touches the fail-closed path M26, so the checker may choose to dual it).
**Authority:** D-120, D-122, D-123. No `src/` module was added (D-122 list untouched); every edit is in place.
**Branch:** `feat/mongo-store-u9` = master (U1, U2, U6a, U3a, U5a) + `feat/mongo-store-u4` at `41400c24` (U4 fix cycle 1, merged at `23eb4af2`) + U3b (checked-PASS). Not merged to master, not pushed.
**Base SHA:** `23eb4af2`
**Code SHA:** `ee4889dc0a19cd43aa794f84a910f45e225c9d49` (the only code commit; this manifest is a second commit on top of it)
**Criteria judged by U9:** M9, M11, M13, M26, M27 (the U9 unit-table row). M11 is U4's marker; U9 only starts the store through it (see below).

## What changed

| File | Kind | One job / change |
|---|---|---|
| `src/autotester/core/env.py:218-231` | E in place | `MONGO_URI_ENV = "PATHLYNKS_MONGO_URI"` and `mongo_uri(root=None)`: non-blank process variable first, else the repo-root `.env` value read through `read_dotenv` (the one parser, literal, AT-1368). It reads the file itself because `load_repo_env` deliberately never exports a project-namespaced key such as `PATHLYNKS_*` (AU21). A test process with no `AUTOTESTER_ROOT` returns `""` instead of reading the real code-tree `.env`, so no unit test can reach a developer's live server. The value is returned only to the caller that opens the store; nothing here logs or prints it. |
| `src/autotester/store/mongo_backend.py:285-292` | E in place, **U4-owned file, single call site only** | `default_backend()` reads `mongo_uri()` instead of `os.environ.get("AUTOTESTER_MONGO_URI")`; the `URI_ENV` constant and the now-unused `import os` are removed; the redactor extra is keyed `PATHLYNKS_MONGO_URI`; the refusal text names `PATHLYNKS_MONGO_URI`. `repo_redactor` (U4 fix 1) is untouched. **Merge note for U4:** the diff is 5 hunks, all inside `default_backend` plus the import block and the removed constant; nothing else in that file moved. |
| `src/autotester/store/mongo_routes.py:123` (`StoreDown`), `:249-259` (`ping_backends`) | E in place | `StoreDown(RuntimeError)`: a **driver-free** base class, so `ui/` can map a store outage to 503 without importing `pymongo` in file mode (M13). `ping_backends(selection, open_backend)`: open and ping each chosen backend once, sorted; a `StoreDown` is re-raised as the same type with the areas on that backend appended (`from None`, so no chained context). |
| `src/autotester/store/mongo_guard.py:24,52` | E in place, U1 file | `StoreUnavailable` now derives from `StoreDown` (one import, one base class). Behaviour, verbs and messages unchanged. Still 300 lines (one docstring line was joined to pay for the import). |
| `src/autotester/store/filestore.py:159-161` | E in place | `validate_store_env()` is now `ping_backends(store_selection(), _backend)`: the same startup call as before, plus the ping. 298 lines. |
| `src/autotester/ui/error_pages.py:129-170` | E in place | `STORE_DOWN` fixed body; `_StoreDownGate`, a pure-ASGI middleware that turns a `StoreDown` into `503` (themed page for `Accept: text/html`, `{"detail": STORE_DOWN}` otherwise); `store_down_middleware()` list. Pure ASGI so the exception arrives unwrapped; once a response has started it re-raises. |
| `src/autotester/ui/app.py:70-72` | E in place | the gate is first in the middleware list, so it wraps the origin guard and the auth gate (a store error inside the auth gate is a 503, never an allowed request). The lifespan already calls `validate_store_env()` at `:64`; that call now pings. |
| `src/autotester/ui/routes_live.py:111-146` | E in place | `store_readiness()` -> `{"areas": {area: backend}, "reachable": bool}`; it never raises and never carries an exception text, URI or database name. `/healthz` adds it as `"store"` **for `settings.manage` callers only**; an anonymous caller still gets exactly `{"ok": true}` (AU16, pinned by the existing `test_healthz_unsigned_in_gets_only_ok`). Status stays 200 while the store is down. |
| `tests/test_store_startup_u9.py` | N (22 tests) | the U9 tests below |
| `tests/test_state_selection.py`, `tests/test_state_sweep_u3b.py`, `tests/test_state_wrappers.py` | E in place | the three tests that set U4's provisional `AUTOTESTER_MONGO_URI` now set `PATHLYNKS_MONGO_URI` (name only; no assertion changed). |
| `qa/evidence/mongo-store-u9/mutations.json`, `mutation-run.txt` | N | C7 mutation spec and its run |

## Criteria map

| Crit | Code | Test (falsifier it kills) |
|---|---|---|
| M27 startup check | `filestore.py:159-161` -> `mongo_routes.py:249-259`; `ui/app.py:64` (lifespan) | `test_startup_pings_the_server_once_per_backend` (one `command:ping` on the configured database), `test_a_mixed_selection_pings_only_the_chosen_backends`, `test_an_unreachable_server_stops_startup_naming_the_area_and_class_only` (names `runs` and `AutoReconnect`; canary password absent from exception text, full traceback, stdout, stderr and logs), `test_a_server_that_dies_after_connecting_is_caught_by_the_ping`, `test_the_server_refuses_to_start_when_the_store_is_down` (the real `_lifespan`). |
| M26 fail closed | `error_pages.py:129-170`, `app.py:70-72`, `routes_live.py:111-146` | `test_a_store_outage_in_a_route_is_a_503_with_a_fixed_body[json, html]` (status 503, body is `STORE_DOWN`, no canary, no `mongodb`), `test_an_outage_raised_below_the_router_is_a_503_too` (store error inside the auth gate -> 503, not allowed), `test_an_unrelated_error_is_not_turned_into_a_503`, `test_an_unreachable_server_...` (data-root tree hash before == after), `test_healthz_stays_200_while_the_store_is_down_and_leaks_nothing`, `test_healthz_stays_200_and_anonymous_learns_nothing_new`, `test_healthz_reports_a_reachable_mongo_area`, `test_healthz_in_file_mode_reports_every_area_as_file_without_a_reach_probe`, `test_healthz_with_the_store_unconfigured_reports_it_without_failing`. |
| M9 URI never echoed | `env.py:222-231` (returns, never logs); `mongo_routes.py:249-259` (fixed text); `error_pages.py:129` | `test_a_dotenv_uri_opens_the_store_and_is_never_echoed`, `test_the_old_name_is_ignored_and_the_new_one_is_named_in_the_refusal`, the canary checks in the M27/M26 rows. The guard's own M9 chain tests (`test_mongo_guard_chain.py`, `test_mongo_guard_uri.py`) pass unchanged. |
| M13 backend is configuration | `filestore.py:159-161` (file mode pings `FileBackend`, no driver); `error_pages.py` and `routes_live.py` import only `mongo_routes` (driver-free) | existing `test_state_selection.py::test_a_file_mode_workload_never_imports_a_database_driver` (fresh interpreter imports `autotester.cli` and `ui.app`, so it covers every new import) and `test_an_unknown_store_value_stops_startup`, both pass. |
| M11 marker | not changed (U4/U1); U9's startup constructs `GuardedStore` through `default_backend`, so `_verify_identity` runs on every start | existing `test_mongo_guard.py` marker tests pass; U9 adds no marker code. |
| URI name (D-120, M28, M36) | `env.py:218-231`, `mongo_backend.py:285-292` | `test_the_process_environment_wins_over_the_dotenv`, `test_a_blank_environment_value_counts_as_unset_and_a_missing_one_is_empty`, `test_a_value_is_read_literally_not_interpolated`, `test_a_test_process_never_reads_the_real_code_tree_dotenv`, `test_the_provisional_name_is_gone_from_the_source` (no `AUTOTESTER_MONGO_URI` anywhere under `src/`). |

## Things the checker should look at (judgement calls)

1. **`PATHLYNKS_MONGO_URI` has two readers.** `browser/db.py:6` and `tests/test_db.py:99` use the same name for the product's read-only DB-assertion URI (a project `SecretRef`, `db-assert.md`). Umesh's D-120 chat and M28/M36 name this variable for the store, so I used it as instructed; if both ever point at different servers on one machine they collide. `mongo_uri()` does not decide that; it is a naming question for Umesh, not a code defect. Flagging it, not changing it.
2. **`/healthz` detail is behind `settings.manage`.** M26 asks that "a readiness field reports the store". An unsigned container health probe still sees only `{"ok": true}` because the AU16 test pins that shape and I am not editing it. A readiness boolean for anonymous callers needs a contract decision (it would change AU16).
3. **`/healthz` pings Mongo for detail callers on every request** (5 s selection timeout when down). It is a sync route and only `settings.manage` callers reach it; the docker health check does not.
4. **`mongo_guard.py` and `mongo_routes.py` were touched** (U1 and U4 files) for the driver-free `StoreDown` base. Without it `ui/` would have to import `pymongo` to catch the outage, which breaks M13. The guard's public surface and tests are unchanged.
5. **Startup refuses on the first failing backend** and names every area on it; it does not continue to a second backend.
6. **Not done here (other units):** `docker/DEPLOY.md` env names and `entrypoint.sh` (U10, M28); auth store behaviour on outage (U6b: auth is still SQLite, `UNROUTED`); an in-progress run ending `interrupted` (needs the run-queue path of U7/U3c).
7. **Not run:** the full suite in one call (low-memory rule).

## Verify (run in `D:/autoTesting/.claude/worktrees/mongo-u9`, `PYTHONPATH=<worktree>/src`, `-o addopts=`, two files per call)

```
pytest tests/test_store_startup_u9.py tests/test_state_selection.py        -> 48 passed
pytest tests/test_state_sweep_u3b.py tests/test_state_wrappers.py          -> 90 passed
pytest tests/test_ui_healthz.py tests/test_mongo_guard_scan.py             -> 38 passed
pytest tests/test_ui_error_pages.py tests/test_ui_error_page_headers.py    -> 15 passed
pytest tests/test_mongo_guard.py tests/test_mongo_guard_surface.py         -> 40 passed
pytest tests/test_mongo_guard_chain.py tests/test_mongo_guard_spec.py      -> 14 passed
pytest tests/test_mongo_guard_uri.py tests/test_mongo_backend_fence.py     -> 88 passed
pytest tests/test_mongo_backend_layout.py tests/test_blobs_mongo.py        -> 81 passed
pytest tests/test_ui_auth_surface.py tests/test_ui_auth_policy_table.py    -> 25 passed
pytest tests/test_hosting_config.py tests/test_env_loading.py              -> 17 passed
pytest tests/test_env_dollar_warning.py tests/test_state_backend_contract.py -> 339 passed, 1 skipped
pytest tests/test_state_signatures.py tests/test_ui_auth_accounts.py       -> 27 passed
(final) pytest tests/test_store_startup_u9.py                               -> 22 passed
ruff check src tests scripts                                               -> All checks passed!
autotester doctor  (redirected to .work/doctor-u9.txt, exit 0)             -> doctor: clean (only the non-blocking D-087 advisories)
python scripts/mutation_check.py qa/evidence/mongo-store-u9/mutations.json --repo .  -> 17/17 mutations killed
```

Full mutation output: `qa/evidence/mongo-store-u9/mutation-run.txt`. Mutants cover: `.env` precedence, the test-process guard, the file read, the retired name, the backend ignoring `mongo_uri`, no ping, areas not named, ping per area, `validate_store_env` not pinging, outage not caught, 500 for 503, gate not installed, gate inside the auth gate, `StoreUnavailable` detached from `StoreDown`, readiness dropped, readiness never pinging, anonymous readiness leak. No live server and no network were used; no `.env` value was read into any output.
