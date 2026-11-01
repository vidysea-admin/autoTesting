# Manifest - mongo-store-u6c

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** `qa/contracts/mongo-store.md`, unit U6c (Mongo video shares, links, access requests, comments, `schedule_owner`, `intake_gate_auth`, audit rows). Criteria judged: M30 (CRITICAL, dual check requested by the brief), M29 for the fence changes. Folds in the two U6bf residuals: AT-1431 and AT-1432.
**Authority:** D-120..D-123, D-126, D-129 (ACTIVE, `docs/DECISIONS.md:3080`) authorizes exactly two new src files, `auth/store_mongo_video.py` and `auth/store_mongo_fence.py`, and the regeneration of the generated sections of `docs/ARCHITECTURE.md` / `docs/MAP.md`. No other new src file.
**Branch:** `feat/mongo-store-u6c` (worktree `D:/autoTesting/.claude/worktrees/mongo-u6c`, cut at `7ae3bba5`). Not merged, not pushed (D-130).
**Base SHA:** `7ae3bba5`. **Code SHA:** the single commit this manifest lands in (`git log -1 -- qa/manifests/mongo-store-u6c.md`).
**Not touched (sibling E4 owns them):** `stages/reachability.py`, `run_launcher.py`, `browser/video.py`, `ui/routes_video.py`.

## What changed

| File | Kind | Change |
|---|---|---|
| `src/autotester/auth/store_mongo_fence.py` (177 lines) | NEW (D-129) | The fence half moved out of `store_mongo_tx.py` (`replay`, `close_epoch` (was `resolve`), `recover`, `insert_fenced`, vocabulary) plus the NEW slot design for AT-1431 |
| `src/autotester/auth/store_mongo_video.py` (145) | NEW (D-129) | `VideoOps(MongoTxBase)`: shares, links, requests, comments on the journalled Mongo transaction; `VIDEO_INDEXES` |
| `src/autotester/auth/store_mongo_tx.py` (238) | EDIT | imports the moved names; `_insert` calls `insert_fenced`; `_write` blanks a deleted slotted document (:137); commit/rollback call `close_epoch` |
| `src/autotester/auth/store_mongo.py` (300, at the cap) | EDIT | `MongoAuthTx(VideoOps)`; `_prepare` creates `VIDEO_INDEXES` |
| `src/autotester/auth/store.py` | EDIT | `on_mongo()` (:103) and `video_tx(write)` (:111) |
| `src/autotester/auth/access.py` | EDIT | `principal_of(tx, email)` (:48): the one principal read, through the seam, both backends |
| `src/autotester/stages/video_access.py`, `video_requests.py`, `video_comments.py` | EDIT | each public function gets an `if on_mongo():` branch ahead of the unchanged SQLite SQL; `db.store_exists()` becomes `auth_store().exists()` |
| `src/autotester/stages/schedule_owner.py` (:23), `ui/intake_gate_auth.py` (:32) | EDIT | principal read via `principal_of` over the seam; store creation, `exists` and `reading` all inside the fail-closed `try` |
| `tests/test_auth_store_fence_slots.py` | NEW (187 lines) | AT-1431 / AT-1432 tests (8) |
| `tests/test_video_store_backends.py` | NEW (248) | U6c parity tests, both backends (21 collected) |
| `tests/test_auth_store_fencing.py`, `test_auth_store_contract.py`, `test_auth_store_mongo.py` | EDIT | see "Existing tests changed" |
| `qa/evidence/mongo-store-u6bf/mutations.stale.json` | NEW | tags the one renamed u6bf test as deliberately stale (doctor `evidence-spec-stale-unexplained`) |
| `docs/MAP.md`, `docs/SNAPSHOT.md` | regenerated | `autotester map` / `snapshot` (doctor `stale-committed`) |

## AT-1431: a stalled holder's late insert of a deterministic id (design)

The u6bf tombstone was a document that a later holder CLEARS before re-creating the id; an older holder's late INSERT then finds the id absent and lands (the checker's P1: grant revoked, then resurrected). Fix: for `SLOTTED = {auth_grants, video_shares}` (ids that are re-created: `slug|user|relation`, `slug|video|sha256(email)`) the id slot is **never empty again** once used.
- A committed delete is a `G:` stamp that stays (`close_epoch` physically deletes only non-slotted collections, `store_mongo_fence.py:141`), and `store_mongo_tx.py:137` blanks every field of the document first.
- An undone insert (`replay` -> `_hide_slot`, fence.py:86) places or converts the document to `{_id, _e: G:<epoch>.000000}`, blanking any landed fields.
- A legitimate insert takes the hidden slot over by compare-and-set on the stamp it read, only when `stamp_epoch(stamp) <= own epoch` (`insert_fenced`, fence.py:158, check at :169). A stalled writer of an OLDER epoch finds a duplicate key and a later epoch's stamp and is refused, however many holders came and went. There is no window in which the id is absent.
- Non-slotted collections keep the u6bf FENCE tombstone (their ids are allocator or random, never re-created).
- M30: a hidden slot holds no address, hash or grant data; a share's id carries `sha256(email)`, not the address.

