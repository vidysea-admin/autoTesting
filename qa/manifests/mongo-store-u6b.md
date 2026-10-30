# Manifest - mongo-store-u6b

**Status:** ready-for-check, WITH ONE OPEN DESIGN-RULE STOP (read "Open STOP" first)
**Fix cycle:** 0
**Contract:** `qa/contracts/mongo-store.md`, unit U6b (dual-checked, security-critical). Criteria judged: M29, M30.
**Authority:** D-120..D-123 (D-122 item 1 lists `auth/store_mongo.py` as an approved new module)
**Branch:** `feat/mongo-store-u6b` (worktree `D:/autoTesting/.claude/worktrees/mongo-u6b`; contains master + `feat/mongo-store-u4` merged). Not merged to master, not pushed.
**Code SHA:** `7cbcd292c8f0874e96a38c26c533bcf7f3e89892` (store, seam, routes, tests); `f0bc9707` is a test-only follow-up (race window widened, orphan-grant assertion) that closed the two survivors of the first mutation run. This manifest is a third commit on top.

## Open STOP (needs a human or parent decision)

`src/autotester/auth/store_mongo.py` is **404 lines; the design rule is 300** (`autotester doctor`: `file-too-long`). I compressed it as far as is readable (a one-liner rewrite reached about 360, still over) and did not create a second module, because only `auth/store_mongo.py` is on the D-122/D-123 list and the brief says a new file is a STOP.

The natural split is by responsibility, and it is **already built and verified, not applied**: `qa/evidence/mongo-store-u6b/split-proposal/`
- `store_mongo_tx.py` (130 lines): `AuthStoreBusy`, `coll_of`, `MongoTxBase` (undo log, write helpers, id counter), `lease()` (the write lease). No auth rule, no database name.
- `store_mongo.py` (292 lines): `MongoAuthTx(MongoTxBase)` with every auth operation, `MongoAuthStore`, the cached factory.
- `tests.patch`: the three test edits it needs (`sm.LOCK_ID` and `WAIT_SECONDS` move to the tx module; the no-SQL/no-driver/no-database AST test scans both files).
- Verified with the split applied and then reverted: 59 tests pass (`tests-with-split.txt`), `ruff` clean, `mypy` clean, doctor shows only the pre-existing `repo_redactor` finding plus `docs/MAP.md` staleness (needs `autotester map`) (`doctor-with-split.txt`).

To apply: add `store_mongo_tx.py` to the D-122 module list (a DECISIONS entry), copy the two files over, `git apply tests.patch`, run `autotester map`, re-run the verify block. Mutation line anchors move, behaviour does not.

## What changed

| File | Kind | One job / change |
|---|---|---|
| `src/autotester/auth/store_mongo.py` (404 lines, over cap, see STOP) | N | `MongoAuthStore` and `MongoAuthTx`: the whole `AuthTx`/`AuthStore` Protocol of `auth/store.py` over `GuardedStore` only |
| `src/autotester/auth/store.py` `:91-100` | E in place | `auth_store()` returns the Mongo store only when `store_selection()["auth"] == "mongo"`; the Mongo module (and `pymongo`) is imported lazily, so a file-mode process never loads the driver (M13) |
| `src/autotester/store/mongo_routes.py` `:28` | E in place, smallest edit | the U4 refusal is lifted for auth only: `"auth"` removed from `UNROUTED` (`credentials` and `blobs` keep theirs). Selection is the existing `AUTOTESTER_STORE` / `AUTOTESTER_STORE_AREAS`; SQLite stays the default |
| `tests/auth_store_backends.py` | N (helper) | `BACKENDS = (sqlite, mongo)` and `auth_env`: the single place a backend joins the suite (mongo leg selects through the real env path and the `fake_mongo` double) |
| `tests/test_auth_store_contract.py` (299) | N | one suite, both backends: 19 tests x 2 = 38 cases |
| `tests/test_auth_store_mongo.py` (298) | N | 21 Mongo-only tests: protocol parity, no SQL/driver/database name, lease, undo, ids, indexes, fail closed |
| `docs/MAP.md` | regenerated | `autotester map` |
| `qa/evidence/mongo-store-u6b/` | N | mutation spec and runs, 200-repetition run, doctor outputs, split proposal |

