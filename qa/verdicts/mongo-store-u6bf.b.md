# Verdict (checker-B) - mongo-store-u6bf (U6bf, auth store on Mongo fix-up), fix cycle 1

**Cycle checked:** 1
**Verdict:** PASS (with 2 Warnings the maker must carry into the close-out, no Block)
**Head checked:** 023d07e2 (code 375b2774, master 468b3832 merged). Fresh, independent; the other checker's verdict was not read. Cycle 0 of this file is in git history (5408c34e).
**Criteria:** M29, M30 (U6b/U6bf) and the four cycle-0 findings (B1, B2, A2 f10/f12, A3/B4).

## Summary
All four cycle-0 blockers are closed on the code I ran: the double-fault keeps no refused grant, a late replay or rollback cannot bring back a deleted
account, f10 and f12 now die on named tests, and the group tombstone carries a placeholder `name`. I could not break the new design with 1,022 + 2 x 665
interleavings that the maker's matrix does not name (two recoverers plus a writer, sweeping both the first death and the second recoverer's pause point), and
12 of the maker's mutants plus 2 of my own die on named tests. Two real gaps remain, neither a regression against base 717aa180 and neither a Block:
a zombie INSERT can still land after its tombstone was cleared and the row revoked (Warning 1, deterministic grant ids only), and the commit-vs-abort CAS
ordering has no test (Warning 2).

## Findings (numbered)

1. **Warning - a stalled holder's late INSERT lands once a later holder has cleared its tombstone and then revoked the row. Reproduced.**
   `src/autotester/auth/store_mongo_tx.py:178-195` (`_insert`) clears a `FENCE` tombstone whose `f <= held.epoch` and re-inserts; `:68-76` (`_replay`) leaves the tombstone as the
   only barrier against the dead holder's insert. After a LEGITIMATE holder clears the tombstone and a later one deletes the row (physically, at commit), nothing is left to refuse the zombie.
   Probe `.work/probe_chkb1/test_probe_chkb1.py::test_p1_zombie_insert_after_tombstone_cleared_and_grant_revoked`: Z = `add_project_relation("proj", B, "viewer")` paused just before its
   `auth_grants` insert; lease aged; S1 = any write (recovers Z, leaves the tombstone); S2 re-grants the same grant (clears tombstone, inserts); S3 `remove_project_relation`. Output:
   `BEFORE ZOMBIE RESUMES: {}` / `Z raised AuthStoreBusy the auth store lease expired mid-transaction` / `PEOPLE after zombie: {'viewer': {'dev@team.test'}}` (assert people == {} fails).
   Z is told it failed, but the revoked grant is back and no journal entry covers it (its entry was deleted by S1). Scope: only ids that are deterministic and re-creatable (`auth_grants`
   `slug|user|relation`, `store_mongo.py:221`); user, group and session ids come from the allocator or are random, so their tombstones are never cleared and those paths stay closed.
   Needs a stall of more than one lease across three further transactions, at one instruction. The manifest's residual (a) says the tombstone "is cleared by the same or a later epoch" but
   not that this reopens the zombie's landing, and the closure argument ("D cannot land", case 2) does not hold past that clear. Required: either record it as an accepted residual in the
   manifest and contract (it is the fencing-token limit for an insert into an absent row), or close it (for example never clear the tombstone: replace it in place with a conditional update, and
   keep a delete of a deterministic id as a tombstone). The 300-line cap leaves no room in this module, so a fix needs the second module D-126 already authorizes. Not a regression: base has no fence.

2. **Warning - the order "abort CAS, then read the marker" in `_resolve` has no test; a mutant that swaps them survives all 98 tests of the five auth suites.**
   `store_mongo_tx.py:93-94`. Mutant x2 (my own: read the marker BEFORE the `open -> aborted` CAS) lets a commit that lands between the two be treated as uncommitted and its entries replayed,
   i.e. undoing a committed change (needs Z's post-commit sweep to have failed so the entries are still there). My probe `test_p5_commit_racing_the_recovery_cas_stands` (pause at S's abort-CAS, Z commits with a failing sweep)
   passes on the real code and kills x2. Runs: `x2s NOT-KILLED(rc=0) ... 98 passed` (maker suites), `x2 KILLED` (probe). The code is right; the guarantee that carries the commit/abort race is untested.
   Required before the next dual check, not before PASS: add p5 (about 20 lines) to `tests/test_auth_store_fencing.py`.

