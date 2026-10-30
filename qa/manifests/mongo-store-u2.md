# Manifest - mongo-store-u2

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** `qa/contracts/mongo-store.md` (ACTIVE 2026-10-29), unit U2. **Criticality:** normal (not dual; U2 row has no dual mark). Seam only: no Mongo code, no driver import.
**Authority:** D-120, D-121, D-122 (U2 edits `store/filestore.py` in place; no new `src/` module; D-122 file list untouched)
Round cap: normal unit, D-014 cap of 2 fix cycles applies.
**Branch:** `feat/mongo-store-u2` (master `0f89becc` merged first; the branch was fast-forwarded, no merge commit). Not merged to master, not pushed.
**Base SHA:** `0f89becc`
**Code SHA:** `42e1fae1874b369c7aafd071920572f6c52fab66` (the only code commit; this manifest is a second commit on top of it)
**Criteria judged by U2:** M13, M14, M15 (File + InMemory legs), M17, M19 (File + InMemory legs). Mongo legs of M15/M17/M19 belong to U4; `BACKEND_FACTORIES` in `tests/state_backends.py` is the one place U4 adds `"mongo"`.

## State of the worktree at pickup (said plainly)

The worktree held uncommitted U2 work from an earlier pass of this unit (filestore rewrite, the five new test files, `safe_key`, a startup call in `ui/app.py`, two mutation specs, a 136-pair regression log). I reviewed it, re-ran everything, fixed three mutation-spec defects found by `scripts/mutation_check.py` (below), and committed it. Nothing was discarded.

## What changed

| File | Kind | One job / change |
|---|---|---|
| `src/autotester/store/filestore.py` (300 lines, cap 300) | E in place | `StateBackend` Protocol `:40-56`; `FileBackend` `:81-168` (atomic `put` `:96`, sidecar-lock CAS `put_if` `:99`, `O_EXCL` `create_exclusive` `:108`, `keys` skips `.tmp-*` and `*.lock` `:133`, position-keeping `upsert_row` `:155`, bool `delete_row` `:161`); `store_selection` `:171` parses `AUTOTESTER_STORE` + `AUTOTESTER_STORE_AREAS`; `area_of` `:186`; `_backend` `:194` wires only `file` (`mongo` is a known name that raises "not wired"); `validate_store_env` `:200`; `_route` `:212` (path under `repo_root()` is a key, a path outside is a plain file). The ten public functions `write_text :232 write_bytes :238 write_json :244 read_json :249 read_jsonl :264 append_jsonl :270 delete_jsonl_row :277 upsert_jsonl :287` keep their signatures and now call the backend. No `pymongo`/`gridfs` import anywhere in the file. |
| `src/autotester/core/safe_names.py` | E in place | `safe_key(key, *, prefix=False)` `:76-86` (M17): refuses backslash, NUL, drive letter in any segment, `.`/`..`/empty segment (so a leading `/` and `//`), an empty key. |
| `src/autotester/ui/app.py` | E in place | `_lifespan` calls `validate_store_env()` (import `:24`, call `:64`): a typo in `AUTOTESTER_STORE` / `_AREAS` stops startup (M13). |
| `src/autotester/store/mongo_guard.py` | E in place (U1 follow-up, no U2 criterion) | the M9 chain fix both U1 checkers asked for: verdict chosen inside `except`, raised outside (`_translate` `:64-73`, constructor `:226-235`), so `__context__` carries no driver exception or URI; `_check_query` and one kwargs line condensed to keep the file at 300 lines. Behaviour otherwise identical; `test_mongo_guard.py`, `_surface.py`, `_spec.py` pass unchanged. |
| `tests/state_backends.py` | N (test helper) | `InMemoryBackend` (dict double) and `BACKEND_FACTORIES = {file, memory}` |
| `tests/test_state_backend_contract.py` | N | one parametrised suite over every backend (M15, M17, M19) |
| `tests/test_state_wrappers.py` | N | the public `Path` functions routed through each backend; model round trip per schema family (M15) |
| `tests/test_state_selection.py` | N | M13 incl. the cold-start import test and the server-start test |
| `tests/test_state_signatures.py` + `tests/state_signatures.json` | N | M14: frozen snapshot of every public `filestore` function and the public methods of `ProjectStore`, `CrawlStoreMixin`, `RunStoreMixin`, plus an importer-side check |
| `tests/test_mongo_guard_chain.py` | N | walks the full exception chain of every guard-raised error (U1 M9 follow-up) |
| `qa/evidence/mongo-store-u2/mutations.json`, `-b`, `-c`, `mutation-run.txt`, `regression-pairs.txt` | N | C7 mutation specs (37 mutants) and their run; the pairwise regression log |