Untouched, as briefed: `store/mongo_guard.py`, `store/mongo_backend.py`, `core/safe_names.py`, `core/env.py`, and every sibling-owned file. No existing test was edited.

## Design (why it holds without multi-document transactions)

Mongo promises one document at a time. A write transaction is therefore built from that:
1. **Lease** (`auth_meta/tx_lock`): taken by `insert_one` under a unique `_id`, or taken over when expired by compare-and-set on `(owner, expires)` (`_acquire :317-334`, `_lease :363-374`). One writer at a time across threads and instances; first-admin, claim and the last-admin check run inside it.
2. **Lost-lease check at commit** (`transaction :380-392`): if the lease changed hands, the transaction raises `AuthStoreBusy` and rolls back.
3. **Undo log** (`_insert :74`, `_patch :79`, `_drop :87`, `rollback :98`): every write snapshots what it replaces; any exception rolls the whole transaction back, like SQL `ROLLBACK`.
4. **Unique indexes** (`INDEXES :42`: email, generation, group name) and `_id` keys as the second line.
5. **Id counter** (`_allocate :105-117`): `auth_meta/alloc:<coll>`, advanced by compare-and-set; ids are never reused after a delete.

## Criteria map

| Crit | Code | Test (falsifier it kills) |
|---|---|---|
| M29 first signups give exactly one admin (AU7) | lease around `transaction :380`; `accounts.signup` runs in it | `test_concurrent_first_signups_yield_exactly_one_admin[mongo]` (6 threads x 5 fresh stores, distinct ids); mutant m2 |
| M29 claim gives one admin (D-109) | same lease | `test_concurrent_claims_yield_exactly_one_admin[mongo]` (4 threads x 5); m2 |
| M29 disabling the last two admins leaves one enabled (AU9) | `ensure_an_admin_remains :256-263`, refusal rolled back by `rollback :98` | `test_disabling_the_last_two_admins_leaves_one_enabled[mongo]`, **200 repetitions** run once (`last-two-admins-200.txt`: 2 passed, sqlite and mongo), 15 in the suite; m1, m3 |
| M29 last admin cannot be removed or demoted, atomically | same guard; raises `db.LastAdmin` with the SQLite message | `test_a_refused_change_is_rolled_back_whole`, `test_last_admin_guard_survives_delete_and_regroup` [mongo]; m1, m3 |
| M29 `generation` cannot change | guard `update_one` refuses it; `_patch` never sets it | `test_generation_is_stable_and_ids_are_integers[mongo]` |
| M29 integer ids, never reused | `_allocate :105` | `test_ids_are_never_reused_after_a_delete`, `test_concurrent_allocation_hands_out_distinct_ids`; m6 |
| M29 sessions store only the sha256 | `insert_session :265` takes the digest | `test_round_trip_users_groups_sessions[mongo]` (`env.digests()` equals sha256; token absent from the dump) |
| M29 disabling takes effect on the next request | `live_principal :282-289` | `test_round_trip_users_groups_sessions[mongo]`; m17 (expiry) via `test_a_disabled_account_or_expired_session_never_resolves[mongo]` |
| M29 default groups seed once (AU11) | `_prepare :344-361` (marker `auth_meta/seeded`, resumable group by group) | `test_the_group_seed_runs_once[mongo]`, `test_a_second_pass_creates_the_same_indexes_and_a_crashed_seed_resumes`; m8, m9 |
| M29 a read creates nothing (AU16) | `exists :340-342` writes nothing | `test_reading_a_missing_store_creates_nothing[mongo]`; m7 |
| M29 existing behaviour is the oracle | every contract test runs on sqlite AND mongo through the unchanged `accounts`/`groups`/`sessions`/`access` | the 38 contract cases; existing auth test files are not edited |
| M30 hash never in a list API, log or error | hashes only in `auth_users`; rollback and lease logs carry only the exception class name | `test_password_hash_never_leaves_the_store[mongo]`, `test_nothing_secret_reaches_a_log`, `test_argon2_strings_live_only_in_auth_users`, `test_an_unreachable_store_denies_and_leaks_nothing` (token, `$argon2`, `mongodb://`, URI canary absent); m5 |
| Writes only to the configured database (M2/M5) | no database name in the module; guard owns it | `test_every_write_lands_in_the_configured_database_only` (foreign databases untouched), `test_the_module_holds_no_sql_no_driver_and_names_no_database` |
| Selection (M13) | `store.py :96`, `mongo_routes.py :28` | `test_sqlite_is_the_default_and_mongo_only_by_selection`, `test_a_mongo_selection_yields_the_mongo_store`, `test_selecting_auth_on_mongo_needs_the_uri_and_names_it_without_a_value`, `test_a_file_mode_process_never_imports_the_driver`; m10, m11 |

