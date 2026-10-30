# Manifest - mongo-store-u4

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** `qa/contracts/mongo-store.md` (ACTIVE 2026-10-29), unit U4. **Criticality:** dual (two independent checkers). Criteria judged: M2, M5, M6, M7, M8, M11, M15 (Mongo leg), M17, M18, M19, M21, M22.
**Authority:** D-120, D-121, D-122 (superseded by D-123), D-123. Two new `src/` modules, both on the D-122/D-123 unit table for U4: `store/mongo_backend.py`, `store/mongo_routes.py`. No other new `src/` file.
Round cap: dual unit, D-014 cap of 2 fix cycles applies.
**Branch:** `feat/mongo-store-u4`. Not merged to master, not pushed.
**Base SHA:** `0a2cbe45`
**Code SHA:** `05e58c2ca1b15d63c7faaa781bd24da983116452` (the only code commit; this manifest is a second commit on top of it)

## Scope additions taken after pickup

1. Dispatcher notes from U3b/U3c/U5a added five public `Path` functions in `store/filestore.py`, all routed through `_route`/`_holders` (table below).
2. `FakeBucket` file ids come from a unique counter (no reuse after a delete). Test: `tests/test_mongo_guard_chain.py::test_a_fake_bucket_never_reuses_a_file_id_after_a_delete :139`. `tests/blob_support.py` not touched.
3. `GuardedBucket.list(prefix)` and a prefix delete: **NOT done** (named follow-up F1 below).

## The FIVE new public functions (`src/autotester/store/filestore.py`, 300 lines, cap 300)

| Function | Line | Backend method it calls | Notes |
|---|---|---|---|
| `append_path(path, text: str or bytes)` | `:232` | `append_text` | File: open `a`; Memory/Mongo: atomic append on the document (compare-and-set loop on Mongo); a row-set key on Mongo gets one row per non-blank line |
| `delete_path(path, *, missing_ok=True)` | `:238` | `delete` | raises `FileNotFoundError` when absent and `missing_ok=False` |
| `exists_path(path)` | `:285` | `exists` / `is_dir` over `_holders` (`:275`) | true for a key or a directory that holds state |
| `list_children(path, *, suffix="")` | `:291` | `children` | sorted immediate names, merged across holders |
| `mtime_path(path)` | `:297` | `mtime` | `None` when absent |

Protocol additions (`store/mongo_routes.py:96` `StateBackend`): `children`, `is_dir`, `mtime`, `append_text`. `FileBackend`: `children :104`, `is_dir :110`, `mtime :113`, `append_text :123` (`append_row` now calls `append_text(key, text + "\n")`). `MongoBackend`: `mtime :162`, `children :174`, `is_dir :178`, `append_text :194`. `tests/state_backends.py::InMemoryBackend` implements all four.

Placement: `_atomic_write` moved to `core/file_lock.py` (`atomic_write`, a D-122-listed module); `RUN_AUX_FILES` and `repo_redactor` live in `store/mongo_routes.py`. `run_store.py` re-exports `RUN_AUX_FILES` from there.

## What changed

