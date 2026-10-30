# Verdict - mongo-store-u4 (checker B, fresh, independent)

**Unit:** mongo-store U4 (dual). **Cycle checked:** 0. **Code SHA:** `05e58c2c`, manifest SHA `1366d1fb`, base `0a2cbe45`.
**Verdict: PASS** (with 1 defect to fix in place before U7/U9 and 5 warnings; none is a fence or insert-only break). Read-only toward `src/` and `tests/`; I never read another checker's verdict.

## Commands I ran (worktree `D:/autoTesting/.claude/worktrees/mongo-u4`, `PYTHONPATH=<worktree>/src`, `-o addopts=`, 2 files per call)

| Command | Result |
|---|---|
| `ruff check src tests scripts` | All checks passed! |
| pytest test_state_backend_contract.py test_state_wrappers.py | 379 passed, 1 skipped |
| pytest test_mongo_backend_fence.py test_mongo_backend_layout.py | 79 passed |
| pytest test_safe_key.py test_state_selection.py | 93 passed |
| pytest test_state_signatures.py test_mongo_guard_chain.py | 25 passed |
| pytest test_mongo_guard.py test_mongo_guard_surface.py | 40 passed |
| pytest test_mongo_guard_scan.py test_mongo_guard_spec.py | 35 passed |
| pytest test_store.py test_store_crawl.py | 28 passed |
| pytest test_team_store.py test_bug_store.py | 79 passed |
| `autotester doctor > .work/doctor-b.txt` | exit 0, last line `doctor: clean` |
| `scripts/mutation_check.py` mutations-e / b / c / d / f / a | 2/2, 3/3, 4/4, 7/7, 8/8, 18/18 killed (42 of 42, all re-run by me on the final tree, so the "a/b/c/e ran on an earlier tree" flag is closed) |
| `wc -l` | filestore.py 300, mongo_guard.py 300, mongo_backend.py 299, mongo_routes.py 268 (cap 300); doctor enforces function length: clean |
| `git diff --stat 0a2cbe45..HEAD` | 28 files; the only new `src/` files are `store/mongo_backend.py` and `store/mongo_routes.py` (both on the D-122/D-123 U4 row); other `src/` changes are in-place edits (`core/file_lock.py`, `core/safe_names.py`, `store/filestore.py`, `store/mongo_guard.py` 2 lines, `store/run_store.py`); no contract, CLAUDE.md or DECISIONS change |

Existing-test edits (`git diff ... | grep '^-'`) are deliberate: "mongo not wired" tests replaced by the wired-mongo ones, `StateBackend` import moved, `UNSAFE` list extended. No assertion was weakened; `test_state_signatures.py` is untouched.

My own adversarial probes (scratch scripts outside the repo, over the in-repo fake):

