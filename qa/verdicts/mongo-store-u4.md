# Verdict - mongo-store-u4 (checker A)

**Verdict:** PASS
**Cycle checked:** 1
**Checker:** A (fresh, independent; did not read checker B's verdict). Dual unit: B's verdict is separate.
**Tree:** branch `feat/mongo-store-u4`, head `41400c24` (code `371b8a8d`), base master `0a2cbe45`. Read-only toward src/ and tests/.
**Contract:** `qa/contracts/mongo-store.md` U4: M2, M5-M8, M11, M15 (Mongo leg), M17-M19, M21, M22. Cycle 0 was A FAIL (`0264cc38`).

## Cycle 0 required fixes: all closed

1. **Row-set delete in the `server_state` catch-all** (was "identity marker is not writable"). `MongoBackend.delete` now finds the rows by `k` and deletes each by `_id` (`src/autotester/store/mongo_backend.py:140-145`); `delete_prefix` (`:181-186`) goes through it. `_mutable` still runs first, so insert-only families refuse (`:140`). Probe on file, memory and mongo: `foo.jsonl`, `dir/foo.jsonl`, `settings/x.jsonl`, `a/b/c/z.jsonl` each delete True, then rows `[]`, `exists` False, second delete False. A mixed prefix (`mixd/` doc + rows + nested doc) deleted 3 and left siblings `mixd.json`, `mixd2.jsonl`, `mixdx/keep.json`. Empty prefix refused. Mongo insert-only rows: `delete`, `delete_prefix`, `replace_rows`, `delete_row` on `approvals.jsonl` all raise `StoreImmutable` and the approval row is intact; `delete_prefix("projects/p")` over a dir that holds an approvals row and an `ai/x.json` refuses before deleting anything (doc still present). Contract case `tests/test_state_backend_contract.py:126` runs on all three backends.
2. **`StoreSecretRefused` no longer echoes the key.** `_guard` (`mongo_backend.py:63-71`) raises the fixed text "refusing to store: the key or text carries a secret" outside the `except` (no `__cause__`), and the secret scan now runs before the size check, so a secret key on an oversize body cannot reach the `StoreDocTooLarge` message. Probe with a unique secret registered in the Redactor, 13 cases on `MongoBackend`: put text, put key, put key + 13 MB body, put_if key, create_exclusive text, append_row text and key, append_text (rows with a secret on line 3; document), upsert_row, replace_rows, put of a rows key, put of a persona-shaped document with the secret in the graph. All raise `StoreSecretRefused`; the secret is absent from `str`, `repr` and `args`; `__cause__` is None. The no-quote assertion is `tests/test_mongo_backend_fence.py` `_quotes_nothing` (used at `test_a_known_secret_is_refused_everywhere_and_never_quoted`).
3. **`append_text` all-or-nothing.** `mongo_backend.py:189-199` vets every line before the first write. Probe: `ok1\nok2\n<secret>\nok4` into a rows key leaves `rows == []`; the document-append case leaves the key absent.
4. **File 16-way append skip is win32 only** (`tests/test_state_backend_contract.py:247`); `append_path` docstring corrected (`src/autotester/store/filestore.py:233`).
5. **`safe_key`** (`src/autotester/core/safe_names.py:21-22`) now refuses COM0, LPT0, `clock$` and the superscript digits. Probe refused: `COM0`, `com0.json`, `LPT0`, `lpt0.txt`, `COM¹`, `COM².txt`, `LPT³`, `CLOCK$`, `clock$.txt`, `a/COM0/b`, `a/clock$/b`, `CONIN$`, `conout$.x`, `com1 .txt`, `NUL.tar.gz`. Accepted: `COM10`, `clock.json`, `CLOCK$x`, `COM⁴`, `a/com.txt`, `lpt10`, `xcom0`. As a prefix `a/COM` is allowed and `a/COM0/` refused.

## Master merge and the blobs.py change (U5a regression check)

- `git diff 2f418a68 HEAD -- src` touches only `src/autotester/store/blobs.py` (15 lines). `repo_redactor` is defined once (`src/autotester/store/mongo_routes.py:185`; `grep "def repo_redactor" src` = 1 hit). `blobs.py:29` imports it; `mongo_routes` imports no store module (imports at `:10-23`: core only), so no cycle. Fresh-interpreter imports of `store.blobs`, `store.mongo_routes`, `store.filestore` succeed with `pymongo` not loaded; `store.mongo_backend` and `store.mongo_guard` load it (expected: guard is the one door).
- `_vet` (`blobs.py:99-107`): `safe_key` returns its argument unchanged, so folding `key.split("/")` before it is equivalent for every key `safe_key` accepts. The only behaviour change is which exception a key that is both unsafe and never-moves gets (`BlobRefused` instead of `UnsafeName`), as master did. Probe: `x.xlsx.`, `.env `, `a/.work./b`, `a/profiles /b`, `a/.env`, `A/.ENV.local`, `a/PROFILES/b`, `.work/x`, `a/b.XLSX` -> `BlobRefused`; `COM0`, `a/COM0/b.png`, `../x`, `a/clock$` -> `UnsafeName`; `a/b.png`, `run/shot.png` accepted; secret in key / kind / text body, and unmasked screenshot -> `BlobRefused`.
- `git diff --stat 1366d1fb..HEAD` outside the master merge touches only: `core/safe_names.py`, `store/filestore.py` (docstring), `store/mongo_backend.py`, `store/blobs.py`, the five test files named in the manifest, qa evidence/manifest/verdict files. No unlisted source file.

## Commands run (worktree `D:/autoTesting/.claude/worktrees/mongo-u4`, `PYTHONPATH=<worktree>/src`, `-o addopts=`, 2 files per call, `env -u ANTHROPIC_BASE_URL`)

```
tests/test_state_backend_contract.py tests/test_state_wrappers.py   415 passed, 1 skipped (File 16-way append, win32)
tests/test_mongo_backend_fence.py tests/test_mongo_backend_layout.py  80 passed
tests/test_safe_key.py tests/test_state_selection.py                 106 passed
tests/test_blobs.py tests/test_blobs_mongo.py                        148 passed
tests/test_blobs_cache.py tests/test_mongo_guard_scan.py              39 passed
tests/test_mongo_guard_chain.py tests/test_state_signatures.py        25 passed
tests/test_mongo_guard.py tests/test_mongo_guard_surface.py           40 passed
uv run ruff check src tests scripts                                   All checks passed!
uv run autotester doctor  (redirected to .work/doctor-chkA1.txt)      exit 0, "doctor: clean"
scripts/mutation_check.py qa/evidence/mongo-store-u4/mutations-{g,b,c,d,e,f,a}.json on the final tree
                                                                      g 10/10, b 3/3, c 4/4, d 7/7, e 2/2, f 8/8, a 18/18 killed
grep -c mongomock pyproject.toml uv.lock = 0/0; grep -c cryptography pyproject.toml = 0
wc -l: mongo_backend.py 297, filestore.py 300, blobs.py 277, tests/test_state_backend_contract.py 300 (cap 300)
```
Ad-hoc adversarial probes (scratch scripts outside the repo, no repo file written) gave 85 passing checks, 0 failures. Not run: full suite in one invocation (low-memory rule); `tests/test_role_port_authz.py` (untouched, known environmental failures).

## Findings (all non-blocking)

1. **Info.** `UnsafeName` still quotes the key it refuses (`safe_names.py:106`, `f"unsafe state key {key!r}"`). A key that is both unsafe and carries a secret would echo the secret in that error. It is refused before any write, so nothing is stored; M8 (stored documents) holds. Follow-up for U9/U11 where keys can come from user input.
2. **Info.** A key literally named `marker` is accepted by File/Memory and refused by Mongo with "identity marker is not writable" (already the manifest's judgement call; no real state key has that name).
3. **Info.** The manifest's listed known follow-ups (8-writer append retry cap, no CAS on a split persona, empty row-set parity, unbounded route cache, `AUTOTESTER_MONGO_URI` provisional name) remain open and are not criteria of U4.

No regression of a cycle-0-passing criterion found. M2, M5-M8, M11, M15, M17-M19, M21, M22: satisfied on the cycle 1 tree.