| File | Kind | One job / change |
|---|---|---|
| `src/autotester/store/mongo_backend.py` (299) | N | `MongoBackend :53` implements `StateBackend` over `GuardedStore` only (no driver import, no database name). `ensure_indexes :58`, size/secret `_guard :63`, `put_if :118`, `create_exclusive :126`, `delete :146`, `delete_prefix :181`, rows `:188-247`, KG split read/write `_build :252` `_generation :267` `_text_of :273` `_drop_graph :281`, `default_backend :288`. |
| `src/autotester/store/mongo_routes.py` (268) | N | Pure data: `AREAS :25`, `UNROUTED :28`, `KG_*`, route table `_RULES :48`, `route :150`, `area_of :162`, `under :178`, `repo_redactor :185`, `text_sha :192`, `store_selection :226`, `split_graph :244`, `join_graph :263`; error types `:119-131`. |
| `src/autotester/store/filestore.py` | E in place | the four Protocol methods on `FileBackend`, the five Path functions above, `_backend :148` wires `mongo`. |
| `src/autotester/core/safe_names.py` | E in place | W1: `safe_key :88` + `_bad_segment :80` + `_device :76` harden key checks (Windows device names and aliases). |
| `src/autotester/core/file_lock.py` | E in place | `atomic_write` (moved from filestore, unchanged behaviour). |
| `src/autotester/store/run_store.py` | E in place | imports `RUN_AUX_FILES` from `mongo_routes`. |
| `src/autotester/store/mongo_guard.py` | E in place (W3) | `InsertOnlyCollection.find :121-125`: the cursor is materialised inside `_translate`, so a cursor dying mid-iteration is translated and carries no chain; `_translate :64` verdict typed. |
| `tests/fake_mongo.py` | E in place | `FakeBucket` unique counter; `$regex`; re-entrant atomic section. |
| `tests/state_backends.py` | E in place | `BACKEND_FACTORIES = {file, memory, mongo}` (the one place, `:142`), `InMemoryBackend` gains the four methods. |
| `tests/test_state_backend_contract.py`, `tests/test_state_wrappers.py`, `tests/test_state_selection.py`, `tests/test_mongo_guard_chain.py` | E in place | contract suite on 3 backends; wrappers incl. the five Path functions; selection incl. mongo; W3/W4 chain tests. |
| `tests/test_mongo_backend_fence.py`, `tests/test_mongo_backend_layout.py`, `tests/test_safe_key.py` | N | M2/M5-M8/M11 fence; layout, indexes, KG split, byte-for-byte (M18, M21, M22); W1. |
| `docs/MAP.md` | regenerated | `autotester map` (two new modules). |
| `qa/evidence/mongo-store-u4/` | N | mutation specs a-f, runs, `verify.txt`. |

## Criteria map

