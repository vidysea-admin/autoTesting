# Manifest - mongo-store-u5a

**Status:** ready-for-check
**Fix cycle:** 1
**Contract:** `qa/contracts/mongo-store.md` (ACTIVE 2026-10-29), unit U5a. **Criticality:** normal (the U5a row has no dual mark). Judged: M2, M5, M8, M23, M25 (the `BlobStore` half; the migrate-dry-run half of M25 is U8's, the call-site half of M24/M25 is U5b's).
**Authority:** D-120, D-121, D-122 (item 1 lists `store/blobs.py` as an approved new module), D-123 (no encryption; irrelevant here, blobs carry no secret door)
Round cap: normal unit, D-014 cap of 2 fix cycles applies.
**Branch:** `feat/mongo-store-u5a`, cut from master `0a2cbe45` (U1, U2, U6a merged). Not merged, not pushed.
**Base SHA:** `0a2cbe457630f0edcefbac96e59122864b8f6b27`
**Code SHA:** `de49a203ec90c94bd7d5b56701074009d93a3e16` (the only code commit; this manifest is a second commit on top of it)

## Cycle 1 changes (answers checker A FAIL cycle 0, `qa/verdicts/mongo-store-u5a.md`, 5cca3e06)

Line numbers in the cycle 0 sections below are for the cycle 0 file; `blobs.py` is now 284 lines (cap 300). Tests were written first and run red (42 failed, 2 of them the race tests) before the code changed.

| Finding | Fix | Test (red first, now green) | Mutants |
|---|---|---|---|
| 1 BLOCKING M25 case-sensitive segments, plus 4 (trailing dot/space) | `_folded` `blobs.py:57-59` (`casefold()` then `rstrip(". ")`) applied to **every** path part in `_vet :110`; the `NOT_BLOB_SEGMENTS`, `.env*` and `.xlsx` checks now run on the folded parts (`:111-114`) | `test_blobs.py::test_data_that_never_moves_is_refused_and_nothing_is_written` gained `.WORK/a`, `a/.Work/b`, `Profiles/x`, `CHUNKS/x`, `Crawl_Summaries/x`, `a/.BLOBMETA/x`, `x.xlsx.`, `x.xlsx `, `.env `, `a/.work./b`, `a/profiles /b`, each on `[file]` and `[mongo]` | a7 "no casefold" (7 cases), a7 "no trailing strip" (5 cases) |
| 2 WARNING M8 body gate | `_is_text :51-54`: media type parsed case-insensitively, parameters dropped; scanned = `text/*`, `TEXT_MEDIA :44-47` (json, xml, javascript, ecmascript, yaml, ndjson, x-www-form-urlencoded, graphql), any `+json`/`+xml`/`+yaml` suffix (incl. `image/svg+xml`); used at `:120` | `test_a_declared_secret_is_refused_everywhere_it_can_ride` gained 10 body types: `TEXT/PLAIN`, `Application/JSON`, `application/problem+json`, `image/svg+xml`, `application/javascript`, `application/yaml`, `application/json; charset=UTF-8`, `application/x-www-form-urlencoded`, `application/vnd.api+xml`, ` text/html` (leading space) | a4 (rewritten), a4b case, a4c suffix, a4d parameters, a4e javascript/yaml/form |
| 3 WARNING race: NoFile on a prune | `_prune :218-222` treats `StoreNotFound` on a revision delete as already pruned (`contextlib.suppress`; `mongo_guard` imported lazily) | `tests/blob_support.py::UniqueBucket.delete` now raises `NoFile` on a missing id, like pymongo (test side only; `fake_mongo.py` and `mongo_guard.py` untouched). `test_blobs_mongo.py::test_two_racing_puts_never_leave_zero_revisions` (was failing red) and new `test_a_delete_racing_a_delete_does_not_raise_for_a_revision_already_gone`; `test_a_missing_revision_is_still_an_error_for_the_bucket_itself` pins that the guard still reports a missing id. | b6 |

A mutation defect found again this cycle: `a4d` (parameters not stripped) first survived, because `text/plain; charset=...` stays textual through the `text/` prefix (an equivalent mutant). The plant is now `application/json; charset=UTF-8`, which only the parameter strip rescues. First-run logs are kept.

Fresh outputs (same rules: worktree, `-o addopts=`, 2 files per call, `env -u ANTHROPIC_BASE_URL`):

