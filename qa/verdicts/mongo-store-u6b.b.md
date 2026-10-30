# Verdict (checker B) - mongo-store-u6b

**Unit:** mongo-store U6b (auth store on Mongo), dual-checked, CRITICAL. **Criteria:** M29, M30 (U6b row), with `auth.md` AU7/AU9/AU11/AU16/AU21.
**Cycle checked:** 1
**Head checked:** `797d03cd` on `feat/mongo-store-u6b` (worktree `D:/autoTesting/.claude/worktrees/mongo-u6b`). Fresh checker: re-ran every claim, did not read any other checker's verdict.
**Verdict:** **PASS** (with 4 warnings and 2 informational notes; none is a Block against M29/M30).

## Ruling on the FLAGGED question: does the lease satisfy M29 "no transactions assumed"?

**PASS on the behaviour, with a wording gap the contract owner should close.** M29's headline is "invariants preserved, no transactions assumed";
the parentheses name one mechanism (`create_exclusive` on an `auth_meta` doc; optimistic CAS on `auth_meta/admin_guard`). The lease is the same two
primitives, used more broadly: acquisition is an `insert_one` under a unique `_id` that raises `StoreDuplicateKey` (`store_mongo_tx.py:106-108`,
which is create-exclusive semantics) and takeover of an expired lease is a CAS on `(owner, expires)` (`:110-112`). Every write transaction goes through it
(`store_mongo.py:267-278`; seeding too, `:252`), so first-admin, claim and the last-admin check see one writer. Only single-document atomics are
used; no multi-document transaction is assumed. The falsifier (zero enabled admins in 200 repetitions; one admin from concurrent signups) is met
by my own runs (below). Recommendation to the contract owner: amend M29's parenthetical to "a write lease (insert-exclusive plus CAS takeover) or
per-invariant create_exclusive/CAS"; no code change is needed to satisfy the wording.

## Commands run (all in the worktree; no .env value read or printed)

| # | Command | Result |
|---|---|---|
| 1 | `env -u ANTHROPIC_BASE_URL uv run pytest tests/test_auth_store_mongo.py tests/test_auth_store_contract.py -o addopts= -q -p no:cacheprovider` | `59 passed` |
| 2 | same, `tests/test_state_selection.py tests/test_auth_store_seam.py` | `36 passed, 1 skipped` (the skip is the empty `UNROUTED` parametrization, see finding 5) |
| 3 | `uv run ruff check --no-cache src tests scripts` | `All checks passed!` |
| 4 | `env -u ANTHROPIC_BASE_URL uv run autotester doctor > .work/doctor-u6b-b.txt` | rc 0, `doctor: clean` (only advisory decision-citation warnings); sizes: `store_mongo.py` 293, `store_mongo_tx.py` 130, `tests/auth_store_backends.py` 106, `test_auth_store_mongo.py` 300, `test_auth_store_contract.py` 299 (all <= 300); no function-length finding |
| 5 | `uv run python scripts/mutation_check.py qa/evidence/mongo-store-u6b/mutations.json --repo .` > `.work/mutation-u6b-b.txt` | `17/17 mutations killed`, rc 0, worktree clean afterwards |
| 6 | scratch simulation `sim_u6b_b.py` S1: 8 threads, 60 repetitions of concurrent first signups (fake slowed 0.5 ms per call) | passed: exactly one Admin/CEO, 8 distinct ids, every call ok, each repetition |
| 7 | S2: two admins disabled concurrently, **200 repetitions** | passed: never zero enabled accounts |
| 8 | S2b: demote one admin and delete the other concurrently, 100 repetitions | passed: an enabled Admin/CEO member always remained |
| 9 | S3: hard-crash enumeration (below) | 50 crash points over 13 operations: **0 privilege escalations, 0 admin lockouts**, 2 real revocation gaps |
| 10 | S4: stalled holder past the lease (below) | **reproduced** a lost update (finding 1) |
| 11 | S5: AU16 footprint (below) | auth_* untouched by reads; shared-client side effects listed (finding 4) |
| 12 | existing auth test files, unchanged, run on the Mongo auth store through a scratch plugin | see finding 6 |

The scratch files (`sim_u6b_b.py`, `mongo_auth_plugin.py`) live in the session scratchpad, outside the repo; nothing under `src/` or `tests/` was edited.