| Crit | Code | Test |
|---|---|---|
| M2 no database name | `MongoBackend.__init__ :54` takes only `(store, redactor=None)`; no public parameter named `db`/`database` | `test_mongo_backend_fence.py::test_no_public_parameter_of_the_backend_is_a_database_name :48`, `::test_a_whole_workload_touches_only_the_configured_database :85` (3 URIs; only the configured database is accessed) |
| M5/M6 no driver, no client | `mongo_backend.py`/`mongo_routes.py` import neither `pymongo`, `gridfs` nor `bson` | `::test_neither_module_imports_a_driver_or_opens_a_client :69` (AST walk) |
| M7 insert-only | `MongoBackend._mutable :84`, `delete_prefix :181`, `append_text :194` | `::test_an_insert_only_row_set_takes_appends_and_refuses_every_edit :103`, `::test_an_insert_only_document_is_written_once_and_never_changed :117`, `::test_append_text_to_an_insert_only_family_adds_rows_but_never_edits_a_document :130`, `::test_delete_prefix_over_an_insert_only_family_deletes_nothing :140` |
| M8 secret refused, never quoted | `_guard :63`, `repo_redactor` `mongo_routes.py:185` | `::test_a_known_secret_is_refused_everywhere_and_never_quoted :160` (all 8 write paths incl. `append_text`, key scanned, no `__cause__`/`__context__`), `::test_a_secret_hidden_by_a_row_that_is_not_the_first_is_still_refused :174`, `::test_the_default_redactor_reads_the_repo_env_without_echoing_it :181` (tmp `.env`, not the repo's) |
| M11 identity marker | marker doc in `server_state` is not a state key | `::test_the_identity_marker_is_not_a_state_document_and_is_never_rewritten :196` |
| M15 one contract suite, Mongo leg | `BACKEND_FACTORIES["mongo"]` `tests/state_backends.py:142` | `test_state_backend_contract.py` x `[file, memory, mongo]` (379 passed incl. wrappers, 1 skipped = the File 16-way append race, see JC3) |
| M17 safe keys | `safe_names.py:88`; backend calls it first on every method | `test_state_backend_contract.py::test_an_unsafe_prefix_is_refused_by_the_listing_methods :265`, `::test_an_unsafe_directory_key_is_refused_by_children_and_is_dir :274`, `test_safe_key.py :24 :30 :40 :46` |
| M18 size limit | `_guard :63-66` (`MAX_DOC_BYTES` 12 MiB) and KG split above 4 MiB | `test_mongo_backend_layout.py::test_a_body_over_12_mb_is_refused_and_nothing_is_stored :59`, `::test_a_persona_over_4_mb_splits_into_kg_rows_and_reads_back_equal :209`, `::test_a_rewrite_never_mixes_generations_and_a_shrink_or_delete_drops_the_rows :222`, `::test_a_persona_that_is_not_a_graph_document_stays_whole_however_large :236` |
| M19 exactly one winner | `put_if :118`, `create_exclusive :126` (`_claim :132`) | contract suite `test_create_exclusive_has_exactly_one_winner_among_16_callers`, `test_put_if_...` x mongo; `test_mongo_backend_fence.py::test_a_document_append_that_loses_the_compare_and_set_retries_and_keeps_both :214` (deterministic interleaving) |
| M21 layout per family | route table `mongo_routes.py:48`; `ensure_indexes :58` | `test_mongo_backend_layout.py::test_each_key_family_lands_in_the_collection_the_table_names :167`, `::test_indexes_exist_for_every_routed_collection_and_a_second_pass_changes_nothing :100`, `::test_every_collection_of_the_closed_set_is_routed_or_owned_by_a_later_unit :112`, `::test_a_row_set_key_refuses_a_document_call_and_the_reverse :183` |
| M22 verbatim text | `_doc :45`, `get :93` return stored text unchanged | `::test_a_body_comes_back_byte_for_byte :43`, `::test_rows_with_dotted_and_dollar_keys_round_trip_and_match_on_a_field :50`, `::test_concurrent_appends_never_share_a_seq_and_keep_one_order :76`, `::test_upsert_keeps_the_seq_of_the_row_it_replaces :91` |
| M13 (selection, no default change) | `filestore.py:148` `_backend`, `mongo_routes.py:226` `store_selection` | `test_state_selection.py::test_mongo_without_a_uri_stops_startup_and_names_the_variable :74`, `::test_mongo_with_a_uri_is_wired_to_the_mongo_backend :84`, `::test_a_file_mode_workload_never_imports_a_database_driver :153` |

## U2 checker-B warnings closed

| W | Closure | Test |
|---|---|---|
| W1 `safe_key` hardening | `core/safe_names.py:76-99` | `tests/test_safe_key.py :24 :30 :40 :46` |
| W2 `delete_prefix` empty prefix / segment boundary | `MongoBackend.delete_prefix :181` and the File/Memory backends | `test_state_backend_contract.py::test_delete_prefix_refuses_an_empty_prefix_and_matches_on_a_segment_boundary :112` x 3 backends |
| W3 lazy cursor in `_translate` | `mongo_guard.py:121-125` | `test_mongo_guard_chain.py::test_a_lazy_cursor_that_dies_mid_iteration_is_translated_and_clean :105` |
| W4 invalid-URI chain | guard already correct | `test_mongo_guard_chain.py::test_the_invalid_uri_branch_raises_one_fixed_error_with_no_chain :126` |
| W5 `area_of` routes approvals/queue; auth/credentials/blobs refused on mongo | `mongo_routes.py:25-28,162` | `test_state_selection.py::test_an_area_that_routes_nothing_is_refused_on_mongo_but_allowed_on_file :103`, `::test_the_approvals_and_queue_families_have_an_area_so_they_can_be_flipped :113`, `::test_area_of_routes_the_documented_prefixes :145` |

## Judgement calls (the checkers should look at these)

1. **`StateBackend` grew four methods** (`children`, `is_dir`, `mtime`, `append_text`). Anything else that implements the Protocol outside this repo's tests must add them.
2. **`append_text` on a Mongo row-set key splits into rows** (one per non-blank line); on a document key it is a compare-and-set loop (`16 * APPEND_RETRIES` tries, then `StoreUnavailable`). On an insert-only document it raises `StoreImmutable`.
3. **File append is not atomic across 16 concurrent writers on Windows** ("a" mode interleaves). The 16-way no-lost-append test is skipped for `file` (the 1 skip); Memory and Mongo promise atomic append. U3b/U3c callers that rely on atomic append on File should keep their lock.
4. **`auth`, `credentials`, `blobs` areas are refused on `mongo`** with a named error (their stores belong to U6, U11, U5a).
5. **Persona KG split** is keyed `key@generation`, read only via the stored generation, and old generations are dropped on a rewrite, shrink or delete.
6. **Provisional env name** `AUTOTESTER_MONGO_URI` for the connection string (the contract does not name one); a missing value stops startup.
7. **`mongo_guard.py` edited** (W3, two lines) although it is U1's file; the dispatcher gave U4 ownership of it.
8. **Mutation specs a, b, c, e ran before the final scope additions** (code was moved and compacted afterwards); every `old` string was re-verified to occur exactly once on the final tree, and d and f were re-run on the final tree (`mutation-run-final.txt`). A checker may re-run a, b, c, e.
9. **Mutant f4 first survived** (the fake serialises threads, so the 16-caller test cannot see a lost compare-and-set); replaced by a deterministic interleaving test, now killed (`mutation-run-f.txt` keeps the surviving first run).

## Follow-ups (named, not done)

- **F1: `GuardedBucket.list(prefix)` and a prefix delete.** Not done: `store/mongo_guard.py` is at the 300-line cap, so the addition needs a placement ruling (a second guard module is not on the D-122/D-123 table). The fake and tests are ready to follow once placement is decided. U5a keeps its own bookkeeping meanwhile.
- **F2:** a live-server run of the Mongo leg is out of scope (fake only, per the brief).

## Verify (run in `D:/autoTesting/.claude/worktrees/mongo-u4`, `PYTHONPATH=<worktree>/src`, `-o addopts=`, at most 2 files per call)

```
pytest tests/test_state_backend_contract.py tests/test_state_wrappers.py      -> 379 passed, 1 skipped
pytest tests/test_mongo_backend_fence.py tests/test_mongo_backend_layout.py   -> 79 passed
pytest tests/test_safe_key.py tests/test_state_selection.py                   -> 93 passed
pytest tests/test_state_signatures.py tests/test_mongo_guard_chain.py         -> 25 passed
pytest tests/test_mongo_guard.py tests/test_mongo_guard_surface.py            -> 40 passed
pytest tests/test_mongo_guard_scan.py tests/test_mongo_guard_spec.py          -> 35 passed
pytest tests/test_store.py tests/test_store_crawl.py                          -> 28 passed
pytest tests/test_team_store.py tests/test_bug_store.py                       -> 79 passed
pytest tests/test_bug_store_concurrency.py tests/test_bug_store_hardening.py  -> 31 passed
pytest tests/test_backup_restore.py tests/test_crawl_guidance_seam.py         -> 31 passed, 1 skipped
ruff check src tests scripts                                                  -> All checks passed!
autotester doctor (redirected to .work/doctor-u4.txt, run after the code commit) -> exit 0, "doctor: clean" (only non-blocking D-087 advisories)
scripts/mutation_check.py mutations-a.json -> 18/18   -b -> 3/3   -c -> 4/4   -d -> 7/7   -e -> 2/2   -f -> 8/8 killed
```

Outputs: `qa/evidence/mongo-store-u4/verify.txt` (its doctor line used a wrong command and shows a failure; the real doctor result above is from `.work/doctor-u4.txt`, exit 0), `mutation-run.txt` (e, c, d, a, b), `mutation-run-final.txt` (f, d on the final tree), `mutation-run-f.txt` (first f run, f4 survived). Not run: the full suite in one invocation (low-memory rule).