- **M2/M5/driver:** no parameter named `db`/`database`/`db_name` on any function or method in `mongo_backend.py`/`mongo_routes.py`; neither file imports `pymongo`/`gridfs`/`bson` (the word appears in prose only); the whole workload touched only `['autotester']` (URIs `h/`, `h/scratch`, `h/?authSource=admin`; `h/autotester` and `h/AutoTester` refuse with `StoreConfigError`, zero client access).
- **M13:** with `AUTOTESTER_STORE` unset, a file-mode write/exists/list/append workload leaves `pymongo` and `gridfs` out of `sys.modules`. `AUTOTESTER_STORE=redis|Mongo`, `AREAS=typo=mongo|runs=postgres|runs` all raise `StoreSelectionError`; `auth=mongo` is refused by name.
- **M7:** for `approvals`, `approval_revocations` (rows) and `bug_events`, `delivery_records` (documents): put, put_if, delete, upsert_row, delete_row, replace_rows, append_text-on-document all raise `StoreImmutable`; append and `create_exclusive` work; an equal re-put is a no-op, a different one raises; `delete_prefix("projects/a")` over a mix raises before any delete.
- **M8:** `Redactor({"K": SECRET})`: put, put with the secret in the key, rows put, put_if, create_exclusive, append_text, append_row, upsert_row, replace_rows (secret in the 2nd row), put(bytes) all raise `StoreSecretRefused`; `__cause__`/`__context__` None; a dump of the whole fake database contains no secret.
- **M17/W1:** `safe_key` refuses `a/b.`, `a/b `, `a/CON`, `con.txt`, `Nul.json`, `COM1`, `com1.x`, `LPT9.z`, `COM` + superscript 1, `aux `, `CONIN$`, `CON .txt`, `CON.`, `prn.tar.gz`, `a/c:d`, `b:s`, `C:/x`, `/a`, `a//b`, `./`, `../`, backslash, empty; as a prefix `a/CON`, `a/b.`, `a/CONFIG` pass (may be unfinished) and `a/CON/` refuses. Closed.
- **W2:** `delete_prefix("")` and `("/")` raise `UnsafeName`; `delete_prefix("projects/a")` deleted `projects/a/x.json` and `projects/a/sub/y.json` only and left `projects/a.json` and `projects/ab/x.json`. Closed.
- **W3:** a fake cursor dying mid-iteration with a canary URI in the driver message: `keys`, `rows` (guarded and insert-only collection), `get`, `mtime`, `append_row`, `children` all raise a bare `StoreUnavailable`, chain `['StoreUnavailable']`, no canary in traceback/str/repr. Closed (`mongo_guard.py:125`).
- **W4:** `mongodb://u:CANARY@h:notaport/`, `MONGODB://...`, `CANARY` alone: one fixed `StoreConfigError`, chain length 1, no canary, client never touched. Closed.
- **W5:** `area_of` gives `approvals` for `approvals.jsonl` and `approval_revocations.jsonl`, `queue` for `.work/run_queue.json` and `.work/team/delivery/x`, `runs` for `trace.jsonl`; `auth`/`credentials`/`blobs` per-area flips are refused by name (`mongo_routes.py:25-28,234`). Closed.
- **M18:** exactly 12 MiB stored (warning logged above 4 MiB); 12 MiB + 1, and 6 Mi + 1 two-byte characters, raise `StoreDocTooLarge`, nothing stored.

## Criteria

| Criterion | Result |
|---|---|
| M2 no API takes a db name | PASS (signature scan above + `test_no_public_parameter_of_the_backend_is_a_database_name`) |
| M5 only the configured database | PASS |
| M6 closed verb set | PASS (backend uses only `GuardedStore.collection` and `GuardedCollection` verbs; `delete_many` always carries `k`) |
| M7 insert-only | PASS (probe above; `mongo_backend.py:84-88,139-144,181-186`) |
| M8 secret refused | PASS, with warnings W1, W2 |
| M11 identity marker | PASS (`get("marker")` is None; marker never rewritten); see W5 for a key named `marker` |
| M15 one suite, three backends | PASS for the listed behaviours (379 passed); defect D1 lies outside the suite |
| M17 safe keys | PASS |
| M18 encoding, size, seq | PASS (verbatim text, 12 MB cap, `(k,seq)` unique, retry on duplicate) |
| M19 exactly one winner | PASS (16-caller tests on all three backends; deterministic CAS-interleave test) |
| M21 collections and indexes | PASS (`ensure_indexes` twice changes nothing; routed set is a subset of `COLLECTIONS`) |
| M22 KG split | PASS (generation-keyed rows, old generations dropped); see W3 |
| `AUTOTESTER_STORE` unset stays file | PASS |

## Findings

**D1 (defect; fix in place before U7/U9; not a falsifier of a listed criterion).** `MongoBackend.delete` on a `.jsonl` key that routes to `server_state` raises `ValueError: the store identity marker is not writable` instead of deleting. Cause: `mongo_backend.py:150` calls `delete_many({"k": key})`, and `mongo_guard.py::_before_write` refuses any `server_state` filter that does not name a string `_id`. Reproduced with `append_row(".work/x.jsonl")` then `delete(".work/x.jsonl")`; `delete_prefix("d")` over `d/x.jsonl` fails the same way, while File and Memory succeed. Reachable families: the `**` catch-all (`mongo_routes.py:90`), for example `docs/FEATURES.jsonl`. No `src/` caller deletes such a key today and the contract suite never deletes a row key, so no test sees it. Fix: delete row by row with `delete_one({"_id": ...})` as `replace_rows` does (`:246-247`), and add a contract case "delete a `.jsonl` key, then `delete_prefix` over it" on all three backends.

**W1 (warning, M8).** `mongo_backend.py:76` writes `refusing to store {key!r}`; when the secret is in the key the message quotes it (probe: `put("projects/a/<SECRET>.json")` gives a message containing the secret). `test_mongo_backend_fence.py:171` asserts only that it raises. Do not quote the key in that message.