```
pytest tests/test_blobs.py tests/test_blobs_mongo.py                 -> 148 passed
pytest tests/test_blobs_cache.py tests/test_mongo_guard_scan.py      ->  39 passed
pytest tests/test_mongo_guard.py tests/test_mongo_guard_surface.py   ->  40 passed
ruff check src tests scripts                                         -> All checks passed!
autotester doctor (> .work/doctor-u5a-c1.txt, exit 0)                -> doctor: clean
mutations-a.json (28)  first run 27/28 (a4d survived), re-run 28/28 killed  (mutation-run-cycle1.txt, mutation-run-cycle1-a2.txt)
mutations-b.json (6)   6/6 killed                                    (mutation-run-cycle1.txt)
mutations-c.json (7)   7/7 killed                                    (mutation-run-cycle1.txt)
```
Total 41 mutants, all killed. `qa/evidence/mongo-store-u5a/mutations-a/b.json` were regenerated (a7 and a4 rewritten, a4b-e and b6 added).

Not changed, per the checker's INFO items: finding 5 (odd basenames `nul`, `foo:bar` raise raw OS errors inside the cache dir before anything escapes it) is not addressed here; no path escapes `.work/blob-cache/`.

## What changed

| File | Kind | One job |
|---|---|---|
| `src/autotester/store/blobs.py` (266 lines) | **N, on the D-122 list** | `BlobStore` Protocol `:68`; `FileBlobStore` `:128`; `MongoBlobStore` `:184`; `materialize` on both (`:177`, `:240`); `_vet` `:91` (every gate before any write); `_evict` `:255` (LRU); `repo_redactor` `:79`. No driver import (`mongo_guard` is imported under `TYPE_CHECKING` and lazily inside `_verified :224`); Mongo is reached only through `GuardedStore.bucket()`. |
| `docs/MAP.md` | generated | one row for the new module (`autotester map`); doctor's stale-generated check requires it |
| `tests/blob_support.py` | N (test helper) | `MongoRig` (guarded store over `FakeMongoServer`), `tree`, `put`, `clean` |
| `tests/test_blobs.py` | N | one contract suite over BOTH stores (`[file]`, `[mongo]`) |
| `tests/test_blobs_mongo.py` | N | GridFS-only behaviour: revisions, interrupted put, the fence, no-database-parameter, URI never echoed, fail-closed, file-mode import boundary |
| `tests/test_blobs_cache.py` | N | `materialize` and the LRU cache (M25) |
| `qa/evidence/mongo-store-u5a/` | N | `mutations-a/b/c.json`, `mutation-run.txt`, `mutation-run-b2.txt` |

No file owned by a sibling unit was edited (`mongo_guard.py`, `filestore.py`, `safe_names.py`, `mongo_backend.py`, `mongo_routes.py`, `stages/`, `sources/`, `core/env.py` are untouched; `git diff 0a2cbe45 --stat` shows only the files above). No new `src/` module besides the listed `blobs.py`. No caller was rewired (U5b).

## Criteria map