## Criteria map

| Criterion | Where | Test(s) |
|---|---|---|
| M30 video data on Mongo, no address/hash leak | `store_mongo_video.py` (whole); share id hash :47; `store_mongo_tx.py:137`; `_hide_slot` blanking fence.py:98 | `test_video_store_backends.py::test_a_deleted_share_keeps_nothing_of_the_address_and_no_hash_is_in_a_video_collection`; `test_auth_store_fence_slots.py::test_an_undone_insert_leaves_a_hidden_slot_with_none_of_its_data` |
| U6c shares / links / purge | `store_mongo_video.py:42-82` | `test_shares_are_idempotent_and_removable[sqlite/mongo]`, `test_one_live_link_per_video_and_only_its_hash_is_stored[...]`, `test_purge_removes_all_four_kinds_for_a_video_and_for_a_project[...]` |
| U6c requests: one pending per person, decide once, approval adds one share | `store_mongo_video.py:85-115` | `test_request_access_decide_once_and_share[...]`, `test_approvers_are_the_admins_and_the_uploader_never_the_requester[...]`, `test_two_racing_requests_make_one_pending_request` |
| U6c comments, scoped to their video | `store_mongo_video.py:118-145`, `video_comments.py:88-96` | `test_comments_order_edit_promote_delete_and_video_scope[...]` |
| a refused approval is undone whole | journal (`store_mongo_tx.py`) | `test_a_refused_approval_is_undone_whole` (asserts the raw document before any recovering read) |
| fail closed on an unreachable store | `video_*` via the seam; `schedule_owner.py:23` | `test_an_unreachable_store_fails_closed_on_every_video_call`, `test_the_schedule_owner_is_nobody_while_the_store_is_unreachable` |
| `schedule_owner` / `intake_gate_auth` principals via the seam, disabled refused | `access.py:48` | `test_principals_for_the_schedule_owner_and_the_intake_gate_come_from_the_seam[sqlite/mongo]` |
| audit rows to the store, no file, no secret | `auth/audit.py` (already routes through `append_path`; unchanged) | `test_audit_rows_go_to_the_store_with_no_file_and_no_secret` |
| AT-1431 zombie insert after re-grant + revoke lands nothing | fence.py:158-169 | `test_auth_store_fence_slots.py::test_a_zombie_insert_after_the_slot_was_re_granted_and_revoked_lands_nothing` |
| AT-1431 committed delete leaves a hidden blank slot; a recoverer raises an older hidden stamp; epoch order | fence.py:86, :141, :75 | `..._a_committed_delete_leaves_the_slot_hidden_and_blank_not_absent`, `..._a_recoverer_raises_an_older_hidden_stamp_past_the_dead_holders_epoch`, `..._the_stamp_epoch_orders_every_stamp_the_fence_writes` |
| AT-1432 late committed sweep (the `_e G:<me>` condition killed directly) | fence.py:141 | `..._a_late_committed_sweep_does_not_delete_a_recreated_document` |
| AT-1432 p5: abort CAS BEFORE the marker read | fence.py:130 | `..._a_commit_that_lands_between_the_abort_cas_and_the_marker_read_stands` |
| AT-1432 `recover()` resolves only epochs below its own | fence.py:148 | `..._a_recovery_resolves_only_earlier_epochs` |

## Existing tests changed (said plainly)
- `test_auth_store_fencing.py`: the tombstone test is renamed `..._meets_a_hidden_slot_only_a_later_epoch_may_take` and asserts a hidden `G:` slot instead of a FENCE document (grants are slotted now). The old nodeid is tagged in `qa/evidence/mongo-store-u6bf/mutations.stale.json`; the property is also covered by `test_a_zombie_insert_...`.
- `test_auth_store_contract.py::test_delete_user_takes_sessions_and_grants_with_it`: on Mongo a deleted user's grant leaves a hidden slot whose id still contains the slug. The assertion is now "no slug in any document of `auth_grants`" instead of "`proj-` absent from the whole dump".
- `test_auth_store_mongo.py::test_an_exception_rolls_every_write_back`: `_state` ignores a hidden blank slot of a slotted collection (what an undone insert leaves by design).

