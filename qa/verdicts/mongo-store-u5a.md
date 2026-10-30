# Verdict - mongo-store-u5a

**Verdict:** PASS
**Cycle checked:** 1
**Checker:** A (fresh, re-check of fix cycle 1; the cycle 0 FAIL stays in git history at 5cca3e06)
**Code under check:** branch `feat/mongo-store-u5a`, HEAD `7a67b4ca` (code fix `60d90dfa`), base `0a2cbe45`
**Contract:** `qa/contracts/mongo-store.md` M2, M5, M8, M23, M25 and the U5a row (normal criticality, single check)

## Cycle 0 findings, re-judged

| # | Cycle 0 finding | Result | Evidence |
|---|---|---|---|
| 1 | M25 exclusions bypassable by case / trailing dot / space | FIXED | `blobs.py:57-59` `_folded` (casefold, then `rstrip(". ")`) applied to every segment at `:110`; the segment set, `.env*` and `.xlsx` tests at `:112-113` run on the folded parts. Own probe (below): `.wOrK/a`, `a/.work../b`, `a/.Work /b`, `.Env.local`, `a/.ENV.Local.`, `a/.ENV. `, `X.XlSx..`, `x.XLSX `, `A/Chunks/x`, `a/CRAWL_SUMMARIES./x`, `a/.BLOBMETA../x`, `a/Profiles. . ./x`, `a/.work.` all raise `BlobRefused`. |
| 2 | M8 body scan skipped non-lowercase / +json / +xml / parameterised types | FIXED for the named classes | `blobs.py:51-54` `_is_text`. Own probe: `Text/Html`, `application/vnd.api+JSON`, `application/x-www-form-urlencoded;charset=x`, ` application/json`, `APPLICATION/JSON ; charset=utf-8`, `application/json;`, `application/xhtml+xml`, `Application/Atom+XML`, `application/vnd.api+yaml`, `application/problem+json; x=y`, `application/x-ndjson`, `TEXT/` all refuse a planted secret body. See WARNING W1 for the residual. |
| 3 | racing prune raised `StoreNotFound` | FIXED | `blobs.py:218-222` `_prune` suppresses only `mongo_guard.StoreNotFound` (not `StoreUnavailable`, which stays loud). `tests/blob_support.py:27-30` `UniqueBucket.delete` now raises `NoFile` on a missing id like pymongo; the guard's `_translate` (`mongo_guard.py:68-69`) maps it to `StoreNotFound`. `test_two_racing_puts_never_leave_zero_revisions` and the new delete-racing-delete test pass; mutant b6 is killed. |

## Regression check on cycle-0-passing criteria

- Only `blobs.py`, tests and evidence changed since cycle 0: `git diff --stat 4b75c05c..HEAD` lists `src/autotester/store/blobs.py`, `tests/blob_support.py`, `tests/test_blobs.py`, `tests/test_blobs_mongo.py`, `qa/evidence/mongo-store-u5a/*`, `qa/manifests/mongo-store-u5a.md`, `qa/verdicts/mongo-store-u5a.md`. `src/autotester/store/mongo_guard.py`, `tests/fake_mongo.py` and `src/autotester/core/` are untouched (empty diff).
- M3 / driver import: `blobs.py` imports `mongo_guard` only under `TYPE_CHECKING` (`:31-32`) and lazily inside `_prune :219` and `_verified :244`; `tests/test_mongo_guard_scan.py` (39 with the cache file) passes, as does the fresh-interpreter file-mode import test.
- M2: no `db`/`database`/`db_name` parameter in the module; `test_no_public_blob_api_takes_a_database_name` passes.
- M23: unmasked screenshot refused `:117-118`; upload-then-prune order `:232-233`; interrupted-put and failed-upload tests pass.
- Materialize: `:258-270` still verifies sha256 before returning and re-hashes a cache hit; the cache path is `<cache>/<sha256>/<basename>` with the key vetted by `safe_key`, so nothing leaves `.work/blob-cache/` (INFO I2).
- Size: `blobs.py` is 284 lines (cap 300); `autotester doctor` clean (function-length rule included).

## Commands run (worktree `D:/autoTesting/.claude/worktrees/mongo-u5a`, `-o addopts=`, 2 files per call, `env -u ANTHROPIC_BASE_URL`)

```
pytest tests/test_blobs.py tests/test_blobs_mongo.py              -> 148 passed
pytest tests/test_blobs_cache.py tests/test_mongo_guard_scan.py   ->  39 passed
ruff check src tests scripts                                      -> All checks passed!
autotester doctor (> .work/doctor-chk-a1.txt)                     -> exit 0, "doctor: clean"
mutation_check.py qa/evidence/mongo-store-u5a/mutations-a.json    -> 28/28 mutations killed
mutation_check.py qa/evidence/mongo-store-u5a/mutations-b.json    ->  6/6 mutations killed
mutation_check.py qa/evidence/mongo-store-u5a/mutations-c.json    ->  7/7 mutations killed
git status after the mutation runs                                -> clean
```
Own adversarial probe: a script in the checker scratchpad drove `FileBlobStore` (same `_vet` as the Mongo store) with a `Redactor` holding a canary value; keys and content types listed above. No `.env` value was read or printed.

## Findings

1. **W1 (WARNING, M8, non-blocking). Body scan is a deny-by-default list of textual types.** `blobs.py:44-48,54`. Probe: a secret body under `application/ndjson`, `application/jsonl`, `application/sql`, `application/toml`, `application/x-sh`, `application/csv`, `multipart/form-data`, `message/rfc822`, `application/rtf`, or an empty / bare `text` type is accepted unscanned. M8's text requires key, kind and content_type (metadata) to be clean, which holds, and its falsifier names case bodies, trace rows, audit rows and GridFS metadata, not blob bodies, so this is extra defence and not a contract failure. Suggested follow-up: invert the rule (skip only `image/*`, `video/*`, `audio/*`, `application/octet-stream`, `application/pdf`, zip) or scan whenever the bytes decode as UTF-8.
2. **I1 (INFO, M25). Windows name aliases beyond case and trailing dot/space are not folded.** NTFS 8.3 short names (`PROFIL~1/x`) and `dir::$INDEX_ALLOCATION` stream syntax are accepted by `safe_key` and `_vet` (colon segments then fail with a raw `OSError` in the file store on Windows, probe: `.work:x/a`, `.work::$DATA/a`). Both are exotic, need a deliberate caller, and the Mongo store has no filesystem to alias. `PROFİLES` (dotted capital I) and fullwidth forms are accepted and are not NTFS aliases of `profiles`, so that is correct. A tab inside a segment (`.work\t/a`) passes `_vet` and then fails in the OS layer; not an alias.
3. **I2 (INFO, materialize, carried from cycle 0 finding 5).** Odd basenames (`nul`, `foo:bar`) raise raw OS errors inside the cache directory before anything could leave it; no path escape found.

No BLOCKING finding. M2, M5, M8 (metadata and the named textual body classes), M23 and M25 hold on this code; the three cycle 0 defects are fixed and mutation-protected (41/41 mutants killed).
