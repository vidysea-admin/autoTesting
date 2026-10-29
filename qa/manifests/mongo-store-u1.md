# Manifest - mongo-store-u1

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** `qa/contracts/mongo-store.md` (ACTIVE 2026-10-29), unit U1. **Criticality:** CRITICAL, dual check (D-100).
**Branch:** `feat/mongo-store-u1` from `qa/mongo-store-gate` (`1c072711`). Not merged, not pushed.
**Criteria judged by U1:** M1-M12 (the write fence), M47 (fake client, `cryptography` untouched, no `mongomock`). M11 is shared with U4/U9 (the marker lives in the guard, see M11 row).

## What changed (D-122 list only; no module outside U1's scope)

| File | Kind | One job |
|---|---|---|
| `pyproject.toml` | E | new table `[tool.autotester.store]`, `database = "autotester"` (D-121) |
| `src/autotester/schema/store_config.py` | N (115 lines max rule: 76) | `StoreConfig` (`extra="forbid"`, `frozen=True`), `StoreConfigError`, the once-per-process loader |
| `src/autotester/store/mongo_guard.py` | N (300 lines) | the only write door: `GuardedStore`, `GuardedCollection`, `InsertOnlyCollection`, `GuardedBucket` |
| `src/autotester/core/paths.py` | E in place | `code_root()` (:21); `repo_root()` default branch now returns it (:26-31). Four docstrings tightened to keep the file at 299 lines (cap 300), no code change |
| `src/autotester/browser/db.py` | E in place | `connect_read_only` refuses the store database (:44-45), before any client exists (M10) |
| `tests/fake_mongo.py` | N | hand-written `FakeMongoServer` / spy `FakeMongoClient` / `FakeDatabase` / `FakeCollection` / `FakeBucket` (M47) |
| `tests/test_store_config.py`, `test_mongo_guard.py`, `test_mongo_guard_surface.py`, `test_mongo_guard_scan.py`, `test_mongo_guard_spec.py` | N | the sabotage and surface tests |
| `qa/evidence/mongo-store-u1/mutations.json`, `mutation-run.txt` | N | M12 mutation spec (19 mutants) and its recorded run |
| `docs/MAP.md`, `docs/SNAPSHOT.md` | generated | `autotester map` / `autotester snapshot` (doctor `stale-generated`; SNAPSHOT also moved because it was already stale at the gate commit: its "Last decisions" list lagged D-118..D-122) |

## Criteria map (every row: code `file:line`, test, how it is falsified)

Guard = `src/autotester/store/mongo_guard.py`; Cfg = `src/autotester/schema/store_config.py`; tests in `tests/`.

