# Verdict - mongo-store-u4 (checker A)

**Verdict:** FAIL
**Cycle checked:** 0
**Checker:** A (fresh, independent; did not read any other checker's verdict)
**Unit:** U4 (`store/mongo_backend.py`, `store/mongo_routes.py`, filestore Path additions, `StateBackend` +4 methods). Dual unit: this is half of the dual check.
**Tree checked:** worktree `D:/autoTesting/.claude/worktrees/mongo-u4`, branch `feat/mongo-store-u4`, HEAD `1366d1fb` (code commit `05e58c2c`, base `0a2cbe45`).
**Contract:** `qa/contracts/mongo-store.md` M2, M5-M8, M11, M15, M17-M19, M21, M22, U4 row.

Two defects block a PASS; both are small and both are reproducible with the commands below. Everything else in the brief checks out.

## Blocking findings (fix in cycle 1)

**F1 - `delete(key)` on a `.jsonl` key that routes to `server_state` raises instead of returning a bool (M15 parity, M6/M11 interplay).**
- Code: `src/autotester/store/mongo_backend.py:149-150` (`delete`, rows branch) calls `coll.delete_many({"k": key})`. On `server_state` the guard's `_before_write(..., selects=True)` (`src/autotester/store/mongo_guard.py:256-258`) refuses any filter whose `_id` is not a string, to protect the identity marker. A `delete_many` filter has no `_id`, so it always trips. Every `.jsonl` key that falls through the route table's catch-all (`mongo_routes.py:90`, `("**", "server_state", "settings")`) is therefore undeletable, and `delete_prefix` over a directory holding one aborts part-way.
- Reproduction (fake client, `MongoBackend(open_store(...), Redactor({}))`):
  - `b.append_row("foo.jsonl", '{"a":1}'); b.delete("foo.jsonl")` -> `ValueError: the store identity marker is not writable` (File and Memory backends return `True`).
  - `b.append_row("zz/rows.jsonl", ...); b.delete_prefix("zz")` -> same `ValueError`. A first `delete_prefix("zz")` over a document key worked (returned 1).
- Why the suite missed it: `tests/test_state_backend_contract.py:35-50, 84-94` use `t/rows.jsonl` and `p/a/y.jsonl` but never `delete` or `delete_prefix` over a rows key that lands in `server_state`. No key the product writes today reaches this path (all known `.jsonl` names are routed to their own collections), so it is latent, but U7 (purge as `delete_many`) and U3c build on this seam.
- Fix direction (maker's choice): delete row sets by listing their `_id`s and `delete_one` each (as `delete_row` and `replace_rows` already do, `:232`, `:247`), or route unknown `.jsonl` keys away from `server_state`. Add a contract case `delete`/`delete_prefix` over a rows key on all three backends.

**F2 - A secret value carried in the KEY is echoed in the `StoreSecretRefused` message (M8; contradicts the unit's own "never quoted" claim).**
- Code: `src/autotester/store/mongo_backend.py:76` formats `f"refusing to store {key!r}: ..."`, and `_guard` scans `f"{key}\n{text}"` (`:72`), so when the key is what matched, the message contains the value.
- Reproduction: `Redactor({"K": "Zq9-secretVALUE-77"})`; `b.put("projects/a/Zq9-secretVALUE-77.json", "{}")` -> `StoreSecretRefused: refusing to store 'projects/a/Zq9-secretVALUE-77.json': it carries a secret value`; same on `append_row` (`.jsonl`) and `create_exclusive`. Text-only secrets are correctly not quoted (8 write paths, checked).
- Why the test missed it: `tests/test_mongo_backend_fence.py:168-169` asserts only `pytest.raises(StoreSecretRefused)` for the key case; the no-quote assertion at `:165` covers the text case only. The manifest (row M8) says the key is scanned and the error never quotes the value; the second half is untrue for keys.
- Fix direction: do not interpolate the key into the message (or pass it through the redactor's `scrub`); add the `SECRET not in str(...)` assertion to the key case.
- Severity note: a key built from a secret is unlikely in practice, but M8 is CRITICAL and the unit states it as a guarantee. If the dispatcher rules this alone a Warning, F1 still blocks.

## Non-blocking findings (carry forward; no action needed to pass cycle 1 unless noted)

**W-A (judgement flag: `GuardedBucket.list(prefix)` + prefix delete skipped) - acceptable deferral, not a FAIL.** None of U4's criteria (M2, M5-M8, M11, M15, M17-M19, M21, M22) requires bucket listing; it belongs to U5a (M23, M25). `mongo_guard.py` is exactly 300 lines (`wc -l`), and no second guard module exists on the D-122/D-123 list. It needs a placement ruling (compact the guard, or a D-entry authorising a module) before U5a starts. Not an amendment of this contract.

**W-B (env name) - acceptable for U4, must be resolved in U9.** `mongo_backend.py:35` `URI_ENV = "AUTOTESTER_MONGO_URI"` is provisional (comment says U9 owns it). The contract and D-120 name `PATHLYNKS_MONGO_URI` (M28 env list, M36; `docs/DECISIONS.md:2926`). Also `default_backend()` (`:288-295`) reads `os.environ` only, not the repo `.env`, so a deployment that only has the URI in `.env` would stop at startup with the clear named error. U9 (`core/env.py::mongo_uri`) must replace this; do not ship wired to the provisional name.

**W-C (auth/credentials/blobs refused on mongo) - correct.** `mongo_routes.py:25-29, 234-236`: `AUTOTESTER_STORE_AREAS=auth=mongo|credentials=mongo|blobs=mongo` -> `StoreSelectionError ... routes nothing yet; ... leave it on file` (probed, all three). Cosmetic inconsistency: with blanket `AUTOTESTER_STORE=mongo`, `store_selection()` still reports those three areas as `mongo` (probed). Nothing routes to them, so it is benign, but U6/U11/U5a must not read that value as "the store is wired".

**W-D (2-line `mongo_guard.py` edit) - justified.** `git diff 0a2cbe45..HEAD -- src/autotester/store/mongo_guard.py` is exactly: `verdict: Exception = ...` (type annotation) and `find` iterating the cursor inside `_translate` (`:125`). It closes U2-B W3, guard tests pass (40 + 35 + 25), mutant e1 is killed.

**W-E (mutations a/b/c/e ran on an earlier tree) - closed by me.** I re-ran every spec on the final tree: a 18/18, b 3/3, c 4/4, d 7/7, e 2/2, f 8/8 killed (details below). `git status` is clean of source changes afterwards.

**W-F (File 16-way append skipped, `tests/test_state_backend_contract.py:226-228`) - acceptable.** The skip is narrow (`FileBackend` only; Memory and Mongo run the race and pass). At base `0a2cbe45` the File append was already a plain `path.open("a")` (`git show 0a2cbe45:src/autotester/store/filestore.py` line 149), so U4 introduces no regression. The docstring of `append_path` ("each call is one atomic append", `filestore.py:233`) overstates the File backend and should say so.

**W-G (append retry bound).** `APPEND_RETRIES = 8` (`mongo_backend.py:36`) on a unique `(k, seq)` index: under real Mongo with more than 8 racing writers one can lose 8 times and get `StoreUnavailable` for a valid append. The fake serialises threads, so the 16/32-thread tests (probed: 32 appends, 0 duplicate seq, 1 winner of 16 `create_exclusive`) cannot show it. Consider a larger bound or jitter before G1; the live smoke should cover it.

**W-H (observations, no action required now).**
1. `put_if` on a split persona (>4 MB graph, `_build :252`): `h` is the digest of the original text while `get` returns the re-serialised join (`join_graph`, "equal as a model, not byte-equal"), so a compare-and-set against `text_sha(get(key))` can never match, and `create_exclusive`/`put_if` store a >4 MB persona whole without the split. No caller uses CAS on a persona today.
2. `replace_rows(key, [])` / deleting the last row leaves File with an empty file (`get` -> `""`, `exists` True) but Mongo with no documents (`get` -> `None`, `exists` False). `read_jsonl` is `[]` either way.
3. `append_text` of a partial line (no newline) to a `.jsonl` key creates a separate row on Mongo but concatenates on File.
4. `safe_key` accepts `com¹`, `COM0`, `lpt0`, `clock$`, `a/ con` (not reserved on all Windows builds); all the contract-listed cases are refused (probed below).

## Contract verification (each claim checked by me)

| Criterion | Result | Evidence |
|---|---|---|
| M2 no API takes a database name | PASS | `grep -rnE "def \w+\(.*\b(db\|database\|db_name)\b" src/autotester/store/mongo_*.py` empty; `MongoBackend.__init__(store, redactor=None)` (`mongo_backend.py:54`); `test_mongo_backend_fence.py::test_no_public_parameter...` passes. `blobs.py`, `cli_store.py` do not exist yet (U5a, U8). |
| M3/M5 one door, only `autotester` touched | PASS | `grep -rnE "import (pymongo\|gridfs\|bson)\|MongoClient\(\|get_database\|list_database_names\|drop_database" src scripts` finds only `browser/db.py:46-48` (read side) and `mongo_guard.py`. Probe: after a full workload `client.accessed == {'autotester'}`, `server.databases == ['autotester']`; with URI `mongodb://u:CANARY@h/`. |
| M6 closed verbs / M7 insert-only | PASS | Probe on `approvals`: `put`, `delete`, `upsert_row`, `delete_row`, `replace_rows`, `delete_prefix` (both prefix forms) all `StoreImmutable`, rows stay `['{"id":1}','{"id":2}']`; `append_text` adds a row. `bug_events` and `delivery_records`: same-text re-put OK, different text / delete / put_if / append_text -> `StoreImmutable`, `create_exclusive` -> False. `delete_prefix` checks every victim before deleting any (`:182-186`). |
| M8 secret gate | PASS for text, FAIL for key echo | Text secret refused on put (doc, rows, bytes), put_if, create_exclusive, append_row, append_text (doc and rows), upsert (new and existing), replace_rows; DB dump contains the value 0 times; no `__cause__`/`__context__`. Key case: see F2. |
| M11 marker | PASS | Probe: `put`, `create_exclusive`, `delete`, `put_if`, `append_text` on key `marker` -> `ValueError the store identity marker is not writable`; marker doc unchanged; `HAS_TEXT` keeps it out of `get`/`exists`; never in `keys("")` (probed: `['projects/p/x.json']`). |
| M15 one suite, three backends | PASS with F1 gap | `BACKEND_FACTORIES = {file, memory, mongo}` (`tests/state_backends.py:140-144`); 379 passed 1 skipped (File append race, W-F). F1 is a parity hole the suite does not exercise. |
| M17 safe keys | PASS | Probe: key `../x` refused with `UnsafeName` by all 17 backend methods (`get put put_if create_exclusive delete exists keys delete_prefix rows append_row append_text upsert_row delete_row replace_rows children is_dir mtime`). |
| M18 encoding / size / order | PASS | 13 MB doc and 13 MB row -> `StoreDocTooLarge`; multibyte (chars below cap, bytes above) refused; exactly 12 MiB accepted with the 4 MB warning logged; `{"a.b":1,"$x":2}` round-trips byte-for-byte (text stored verbatim); 32 threaded appends: 32 rows, no duplicate `seq`. See W-G for the real-server retry bound. |
| M19 exactly one winner | PASS (fake) | 16 threads `create_exclusive`: 1 winner; `put_if` sequence `True False False True` and final value `c`. |
| M21 layout/indexes | PASS | `test_mongo_backend_layout.py` (indexes twice = no change; every closed-set collection routed or owned by a later unit); a15 mutant killed. |
| M22 KG split | PASS | Probe: 6.0 MB persona (600 nodes, 600 edges) -> `kg_nodes` 600, `kg_edges` 600, `project_docs` 1; `get` equal as a model; rewrite to a 3-node persona drops all KG rows; delete drops all; 601-node rewrite leaves exactly 601/601 (no mixed generations). |
| M13 AUTOTESTER_STORE unset stays file | PASS | Probe (env unset, temp data root): `write_text`, `append_path`, `exists_path`, `list_children`, `mtime_path`, `validate_store_env()` all work; `pymongo`, `gridfs`, `bson`, `autotester.store.mongo_backend`, `autotester.store.mongo_guard` all absent from `sys.modules`; all nine areas `file`. Typos (`Mongo`, unknown area, `auth=`, `auth=redis`) stop startup with `StoreSelectionError`. |

## U2 checker-B warnings (my own adversarial inputs)

- **W1 `safe_key`:** refused (`UnsafeName`): trailing `.`/space (`a/b.`, `a/b `, `a/con.`, `a/CON `), device names any case and extension (`CON`, `con`, `Con.txt`, `nul.json`, `NUL.tar.gz`, `COM1`, `lpt9.x`, `prn`, `aux .x`, `CONIN$`, `CONOUT$`), `:` (`a/b:c`, `C:/x`, `a/b:stream`), `* ? < > " |`, control chars `\x01 \x1f`, `..`, `.`, empty segment, leading `/`, backslash. Prefix mode allows an unfinished last segment (`a/CON`, `a/b `, `a/b.`) but refuses a completed one (`a/CON/`, `a/b./c`, `a/con/x`). Closed, except the observations in W-H(4). CLOSED.
- **W2 `delete_prefix`:** `""`, `"/"`, `"//"` -> `UnsafeName`; with `projects/a` and `projects/ab` present, `delete_prefix("projects/a")` deleted 2 (project.json and cases.jsonl of `a`) and left `projects/ab/cases.jsonl`, `projects/ab/project.json`; `"projects/a/"` then deleted 0. `keys("projects/a")` is still a string prefix (matches `ab`), as File does and the contract suite pins (`test_state_backend_contract.py:94`). CLOSED (but see F1 for the rows-in-`server_state` case).
- **W3 lazy cursor:** through the backend with `cursor_error` and `down_message` both carrying a URI containing a canary password: `rows`, `keys`, `mtime`, `children` -> `StoreUnavailable`, canary absent from `format_exception`, `repr`, `str`; `__cause__` and `__context__` are `None`; `put`, `append_row`, `ping` on a downed server likewise. `mongo_guard.py:125` iterates inside `_translate`. CLOSED.
- **W4 invalid-URI chain:** 11 URIs incl. bad port (`h:99999999`), upper-case scheme, `http://`, empty, leading space, `h,/db`, `p%<canary>`: invalid ones raise the fixed `StoreConfigError("the store connection string is not a valid mongodb:// URI")` with no cause/context and no canary; the valid-by-parser ones (`mongodb+srv://`, `?authSource=%ZZ`, `?tls=maybe`) construct and any later driver error is reduced to a class name (`mongo_guard.py:229-235`). CLOSED.
- **W5 `area_of`:** `approvals.jsonl` -> `approvals`; `approval_revocations.jsonl` -> `approvals`; `.work/run_queue.json`, `.work/team/schedule/claims/x`, `.work/team/delivery/x.json` -> `queue`; `.work/audit.jsonl` -> `settings`; `projects/p/runs/r1/trace.jsonl` -> `runs`; `crawl/c1/nodes.jsonl` -> `crawls`. `auth`/`credentials`/`blobs` = W-C. CLOSED.

## Scope, size, process

- `git diff --stat 0a2cbe45..HEAD`: 28 files, +2419/-150. Two new `src/` modules (`store/mongo_backend.py` 299 lines, `store/mongo_routes.py` 268), both on the U4 row of the unit table; the other `src/` changes are in-place edits (`filestore.py` 300, `safe_names.py` 106, `file_lock.py` 69, `run_store.py` 90, `mongo_guard.py` +2/-2). No `*_v2`/`*_new` file; no file over 300 lines; `autotester doctor` enforces the 50-line function cap (clean).
- Signatures: `tests/test_state_signatures.py` passes (M14); the five new public Path functions exist at `filestore.py:232, 238, 285, 291, 297` and `StateBackend` has `children`, `is_dir`, `mtime`, `append_text` (`mongo_routes.py:96-116`), all implemented on File, Memory (tests) and Mongo.
- `qa/evidence/mongo-store-u4/` present; `verify.txt` doctor line is known-wrong per the manifest, I used my own doctor run.

## Commands run and results (all in the worktree, `PYTHONPATH=<worktree>/src`, `uv run --no-sync`, `-o addopts=`, at most 2 files per call)

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
autotester doctor > .work/doctor-chkA.txt (redirected)                        -> exit 0, "doctor: clean" (2 D-087 advisories, non-blocking)
scripts/mutation_check.py qa/evidence/mongo-store-u4/mutations-{a,b,c,d,e,f}.json
                                                                              -> a 18/18, b 3/3, c 4/4, d 7/7, e 2/2, f 8/8 killed; git status clean of source edits afterwards
```

Adversarial probes (fake client; scripts in the checker scratchpad, not committed): the F1 and F2 reproductions, W1-W5 inputs above, secret on 13 write paths, `../x` on 17 methods, size edges, KG split generations, 32-thread append and 16-thread `create_exclusive`, `AUTOTESTER_STORE` unset import check. Not run: the full suite in one invocation (low-memory rule); `tests/test_role_port_authz.py` not touched by this unit; nothing connected to Mongo; no `.env` value read or printed.

## Required for cycle 1

1. F1: make `delete`/`delete_prefix` work for rows keys under `server_state`; add the contract case on all three backends.
2. F2: stop echoing the key in `StoreSecretRefused`; assert it in `test_a_known_secret_is_refused_everywhere_and_never_quoted`.
3. Optional in the same pass: W-F docstring wording, W-G retry bound note. Re-run mutation specs touching `mongo_backend.py` after the edit.