## Q1 - races and crash (M29)

**Races:** held, runs 6-8. **Crash simulation (run 9):** for each of 13 operations (`set_disabled`, `delete_user`, `reset_password`, `set_user_groups`
promote/demote, `approve_waiting`, `decline_waiting`, `delete_group`, `update_group`, `bootstrap_admin`, `claim_admin`) I ran the operation once to
completion, then re-ran it once per write call with the process "killed" before that write (every later store call, including the rollback and the
lease release, raises, so no undo runs; the lease is then cleared as if it had expired). I compared each user's effective permissions and enabled
state and each session's survival against the pre-state and the completed post-state. Result: no user ever holds a permission, enabled state or session
that is in neither the pre nor the post state; no state has all admins gone. Why it holds: each risky step is either one document or ordered so the
intermediate state is lower privilege (sign-up inserts the user before the group, a disable lands before sessions are purged, a deleted group's id is
never reused so a dangling membership grants nothing).

## Findings

1. **WARNING (M29, stalled holder, not a crash): a rollback after a lost lease clobbers the successor.** `lease()` expires after 30 s with no
   renewal (`store_mongo_tx.py:24`, `:100-116`); the lost-lease check runs only at commit (`store_mongo.py:274-275`), and the handler then rolls back
   using snapshots taken before the successor wrote (`store_mongo_tx.py:78-83`, `_patch :59-65`, `_drop :67-72`). Reproduced (S4, lease scaled to
   0.3 s): holder A writes `disabled=True` on D and stalls; B takes the lease, disables D and is told ok; A raises `AuthStoreBusy` and its rollback
   writes D's prior `disabled=False` back. Result: `b_ok: True, a_err: AuthStoreBusy`, D enabled although a committed transaction disabled it. This
   is a privilege restoration, reachable only if a write transaction stalls longer than 30 s (guard retries are 3 tries per call, so a Mongo outage
   mid-transaction could stretch it). Not a Block: the contract's failure cases are races and crash, the deployment is `--max-instances 1` (M28), the
   window is a stall of 30 s inside a millisecond section, and AU9 itself held in S4's variants because the holder's uncommitted writes are visible to
   the successor's check. Fix before multi-instance (U7/G1 hosting): make each undo step conditional (apply only if the document still equals what
   this transaction wrote) or skip the rollback once `holds()` is false, and consider renewing the lease per write.
2. **WARNING (M29, crash): password reset is not crash-atomic.** `accounts.reset_password` and `accounts.bootstrap_admin` write the new hash and then
   purge sessions as separate writes (`accounts.py` `_update` / `bootstrap_admin`; `store_mongo.py:80-84`, `:192-193`). A kill between them leaves the
   old sessions valid until their expiry (S3: `reset_pw_D` crash before write 3 and `bootstrap_D` crash before write 3; the other 14 "revocation-lag"
   rows my script printed are crash points before the operation took effect, or a disabled account whose sessions are already dead, not gaps). SQLite
   is atomic here. The maker disclosed that a crash leaves partial state (manifest item 3) but not this consequence. Mitigation: purge the sessions
   first, then write the hash, so a crash leaves a changed-nothing or revoked-but-old-password state.
3. **WARNING (M29 reader claim): "every rollback follows a refused change, which only lowers privilege" is not strictly true.** `claim_admin`
   adds the Admin membership and only then calls `ensure_an_admin_remains` (`accounts.py:92-93`), and `update_group` raises permissions and members
   before its check (`groups.py:88-93`). A reader without a lease can resolve a principal in that window (`store_mongo.py:262-265`, `:200-207`) and see
   the raised privilege until the rollback lands. The check can fail there only when the Admin invariant is already broken (for example the Admin group
   lacks `users.manage`), and the window is milliseconds, so this is a documentation correction, not a code Block. Readers taking no lease is otherwise
   acceptable.