| Crit | Code | Test (falsifier it kills) |
|---|---|---|
| M2 no database name | no parameter named `db`/`database`/`db_name` anywhere in `blobs.py`; `MongoBlobStore(store, *, redactor, cache_dir, cache_cap_bytes)` `:188` | `test_blobs_mongo.py::test_no_public_blob_api_takes_a_database_name` (signature walk over every function, class `__init__` and public method of the module; `MongoBlobStore(None, "x")` and `database="x"` raise `TypeError`) |
| M3 (not judged, still must hold) | `blobs.py` has no `pymongo`/`gridfs` import and no `MongoClient` | existing `test_mongo_guard_scan.py` (39+ tests pass with `blobs.py` present) and `test_blobs_mongo.py::test_the_file_store_alone_never_imports_a_database_driver` (fresh interpreter: `pymongo`, `gridfs`, `bson` absent after importing `blobs` and running a file workload) |
| M5 URI database never used | the only handle is `store.bucket()` `:190` | `test_the_spy_sees_only_the_configured_database_across_the_blob_workload` x 3 URIs (`mongodb://h/`, `/scratch`, `/?authSource=admin`): put, changed put, get, stat, materialize, delete; spy `accessed` and `server.log` hold only `autotester`; a seeded foreign `scratch` database is unchanged. `test_the_bucket_lives_only_in_the_configured_database`. |
| M8 no secret in a stored blob | `_vet :91-110`: `Redactor.assert_clean` over key, kind, content_type and, for `text/*`/JSON/XML bodies, the decoded body; the redactor is a callable asked at **every** put (`:133`, `:191`); default `repo_redactor :79` = every repo `.env` value | `test_blobs.py::test_a_declared_secret_is_refused_everywhere_it_can_ride` (key, content_type, text body, json body; x file, mongo; nothing written, the error shows no value), `test_a_folded_or_encoded_secret_in_a_text_body_is_refused` (base64), `test_the_redactor_is_asked_at_every_put_so_a_later_secret_is_seen`, `test_the_default_redactor_reads_the_repo_env`, `test_binary_bytes_are_not_text_scanned...`; `test_blobs_mongo.py::test_a_secret_is_in_no_collection_or_chunk_of_the_whole_fake` (whole fake dumped), `test_the_uri_password_is_never_echoed_by_a_failing_blob_call` (M9 canary through failing put/get/materialize/delete). |
| M23 GridFS invariants | metadata `sha256,size,kind,masked,content_type,put_seq` `:113`, `:206-216`; unmasked screenshot refused `:101`; equal put no-op `:211`; upload first, prune only the revisions seen before `:214-215`; `delete` all revisions `:235-238` | `test_put_get_round_trip_records_sha_kind_masked_and_content_type`, `test_an_unmasked_screenshot_is_refused_and_nothing_is_written`, `test_an_unmasked_non_screenshot_is_accepted...`, `test_an_equal_put_is_a_no_op` (file: mtimes aged then compared; mongo: whole fake snapshot), `test_a_changed_put_replaces_the_content_and_leaves_exactly_one_revision`, `test_the_same_bytes_with_new_metadata_are_a_change_not_a_no_op`, `test_delete_removes_the_blob...`; Mongo: `..._uploads_the_new_revision_before_it_deletes_the_old` (observed op order), `test_an_upload_that_fails_leaves_the_old_revision_readable`, `test_a_put_interrupted_after_the_upload_leaves_both_and_reads_the_newest` (+ the retry heals), `test_two_racing_puts_never_leave_zero_revisions` (stale view), `test_delete_removes_every_revision_of_the_key_and_only_that_key`, `test_the_newest_revision_is_the_one_with_the_highest_put_seq...`. |
| M25 what does not move | `_vet :96-101`: any key segment in `{.work, profiles, chunks, crawl_summaries, .blobmeta}`, a `.env` / `.env.*` name, a `.xlsx` name (case-folded), kind `export` -> `BlobRefused`, nothing written; cache cap 512 MB LRU `:36`, `_evict :255` | `test_data_that_never_moves_is_refused_and_nothing_is_written` (11 keys x 2 stores incl. `.work/ceo-bench/answers.json`, `profiles/...`, `.../chunks/...`, `crawl_summaries`, `.env`, `.env.local`, `.xlsx`/`.XLSX`), `test_an_export_kind_is_refused`; `test_blobs_cache.py::test_the_cache_evicts_the_least_recently_used_past_its_cap`, `..._a_hit_refreshes_recency...`, `..._a_blob_bigger_than_the_cap_is_still_served`. |
| M17-adjacent (keys) | `safe_key` first in `_vet`, `_path`, `_revisions` | `test_an_unsafe_key_is_refused_before_any_write` (9 keys x 2 stores) |
| `materialize` contract (M24's reader side) | file: the real path `:177`; mongo: hash-verified copy in `<work_dir()>/blob-cache/<sha256>/<basename>` `:240-253`, extension kept | `test_materialize_writes_a_verified_copy_that_keeps_the_extension`, `..._cache_hit_does_not_download_again_and_a_tampered_copy_is_refetched`, `..._blob_whose_bytes_do_not_match_its_recorded_sha_is_corrupt` (get and materialize), `..._missing_key_does_not_create_a_cache`, `test_get_and_materialize_of_a_missing_key_raise_not_found` |
| M26 (store side, not judged) | every Mongo call goes through the guard, so `StoreUnavailable` | `test_with_the_server_down_nothing_is_created_on_disk` (tree identical before/after a failing put/get/stat/materialize) |

## Verification (worktree `D:/autoTesting/.claude/worktrees/mongo-u5a`, `-o addopts=`, 2 files per call, `env -u ANTHROPIC_BASE_URL`)

```
pytest tests/test_blobs.py tests/test_blobs_mongo.py                 -> 104 passed
pytest tests/test_blobs_cache.py tests/test_mongo_guard_scan.py      ->  39 passed
pytest tests/test_mongo_guard.py tests/test_mongo_guard_surface.py   ->  40 passed
pytest tests/test_mongo_guard_uri.py tests/test_mongo_guard_chain.py ->  76 passed
pytest tests/test_mongo_guard_spec.py tests/test_state_backend_contract.py -> 87 passed
ruff check src tests scripts                                         -> All checks passed!
autotester map                                                       -> docs/MAP.md regenerated (committed)
autotester doctor (redirected to .work/doctor-u5a.txt, exit 0)       -> doctor: clean
python scripts/mutation_check.py qa/evidence/mongo-store-u5a/mutations-a.json --repo . -> 23/23 mutations killed
python scripts/mutation_check.py qa/evidence/mongo-store-u5a/mutations-b.json --repo . -> 4/5 on first run, then 5/5 (below)
python scripts/mutation_check.py qa/evidence/mongo-store-u5a/mutations-c.json --repo . ->  7/7 mutations killed
```

Full outputs: `qa/evidence/mongo-store-u5a/mutation-run.txt` (first run of a, b, c; b shows `SURVIVED b1`) and `mutation-run-b2.txt` (b re-run after the fix).

**Mutation defect found and fixed this cycle (said plainly):** `b1` (prune before upload) survived `test_an_upload_that_fails_leaves_the_old_revision_readable`, because that test took the whole fake server down, so the failure hit the first listing call before any prune could run. The test now fails only `UniqueBucket.upload_from_stream` (the listing and reads work), so a prune-first implementation loses the old revision and is caught. Re-run: 5/5. The first-run log is kept, not overwritten.

**Order of work, said plainly:** `blobs.py` was drafted before its tests (not strict TDD); the tests were then written against the contract's falsifiers and 35 mutants (35/35 killed after the b1 fix) are the evidence they are not vacuous. 35 = 23 + 5 + 7.

**Not run:** the full suite in one invocation (low-memory rule); only the pairs above. Nothing was run against a live Mongo (no server; M47 fake only).

## Things the checker should look at (judgement calls and gaps)

1. **No listing / prefix delete on the Mongo side.** `GuardedBucket` (U1, `mongo_guard.py`) exposes `upload`, `download`, `revisions(filename)`, `delete(id)` and nothing that lists filenames, and the fake has no listing either. So `BlobStore` has no `keys(prefix)` / `delete_prefix`. Nothing in M2/M5/M8/M23/M25 needs one, so I did **not** touch `mongo_guard.py`. A run purge (U7) or a "which blobs exist under a run" sweep (U5b `sync_run_blobs`, U8 verify) will need a `GuardedBucket.list(prefix)`: that is a U1-file change, a decision for the orchestrator.
2. **`BlobInfo` is a frozen dataclass in `blobs.py`, not a Pydantic model in `schema/`.** A `schema/` file is not on the D-122 list, so I kept the return value local. It is an in-memory return type, never persisted (GridFS metadata is a plain dict). Doctor is clean. If the checker reads the "every domain shape is a Pydantic model in `schema/`" rule as covering it, the move is a one-line follow-up that needs a D-entry for the new file.
3. **Newest revision = highest `put_seq` (`time.time_ns()` in metadata), but `download()` reads GridFS's own newest (by `uploadDate`).** They differ only under cross-instance clock skew inside a put race; the sha check in `_verified :224` then raises `BlobCorrupt` instead of serving the wrong bytes. A put race leaves two revisions at worst, never zero (`test_two_racing_puts...`); the next put heals.
4. **M8 false-positive risk, inherited from `Redactor`:** `assert_clean` is floorless on the exact value, so a short `.env` value that happens to occur inside a blob KEY (a run id, a slug) refuses that put. Keys and content types are checked on purpose (M8 says blob metadata). Binary bodies are not text-scanned (a PNG is compressed bytes; a coincidence there is not a leak); only `text/*`, JSON, XML and NDJSON bodies are.
5. **The credential store's values (M34) are not in the default redactor yet** (U11 does not exist). `MongoBlobStore(..., redactor=callable)` is the seam: U11/U9 pass a callable that unions them, and the Mongo URI. The default is repo-root `.env` values only (`read_dotenv`, never printed). A test pins that the callable is asked at every put.
6. **File store keeps a sidecar** under `<root>/.blobmeta/<key>.json` (the file layout otherwise unchanged). `stat` ignores a sidecar whose sha no longer matches the bytes and reports `kind="unknown", masked=False` for a legacy file with no sidecar; it never claims a mask it cannot prove. `.blobmeta` is itself a refused key segment.
7. **`tests/fake_mongo.py::FakeBucket` reuses ids** (`f{len(docs)}`): upload, delete, upload collides (a false `DuplicateKey`). Not my file (shared; U4 may edit it), so `tests/blob_support.py::UniqueBucket` overrides `upload_from_stream` for these tests only. A real GridFS uses ObjectIds, so this is a fake defect, not a code one.
8. **`docs/MAP.md` will conflict** with the other makers' branches (each new module adds a row); regenerate with `autotester map` after merging.
9. **`materialize` returns a path whose file the LRU may later evict** while a slow reader still holds it (the just-served file is protected; older ones are not). Readers take a path, use it, and do not keep it across calls; U5b should call `materialize` at the read site, not cache the path.
10. Cache hit re-hashes the cached file every time (correctness over speed; videos are the cost). Revisit only if U5b measures it.
