# Verdict (checker-B) - mongo-store-u6bf (U6bf, auth store on Mongo fix-up)

**Cycle checked:** 0
**Verdict:** FAIL
**Head checked:** a254af9c (code 7b93f34b); evidence commit 4b12585b read as briefed (mutation-run.txt, 39/45).
**Criteria:** M29, M30 and the two U6b cycle-2 residuals. Fresh, independent; no other checker's verdict read.

## Summary
The five items the maker named are closed for single-fault interleavings, and the named gates are green (below). But my own double-fault
sweep finds a REGRESSION against the base (717aa180): a refused privilege grant survives permanently when the dead holder's first recovery
also dies part way (31 of 917 points persist; base: 0 of 452). A stalled RECOVERER or stalled ROLLBACK can also resurrect an account a later
holder legitimately deleted. Both are in the fencing/undo design this unit introduced. Two merge-time breaks with master (U8) are also found.

## Findings (numbered)

1. **BLOCK - a refused change survives a double fault: a second recoverer cannot undo a first write once the first recoverer already undid a later write to the same document.**
   `src/autotester/auth/store_mongo_tx.py:70-86` (`_replay`). Entries are replayed newest first; after an undo the document is stamped `stamp = fence` = `F:<recoverer epoch>` (:79).
   If recoverer R1 dies after replaying entry 2 of a document but before entry 1, R2 (a different epoch, `fence` = `F:<R2>`) replays entry 1 with
   `mine = {"$in": [entry["me"], "F:<R2>"]}` (:72), but the document is stamped `F:<R1>`; neither matches, the undo is a silent no-op and the entry is deleted (:100).
   Any operation that patches one document twice is exposed (here: `set_group_permissions` then `rename_group` on the Developer group).
   Reproduction (scratch, not committed: `.work/probe_chkB/test_probe_chkb.py::test_p3_double_fault_same_doc_patched_twice`): a transaction grants `users.manage`
   to the Developer group, renames the group, then raises; the store dies at call k (1..80) of that operation, lease aged out, the next writer dies at call j (1..80)
   of its recovery, lease aged out, then a reader and a second writer run. Output on a254af9c:
   `POINTS 917 BAD 31 [(23, 12, 'persisting'), (23, 13, ...), ...]` - the Developer group keeps `users.manage` AND the new name after the second writer, no journal left, the
   shape differs from before. Same probe on base 717aa180 (src from `git archive`, same helpers): `POINTS 452 BAD 0 []`. So this is introduced by U6bf.
   The new test only kills a single nested second death at `3 + k % 5` (tests/test_auth_store_fencing.py reader test), on an operation whose entries do not share a document.
   Needs: the undo condition must accept any later recoverer's stamp (for example a `F:` prefix match, or a stamp chain recorded in the entry), and a nested kill sweep over a
   same-document double patch in the suite (M29: a refused change leaves no trace; a privilege grant is the worst case).

2. **BLOCK - a stalled recoverer or rollback replays stale `del` entries over a newer state (resurrection of a deleted account).**
   `store_mongo_tx.py:85-86` (`insert_one({**entry["doc"], "_e": stamp})`, unconditional apart from a duplicate-key) and `:228-238` (`rollback`: `held()` is checked once, then
   `_resolve(..., None)`, which replays with no fence at all). `recover` (:104-110) and `rollback` do not re-check the lease or epoch between listing an entry and replaying it.
   Reproduction (`test_p1_stalled_recoverer_resurrects_a_deleted_account`): X dies after deleting account C (a `del` entry is left); Z takes the lease and, inside its recovery just before it re-inserts C,
   the lease is aged, S takes over, recovers (C restored), commits, and a legitimate `delete_user(C)` runs; Z then resumes. Output at every call point k=14..19 reached:
   `Z raised AuthStoreBusy` and `deleted account back: True`. Z is told it failed but has already written. This is the "stalled holder writes over a newer epoch" class the
   unit exists to close, in the one path (replay) that is not fenced. A `del` replay must be conditional on state it owns (for example insert only while a fence document for this entry exists and is still its own).

