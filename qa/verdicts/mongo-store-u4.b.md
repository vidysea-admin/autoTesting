# Verdict - mongo-store-u4 (checker B, fix cycle 1 re-check)

**Verdict:** PASS
**Cycle checked:** 1
**Checker:** B (fresh, independent; did not read checker A's verdict)
**Tree checked:** branch `feat/mongo-store-u4`, head `41400c24` (code `371b8a8d`, manifest on top), base master `0a2cbe45`.
**Contract:** `qa/contracts/mongo-store.md`, unit U4: M2, M5-M8, M11, M15 (Mongo leg), M17-M19, M21, M22.
**Dual-check note:** this is one of the two required checkers; this verdict does not close the unit alone.

## Required fixes (answering cycle 0: A FAIL `0264cc38`, B PASS-with-defect `9a2800e6`)

| # | Fix | Result | Evidence |
|---|---|---|---|
| 1 | `delete`/`delete_prefix` on a `.jsonl` key in the `server_state` catch-all raised "identity marker is not writable" | FIXED | `mongo_backend.py:143-145` deletes row by row on `_id` (`hits = self._docs(...)`, then `delete_one`); `delete_prefix :176-181` goes through `delete`. Contract case `test_state_backend_contract.py:126` runs on file, memory, mongo (all pass). Mutant g1 (back to bare `delete_many` on `k`) is killed by the `[mongo]` leg. |
| 2 | `StoreSecretRefused` echoed the key | FIXED | `mongo_backend.py:63-76`: fixed message, scan runs before the size check, raised outside `except` (no `__cause__`/`__context__`). Test `test_mongo_backend_fence.py:160-178` (`_quotes_nothing` over str, repr, args). Mutant g3 (quotes the key again) and g4 (key no longer scanned) killed. |
| 3 | `append_text` all-or-nothing | FIXED | `mongo_backend.py:189-196` vets every line before the first write. Test `:240`; mutants g5 (no pre-vet) and g6 (blank lines kept as rows) killed. |
| 4 | File 16-way append skip only on win32; `append_path` docstring | FIXED | `tests/test_state_backend_contract.py:247` (`sys.platform == "win32"`); `filestore.py:233` docstring says atomic on Memory/Mongo, plain `a` on File. |
| 5 | `safe_key` refuses COM0, LPT0, superscript digits, `clock$` | FIXED | `core/safe_names.py:21-22` (`_DIGITS` starts at `0`, `clock$` added). Mutants g7-g10 killed (g10 pins that COM10 stays accepted). |
| 6 | master merge: one `repo_redactor`; `blobs._vet` ordering | OK | See "blobs.py change" below. |

## Commands run (all in `D:/autoTesting/.claude/worktrees/mongo-u4`, `PYTHONPATH=<worktree>/src`, `-o addopts=`, `env -u ANTHROPIC_BASE_URL`, two files per call, one call at a time)

```
tests/test_state_backend_contract.py tests/test_state_wrappers.py   415 passed, 1 skipped (File 16-way append, win32)
tests/test_mongo_backend_fence.py tests/test_mongo_backend_layout.py   80 passed
tests/test_safe_key.py tests/test_state_selection.py                106 passed
tests/test_blobs.py tests/test_blobs_mongo.py                       148 passed
tests/test_blobs_cache.py tests/test_mongo_guard_scan.py             39 passed
tests/test_mongo_guard.py tests/test_mongo_guard_surface.py          40 passed
tests/test_mongo_guard_chain.py tests/test_state_signatures.py       25 passed
tests/test_mongo_guard_spec.py tests/test_sweep_u3a.py               12 passed
uv run ruff check src tests scripts                                  All checks passed!
uv run autotester doctor > .work/doctor-b1.txt                       exit 0, final line "doctor: clean" (only non-blocking D-087 advisories)
scripts/mutation_check.py on qa/evidence/mongo-store-u4/ specs, final tree:
  g 10/10, a 18/18, b 3/3, c 4/4, d 7/7, e 2/2, f 8/8 killed (52/52, 0 survived)
```

Not run: the full suite in one call, `tests/test_role_port_authz.py` (low-memory rule; not touched by this unit).
`git status --short` was empty after the mutation runs (the harness is sandboxed).

## Scope check

`git show --stat` of the three non-merge commits since the cycle-0 checkers: `7a835857` touches `core/safe_names.py`, `store/filestore.py` (docstring only), `store/mongo_backend.py`, three test files and `qa/evidence/mongo-store-u4/*`; `371b8a8d` touches `store/blobs.py` and `verify-cycle1.txt`; `41400c24` touches only `qa/manifests/mongo-store-u4.md`. The rest of `git diff 1366d1fb..HEAD` is master's U3a, U5a and ts6 merges (`2f418a68`), not this unit. No `*_v2`-style file. No new `src/` module beyond the two on the D-122/D-123 list. `mongo_backend.py` is 297 lines, `blobs.py` 277, `test_state_backend_contract.py` 300 (cap 300).

## blobs.py change (371b8a8d) - U5a behaviour kept, no import cycle

- `blobs.py:29` imports `repo_redactor` from `mongo_routes`; `grep -rn "def repo_redactor" src` finds exactly one definition (`mongo_routes.py:185`). The body is the same as the removed one (non-empty `.env` values, plus an optional `extra`), so callers passing `repo_redactor` as a zero-argument callable (`blobs.py:142, 200`) behave as before.
- Fresh-interpreter imports (`python -I -c "import ..."`): `blobs`, `mongo_routes`, `filestore` import clean and `pymongo` is not in `sys.modules` (M13); `mongo_backend` imports clean. No cycle.
- `_vet` (`blobs.py:99-118`): the never-moves check folds the raw `key.split("/")`, then `safe_key(key)` runs. Since `safe_key` returns an accepted key unchanged, the folded parts are identical for every accepted key; the only difference is that a key which is both unsafe and a never-moves path is now `BlobRefused` rather than `UnsafeName`, which matches master. My own probe of `_vet` (key, kind, content-type and text body carrying a known secret; `.env`, `.env `, `x.xlsx.`, `a/profiles /b`, `a/.work./b`, unmasked screenshot, `../x`, `CON`): every refusal is `BlobRefused` or `UnsafeName`, none quotes the secret, `ok` is accepted.
- `test_blobs.py` + `test_blobs_mongo.py` (148), `test_blobs_cache.py` + `test_mongo_guard_scan.py` (39) all pass, including the M3 AST scan (still exactly two driver-touching files).

## My own adversarial probes (fake client, `.work/adv_b.py`, outside `src/` and `tests/`)

- Row-set delete in the catch-all: `foo.jsonl` deleted True then False, rows empty, `exists` False; a sibling `zzz.jsonl` survives; `delete_prefix("dir/")` over a mixed directory (rows keys at two depths, `.json`, `.txt`) returns 4 and leaves `other/z.json`; the identity marker document is untouched; `delete("marker")` raises `ValueError`, `delete("marker.jsonl")` returns False.
- Insert-only: `delete_prefix("projects/p/")` over a directory holding an approvals row set and an ordinary document raises `StoreImmutable` and deletes nothing; `delete` of the approvals key raises `StoreImmutable`.
- Secrets: `StoreSecretRefused`, with the secret in no rendering (str, repr, args, cause, context), for secret in text, in key, in key plus a 12 MB+1 body, in text plus a 12 MB+1 body, `append_row` key and text, `append_text` key and a later row line, `create_exclusive` key, `put_if` key, `replace_rows`, `upsert_row`. A dump of every fake collection afterwards contains no secret and no partial rows were left (`rows` of the failed-append logs are empty).
- Partial append: lines `{"a":3}`, a secret line, `{"a":4}` raise `StoreSecretRefused` and none of the three lands; an oversize second line raises `StoreDocTooLarge` and the first line (`{"a":5}`) does not land; CRLF and whitespace-only lines add only the real rows; an empty append adds nothing.
- `safe_key`: refused COM0, com0.json, LPT0, lpt0.x, COM and LPT with superscript 1/2/3 (with and without extension), CLOCK$, clock$.txt, CONIN$/CONOUT$ forms, `COM0.`, `Com0 .x`; accepted COM10, COM00, clock.json, CLOCK$x, COM with superscript four, LPT.

## Findings (none blocking)

1. WARNING `core/safe_names.py` (`UnsafeName` text) - a key that is BOTH unsafe (`a/../<secret>`, `a/CON/<secret>`, a control character) and contains a known secret is refused with `UnsafeName`, whose message includes the key, so the secret is echoed in that one case. Pre-existing U2 behaviour (not from this cycle's diff), reached before `_guard`; the key is the caller's own input and no store write happens. Suggest `UnsafeName` not quote the key, or `MongoBackend._route` redact it, in a later cycle or U9/U11.
2. INFO `core/safe_names.py:21` - fullwidth digit forms (`COM` + U+FF11) are accepted. Whether Windows treats them as devices was not verified here; only the superscripts the contract-cycle-0 finding named are refused. Low risk; verify on the Windows host if it matters.
3. INFO `tests/test_mongo_backend_fence.py:248-250` - three trailing blank lines at end of file (ruff passes). Cosmetic.
4. INFO - the manifest's "Known follow-ups" (8-writer append retry ceiling, no CAS on a split persona, empty `.jsonl` parity, unbounded route cache, `marker` key reserved, mid-rewrite persona read, `AUTOTESTER_MONGO_URI` provisional, `GuardedBucket.list` F1) are accurate as listed and none is a U4 criterion failure. F1 and the split-persona CAS need a ruling before U7/U5b rely on them.

## Criteria

M2, M5, M6, M7, M8, M11, M15 (Mongo leg: all 3 backends pass the one suite), M17, M18, M19, M21, M22: PASS on the cycle-1 tree. No regression of a cycle-0-passing criterion found (all 52 mutants killed, including the older a-f specs re-run on this tree).

PASS, subject to the dual-check rule (checker A must also PASS the same cycle).