4. **WARNING (AU16 test honesty): the narrowed `nothing_written()` is truthful about auth but hides real shared-client writes.**
   `tests/auth_store_backends.py:74-79` now inspects only `auth_*` collections. I measured the footprint of `exists()` + `resolve_session` +
   `end_session` on an empty fake (S5): `autotester.auth_meta` holds 0 documents and 0 indexes, and no `auth_users/groups/sessions/grants` collection
   exists, so the auth guarantee is real. Outside auth, the first open of the shared client creates the state-collection indexes (about 40
   collections) and one `server_state` marker document (`mongo_backend.py:53-55`, U9). That is not an auth write and the comment says so, and at hosted
   startup `check_startup` opens the client before any request. But the AU16 sentence "a refused request changes nothing" is then not asserted for
   the whole store on a fresh deployment. Add a U9/U10 test: after startup, an unauthenticated read leaves the database inventory identical. Parity note:
   `groups.list_groups()` (no `exists()` guard) seeds the default groups and indexes on Mongo exactly as SQLite's `connect()` seeds on first open
   (`db.py:138-152`), so that is not a regression.
5. **INFO (merge resolution confirmed).** Master `fe1ac6c8` has `UNROUTED = {"auth": "the auth store (U6)"}` and no other entry (`git show
   fe1ac6c8:src/autotester/store/mongo_routes.py`), so `UNROUTED: dict[str, str] = {}` (`mongo_routes.py:28`) drops only the intended auth entry;
   `credentials` and `blobs` were already routed on master. The only consumers are `mongo_routes.py:241-243` and the parametrized
   `tests/test_state_selection.py:102`, which now skips its single case (the skip in run 2). `auth` is now selectable. Caveat for G1 readiness: the
   `stages/schedule_owner.py`, `stages/video_*.py` and `ui/intake_gate_auth.py` readers still query SQLite directly (U6c). With `auth=mongo` they
   fail closed (`store_exists()` false or no user, so the caller refuses), so this is an availability limit, not a leak; do not flip `auth` at G1 before U6c.
6. **INFO (M29 "existing auth tests run unchanged against store_mongo").** The manifest (item 7) says the existing files were not run on Mongo. I ran
   them unchanged through a scratch autouse plugin that selects `auth=mongo` on the fake. `test_ui_auth_accounts.py` + `test_ui_auth_groups.py`: 46 passed.
   `test_ui_auth_escalation.py` + `test_ui_auth_survivors.py`: 23 passed, 2 failed. `test_ui_auth_login.py` + `test_ui_auth_claim_admin.py`: 22 passed, 7 failed.
   Eight of the nine failures open SQLite directly (`sqlite3.OperationalError` at `test_ui_auth_login.py:33` x6 and `test_ui_auth_survivors.py:32`,
   and `test_ui_auth_claim_admin.py:100` through `_disable_raw`, `:107-110`); they cannot pass on any non-SQLite backend and are covered by the
   mirrored contract suite (run 1). One, `test_ui_auth_survivors.py:71` (401 where 404 expected, the suite auto-login path), I did not root-cause;
   it does not concern a store invariant. No assertion about accounts, groups, sessions, escalation or the last-admin guard failed.

## Other checks asked for

- **URI (3):** `AUTOTESTER_MONGO_URI` appears nowhere under `src/` (grep; only test-env scrubs and a U9 test name it). `mongo_auth_store()`
  (`store_mongo.py:281-289`) uses `default_store()`, which reads `core.env.mongo_uri()` (`PATHLYNKS_MONGO_URI`). A missing URI raises
  `StoreSelectionError("PATHLYNKS_MONGO_URI is not set; the store needs it")` (`mongo_backend.py:290`): names the key, never a value
  (`test_auth_on_mongo_needs_the_uri_named_without_a_value` passed). One client: `default_backend()` caches one `MongoBackend`;
  `MongoBackend.rearm` only clears `_redactor` (`mongo_backend.py:246-247`), so the `_store` object the auth store is keyed to stays; the auth
  store is rebuilt only when `reset_default_backend()` swaps the client (`_AUTH` identity check, `store_mongo.py:285-287`). No orphaning.
- **Cycle-0 limits (5):** readers without a lease: acceptable (finding 3 corrects the claim). Membership lookups that scan users
  (`store_mongo.py:105`, `:149`, `:152`): acceptable at team scale (tens of accounts), O(groups x users) for `list_groups`; flag for U8 as the
  maker did. A crash leaving partial state: acceptable given findings 1-2 are recorded; no escalation found.
- **Boundaries:** auth module names no database and imports no driver (AST test in run 1); M30 tests (hash containment, canary absence) in run 1 passed.

## Checker-B recommendation
PASS cycle 1. Warnings 1-4 should be folded into the feedback inbox for U7/U9/U10 rather than block this unit.