No `src/` module was added. `docs/MAP.md` and `docs/SNAPSHOT.md` needed no regeneration (doctor was clean before and after the commit).

## Criteria map

| Crit | Code | Test (falsifier it kills) |
|---|---|---|
| M13 backend is configuration | `filestore.py:171-183` (`store_selection`: unset or blank = `file`; unknown backend or area raises `StoreSelectionError`), `:194-197` (`mongo` not wired), `:200-205` (`validate_store_env`), `ui/app.py:64` | `test_state_selection.py`: `test_unset_and_blank_mean_file_for_every_area`, `test_an_unknown_store_value_stops_startup` (6 values incl. `File`, `mongo,file`), `test_a_typo_in_the_areas_stops_startup` (7 forms), `test_a_typo_surfaces_on_first_use_not_only_at_startup` (no directory created), `test_the_server_refuses_to_start_on_a_typo` (real `_lifespan`), `test_a_file_mode_workload_never_imports_a_database_driver` (fresh interpreter imports `autotester.cli` + `ui.app`, runs a file workload, asserts no `pymongo`/`gridfs`/`bson` in `sys.modules`). The "full existing suite passes with no Mongo and no network" half: see Verification (regression pairs). |
| M14 signatures unchanged | the ten `filestore` functions above; `ProjectStore`/`CrawlStoreMixin`/`RunStoreMixin` untouched (`git diff` shows no edit under `store/` other than `filestore.py` and `mongo_guard.py`) | `test_state_signatures.py::test_every_filestore_function_keeps_its_signature` (one case per function, against `tests/state_signatures.json`), `::test_the_store_classes_keep_every_public_method_and_signature`, `::test_the_package_exports_are_unchanged`, `::test_every_name_the_importers_use_still_exists` (every `from ...filestore import` in `src/`, `scripts/`, `tests/`). Snapshot taken from baseline `4de46d52`. |
| M15 one contract suite | `FileBackend` + `tests/state_backends.py::InMemoryBackend` | `test_state_backend_contract.py` (ordered rows, idempotent add, position-keeping upsert, `delete_row` bool, `keys(prefix, suffix)` order, `replace_rows`, `delete_prefix`, bytes in / text out, `ping`) x `[file, memory]`; `test_state_wrappers.py::test_a_model_round_trips_equal_through_a_whole_document` and `..._through_rows`, one case per family in `FAMILIES` (project, source, case, flowspec, case_proposal, issue), each x `[file, memory]`. The Mongo leg is U4's: it adds one `BACKEND_FACTORIES` entry and `FAMILIES` rows for its route table. |
| M17 keys are safe | `core/safe_names.py:76-86`; `FileBackend._path :87` and `keys :134` call it; `InMemoryBackend` calls it on every method | `test_state_backend_contract.py::test_an_unsafe_key_is_refused_by_every_method_before_any_io` and `::test_an_unsafe_prefix_is_refused_by_the_listing_methods` over `UNSAFE` (`..`, `a/../b`, `/x`, `C:/x`, `c:x`, `a/C:/y`, `a\b`, `x\x00y`, `a//b`, `a/./b`, empty, `a/`...) x both backends, asserting no I/O happened; `test_state_wrappers.py::test_a_path_that_climbs_out_of_the_root_is_refused_before_any_write` |
| M19 exactly one winner | `FileBackend.create_exclusive :108` (`O_CREAT|O_EXCL`, empty claim removed on a failed write), `put_if :99` | `test_create_exclusive_has_exactly_one_winner_among_16_callers`, `test_create_exclusive_never_overwrites`, `test_put_if_has_one_winner_among_16_callers_holding_the_same_sha`, `test_put_if_a_stale_sha_loses_and_writes_nothing`, `test_put_if_on_a_missing_key_with_an_expected_sha_loses`, each x `[file, memory]`. The 200-repetition falsifier is not run in CI (16 threads x each test once); the checker may loop it. |

## Things the checker should look at (judgement calls)

