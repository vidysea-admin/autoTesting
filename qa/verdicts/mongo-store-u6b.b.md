# Verdict (checker B) - mongo-store-u6b

**Unit:** mongo-store U6b (auth store on Mongo), dual-checked, CRITICAL. **Criteria:** M29, M30 (U6b row), with `auth.md` AU7/AU9/AU11/AU16/AU21.
**Cycle checked:** 2
**Head checked:** `fe1b9844` on `feat/mongo-store-u6b` (worktree `D:/autoTesting/.claude/worktrees/mongo-u6b`). Fresh checker: re-ran every claim; read only my own cycle-1 verdict, no other checker's verdict.
**Verdict:** **PASS** (with 3 warnings and 3 informational notes; none is a Block against M29/M30). Warning 1 is the residual stalled-holder window and must be closed before a multi-instance / G1 flip (see finding 1).

## Q1 - did the write-ahead journal close B1? Yes, for every crash and outage model I could build

B1 (cycle 1, checker A): a crash between a refused change's write and its rollback left no Admin/CEO member and any signed-in account could `claim_admin`.
The journal (`store_mongo_tx.py:97-113` `_log`, `:52-77` `_replay`/`recover`, `:201-213` `lease`) writes an undo entry in `auth_users` BEFORE each write,
inserts the commit marker `auth_meta/journal` lazily, and every lease acquire (fresh or takeover) runs `recover(store)` before yielding. Commit = CAS delete of the marker (`:139-153`).
Reading the code I looked for: a replay that is not idempotent (`ins` delete-by-id, `set` CAS on `after`, `del` re-insert tolerating a duplicate: all idempotent), a recovery that loses its place
on a crash (entries are deleted one by one AFTER being replayed, the marker last: resumable), a second fault inside recovery (see below), and an `ins` undo that could delete a pre-existing document
(every inserted `_id` is a fresh allocated id, a session digest, or a grant id guarded by `_get` first, `store_mongo.py:228-231`; `replace_project_owner` drops before it inserts, journalled in order). None found.

### My own crash harness (not the maker's)
`probe_u6b_b2.py` in the session scratchpad (outside the repo; nothing under `src/` or `tests/` was edited). It differs from the maker's `_sweep` in four ways:
1. **Six refused operations on the SOLE admin**, two more than the maker's four: `set_user_groups(a, [])`, `delete_user(a)`, `set_disabled(a, True)`, `update_group(developer, +users.manage, member 99999)`,
   **`update_group(Admin/CEO, no permissions)`** and **`delete_group(Admin/CEO)`**. Plus `claim_admin` on an empty Admin group, `reset_password`, `bootstrap_admin`.
2. **Five outage shapes per call point k**: dead for good from call k, and an outage window of exactly m = 1, 2, 3, 6 calls (the store comes back; the rollback/lease release may or may not fall in the window). The lease is then aged out.
3. **Death DURING recovery (nested)**: after a permanent death at call k, the next writer (`set_display_name`, which acquires the lease and runs `recover`) is itself killed at every one of its own call points j, then the lease is aged again and a third writer runs; the raw pre-recovery state is restored for each j.
   This includes "between the journal write and the data write", "between replay and entry delete", "between the last entry delete and the marker delete" (call counting visits every database call).
4. Each point asserts: `claim_admin` by a non-admin is refused; the user/group shape equals the pre-state exactly; an enabled Admin/CEO member remains; `$argon2` appears only in `auth_users` (M30). Password operations: exactly one of old/new password works, the session survives iff the old password works, claim refused, shape unchanged.