## Verify (worktree, `env -u ANTHROPIC_BASE_URL`, `-o addopts= -p no:cacheprovider`, two files per call)

```
pytest tests/test_auth_store_mongo.py tests/test_auth_store_contract.py -> 59 passed   (tests-final.txt)
pytest tests/test_state_selection.py tests/test_auth_store_seam.py      -> 38 passed   (selection + SQLite seam unchanged)
ruff check src tests scripts                                            -> All checks passed!
mypy src/autotester/auth/store_mongo.py src/autotester/auth/store.py    -> Success: no issues found
autotester doctor (> .work/doctor-u6b.txt)                              -> 3 violations at the code commit:
   file-too-long   auth/store_mongo.py 404 > 300        (the Open STOP; gone with the split)
   duplicate-concept repo_redactor mongo_routes.py:184 vs store/blobs.py   (PRE-EXISTING, sibling units; not mine, not fixed)
   stale-committed docs/MAP.md                          (fixed in the code commit by `autotester map`)
python scripts/mutation_check.py qa/evidence/mongo-store-u6b/mutations.json --repo . -> 17/17 mutations killed (mutation-run.txt)
```

**Mutation history, said plainly:** the first run (`mutation-run-first.txt`) was 15/17. m2 (writers take no lease) survived because the fast fake let 6 threads finish before they overlapped, so the race tests proved nothing about the lock; m16 (account delete leaves its grants) survived because orphan grants are invisible through `access.resource_for`. Fix (commit `f0bc9707`, tests only): `AuthEnv.fresh(slow=True)` stretches each fake Mongo call by 0.5 ms for the three race tests, and the delete test now asserts the dump holds no `proj-` grant. The second run killed both. Mutants m1-m17 cover: last-admin guard, lease, rollback, session purge namespace, hash logged, id counter, `exists()` writing, seed guards (x2), selection ignored / default flipped, reader writes, lost-lease check, expired-lease takeover, email uniqueness, grant cascade, session expiry.

## Things the checker should look at (judgement calls and limits)

1. **Lease instead of the contract's wording.** M29 names `create_exclusive` on an `auth_meta` doc and an optimistic CAS on `auth_meta/admin_guard`. I serialise ALL writers with one lease and an undo log instead, which is stronger (it also covers claim, memberships and the undo of a refused demotion). It meets the stated falsifier (200 repetitions of the two-admin disable leave one enabled; exactly one admin from concurrent signups and claims). If the contract wording is meant literally, that is an amendment for the checker.
2. **Readers take no lease.** A reader can see a write just before its rollback. Every rollback follows a refused change (a last-admin refusal or an exception), which only lowers privilege, so a stale read can show a little more access for an instant, never less.
3. **A crash mid-transaction** leaves partial state until the lease expires (30 s) and nothing undoes it; the undo log is in process memory. A crash during seeding is resumable (tested).
4. **Provisional URI name.** The store reads `AUTOTESTER_MONGO_URI` (`URI_ENV` in `mongo_backend.py`); U9 owns the wiring into `core/env.py`. A missing value raises `StoreSelectionError` naming the variable, never a value.
5. **Each Mongo area opens its own `GuardedStore`** for now; U9 unifies them.
6. **Membership lookups scan users** (the fake has no array-contains and the data is small); acceptable at auth scale, flagged for U8.
7. **Existing auth test files were not run against Mongo directly** (they use the SQLite gate); the new contract suite mirrors their assertions on both backends instead, and the SQLite legs of that suite run the same assertions through the unchanged business modules.
8. **Not run:** the full suite in one call (low-memory rule). Run: the four store/auth files above, in pairs.