**W2 (warning, M8 reach).** `append_text` on a row-set key writes line by line (`mongo_backend.py:197-198`): if a later line is refused, the earlier lines stay stored. No secret is stored, so M8 holds, but the refusal is not all-or-nothing.

**W3 (warning, M22).** `_text_of` (`:273-279`) reads the `kg_*` rows after the skeleton, and a concurrent rewrite drops that generation (`:115-116`): a reader can get a skeleton with an empty or short graph (not a mix). The skeleton carries no node/edge counts to detect it. Low reach under `--max-instances 1`; add counts to the skeleton or retry when rows are missing.

**W4 (warning, parity and scale).** (a) `exists_path(repo_root())` and `list_children(repo_root())` raise `UnsafeName` for key `""` because `backend_for` runs `safe_key("")` (`filestore.py:167`), although every backend's `children`/`is_dir` handles `""` (`mongo_backend.py:175,179`, `filestore.py:101`); reproduced in file mode. (b) A `.jsonl` key's `get` on Mongo returns rows joined by `\n` (`'a\n\nb'` becomes `'a\nb\n'`), not the original text. (c) `put(bytes)` with non-UTF-8 content raises a bare `UnicodeDecodeError` on Mongo (the two `write_bytes` callers write UTF-8 JSON or config today). (d) `children`/`is_dir` list every key under the directory (`:169-171`), one document per row, so a large crawl or runs directory scans every row; `@cache` on `route` (`mongo_routes.py:149`) is unbounded.

**W5 (warning, minor).** A state key literally named `marker` cannot be stored in `server_state` (`ValueError` from the guard); File allows it. Add it to the unsafe list or document it.

## Flags the caller asked me to judge

- **F1 `GuardedBucket.list(prefix)` and prefix delete skipped: deferral, not a U4 FAIL.** No U4 criterion needs it (the U4 row is M2, M5-M8, M11, M15, M17-M19, M21, M22); it serves U5a (M23). But `mongo_guard.py` is exactly at the 300-line cap and D-122/D-123 lists no second guard module, so U5a cannot add it without a placement ruling. This needs a human decision (a D-entry from Umesh) before U5a starts: a raised cap for `mongo_guard.py`, or an approved second module that is not a second door (M3 allows exactly two files that touch the client).
- **Env name `AUTOTESTER_MONGO_URI` vs `PATHLYNKS_MONGO_URI`: warning; U9 must fix.** D-120 (`docs/DECISIONS.md:2926`) and contract M28/M36 name `PATHLYNKS_MONGO_URI` from the repo-root `.env`; `default_backend` (`mongo_backend.py:35,291`) reads `AUTOTESTER_MONGO_URI` from `os.environ` only (not `.env`). It fails closed (a missing value stops startup, `test_state_selection.py:74`), the URI is still redacted (`repo_redactor` reads `.env` and adds the URI), and the manifest marks it provisional. U9's `core/env.py::mongo_uri` must replace it, not add a second name.
- **auth/credentials/blobs refused on mongo: acceptable.** Per-area flips are refused by name (`mongo_routes.py:234`); `AUTOTESTER_STORE=mongo` alone still labels all nine areas `mongo`, harmless because no key routes to those three, but U6/U11/U5a must check the selection themselves.
- **2-line `mongo_guard.py` edit: acceptable.** The diff is the `verdict: Exception` annotation and the lazy-cursor `list(...)` moved inside `_translate`; U1 guard tests (40 + 35) and the chain tests pass; W3 is closed by it.
- **File skip of the 16-way append test: acceptable, with a note.** `FileBackend.append_text` is the same plain `open("a")` that `append_row` was on base (`git show 0a2cbe45:src/autotester/store/filestore.py:146-150`), so there is no regression. I measured it: 16 threads x 50 appends gave 726 lines of 800 on this Windows host. The skip is unconditional (`test_state_backend_contract.py:227-228`); prefer `sys.platform == "win32"`, and callers that need atomic append on File keep their lock.
- **Mutations a/b/c/e on an earlier tree: closed.** I re-ran all six specs on the final tree, 42/42 killed.

## Dual-check note
This is checker B only. The unit closes on both verdicts. D1 should be recorded in `qa/issues.jsonl` (maker fixes in place, no new file); W1 to W5 are at the maker's discretion except where they gate U5a, U7 or U9 as stated.