Call points reached (k): set_user_groups 19, delete_user 19, set_disabled 18, update_group 31, strip_admin_perm 39, delete_admin_group 31 (x5 outage shapes), plus **2,975 nested (k,j) cases** (357+365+344+585+729+595 per op family).
Result: **`FAILS 0`** (`.work/probe-u6b-b2.txt` in the worktree; the file is mostly the store's own "lease not released / rollback deferred (StoreUnavailable)" log lines, which carry only the exception class name).

### The harness is not vacuous: six crash mutants of my own, all caught
Run as `MUT=<name> uv run python probe_u6b_b2.py` (monkeypatching `store_mongo_tx`; output `.work/probe-mutants-u6b-b2.txt`):

| Mutant | Result |
|---|---|
| recovery not run at lease acquire | probe crashes (the claim succeeds over a half-applied change) |
| recovery deletes the marker before replaying | `FAILS 452` (claim by non-admin succeeded, shape differs) |
| recovery deletes each entry before replaying it | `FAILS 420` |
| `_patch` writes first, journals after (write-ahead reversed) | `FAILS 546` |
| `commit` sweeps entries before deleting the marker | `FAILS 6` (reset_password / bootstrap_admin session/password mismatch) |
| `del` undo does not re-insert | `FAILS 1476` |

## Q2 - M30: hashes in the journal

Entries live in `auth_users` (`store_mongo_tx.py:27`, `:110-112`; `email` and `generation` carry the key so the unique indexes accept them). In all 2,975+ crash/outage points above `$argon2` appeared only in `auth_users`
(the check inside `check_refused`; a miss would have been a FAIL). `test_the_journal_holds_hashes_only_beside_the_users` (`tests/test_auth_store_recovery.py:281`) asserts it mid-transaction. Logs: the only `LOG` calls
(`store_mongo_tx.py:153`, `:165`, `:213`) print `type(exc).__name__`; no hash, no value, no URI. Journal entries are filtered out of every account read (`_docs`, `:87`); `find_user`/`login_record` use the unfiltered `_one`
but an entry's `email` is `undo:<owner>:<n>`, which `normalize_email` can never produce, so no entry is addressable as an account. **M30 holds.**
Side effect worth knowing (warning 3): a sweep that fails after commit leaves the old hash / a deleted user's whole document in `auth_users` indefinitely.

## Q3 - the stalled holder and the residual TOCTOU (judged)

The three fences hold as described: `_log` checks `held()` before every write (`:100-102`), rollback replays only while the lease is still owned and only its own journal (`:155-165`), a `set` undo is a CAS on the value it wrote
(`:59`), commit is a CAS delete of the marker (`:145-147`). The maker's tests and my reading agree; `test_a_stalled_holders_rollback_leaves_a_live_successor_alone` etc. pass.

**The residual window is wider than the manifest says and ends in the B1 outcome.** The manifest (flag 5) describes "`held()` is checked, then the write happens". In the code the window is `held()` -> marker insert -> entry insert -> data write
(up to three database calls). I reproduced it deterministically (`probe_zombie.py`, scratchpad): holder A runs `set_user_groups(sole_admin, [])`; at the moment of (a) the entry insert, and separately (b) the data `update_one`, the lease is aged out and
a successor writer takes over, recovers (deleting the marker) and commits. A then finishes its single write. Output:

```
held_to_entry op raised LastAdmin
held_to_entry fired True admins after: 0 | claim by C: SUCCEEDED (privilege escalation window)
between_entry_and_write op raised LastAdmin
between_entry_and_write fired True admins after: 0 | claim by C: SUCCEEDED (privilege escalation window)
```

The orphan is never recovered (the marker and entry are gone) and A's rollback is skipped because `held()` is false. This is exactly the B1 end state, reached by a different road.
**Ruling: WARNING, not Block**, because it needs ALL of: (1) one database call of a write transaction stalling more than 30 s (pymongo's selection timeout is 5 s in the guard; this is a socket-level stall or a stop-the-world pause),
(2) a second writer that arrives only after the 30 s expiry (it waits at most 15 s, `WAIT_SECONDS`, so it must start waiting between t=15 s and t=30 s of A's stall), (3) the stalled transaction being a refused last-admin change, (4) `--max-instances 1` today (M28) so the second writer
is a thread of the same process. B1 itself was reachable by an ordinary crash or outage; this is three coincidences. The maker disclosed the class (flag 5) but under-described its width and said it is "not closable without a fencing token"; it is closable
in effect (see "Recommended", below). It MUST be closed before G1 raises `--max-instances` or the auth area is flipped on a multi-process deployment; I recommend recording it as an open issue with that gate.
Recommended close: (a) after every data write re-check `held()` and, if the lease is gone, undo that write from the in-hand `old`/`doc` (a CAS), narrowing the window to the re-check; (b) put the lease owner into the written document and have `recover` also sweep documents stamped by a dead owner; or (c) pass `maxTimeMS` on every write so a stalled call fails well inside 30 s.

## Q4 - sessions revoked before the new hash

`store_mongo.py:80-86`: `set_password_hash` and `enable_with_password_hash` call `delete_user_sessions` first. `test_sessions_are_revoked_before_the_new_hash_is_written[reset_password|bootstrap_admin]` kills on raw state with no recovery and
asserts "new hash implies no live sessions" (passes). My sweep: for reset_password and bootstrap_admin, across 5 outage shapes, always exactly one password works and the session survives iff the old password works. **Holds.**
**But it introduced a behaviour change (warning 2):** `set_password_hash` is also called by the login-time rehash (`accounts.py:128`, `authenticate`), where SQLite does NOT revoke sessions (`store_sqlite.py:79-81`). Probe: an account whose stored hash needs
rehash, two live sessions, one `authenticate()` -> `rehash: other sessions survive the login-time rehash: False False`. On Mongo a legacy-parameter login signs the user out of every other device; on SQLite it does not. The business modules already purge in the reset paths
(`accounts.py:167`, `:254`), so the purge inside the store is redundant there and wrong for rehash. M29 makes SQLite the oracle. Fix: do the purge-first in `accounts` (`_update` ordering for reset_password, `bootstrap_admin`), not in `set_password_hash`. No test pins this divergence either way.

## Q5 - a global `AUTOTESTER_STORE=mongo` keeps auth on SQLite

`store.py:92-110`. `_auth_on_mongo()` over eight inputs (scratch script, repo venv): `STORE=mongo` with areas empty -> False; `mongo` + `auth=file` -> False; `mongo` + `settings=mongo` -> False; `mongo` + `auth=mongo,auth=file` -> False (last entry wins);
`""` + `auth=mongo` -> True; `file` + `auth=mongo` -> True; `""` + `auth=file,auth=mongo` -> True; `mongo` + ` auth = mongo ` -> True. `test_a_global_mongo_selection_does_not_move_auth` and the updated `test_a_mongo_selection_yields_the_mongo_store` pass. **Holds.**
Cold-start check (M13): the Mongo module still loads lazily (`store.py:106-108`); `test_a_file_mode_process_never_imports_the_driver` passes.

## Q6 - removed or changed existing tests

`git diff 797d03cd fe1b9844 -- tests/` : two edits to existing tests, no other test file touched.
1. `test_a_mongo_selection_yields_the_mongo_store` (`test_auth_store_mongo.py`): the second assertion flips from "global STORE=mongo yields Mongo" to "yields SQLite". An intentional behaviour change (A-W1), pinned by the new recovery test as well. Not a weakening.
2. `test_a_lease_lost_mid_transaction_rolls_the_transaction_back` removed; recreated in `test_auth_store_recovery.py:228` as `test_a_lease_lost_mid_transaction_is_undone_by_the_next_holder`. The old test asserted the write was gone immediately after the failed transaction; the new one asserts it is gone after the next holder takes the lease
   (the lost-lease holder no longer rolls back, `store_mongo_tx.py:162`). That is a real loosening of the immediate guarantee (readers can see the zombie's write until the next writer), consistent with the design, but it is weaker than the old assertion. Informational (note C).
New file `tests/test_auth_store_recovery.py` (288 lines) is allowed by the brief; I confirmed it contains the sweeps the manifest names.

## Commands run (all in the worktree; no `.env` value read or printed)

| # | Command | Result |
|---|---|---|
| 1 | `env -u ANTHROPIC_BASE_URL uv run pytest tests/test_auth_store_recovery.py tests/test_auth_store_seam.py -o addopts= -q -p no:cacheprovider` | `31 passed` |
| 2 | same, `tests/test_auth_store_mongo.py tests/test_auth_store_contract.py` | `58 passed` |
| 3 | same, `tests/test_state_selection.py` | `23 passed, 1 skipped` (empty `UNROUTED` parametrization) |
| 4 | `uv run ruff check --no-cache src tests scripts` | `All checks passed!` |
| 5 | `env -u ANTHROPIC_BASE_URL uv run autotester doctor > .work/doctor-u6b-b2.txt` | `doctor: clean`, rc 0 (only advisory decision-citation warnings). Sizes: `store_mongo.py` 297, `store_mongo_tx.py` 213, `store.py` 110, `test_auth_store_recovery.py` 288 (all <= 300) |
| 6 | `uv run python scripts/mutation_check.py qa/evidence/mongo-store-u6b/mutations.json --repo .` > `.work/mutation-u6b-b2.txt` | `32/32 mutations killed`, 32 KILLED, 0 SURVIVED, rc 0; worktree clean afterwards (`git status --short` empty) |
| 7 | `probe_u6b_b2.py` (my crash/outage sweep, nested faults) | `FAILS 0` across all families; see Q1 |
| 8 | `MUT=<six mutants> probe_u6b_b2.py` | all six caught (table in Q1) |
| 9 | `probe_zombie.py` | stalled-holder window reproduced (Q3); rehash divergence reproduced (Q4) |
| 10 | `_auth_on_mongo()` over 8 env combinations | Q5 table |

Scratch scripts (`probe_u6b_b2.py`, `mutants.py`, `probe_zombie.py`) are in `C:/Users/Lenovo/AppData/Local/Temp/claude/D--autoTesting/dc6b1ba4-60cc-4209-9cdc-762cbc8dd078/scratchpad/`, outside the repo. Run once concurrently with a second mutation run of the same spec that I had started by mistake (both finished 32/32); no test count was affected.

## Findings

1. **WARNING (M29, stalled holder; must close before multi-instance/G1):** a holder stalled more than 30 s anywhere in `held()` -> marker -> entry -> data write, with a successor taking over and committing in that window, leaves one orphan data write that is never recovered (`store_mongo_tx.py:100-113`, `:162`). Reproduced to the B1 end state: zero admins and a non-admin `claim_admin` succeeds. Needs a 30 s+ database stall plus a late second writer plus a refused last-admin change; single instance today (M28). Fixes in Q3.
2. **WARNING (M29, behaviour divergence from the SQLite oracle):** `set_password_hash` now revokes all of the user's sessions first (`store_mongo.py:80-82`), so the login-time rehash (`accounts.py:128`) signs the user out of every other device on Mongo only. Reproduced (Q4). Move the revoke-first ordering into `accounts` (reset_password, bootstrap_admin) and add a contract test that a rehash login keeps other sessions on both backends.
3. **WARNING (M30 hygiene / at-rest retention):** if the post-commit sweep fails (`store_mongo_tx.py:149-153`) the entries stay in `auth_users` forever (nothing reads or deletes them): an old password hash after a reset, or the full document (hash included) of a deleted account. They are in the allowed collection, but retaining a deleted user's hash is a data-lifecycle defect. Add a sweep of `kind == "undo"` entries whose owner has no marker, at the lease acquire (one `delete_many` scoped by `p`/`k` per M6, or loop `delete_one`).
4. **INFO (carried, accepted):** a crashed holder blocks writers until its lease expires (<= 30 s), and readers take no lease, so an unrecovered refused change is visible to readers until the next writer (A-W3). In my sweep this window exists after every kill point and closes at the next writer's acquire; I did not count it against M29 because no writer can act on it (every privileged action is a write), but a reader-derived principal (`live_principal`, `store_mongo.py:202-209`) does see the intermediate permissions in that window.
5. **INFO:** the `mongo_backend._CACHE/_AUTH` cold-start race (A-W4) is U9's, as the manifest says; not re-tested.
6. **INFO (C):** the lost-lease rollback is now deferred to the next holder rather than immediate (Q6 item 2).

## Mapping to the criteria

- **M29:** concurrent-signup / last-two-admins / generation / id allocator / hash-only-sessions all green in the 58+31 passing tests, and the new crash-survival evidence above. The lease+journal still satisfies the "no transactions assumed" wording (cycle-1 ruling stands; the contract owner should still amend the parenthetical).
- **M30:** holds (Q2).
- **Next step:** PASS stands; the dual verdict is the coordinator's. Warnings 1-3 should be filed in `qa/issues.jsonl` with warning 1 gated on any increase of `--max-instances` or the G1 auth flip.