## Verify (worktree, `env -u ANTHROPIC_BASE_URL`, `-o addopts=`, at most two files per call)
```
tests/test_auth_store_contract.py + test_auth_store_seam.py            -> 51 passed
tests/test_auth_store_mongo.py + test_auth_store_fence_slots.py        -> 28 passed
tests/test_auth_store_recovery.py + test_auth_store_double_fault.py    -> 25 passed
tests/test_auth_store_fencing.py + test_auth_store_fence_slots.py      -> 23 passed
tests/test_video_store_backends.py                                      -> 21 passed (alone)
tests/test_cli_store_auth_creds.py + test_schedule_owner_guard.py      -> 20 passed
tests/test_intake_gate_auth.py + test_video_review_route.py            -> 23 passed
tests/test_intake_gate_auth.py + test_portal_access.py                 -> 36 passed (earlier run)
tests/test_video_review_route.py + test_ui_video_route.py              -> 13 passed (earlier run)
tests/test_tracker_auth.py + test_ui_intake.py                         -> 47 passed (earlier run)
tests/test_schedule_tick.py + test_ui_auth_envkeys.py                  -> 43 passed, 1 FAILED (pre-existing, below)
tests/test_cli_advice_resolves.py + test_mongo_guard.py                -> 56 passed, 1 FAILED (pre-existing, below)
ruff check --no-cache src tests scripts                                 -> All checks passed!
autotester doctor (> .work/doctor.txt)                                  -> no violation of this unit; only `stale-committed` for docs/MAP.md and docs/SNAPSHOT.md before this commit (the regenerated files are in it), plus the advisory D-087 findings
file sizes: store_mongo.py 300 (cap), store_mongo_fence.py 177, store_mongo_video.py 145, store_mongo_tx.py 238, video_access.py 206, video_requests.py 193, video_comments.py 163
```
Some of the "earlier run" pairs ran before the last edits (the `_hide_slot` blanking, the constant split, the renames); the fence, store and video pairs were re-run after them.

**Pre-existing red tests (not from this unit; measured):**
1. `test_cli_advice_resolves.py::test_the_collector_reports_what_it_could_not_resolve`: one site, `store/mongo_backend.py:73` (same as the u6bf manifest). My first fence module added 4 more sites (multi-name constant assignments); fixed by splitting them, so only that one remains.
2. `test_schedule_tick.py::test_the_scheduler_side_reaches_no_browser_or_pipeline_module_even_transitively`: **red at HEAD `7ae3bba5` too** (I ran `scheduler_side_violations()` against a `git archive HEAD` tree: 3 violations: `store.mongo_routes -> browser.profiles` (a lazy import), `auth.store -> auth.store_mongo`, `auth.store_mongo -> auth.store_mongo_tx`). This unit adds 3 edges of the same kind (`store_mongo -> store_mongo_video`, `store_mongo_video -> store_mongo_tx`, `store_mongo_tx -> store_mongo_fence`). I did NOT widen `ALLOWED_OUTSIDE`: the root cause is the lazy `mongo_routes -> browser.profiles` edge, which needs a decision rather than an allow-list edit. Flagged for the coordinator.

## Mutation evidence (`scripts/mutation_check.py`; outputs in `qa/evidence/mongo-store-u6c/`)
- `mutations-fence.json` -> `mutation-run-fence.txt`: **11/11 killed** (s1 takeover ignores epoch, s2 committed slotted delete physical again, s3 recoverer leaves an older hidden stamp, s4 sweep without `_e`, s5 marker read before abort CAS, s6 recover above own epoch, s7 undone insert keeps its data, s8 landed insert not hidden, s9 hidden slot treated as a real duplicate, s10 deleted slotted document keeps fields, s11 unparsable stamp sorts first).
- `mutations-video.json` -> `mutation-run-video.txt`: **12/12 killed** (v1 decide twice, v2 no dedupe, v3 no link revoke, v4 revoked link resolves, v5 purge keeps shares, v6 approval adds no share, v7 plain address in the id, v8 cross-video comment, v9 disabled principal accepted, v10 schedule owner fails open, v11 no rollback, v12 edit drops text).
- Honest account of the runs: the first fence run killed 10/11 (s9's kill list named a test that does not fail under s9; the list was corrected to the two that do, then 11/11). The first video run was refused (a `kills` name that is not collected; fixed). The second video run left v10 and v11 alive: v10 because no test covered `owner_principal` on an outage (test added); v11 because a lost rollback is repaired by the next holder's recovery, so the old assertion could not tell (the test now asserts the raw document immediately after the refused write). Both were re-run and killed.

## Deviations, residuals, flags
- **SQLite video SQL stays in the stage modules** behind `on_mongo()` branches, not behind the `AuthTx` protocol: `store_sqlite.py` and `store_mongo.py` are at the cap. The video operations exist only on the Mongo transaction (`VideoOps`). D-129 says "behind the AuthTx protocol"; this is the smaller step. The checker may require the protocol form.
- **AT-1432 item "a no-op `store migrate --apply` should not write auth_meta/epoch": NOT changed.** Every lease acquire bumps the epoch under the fence; skipping the lease on a no-op would weaken it. Documented here instead (the u6bf manifest already excludes the epoch from the idempotence comparison).
- **Hidden slot documents persist** in `auth_grants` and `video_shares` (one tiny blank document per ever-used id). They are never reaped; reaping them would re-open AT-1431 unless it can prove no older holder is alive.
- **Video tables are not imported by the U8 SQLite-to-Mongo importer** (`auth/migrate_auth.py`); flipping the `auth` area to Mongo starts with empty shares, links, requests and comments. Follow-up unit.
- `approvers` and principal reads on Mongo go through the seam (`principal_of`), so a disabled account is refused on both backends.
- Independent review (`senior-software-engineer`) not run by the maker; the checker is the independent read.