1. **`delete_jsonl_row` keyed by a property is now refused** (`filestore.py:280-281`, `ValueError`): the original `getattr(item, key)` accepted a property, but the backend deletes by a stored field. Both in-tree callers use `id` (`project_store.py:123`, `:285`). Pinned by `test_a_delete_by_a_property_is_refused_not_silently_a_no_op`. `upsert_jsonl` keeps the property path (`:292-299`, matched on parsed rows, collection rewritten), pinned by `test_upsert_by_a_derived_key_replaces_in_place_and_appends_when_new`. This is the one place the old call contract is narrowed; say so in the verdict if you want it widened.
2. **Row-number in a malformed-row error counts non-blank rows** (`_parse_rows :222`, `rows()` drops blank lines), where the old code counted file lines including blanks. Message shape `path:N: ...` is unchanged; N can differ only on a file with blank lines.
3. **Byte equivalence with `AUTOTESTER_STORE` unset**: `put`/`append_row`/`replace_rows` use the same atomic temp+`os.replace`, same text-mode newline translation and same `a` append as before; `read_*` use `read_text(encoding="utf-8")`. I did not diff bytes of an old-vs-new run in a dedicated test; `test_state_wrappers.py` and the 136-pair regression below are the evidence.
4. **`file_lock` import** (`core/file_lock.py`, existing) backs `put_if`; no new module.
5. **`mongo_guard.py` was touched** although it is U1's file: it carries the M9 chain fix and was edited in place (no duplicate). The checker for U2 can ignore it for M13-M19; it is committed with U2 because the earlier pass fixed it here and `test_mongo_guard_chain.py` (5 tests, mutants c1-c5) guards it.
6. **Mutation run defects found and fixed this cycle** (`scripts/mutation_check.py`, first run: 21/22, 9/10, 4/5): `a19` was an equivalent mutant (`key.startswith("/")` was redundant with the empty-segment check); I removed the redundant clause from `safe_key` and retargeted `a19` at the empty-segment set. `b10` renamed a function, which breaks collection (exit 4, "not a kill"); it now renames a parameter. `c3` named a test that does not distinguish the mutant; it now names the one that does. Re-run: 22/22, 10/10, 5/5.
7. **Not run**: the full suite in one invocation (low-memory rule). The wider suite was run as 136 two-file pairs by the earlier pass (below) and four store-adjacent pairs again after the master merge.

## Verify (run in `D:/autoTesting/.claude/worktrees/mongo-u2`, `PYTHONPATH=<worktree>/src`, `-o addopts=`, at most 2 files per call)

```
pytest tests/test_state_backend_contract.py tests/test_state_selection.py -> 105 passed
pytest tests/test_state_signatures.py tests/test_state_wrappers.py        -> 52 passed
pytest tests/test_mongo_guard_chain.py tests/test_mongo_guard_spec.py     ->  8 passed
pytest tests/test_mongo_guard.py tests/test_mongo_guard_surface.py        -> 40 passed
pytest tests/test_store.py tests/test_store_crawl.py                      -> 28 passed
pytest tests/test_team_store.py tests/test_bug_store.py                   -> 79 passed
pytest tests/test_bug_store_concurrency.py tests/test_bug_store_hardening.py -> 31 passed
pytest tests/test_backup_restore.py tests/test_crawl_guidance_seam.py     -> 31 passed, 1 skipped
ruff check src tests scripts                                              -> All checks passed!
autotester doctor  (redirected to .work/doctor-u2b.txt, exit 0)           -> doctor: clean   (only the non-blocking D-087 decision-citation advisories)
python scripts/mutation_check.py qa/evidence/mongo-store-u2/mutations.json   --repo .  -> 22/22 mutations killed
python scripts/mutation_check.py qa/evidence/mongo-store-u2/mutations-b.json --repo .  -> 10/10 mutations killed
python scripts/mutation_check.py qa/evidence/mongo-store-u2/mutations-c.json --repo .  ->  5/5 mutations killed
```

Full outputs: `qa/evidence/mongo-store-u2/mutation-run.txt`.

**Wider regression** (`qa/evidence/mongo-store-u2/regression-pairs.txt`): 136 two-file pytest calls over the pre-merge tests, 136 lines with `passed`, none failed, ends `DONE`. That log predates the `0f89becc` merge and the last `safe_key` simplification, so it is supporting evidence only; the checker should re-run the importer-heavy files (everything that imports `filestore`, `ProjectStore`, `RunStoreMixin`) on its own terms. The `.venv` used is the worktree's own.