3. **Warning (merge) - master's U8 test imports a name this unit deleted.** `tests/test_cli_store_auth_creds.py:26` on master (468b3832) does
   `from autotester.auth.store_mongo_tx import JOURNAL_COLL, JOURNAL_ID, META`; U6bf removed `JOURNAL_ID` (constants at store_mongo_tx.py:32-37). `git merge-tree` of master and the branch is clean
   (tree 6efc55f6), but collecting that test on the merged tree gives `ImportError: cannot import name 'JOURNAL_ID'` (0 collected, 1 error). With `JOURNAL_ID = "journal"` patched in a scratch copy,
   14 pass and 1 fails: `test_a_second_apply_writes_nothing_and_keeps_the_allocator` (`rig.everywhere() == before` differs on the new `auth_meta/epoch` counter, `n: 2` vs `n: 4`,
   because every lease acquire (`_next_epoch`, store_mongo_tx.py:274-284) bumps the counter even for a no-op apply that the test also expects to be "written: 0"). The brief's requirement that this test
   "must stay green" is not met. The private helpers `_docs/_get/_writer/_insert/_patch/_drop/_allocate/_one/_grant` that `migrate_auth.py:44-117` calls kept their signatures. The fix belongs with the merge
   (U8's test, and the epoch counter excluded from the idempotence comparison), but the maker must own and report it; as it stands the integration is red.
   NOTE: `tests/test_cli_store_auth_creds.py` does not exist in this worktree (cut before U8), so running it here collects nothing; I ran it on a `git archive` of the merge-tree (scratch dir, worktree venv, PYTHONPATH).

4. **Warning - the tombstone is unverifiable against a real unique index (reasoned, not reproduced: the fake does not model it).** `_replay` :73-76 inserts a tombstone
   `{_id, kind, f, email, generation}` into whichever collection the entry names, inside `suppress(StoreDuplicateKey)`. `INDEXES` (`src/autotester/auth/store_mongo.py:27-29`) has a unique index on `auth_groups.name`.
   On real MongoDB a unique non-sparse index treats a missing field as null, so a second tombstone in `auth_groups` (no `name`) raises a duplicate-key error that `suppress` swallows, leaving that
   insert unfenced. `tests/fake_mongo.py:64-72` checks a unique field only when the document contains it, so no test can see this. Low reach (two fenced group inserts), but it is the fence failing silently.
   Give tombstones a `name` as they already carry `email`/`generation`, or stop swallowing duplicate-key for them.

5. **Info - A-W3 (writers wait behind a stalled holder): accept, with a correction.** `WAIT_SECONDS = 15.0 < LEASE_SECONDS = 30.0` (store_mongo_tx.py:38). A writer behind a stalled holder gives up with `AuthStoreBusy`
   after 15 s ("try again", :269-270); it does not wait 30 s and take over. Availability cost only, no integrity effect (the lease is never renewed; a transaction slower than 30 s is refused at the `held()` check).
   `Lease.__call__` (:61-62) ignores expiry, so an expired-but-untaken holder still passes `held()`; readers handle that through `dead_marker` (:113-120), which does check expiry. I accept A-W3 as documented; the manifest should say 15 s, not 30 s.

6. **Info - file size.** `store_mongo_tx.py` is exactly 300 lines (`wc -l` = 300), at the cap, not over (rule: <= 300). `store_mongo.py` is 299. Doctor is clean, so no function breaks the 50-line rule. There is no headroom: the fix for 1 and 2 needs
   a restructure or the second module D-126 already authorizes; the cap must not be raised or exempted.

## The five items from the brief (what I confirmed)
- (1) Single-fault stalled holder: the maker's tests pass, and my own hooks at held()/marker/entry/data-write points land nothing. The reachable holes are findings 1 and 2, both in recovery/rollback, not in the holder write path.
- (2) Reader recovery: `reading()` -> `dead_marker` -> `lease()` (store_mongo.py diff, store_mongo_tx.py:113-120) works for the single and one-nested-death cases the test covers; finding 1 is the double fault it does not cover.
- (3) Rehash parity: confirmed. The accounts.py diff makes `reset_password` and `bootstrap_admin` revoke first, and `set_password_hash`/`enable_with_password_hash` just write on both stores; `test_a_login_time_rehash_keeps_sessions_but_a_reset_revokes_them[sqlite|mongo]` passes.
- (4) Committed leftovers swept, never replayed: `_resolve` :95-101 (`committed` read from the marker); the `[reset|delete]` sweep tests pass.
- (5) A refused change leaves no trace: true for single faults; FALSE for the double fault in finding 1.

## Mutation survivors (maker's run at 4b12585b, 39/45; I re-ran f10, f12, f23 on a254af9c: `0/3 mutations killed`, same as recorded)
| Survivor | Judgement | Kill before PASS? |
|---|---|---|
| m3 rollback skipped on failure | Exit 1: killed by other tests (`test_an_exception_rolls_every_write_back`, the reader test). The named `test_a_refused_change_is_rolled_back_whole[mongo]` passes without rollback. Wrong kill list plus a weak named test | No (the suite kills it); fix the kill list |
| f10 journal replayed oldest first | `test_several_writes_to_one_document_are_undone_newest_first` does not fail; only `test_an_exception_rolls_every_write_back` does. Real gap in the test that names this behaviour, and it is the scenario of finding 1 | Yes: the named test must fail, and the double-fault same-document sweep added |
| f12 undo ignores the fence stamp (`mine` = `entry["me"]` only) | After the fence step the content equals the pre-state, so the undo is a no-op in the same call; behaviourally equivalent in the covered paths. The stamp clause is what finding 1 breaks across recoverers, so the real fix may change it | No as written (equivalent); revisit with the fix for 1 |
| f23 rollback runs without owning the lease | Real gap: the stalled-holder rollback test does not fail without the `held()` check, so the unfenced rollback replay (finding 2) is untested | Yes |
| f25 write not fenced by the lease (C1 removed) | C2 after the entry still refuses the write, so it is data-level equivalent (only a stray marker/entry for the next holder). Wrong kill list | No; drop it, or assert no marker is written by a lost holder |
| f28 every inserted document journalled with its hash | The journal sits in `auth_users`, so M30 (argon2 only in `auth_users`) still holds; bloat, not a leak. Test is weak, mutant harmless to the contract | No; drop it, or make the test assert the entry carries no document body |

Required kills: **f10** and **f23**, plus the new double-fault and stalled-replay tests for findings 1 and 2.

## Commands run (worktree D:/autoTesting/.claude/worktrees/mongo-u6bf; `env -u ANTHROPIC_BASE_URL`, `-o addopts=`, at most 2 files per call)
```
uv run pytest tests/test_auth_store_fencing.py tests/test_auth_store_recovery.py -o addopts=  -> 32 passed
uv run pytest tests/test_auth_store_mongo.py tests/test_auth_store_contract.py -o addopts=    -> 58 passed
uv run pytest tests/test_cli_store_auth_creds.py -o addopts=                                  -> collected 0 items (file absent on this branch)
git archive of merge-tree 6efc55f6 + PYTHONPATH: tests/test_cli_store_auth_creds.py           -> 1 error: ImportError JOURNAL_ID
   same, JOURNAL_ID patched in the scratch copy                                               -> 14 passed, 1 failed (second_apply_writes_nothing: epoch n 2 vs 4)
uv run ruff check --no-cache src tests scripts                                               -> All checks passed!
uv run autotester doctor > .work/doctor-chkB.txt                                              -> "doctor: clean" (advisory D-087 notes only)
scripts/mutation_check.py on f10,f12,f23 subset                                              -> 0/3 mutations killed
probe test_p3 double fault, U6bf a254af9c                                                    -> POINTS 917 BAD 31
probe test_p3 double fault, base 717aa180                                                    -> POINTS 452 BAD 0
probe test_p1 stalled recoverer                                                              -> deleted account back: True (k=14..19)
```
The full 45-mutant rerun was not repeated (about 45 minutes; memory limit); I read the maker's recorded run and re-ran the survivors I judged. No `.env` value was printed or read. Scratch probes are in `.work/` (gitignored), not committed.

## What would make this PASS at cycle 1
1. Fix finding 1 and add a nested double-fault sweep over a same-document double patch (and the `del`/`ins` mixes) to the suite; the probe must show `BAD 0`.
2. Fix finding 2 (a replay and a rollback must be fenced against a later epoch), with a test that fails when the fix is removed (kills f23 and f10).
3. Make the merged U8 test green (keep `JOURNAL_ID` or update the test, and exclude `auth_meta/epoch` from the idempotence comparison) and report it.
4. Resolve finding 4 (tombstone on a real unique index) or state why it cannot occur.
