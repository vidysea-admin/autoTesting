# Manifest - mongo-store-u6b

**Status:** checked-PASS (cycle 2, dual: A 9df1ea10, B 931b1a1a)
**Fix cycle:** 2
**Contract:** `qa/contracts/mongo-store.md`, unit U6b (dual-checked, security-critical). Criteria judged: M29, M30.
**Authority:** D-120..D-123; D-126 (ACTIVE on master `fe1ac6c8`) authorizes the second module `src/autotester/auth/store_mongo_tx.py`
**Branch:** `feat/mongo-store-u6b` (worktree `D:/autoTesting/.claude/worktrees/mongo-u6b`; contains master + `feat/mongo-store-u4` merged). Not merged to master, not pushed.
**Code SHA:** see `git log` on the branch; fix cycle 1 head `797d03cd`; fix cycle 2 is the commit that carries this manifest (the head sha is in the hand-back).

## Fix cycle 2 (checker A FAIL `15713323`, checker B PASS with warnings `3419a12c`)

### B1 (BLOCK) - no crash point may leave a refused or partial change: a write-ahead journal in Mongo

**Choice: persist the undo entries in Mongo and replay them when the next holder takes the lease.** Not "check before writing".
Why not check-before-write: (a) the invariants are enforced in the business modules (`accounts`, `groups`), which call `tx` methods in sequence and judge the result afterwards (the last-admin check needs the post-change membership, `update_group` learns an unknown member only while applying). Checking first means re-implementing each rule against a hypothetical state, and the Mongo path would then differ from the SQLite one in semantics, which breaks the "existing behaviour is the oracle" rule (M29); (b) it moves auth rules into the store, which M2/M5 and D-126 keep out; (c) it still leaves a multi-write operation (`set_user_groups` = delete grants + insert, `delete_user` = sessions + grants + user) half-done on a kill between its own writes. The journal covers all of these with one mechanism and no change to a business module.