3. **Info - the maker's judgement calls, weighed.**
   (1) *U8 test excludes only the epoch counter* (`tests/test_cli_store_auth_creds.py` `_without_the_epoch`, `_epoch`): accepted. Everything else (accounts, groups, grants, allocator, sessions, all databases) is still compared
   byte for byte, and the test now also asserts the epoch advanced, so the exclusion cannot hide a stuck counter. The alternative (skip the lease on a no-op) would weaken the fence. The `commit` spy asserts an `open` marker existed, so the old vacuous line-89 check is replaced by a real one. 33 passed.
   (2) *delete-then-reinsert of one id/unique key in one transaction is now unsupported*: I checked every `_drop`, `_drop_where`, `_insert` and `add_project_relation` call in `store_mongo.py` (lines 76, 93-97, 128, 134-135, 185, 191-199, 224-233, 258) and the transaction bodies in `accounts.py`, `groups.py`, `access.py`
   (`set_owner`, `set_relation`, `delete_group`, `delete_user`, `reset_password`, `bootstrap_admin`). The only caller that did drop-then-insert of the same grant id was `replace_project_owner`; it now drops `user_id $ne` and goes through `add_project_relation`. No other caller pairs a drop with an insert of the same id or unique key
   (sessions are random digests, users/groups allocator ids, `delete_user_sessions` precedes only writes to other documents). All reads in `store_mongo.py` go through `_docs/_one/_get` which hide `G:` and tombstones (grep: only 3 raw `find_one` calls, all on `auth_meta`). Accepted.
   (3) *f11 kill list* `[before-a-patch]`, `[before-a-delete]`: honest. Run separately: f11 vs `before-a-patch` KILLED, vs `before-a-delete` KILLED, vs `before-its-second-write` NOT killed (y1, rc=0), vs `before-an-insert` NOT killed (y3, rc=0). Not a weakening: the second-write case there is covered by f12 (KILLED by exactly that case). Accepted.
   The wait is 15 s (`WAIT_SECONDS`, `:38`), lease 30 s; the manifest now says so.