| Crit | Code | Test (and mutant that kills it, `mutations.json`) |
|---|---|---|
| M1 one source | Cfg:29-43 model, Cfg:46-48 `default_config_path` = `code_root()/pyproject.toml`, Cfg:52-69 loader, Guard:233 `[cfg.database]` is the only handle; `pyproject.toml` `[tool.autotester.store]` | `test_store_config.py::test_environment_and_data_root_have_no_effect_on_the_name` (sets `AUTOTESTER_DB`, `AUTOTESTER_STORE_DATABASE`, `MONGODB_DB`, `MONGO_DB_NAME`, `AUTOTESTER_STORE_CONFIG`, `AUTOTESTER_ROOT=<no pyproject>`; spy sees `["autotester"]`); `::test_the_committed_file_names_autotester_and_the_loader_returns_it`; `::test_the_data_root_moves_repo_root_but_never_code_root`; `::test_the_config_is_read_once_per_process`. Mutants a (name from `os.environ`), m (config from the data root): KILLED |
| M2 no db parameter | Guard:226 ctor is `(uri, *, config_path, client_factory, bucket_factory)` | `test_mongo_guard.py::test_signatures_take_no_database_parameter` (`GuardedStore(uri,"x")` and `db`/`database`/`db_name` kwargs raise `TypeError`; `inspect.signature` over every function and method defined in the module, 20+ checked, private ones too). Other store modules (`mongo_backend`, `blobs`, `cli_store`) do not exist yet: their U4/U5a/U8 own re-running this over their surface |
| M3 one door | `browser/db.py:37-48` and Guard are the only driver sites | `test_mongo_guard_scan.py::test_exactly_two_files_touch_the_driver_and_they_are_the_allowed_two` (AST scan of `src/` + `scripts/`: `MongoClient(`, `get_database`, `get_default_database`, `list_database_names`, `drop_database`, `import pymongo/gridfs`, dynamic `import_module/__import__`, subscript on a client-bound name); `::test_the_scan_flags_a_third_file_with_each_pattern` (10 patterns x {src, scripts}) proves the scan is not vacuous; `::test_the_scan_leaves_innocent_code_alone` |
| M4(a,b,d) | Cfg:37-43 validators, Cfg:52-67 table-missing / unknown-key / unreadable -> `StoreConfigError` | `test_store_config.py::test_system_databases_are_refused_case_folded` (6), `::test_names_that_are_not_plain_identifiers_are_refused` (11 incl. 39 chars, non-ASCII, trailing newline, NUL), `::test_a_missing_table_missing_key_or_unknown_key_stops_startup` (9 incl. leftover `product_databases`), `::test_a_missing_config_file_stops_startup`, `::test_the_model_is_frozen_and_forbids_extra_keys`; every refusal uses a factory that fails the test if called (zero client). Mutants c, f, l: KILLED |
| M4(c) | Guard:230-231 (`urlsplit`, parse only, no DNS; scheme check Guard:203-208) | `test_mongo_guard.py::test_a_uri_path_naming_the_store_database_is_refused_before_any_client` (5 URIs: case variants, multi-host, `mongodb+srv`), `::test_a_non_mongodb_uri_is_refused_without_echoing_it`. Mutant d: KILLED |
| M4(e) | Guard:240-245 `_verify_identity` (`list_collection_names()` on the configured db only) | `::test_an_existing_unmarked_database_with_collections_is_somebody_elses` (spy saw only `autotester`; foreign collection untouched). Mutant e1: KILLED |
| M5 URI never selects a db | Guard:233 | `::test_the_spy_sees_exactly_the_configured_database_across_the_whole_workload` x4 URIs (`mongodb://h/`, `/scratch`, `/?authSource=admin`, multi-host with `/pathlynks`): whole workload (every collection and verb, GridFS put/get/delete, marker, ping, listing); asserts spy names == `{"autotester"}`, server-side op log db set == `{"autotester"}`, foreign `pathlynks`/`scratch`/`admin` documents unchanged and no extra database created. Mutant b: KILLED |
| M6 closed verb set | Guard:112-175 (classes), Guard:274-278 (`collection` allow-list), Guard:263-300 (`GuardedStore`) | `test_mongo_guard_surface.py::test_the_public_surface_is_exactly_the_frozen_list` (exact sets), `::test_no_forbidden_name_is_reachable_on_any_guarded_object` (`aggregate, command, bulk_write, watch, drop*, rename, with_options, get_database, client, database, db ...`), `::test_no_walk_of_the_guarded_objects_reaches_a_driver_or_fake_object` (recursive `__dict__`/public-attr walk; the driver handle lives in the module-private `_REGISTRY` Guard:45, not in any instance), `::test_the_walker_itself_finds_a_client_hidden_in_an_instance_dict`, `::test_collection_names_are_a_closed_set`, `::test_update_operators_are_limited_and_immutable_fields_are_untouchable`, `::test_writes_need_a_filter_and_delete_many_needs_a_project_or_key`, `::test_script_and_function_operators_are_refused_in_every_filter`, `::test_live_smoke_collection_needs_the_flag_and_no_ci` (M47 `t_` exception). Mutants g, i, j, k, q, r: KILLED |
| M7 insert-only | Guard:38 `INSERT_ONLY`, Guard:277 picks `InsertOnlyCollection` (class has no replace/update/delete at all) | `::test_insert_only_collections_have_no_replace_update_or_delete` x4 (also duplicate `_id` -> `StoreDuplicateKey`). Mutant h: KILLED |
| M9 URI never echoed | Guard:60-71 `_translate` (class name only, `from None`), Guard:234-235 ctor wraps driver errors, Guard:299 `__repr__` | `test_mongo_guard.py::test_a_failing_connect_never_echoes_the_uri`, `::test_a_failing_ping_and_write_never_echo_the_uri` (ping, insert, GridFS upload; checks `str`, `repr`, `traceback.format_exception`, stdout, stderr, log records), `::test_a_malformed_uri_rejected_by_the_driver_never_echoes_itself` (real pymongo parse error, no connection), `::test_identity_reports_the_configured_name_and_nothing_secret`, `test_mongo_guard_surface.py::test_the_store_holds_no_uri_after_construction`. Mutant p: KILLED. (`autotester store *` output and the UI 503 page belong to U8/U9) |
| M10 read side | `browser/db.py:44-45` | `test_mongo_guard_scan.py::test_the_read_side_refuses_the_store_database_before_creating_a_client` (`autotester`, `Autotester`, `AUTOTESTER`; no client constructed; other db still works). Mutant n: KILLED |
| M11 marker | Guard:240-272 (`_verify_identity`, `_check_marker`, `ensure_marker`, `_before_write` Guard:252-261: first write of any kind inserts `server_state/_id=marker {database, created_at, schema_version}`; insert-only; the marker is unreachable through the verbs) | `test_mongo_guard.py::test_a_marker_for_another_name_stops_startup`, `::test_an_empty_database_starts_without_writing_and_marks_on_first_write`, `::test_the_marker_is_never_rewritten_and_a_second_start_accepts_it`, `::test_the_marker_cannot_be_written_deleted_or_reached_by_a_broad_filter`, `::test_identity_reports...`. Mutants e2, o: KILLED. The `autotester store ping` CLI that prints the name is U8/U9 |
| M12 non-vacuous | `qa/evidence/mongo-store-u1/mutations.json` (19 mutants over Guard, Cfg, `browser/db.py`) | `qa/evidence/mongo-store-u1/mutation-run.txt`: **19/19 mutations killed** (the seven required: a env, b URI path, c forbidden name, d URI clash, e marker (e1 + e2), f `extra="forbid"`, g `aggregate` verb; plus h-r). `test_mongo_guard_spec.py` keeps each `old` string unique and each `kills` name a real test |
| M47 | `tests/fake_mongo.py` (hand-written, exactly the guard's verbs; no socket), Guard:42/:274-284 | `grep -c mongomock pyproject.toml uv.lock` -> `0` / `0`; `uv lock --check` -> `Resolved 335 packages`; no new dependency added by U1 (`cryptography` belongs to U11) |

Not in U1 (named so nothing is silently dropped): M8 (`Redactor.assert_clean` on writes: U4/U5a/U11/U12), M26 retry/503 (U9: the guard translates driver errors to `StoreUnavailable` once, no 3-try retry yet), the exclusive-create helper (U4: `insert_one` + `StoreDuplicateKey` is the primitive).

## Things the checker should look at (judgement calls and one contract divergence)

1. **M1 parenthetical not implemented, on purpose.** The contract says `repo_root()` "falls back to [`code_root()`] when `AUTOTESTER_ROOT` has no `pyproject.toml`". Done literally that moves the data root of every test that sets `AUTOTESTER_ROOT=<tmp dir>` (196 test references) and, on Cloud Run (`/data`, no `pyproject`), would silently move all state back into the container image. The sentence's own purpose (config resolved from the code tree) is met without it: `code_root()` is separate, only the config path uses it, and `repo_root()`'s default branch now calls it. Test: `test_the_data_root_moves_repo_root_but_never_code_root`. If the contract really wants the fallback, say so in the verdict and I will take the cycle.
2. **`COLLECTIONS` (Guard:27-37)** is the union of every collection named in design section 2 plus `run_traces`, `secrets`, `browser_sessions`, `server_state`, `bug_config`. M21 (every family present with its indexes) is U4's; U4 may extend this set, never U1's tests.
3. **`delete_many` is stricter than the contract text**: `p` or `k` must be a non-empty string or `{"$in": [non-empty strings]}`; `{"p": {"$exists": true}}`, `{"p": ""}`, `{"k": null}` are refused (they satisfy "filter contains p or k" and match everything). `server_state` writes must name one string `_id` so a broad filter cannot hit the marker. `$where`, `$function`, `$accumulator` are refused in any filter. U7's purge uses `p`.
4. **`config_path`, `client_factory`, `bucket_factory`** are keyword-only injection points (tests need other configs and the spy). None carries a database name. `config_path` can only point at a TOML file with the same one-key table.
5. **Driver handle storage**: `_REGISTRY` (Guard:45) holds the handle out of instance `__dict__` so the M6 walk is honest. Python cannot hide it from `gc` or a module-global read; the AST test (M3) is the fence against a second client, as the module says.
6. `StoreConfigError` is raised for everything refused at startup; building a `StoreConfig(...)` directly raises pydantic `ValidationError`. The contract allows either.
7. `docs/SNAPSHOT.md` was stale at the gate commit; regenerating it is unrelated to U1's logic but doctor demands it.
8. `mypy` (not in `qa/adapter.json` verify) on `store/mongo_guard.py` + `schema/store_config.py`: "Success: no issues found in 2 source files". On `browser/db.py` it reports 2 `no-any-return` errors at :32 and :35 in functions U1 did not touch (pre-existing; left alone). ruff and doctor are clean.

## Verify (run in `D:/autoTesting/.claude/worktrees/mongo-u1`, `PYTHONPATH=<worktree>/src`, shared venv; at most 2 files per pytest call)

```
pytest tests/test_store_config.py tests/test_mongo_guard.py          -> 56 passed
pytest tests/test_mongo_guard_surface.py tests/test_mongo_guard_scan.py -> 28 passed
pytest tests/test_mongo_guard_spec.py tests/test_db.py               -> 6 passed, 1 skipped   (test_db.py: 5 passed + its 1 pre-existing skip; unchanged by U1)
ruff check src tests scripts                                         -> All checks passed!
uv lock --check                                                      -> Resolved 335 packages in 1ms
autotester doctor                                                    -> 0 rule violations after docs/MAP.md and docs/SNAPSHOT.md are committed (before the commit it listed exactly the two stale-committed files)
python scripts/mutation_check.py qa/evidence/mongo-store-u1/mutations.json --repo .   -> 19/19 mutations killed
```

The full suite was NOT run (low-memory rule); only U1's five new test files and `test_db.py` (the one existing file that exercises `connect_read_only`). Files touched by U1 that other tests exercise: `core/paths.py` (docstrings and `code_root`), `browser/db.py` (`connect_read_only`); the checker may run the wider suite.