How it works (`auth/store_mongo_tx.py`, 213 lines):
- **Write-ahead.** `_log` writes the undo entry BEFORE the write it undoes (`_insert`, `_patch`, `_drop`). Ops: `ins` (undo = delete by `_id`), `set` (carries `after` and `prior`; undo = update filtered on `after`, so it is a compare-and-set), `del` (carries the document; undo = re-insert, a duplicate means it is already back).
- **Commit marker.** `auth_meta/journal` (`{_id, owner}`) is inserted lazily by the first logged write. Deleting it with a compare-and-set on `(_id, owner)` IS the commit (`commit`); it fails if the lease was lost. The entry sweep after it is best effort and inert if it fails (`_docs` filters `kind == "undo"`).
- **Recovery at every acquire.** `lease()` calls `recover(store)` right after taking the lease, on a fresh acquire as well as a takeover: if a journal marker exists its owner never committed, so its entries are replayed newest first, each deleted after it is replayed (a crash inside recovery resumes), then the marker is deleted. A rollback inside a live transaction is the same replay restricted to its own journal (`recover(store, only=owner)`).
- **Where the entries live.** In `auth_users` (fields `email` and `generation` carry the entry key so that collection's unique indexes accept them), because M30 requires `$argon2` strings to appear only in `auth_users`, and a `set`/`del` entry can carry a hash. Test: `test_the_journal_holds_hashes_only_beside_the_users`.
- **Nothing in memory.** The old `_undo` list is gone.

Tests that kill the store at EVERY call point (`tests/test_auth_store_recovery.py`, new): `_sweep` runs the operation with the fake Mongo set down at database call k = 1, 2, 3, ... (the rollback and the lease release then fail too), until the operation needs no more calls; for each k it ages out the lease, runs `claim_admin` as another account and checks (1) the claim is refused, (2) an enabled Admin/CEO member remains, (3) no permission was granted, (4) nothing is half-applied.
- `test_a_refused_change_survives_a_kill_at_every_call_point[set_user_groups|delete_user|set_disabled|update_group]` (each asserts at least 8 call points reached), on the SOLE admin; the update_group case is the refused-on-unknown-member one that could grant `users.manage`.
- `test_a_claim_killed_anywhere_leaves_exactly_one_admin` (claim_admin).
- `test_a_password_change_killed_anywhere_is_whole_or_absent[reset_password|bootstrap_admin]`.
- Journal behaviour: `test_several_writes_to_one_document_are_undone_newest_first`, `test_an_undo_never_overwrites_a_newer_value`, `test_a_commit_whose_journal_was_undone_underneath_it_fails`, `test_a_lease_lost_mid_transaction_is_undone_by_the_next_holder`.

### Stalled holder (A-W2, B-W1)
Three fences, each tested by a reproduction: holder A stalls past 30 s, B takes over and commits, A's late rollback/commit leaves B's change intact.
1. `_log` checks `held()` (lease still owned) before every write and raises `AuthStoreBusy("the auth store lease was lost")`: a zombie writes nothing (`test_a_stalled_holder_writes_nothing_once_the_lease_is_gone`).
2. `rollback` replays only if the holder still owns the lease, and only its own journal (`only=owner`): `test_a_stalled_holders_rollback_leaves_a_live_successor_alone` (B holds the lease with uncommitted work; A's late failure must not touch it).
3. `commit` is the compare-and-set delete of the marker: `test_a_stalled_holder_never_undoes_a_successors_commit`. A `set` undo is itself a CAS on the value it wrote (`test_an_undo_never_overwrites_a_newer_value`).

### B-W2 - sessions are revoked before the new hash is written
`set_password_hash` (reset_password) and `enable_with_password_hash` (bootstrap_admin) call `delete_user_sessions` first (`store_mongo.py:80-86`). `test_sessions_are_revoked_before_the_new_hash_is_written[reset_password|bootstrap_admin]` kills the store between the two steps on raw state (no recovery) and asserts that the old sessions are gone whenever the hash is new.

### A-W1 - a global `AUTOTESTER_STORE=mongo` does not move auth
`auth/store.py:92-110` `_auth_on_mongo()`: auth is on Mongo only when `store_selection()["auth"] == "mongo"` AND `AUTOTESTER_STORE_AREAS` has an explicit `auth=mongo` entry (the last entry wins). `test_a_global_mongo_selection_does_not_move_auth` covers global only, `settings=mongo,auth=file`, and `auth=mongo`. `test_a_mongo_selection_yields_the_mongo_store` (existing) now selects through the area entry; that is the intended behaviour change, flagged below.

### Other changes in this cycle
- The seed in `_prepare` runs inside a journaled transaction: `tx.commit()` first, then the `seeded` marker (a stop between them leaves nothing half-seeded and recovery needs no special case). `count_users` skips journal entries.
- `store_mongo.py` 297 lines (was 293), `store_mongo_tx.py` 213 (was 130), `store.py` 110. All under 300; doctor clean.

### Mutants for the recovery path (the 17 old ones touched none)
`qa/evidence/mongo-store-u6b/mutations.json` has 32 mutants (17 old, 6 of them re-anchored to the new code, + 15 new); `mutation-run-cycle2.txt`: 31/32 on the full run. The one reported survivor was r11 whose kill list named two tests that did not fail (the mutant itself was killed by 12 other tests); its kill list was corrected and it was rerun alone: killed. Effective 32/32 (run file records both). New mutants: r1 recovery not run at acquire; r2 write before its undo entry; r3 recovery leaves the marker; r4 undo without the CAS filter; r5 commit ignores a lost marker; r6 rollback replays any journal; r7 write not fenced by the lease; r9/r10 purge after the new hash (reset_password / bootstrap_admin); r11 entries read as accounts; r13 replay oldest first; r16 `del` not re-inserted; r17 `ins` not deleted; r19 seed never committed; m18 global selection moves auth. Retargeted: m2, m3, m5, m10, m11, m13.

### Verify, fix cycle 2 (worktree, `env -u ANTHROPIC_BASE_URL`, `-o addopts= -p no:cacheprovider`, two files per call)
```
pytest tests/test_auth_store_recovery.py tests/test_auth_store_seam.py   -> 31 passed
pytest tests/test_auth_store_mongo.py tests/test_auth_store_contract.py  -> 58 passed
pytest tests/test_state_selection.py                                     -> 23 passed, 1 skipped
ruff check --no-cache src tests scripts                                  -> All checks passed!
mypy src/autotester/auth/store_mongo.py src/autotester/auth/store.py     -> Success: no issues found in 2 source files
autotester doctor (> .work/doctor-u6b-c2.txt)                            -> doctor: clean (rc 0)
mutation_check qa/evidence/mongo-store-u6b/mutations.json --repo .       -> 31/32 on the full run, r11 rerun killed: 32/32 (mutation-run-cycle2.txt)
```
Sanity check done while building: with `recover(store)` removed from `lease()`, 7 of the 9 recovery tests then written failed.

### Flagged for the checker (cycle 2)
1. **New test file.** `tests/test_auth_store_recovery.py` (288 lines, 18 test cases) is not on the D-122/D-123/D-126 list; the fake-Mongo kill harness did not fit in the two existing test files, which are at 291 and 299 lines. Source files are only the three authorised ones.
2. **Existing tests changed.** `test_a_lease_lost_mid_transaction_rolls_the_transaction_back` (`test_auth_store_mongo.py`) was removed and re-created, stronger, in the recovery file as `test_a_lease_lost_mid_transaction_is_undone_by_the_next_holder` (under the journal the pending write stays until the next holder recovers, so the old assertion was no longer the truth). `test_a_mongo_selection_yields_the_mongo_store` was updated for A-W1 (global alone yields SQLite). Both are behaviour changes made on purpose.
3. **A-W3, left as asked.** A crashed holder still blocks other writers until its lease expires (up to 30 s); recovery then runs on the next acquire. Readers take no lease and may see an unrecovered half-write during that window.
4. **A-W4, left as asked (U9's).** `mongo_backend._CACHE` / `_AUTH` cold-start race can create more than one client.
5. **Residual TOCTOU.** `held()` is checked, then the write happens; a holder that stalls more than 30 s exactly between the two could still write once, and its successor's recovery then finds a journal entry for it only if the entry was written before. Needs a stall at one precise point; not closable without a server-side fence (a fencing token on every write) which Mongo gives us only per document.
6. **M29 wording (carried over):** a lease plus journal instead of `create_exclusive` and an `admin_guard` CAS; both checkers ruled it acceptable in cycle 1; the contract owner should record the amendment.
7. **AU16 narrowing (carried over):** `nothing_written` looks at `auth_*` only, because opening the shared client creates the state indexes (U9).
8. **Sibling tests** still mention `AUTOTESTER_MONGO_URI`; not mine to edit.
9. **Leftover journal entries** after a failed sweep are inert (filtered in `_docs`, skipped by recovery because no marker names them); they cost a few documents, not correctness.
10. **Membership lookups scan users** (carried over, for U8).

## Fix cycle 1 (history; superseded where cycle 2 says so) (from the cycle-0 hand-back and the coordinator's instruction)

1. **Master merged.** `fe1ac6c8` (D-126) merged into the branch. One conflict, `store/mongo_routes.py` `UNROUTED`: master still listed `"auth"`, my side had removed it and kept `credentials`/`blobs`; master has since routed those, so the resolved value is `UNROUTED: dict[str, str] = {}` (`:28`). `tests/test_state_selection.py` parametrizes over `sorted(UNROUTED)`, so its one parametrized case is now skipped (1 skipped), nothing broken.
2. **Split applied (D-126).** `auth/store_mongo_tx.py` (130 lines: `AuthStoreBusy`, `coll_of`, `MongoTxBase`, `lease()`) and `auth/store_mongo.py` (293 lines). Both under 300; doctor's `file-too-long` and function-length rules are clean. `tests.patch` applied (`sm.LOCK_ID`/`WAIT_SECONDS` now `tx_mod.*`; the no-SQL/no-driver/no-database AST test scans both modules).
3. **URI.** `AUTOTESTER_MONGO_URI` is no longer read anywhere in the auth code. `mongo_auth_store()` (`store_mongo.py:279-290`) builds on `mongo_backend.default_store()`: URI from `core.env.mongo_uri()` (`PATHLYNKS_MONGO_URI`), ONE client per process shared with every other area, and `MongoBackend.rearm` (as the env editor calls it) keeps that client. The auth store is keyed to that client (`_AUTH`), so `reset_default_backend()` also drops it; `reset_auth_store()` stays for tests. A missing URI raises `StoreSelectionError` naming `PATHLYNKS_MONGO_URI`, never a value. `core/env.py` and `mongo_backend.py` are untouched.
4. **Test support adapted** (not a test weakened): `tests/auth_store_backends.py` sets `PATHLYNKS_MONGO_URI`, resets the default backend with the auth store (`fresh()` and fixture), and `nothing_written()` (AU16) now looks only at `auth_*` collections: opening the shared client creates the state-area indexes (U9 `MongoBackend.__init__`), which is not an auth write. `test_auth_store_mongo.py` uses the new variable name/message and stays at exactly 300 lines.
5. **M29 lease vs `create_exclusive`/CAS: flagged below (item 1), NOT decided by the maker.**
6. **Mutation spec retargeted** to the new files (`mutations.json`: file fields and the m2/m7 anchors moved), rerun in `mutation-run-cycle1.txt`.

## What changed

| File | Kind | One job / change |
|---|---|---|
| `src/autotester/auth/store_mongo.py` (293) | N | `MongoAuthStore` and `MongoAuthTx`: the whole `AuthTx`/`AuthStore` Protocol of `auth/store.py` over `GuardedStore` only |
| `src/autotester/auth/store.py` `:91-100` | E in place | `auth_store()` returns the Mongo store only when `store_selection()["auth"] == "mongo"`; the Mongo module (and `pymongo`) is imported lazily, so a file-mode process never loads the driver (M13) |
| `src/autotester/store/mongo_routes.py` `:28` | E in place, smallest edit | the U4 refusal is lifted for auth only: `"auth"` removed from `UNROUTED` (`credentials` and `blobs` keep theirs). Selection is the existing `AUTOTESTER_STORE` / `AUTOTESTER_STORE_AREAS`; SQLite stays the default |
| `tests/auth_store_backends.py` | N (helper) | `BACKENDS = (sqlite, mongo)` and `auth_env`: the single place a backend joins the suite (mongo leg selects through the real env path and the `fake_mongo` double) |
| `tests/test_auth_store_contract.py` (299) | N | one suite, both backends: 19 tests x 2 = 38 cases |
| `tests/test_auth_store_mongo.py` (300) | N | 21 Mongo-only tests: protocol parity, no SQL/driver/database name, lease, undo, ids, indexes, fail closed |
| `src/autotester/auth/store_mongo_tx.py` (213) | N (D-126) | the transaction machinery: error, write lease, write-ahead journal and its recovery, id counter; no auth rule, no database name |
| `docs/MAP.md`, `docs/SNAPSHOT.md` | regenerated | `autotester map` |
| `qa/evidence/mongo-store-u6b/` | N | mutation spec and runs, 200-repetition run, doctor outputs, split proposal |

Untouched, as briefed: `store/mongo_guard.py`, `store/mongo_backend.py`, `core/safe_names.py`, `core/env.py`, and every sibling-owned file. No existing test was edited.

## Design (why it holds without multi-document transactions)

Mongo promises one document at a time. A write transaction is therefore built from that:
1. **Lease** (`auth_meta/tx_lock`): taken by `insert_one` under a unique `_id`, or taken over when expired by compare-and-set on `(owner, expires)` (`_acquire :317-334`, `_lease :363-374`). One writer at a time across threads and instances; first-admin, claim and the last-admin check run inside it.
2. **Lost-lease check at commit** (`transaction :380-392`): if the lease changed hands, the transaction raises `AuthStoreBusy` and rolls back.
3. **Write-ahead journal** (cycle 2, see above; replaces the in-memory undo log): every write is preceded by a durable undo entry, any exception rolls the whole transaction back like SQL `ROLLBACK`, and a crash is repaired by the next lease holder.
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
| Selection (M13) | `store.py :96`, `mongo_routes.py :28` | `test_sqlite_is_the_default_and_mongo_only_by_selection`, `test_a_mongo_selection_yields_the_mongo_store`, `test_auth_on_mongo_needs_the_uri_named_without_a_value`, `test_a_file_mode_process_never_imports_the_driver`; m10, m11 |

## Verify (worktree, `env -u ANTHROPIC_BASE_URL`, `-o addopts= -p no:cacheprovider`, two files per call), fix cycle 1

```
pytest tests/test_auth_store_mongo.py tests/test_auth_store_contract.py -> 59 passed
pytest tests/test_state_selection.py tests/test_auth_store_seam.py      -> 36 passed, 1 skipped (empty UNROUTED parametrization)
ruff check --no-cache src tests scripts                                 -> All checks passed!
mypy src/autotester/auth/store_mongo.py (and _tx via import)             -> Success: no issues found
autotester doctor (> .work/doctor-u6b-c1.txt, rerun after the commit)    -> `doctor: clean` (rc 0; only advisory decision-citation warnings; the old `repo_redactor` duplicate is gone after the merge)
python scripts/mutation_check.py qa/evidence/mongo-store-u6b/mutations.json --repo . -> 17/17 mutations killed (mutation-run-cycle1.txt; first lines of the cycle-0 history unchanged)
```

**Mutation history, said plainly:** the first run (`mutation-run-first.txt`) was 15/17. m2 (writers take no lease) survived because the fast fake let 6 threads finish before they overlapped, so the race tests proved nothing about the lock; m16 (account delete leaves its grants) survived because orphan grants are invisible through `access.resource_for`. Fix (commit `f0bc9707`, tests only): `AuthEnv.fresh(slow=True)` stretches each fake Mongo call by 0.5 ms for the three race tests, and the delete test now asserts the dump holds no `proj-` grant. The second run killed both. Mutants m1-m17 cover: last-admin guard, lease, rollback, session purge namespace, hash logged, id counter, `exists()` writing, seed guards (x2), selection ignored / default flipped, reader writes, lost-lease check, expired-lease takeover, email uniqueness, grant cascade, session expiry.

## Things the checker should look at (judgement calls and limits)

1. **FLAGGED FOR THE CHECKER, NOT DECIDED BY THE MAKER: lease vs the contract's wording.** M29 names `create_exclusive` on an `auth_meta` doc and an optimistic CAS on `auth_meta/admin_guard`. I serialise ALL writers with one lease and an undo log instead, which is stronger (it also covers claim, memberships and the undo of a refused demotion). It meets the stated falsifier (200 repetitions of the two-admin disable leave one enabled; exactly one admin from concurrent signups and claims). Whether a lease satisfies M29's `create_exclusive`/CAS wording, or the contract needs amending (or the code changing), is the checker's call.
2. **Readers take no lease.** A reader can see a write just before its rollback. Every rollback follows a refused change (a last-admin refusal or an exception), which only lowers privilege, so a stale read can show a little more access for an instant, never less.
3. **SUPERSEDED in cycle 2 (B1).** A crash mid-transaction is now repaired by the next lease holder from the persisted journal; what remains is A-W3 (writers wait for the lease to expire, up to 30 s).
4. **URI and client are U9's now.** The auth store uses `default_store()`; it does not own a client. Side effect worth a look: the first open of that shared client runs `MongoBackend.ensure_indexes()` on the state collections, so a read-only auth call such as `exists()` can be the first thing to open the client and so triggers those index creations (none in `auth_*`). AU16 is judged on the auth collections only (`nothing_written`); if the checker wants "no write anywhere on a read", that is a U9 design question, not fixable in this file.
5. **Reset coupling.** `reset_default_backend()` drops the auth store with it (identity check on the client); `rearm` leaves both in place.
6. **Membership lookups scan users** (the fake has no array-contains and the data is small); acceptable at auth scale, flagged for U8.
7. **Existing auth test files were not run against Mongo directly** (they use the SQLite gate); the new contract suite mirrors their assertions on both backends instead, and the SQLite legs of that suite run the same assertions through the unchanged business modules.
8. **Not run:** the full suite in one call (low-memory rule). Run: the four store/auth files above, in pairs.