4. **Info - test stability under load.** On 2 of 9 whole-file runs on this loaded machine (other agents' pytest running, one of my own runs overlapped by accident) tests failed: first run of `test_auth_store_double_fault.py` (1 failed 6 passed, test `..._insert_then_a_patch_of_one_document_is_recovered_whole_or_absent`), and
   `test_auth_store_recovery.py::test_a_password_change_killed_anywhere_is_whole_or_absent[...]` / `test_sessions_are_revoked_before_the_new_hash_is_written[...]` (4 failed, `_sweep` returned 0 or "neither password works", i.e. argon2 returned nothing; `doctor` also hit `MemoryError` twice at import).
   Clean sequential re-runs: double_fault 7 passed x4 (24 s, 14 s, 10 s, 9 s), fencing+recovery 33 passed (72 s). I judge these environmental (memory exhaustion, same as the maker's note about argon2 `Memory allocation error`), but I did not capture the first failure's traceback, so I cannot rule out a load-dependent flake. G1 should run these on a quiet host.

5. **Info - file sizes and cap.** `store_mongo_tx.py` is 300 lines (`wc -l`), `store_mongo.py` 299; the cap is respected with no headroom. Test files: fencing 268, double_fault 234 (new test file, flagged by the maker, fine). Doctor clean.

6. **Info - pre-existing failure.** `tests/test_cli_advice_resolves.py::test_the_collector_reports_what_it_could_not_resolve` fails on master 468b3832 (clean `git archive`) with TWO unresolved sites, `auth/store_mongo_tx.py:109` and `store/mongo_backend.py:73`; on the branch only `store/mongo_backend.py:73` remains (the cycle 0 plain-constant fix removed the tx site). Not counted against this unit.

## Cycle-0 findings, closed or not
| Finding | State | Evidence |
|---|---|---|
| B1 double fault keeps a refused grant | CLOSED | `test_a_recovery_killed_at_any_call_is_finished_by_the_next_one` passes; mutant b1 KILLED by it; my P2 sweep (below) 0 bad |
| B2 late replay / rollback resurrects a deleted account | CLOSED for accounts, groups, sessions; OPEN as Warning 1 for deterministic grant ids | `..._does_not_bring_back_an_account_deleted_since[recovery|rollback]` pass; b2a KILLED; my P3 sweeps 1,330 points 0 bad; P1 shows the grant residual |
| A2 f10, f12 survivors | CLOSED | f10 KILLED by `..._insert_then_a_patch_of_one_document_is_recovered_whole_or_absent`; f12 KILLED by `[before-its-second-write]` |
| A3/B4 tombstone unique-name null clash | CLOSED | `tests/fake_mongo.py:66-72` now uses non-sparse null semantics (diff read); a3/a3b run: not re-run by me, see "not done" |
| U8 integration (JOURNAL_ID, epoch) | CLOSED | `test_cli_store_auth_creds.py` 33 passed with `test_cli_store_state.py` |

## Adversarial probes (mine, not committed; `.work/probe_chkb1/test_probe_chkb1.py`, run from a `git archive` copy with `PYTHONPATH=<copy>/src`)
- **P2, two recoverers and a writer.** Z = `_grant_rename_refuse` (grant `users.manage` + rename, then refuse) killed at call k0 (every point, 1..N); lease aged; recoverer R1 (a plain write) is PAUSED (not killed) just before its k-th database call, and while it sleeps the lease is aged, R2 recovers fully and a writer W commits a rename plus a permission change on the SAME group document; R1 then resumes. Last holder runs. Asserted: no `users.manage`, name == `Legit`, W's permission present, no journal. `POINTS 1022 BAD 0`.
- **P3, same with an account.** Z deletes account C and renames it, refuses; same interleaving; W either deletes C or renames it. Asserted: C absent (not even hidden) / C == `W` and visible, no journal. `POINTS delete 665 BAD 0`, `POINTS rename 665 BAD 0`.
- **P1** above (Warning 1). **P4** (a stalled post-commit physical delete of a grant, a successor sweeps, a later holder re-grants, the stale delete resumes: the re-grant must survive) passes on the real code and kills my mutant x1. **P5** passes on the real code and kills x2 (Warning 2).

## Mutants
Run from a `git archive` copy of HEAD (script `.work/probe_chkb1/mutrun.py`, applies the recorded `old`->`new`, runs the NAMED kill tests with `-x`, exit 1 = killed).
| Mutant | Result | Killed by |
|---|---|---|
| f10 oldest-first replay | KILLED | `test_auth_store_double_fault.py::test_an_insert_then_a_patch_of_one_document_is_recovered_whole_or_absent` |
| f11 dead holder's doc not fenced | KILLED | `test_auth_store_fencing.py::..._ran[before-a-patch]` (and `[before-a-delete]` separately) |
| f12 undo ignores the F: stamp | KILLED | `..._ran[before-its-second-write]` |
| f23 rollback without owning the lease | KILLED | `test_a_rollback_that_lost_its_lease_writes_nothing` |
| f25 write not fenced by the lease | KILLED | `test_auth_store_recovery.py::test_a_stalled_holder_writes_nothing_once_the_lease_is_gone` |
| b2c deleted document stays readable | KILLED | `test_a_refused_change_survives_a_kill_at_every_call_point[delete_user]` |
| b1, b2a, b2b, f9, f26, f27 (extra) | all KILLED | `..._finished_by_the_next_one`, `..._bring_back_an_account_deleted_since[recovery]`, `..._swept_by_the_next_holder[delete]`, `..._cannot_commit_while_its_journal_is_being_undone`, `test_an_undo_never_overwrites_a_newer_value`, `..._kill_at_every_call_point[delete_user]` |
| **x1 (mine)** the post-commit physical delete not conditional on the `G:` stamp (`:101`) | KILLED | by the maker suite (`..._swept_by_the_next_holder[delete]`) and by my P4 |
| **x2 (mine)** marker read before the abort CAS (`:93-94`) | **SURVIVES the maker suites (98 passed)**; KILLED by my P5 | Warning 2 |
| **x3 (mine)** the replay undo of a `set` not conditional on the stamp (`:86`) | KILLED | `test_an_undo_never_overwrites_a_newer_value` |
Y-runs for the f11 kill list: see Finding 3(3).

## Commands run (worktree D:/autoTesting/.claude/worktrees/mongo-u6bf; `env -u ANTHROPIC_BASE_URL`, `-o addopts=`, at most 2 files per call, one at a time except the accident noted in Finding 4)
```
pytest tests/test_auth_store_double_fault.py                                  -> 7 passed (clean runs x4; one earlier run under load 1 failed 6 passed, Finding 4)
pytest tests/test_auth_store_fencing.py tests/test_auth_store_recovery.py     -> 33 passed in 72.52s (clean run)
pytest tests/test_auth_store_mongo.py tests/test_auth_store_contract.py       -> 58 passed in 69.52s
pytest tests/test_cli_store_auth_creds.py tests/test_cli_store_state.py       -> 33 passed in 16.52s
uv run ruff check --no-cache src tests scripts                                -> All checks passed!
uv run autotester doctor > .work/chkb1-doctor.txt                             -> "doctor: clean" (exit 0; first two attempts MemoryError at import, host memory)
pytest tests/test_cli_advice_resolves.py   (master 468b3832 archive)          -> 1 failed 40 passed; sites store_mongo_tx.py:109 and mongo_backend.py:73
pytest tests/test_cli_advice_resolves.py   (branch)                           -> 1 failed 40 passed; site mongo_backend.py:73 only
wc -l store_mongo_tx.py store_mongo.py                                        -> 300, 299
```
Not done: mutants a3, a3b and the remaining ~30 of the 51 were not re-run (I ran 15 of the maker's plus 3 of mine plus 4 f11 variants); the `.work/chkb1-*` logs hold the full output. No `.env` value was read or printed. Nothing merged or pushed.

## What the maker must do next
1. Warning 1: record the zombie-insert-after-clear residual for deterministic grant ids in the manifest and contract (or fix it); say which.
2. Warning 2: add the P5 test (commit racing the abort CAS) to `tests/test_auth_store_fencing.py`; re-run mutant x2.
3. G1 dual check: run the five auth suites on a quiet host once more (Finding 4).
