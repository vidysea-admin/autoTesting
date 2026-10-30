# Verdict - mongo-store-u6b (Checker A)

**Cycle checked:** 1
**Verdict:** FAIL (one Block, B1: a crash or store outage between a refused change's write and its rollback can leave the store with no Admin/CEO member, after which any signed-in account can claim admin; reproduced). Everything else the brief asked for holds.
**Unit:** U6b (`qa/contracts/mongo-store.md`, criteria M29 and M30; auth.md AU7/AU9/AU11/AU16/AU21). Branch `feat/mongo-store-u6b`, head `797d03cd` (manifest says fix cycle 1; D-126 authorizes `auth/store_mongo_tx.py`).
**Role:** Checker A. U6b is dual-checked (D-100); this is one half. I did not read any other checker's verdict on this unit.
**Method:** fresh context; read-only toward `src/` and `tests/`; claims re-run; at most two test files per pytest call, one call at a time, `env -u ANTHROPIC_BASE_URL`; no `.env` value read or printed (probes set `AUTOTESTER_ROOT` to a temp dir). Probe scripts (scratch, not committed): `C:/Users/Lenovo/AppData/Local/Temp/claude/D--autoTesting/dc6b1ba4-60cc-4209-9cdc-762cbc8dd078/scratchpad/probe_crash.py`, `probe_race.py`, `probe_r2.py`, `probe_3.py`, `probe_4.py`, `probe_5b.py`; outputs in the worktree `.work/chk-a-*.txt`.

## Ruling on the four asked questions

1. **M29 lease vs the contract wording: PASS on the wording, FAIL on crash safety (B1).** The lease (`auth/store_mongo_tx.py:100-135`) uses only single-document atomic primitives (unique-`_id` insert; compare-and-set takeover on `(owner, expires)`), so it satisfies "no transactions assumed". It is stronger than the `create_exclusive` + `admin_guard` CAS the text names, and it meets M29's stated falsifiers (races below). I rule the lease an acceptable realisation, and recommend the contract text be amended to say "a single-writer lease" so the wording and the code agree. It does not give atomicity across a crash: the undo log is in process memory (`store_mongo_tx.py:41,78-84`), so anything that stops the process or the store between a write and its rollback leaves a half-applied change (see B1).
2. **UNROUTED merge: clean.** Master `fe1ac6c8` had `UNROUTED = {"auth": "the auth store (U6)"}` and nothing else; the branch value `{}` (`store/mongo_routes.py:28`) drops exactly that entry. Its only consumer is `store_selection` (`mongo_routes.py:241`). See W1 for a behavioural side effect.
3. **URI: PASS.** No `AUTOTESTER_MONGO_URI` read in `src/` (grep: only tests and docs mention it). Missing URI raises `StoreSelectionError` "PATHLYNKS_MONGO_URI is not set; the store needs it", with a canary value in the legacy variable not echoed. One client per process in sequential use; `rearm` keeps the same auth store; `reset_default_backend` drops it. See W4 for the cold-start concurrency caveat.
4. **AU16 narrowing: honest.** I snapshotted the whole fake server (all databases, docs and indexes). Opening the shared client writes the state-area indexes and marker (U9, 42 collections, none `auth_*`); after that `exists()`, `resolve_session` and `end_session` on an empty store change nothing at all, and no `auth_*` collection holds a doc or index. The narrowing excludes U9's open-time writes, not an auth write. (`reading()` on a missing store does seed, as the SQLite `db.reading()` path does; callers gate on `exists()`: `access.py:51`, `sessions.py:55,68`.)
5. **Cycle-0 limits: acceptable as Warnings** (readers without a lease only lower privilege on a refused change; membership scans are O(users) at auth scale), except the crash limit, which is B1.

## Findings

### B1 (BLOCK) - Crash or store outage mid-transaction can leave zero Admin/CEO members, and then any signed-in account can claim admin
`store_mongo_tx.py:41` (`self._undo` is a Python list), `:78-84` (`rollback` runs in the dying process), `store_mongo.py:268-278` (`transaction`: `except BaseException: tx.rollback()`). A refused change is written first and checked after (`accounts.py:90-93,160-168,198-211`: write, then `ensure_an_admin_remains`, which raises `LastAdmin`; the rollback then undoes the write). If the process is killed, or the store becomes unreachable, in that window, the write stays. SQL gives this atomically; the Mongo store does not.
Reproduction (`probe_crash.py`; store goes `down` at call k of the operation, comes back up, leftover lease aged out; one sole admin A, one waiting account B, then B calls `accounts.claim_admin`):
- `set_user_groups(A, [])` (refused: last admin): 10 call points; at calls 7, 8, 9 the Admin/CEO group is left with no member and **B's `claim_admin` succeeds**.
- `delete_user(A)`: 10 call points; at calls 5-9 same result, **B claims Admin/CEO**.
- `set_disabled(A, True)`: at calls 5-8 A stays disabled (lockout; claim refused because membership remains; no escalation).
- `update_group` (developer group, perms raised then refused on an unknown member): at calls 11-12 the refused request leaves **`users.manage` granted to the group's members** (a refused request that took effect).
- First signup (171 call points): no extra admin ever appears; at worst the first account has no group (lockout, CLI break-glass recovers).
The claim path needs no setting: `_claim_refusal` (`accounts.py:59-70`) refuses only when an admin member exists or a first-admin address is configured and differs. A real trigger is a Cloud Run instance kill or a Mongo failover during an admin demotion attempt. Probability is low; the outcome is a full admin takeover, on a CRITICAL criterion that the SQLite store does not have, and the manifest knew of it (limit 3) without a mitigation.
Fix direction (inside `store_mongo_tx.py`, no business-module edit): persist the undo entries as data under the lease (for example `auth_meta/tx_journal` holding `{owner, steps}` written before each write and cleared at commit/rollback), and have `_acquire` replay and clear a journal found when it takes over an expired lease (and `_prepare` on first use). Add tests that kill the store at each call point of the three refused operations above and assert the post-recovery state equals the pre-state. Alternatively evaluate the guard before the write; that needs `accounts.py`/`groups.py` edits and is a different unit's file.

### W1 (Warning) - A global `AUTOTESTER_STORE=mongo` now also moves auth, onto an empty collection set
`auth/store.py:96-98` selects Mongo when `store_selection()["auth"] == "mongo"`, and `store_selection` (`mongo_routes.py:236`) applies the global value to every area including `auth`; on master `auth_store()` was hard-wired to SQLite, so a deployment that already sets `AUTOTESTER_STORE=mongo` would, on the next deploy, switch to an empty Mongo auth store (everyone logged out, first signup or claim becomes admin) before U8 migrates users. G1 (human flip per area, M52) is the intended gate; make sure the deploy env does not set the global value before U8, or have the manifest/DEPLOY.md say so.

### W2 (Warning) - Lease expiry mid-transaction reverts a later writer's change
`store_mongo_tx.py:24` (`LEASE_SECONDS = 30`), `store_mongo.py:274` (`holds()` is checked only at commit). `probe_race.py` R6: transaction A writes, stalls past 30 s; B takes the lease over and resets the same user's password; A exits, `holds()` is false, A raises `AuthStoreBusy` and its rollback restores the pre-A password hash: **the reset is reverted to the original hash**. It needs a stall above 30 s, so Warning; a fencing check on each rollback step (restore only if the field still equals what A wrote) closes it.

### W3 (Warning) - A crashed holder blocks all writes (sign-in included) for up to 30 s
Waiters give up at 15 s (`WAIT_SECONDS`), the lease lives 30 s: with a stale foreign lease `signup` raised `AuthStoreBusy` after 1.1 s (wait lowered for the probe). Fail-closed availability, no security effect; B1's journal would also let a takeover happen sooner.

### W4 (Warning) - "One client per process" is not true under a cold-start race
`mongo_backend.py:288-291` (`default_backend`, U9, unlocked `_CACHE`) and `store_mongo.py:285-287` (`_AUTH.update`, unlocked): in `probe_4.py`, 10 threads hitting a cold process created more than one client in 30 of 30 runs (sequential use creates exactly one). The admin invariants still held in all runs (the lease lives in the database). Not this unit's file; route to U9.

### I1 (Info) - Cycle-0 limits judged
Readers take no lease (`reading()` at `store_mongo.py:263-265`): during a refused change a reader can see the write before its rollback; the writes at issue lower privilege except the `update_group` raise (S5), which only an actor already allowed to grant it can reach. Membership/permission lookups scan the user and group collections (`store_mongo.py:40,149,152`, `_group` is O(groups x users)); fine at auth scale, flagged for U8. The tests do not run the pre-existing `test_ui_auth_*` files on Mongo; the new contract suite mirrors them on both backends (I ran the SQLite ones, below).

### I2 (Info) - Contract wording
M29 names `create_exclusive` and an `admin_guard` CAS. The code has neither by name. Ruled acceptable (finding above); the checker seat that maintains `qa/contracts/` should record the amendment, not the maker.

## What I verified held

- Races (`probe_race.py`, thread count and repeats beyond the suite's, fake slowed 0-1 ms per call): 12-way first signup x30: exactly one admin, 12 distinct ids, zero errors. 3 admins with 3 concurrent mixed demotions (disable / delete / regroup) x60: never zero enabled admins. 2 admins deleting each other x100: never zero. 5-way claim x30: exactly one admin. Planted expired lease then 6-way claim x40: exactly one winner, no unexpected errors (takeover works).
- Files and shape: `store_mongo.py` 293 lines, `store_mongo_tx.py` 130; no database name, no SQL, no driver import (suite test + doctor); `autotester doctor` clean, longest-function and file rules pass; ruff clean.
- Merge hygiene: only 9 non-qa files differ from `fe1ac6c8` (`git diff --stat fe1ac6c8..HEAD`); `mongo_routes.py` diff is the one line.

## Commands run and outputs (worktree `D:/autoTesting/.claude/worktrees/mongo-u6b`)

```
env -u ANTHROPIC_BASE_URL uv run pytest tests/test_auth_store_mongo.py tests/test_auth_store_contract.py -o addopts= -q -p no:cacheprovider  -> 59 passed, 2 warnings in 39.97s
env -u ANTHROPIC_BASE_URL uv run pytest tests/test_state_selection.py tests/test_auth_store_seam.py -o addopts= -q -p no:cacheprovider      -> 36 passed, 1 skipped (empty UNROUTED parametrization), 1 warning
env -u ANTHROPIC_BASE_URL uv run pytest tests/test_ui_auth_accounts.py tests/test_ui_auth_claim_admin.py ...                              -> 21 passed
env -u ANTHROPIC_BASE_URL uv run pytest tests/test_ui_auth_groups.py tests/test_ui_auth_escalation.py ...                                 -> 54 passed
env -u ANTHROPIC_BASE_URL uv run ruff check --no-cache src tests scripts                                                                   -> All checks passed!
env -u ANTHROPIC_BASE_URL uv run autotester doctor > .work/chk-a-doctor.txt                                                                -> rc 0, "doctor: clean" (advisory decision-citation warnings only)
probe_crash.py  -> S1 10 points, escalation at 7,8,9; S2 10 points, escalation at 5-9; S3 lockout only at 5-8; S4 no escalation; S5 raise-left-in-place at 11,12; stale lease -> AuthStoreBusy
probe_race.py   -> R1 bad=0; R3 zero-admin runs=0; R4 =0; R5 =0; R6 reset reverted to original hash = True
probe_r2.py     -> R2 stale-lease takeover, 6-way claim x40: bad=0
probe_3.py      -> 3a StoreSelectionError names PATHLYNKS_MONGO_URI, value not leaked; 3b same client, rearm keeps store, reset drops it; 1 client for 5 sequential signups
probe_4.py      -> cold-start 10-way race: >1 client in 30/30 runs; admin invariant held 30/30
probe_5b.py     -> exists()/resolve_session/end_session on empty store: no change after client open; no auth_* doc or index
python scripts/mutation_check.py qa/evidence/mongo-store-u6b/mutations.json --repo .  -> 17/17 mutations killed (17m35s). None of the 17 mutants exercises crash recovery, which is why B1 survives them.
```

## To reach PASS

1. Close B1 (journal replayed at lease takeover, or equivalent) with tests that fail the store at every call point of `set_user_groups`, `delete_user`, `set_disabled` and `update_group`-refused and assert recovery restores the pre-state. Re-run the mutation spec with a mutant that drops the replay.
2. Take W2 into the same change if cheap (fenced rollback steps); W1, W3, W4 may be recorded and routed (deploy note, U9).
