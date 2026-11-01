# Verdict (checker-B) - mongo-store-u6c (U6c, Mongo video shares/links/requests/comments, AT-1431 slot fence, AT-1432), fix cycle 0

**Cycle checked:** 0
**Verdict:** PASS (with 4 Warnings the maker must carry into the close-out; no Block)
**Head checked:** 51eeaeff on `feat/mongo-store-u6c` (code commit 5caadae6, base 7ae3bba5). Fresh, independent; no other checker's verdict on this unit was read.
**Criteria:** M30 (CRITICAL, dual), M29 for the fence changes, M20 (stale-epoch refusal unchanged), the manifest's claims, D-129.

## Summary
The AT-1431 design holds under every adversarial interleaving I could build: a stalled old-epoch holder cannot resurrect a revoked grant or share, not
after one recoverer, not after recoverer + re-grant + revoke, not with two stalled holders of different epochs, and not when it is paused between its
`find_one` and its takeover compare-and-set. The raw documents of an undone insert and of a committed delete hold none of the address, the hash or the
grant data. A disabled account is refused through `principal_of`, `owner_principal`, `principal_for_email` and `approvers`. All seven named suites, ruff and
`autotester doctor` are green; 14 of the maker's mutants die on named tests when I re-run them.
Four things the maker must carry (none reachable from a caller today, none a Block): a delete-then-recreate of one slotted id inside a single transaction is
not undone whole (reproduced, fails closed), two of my own mutants of the takeover compare-and-set survive because no test covers that race, D-129's
"behind the AuthTx protocol" was not followed, and the U8 importer skips the four video tables (a G1 flip precondition).

## Findings (numbered)

1. **Warning - delete-then-recreate of ONE slotted id in a single transaction is not undone whole (rollback AND crash recovery). Reproduced; not reachable today.**
   `src/autotester/auth/store_mongo_fence.py:86-103` (`_hide_slot`) and `:106-127` (`replay`), with `store_mongo_tx.py:137-143` (`_write`) and `store_mongo_fence.py:158-172`
   (`insert_fenced` takeover). Sequence: tx = `set_share(False)` (journal 1, `set`, `gone`, prior = whole document) then `set_share(True)` (journal 2, `ins`, takes the hidden slot over).
   Newest-first replay: entry 2 hides the slot as `G:<epoch>.000000` (blanking the landed document); entry 1 then restores only `where _e in {me1, G:me1, F:me1}`, and the slot now
   carries `G:<epoch>.000000`, so the restore matches nothing. The original share is gone. Probe `.work/probe/test_probe_b.py::test_p7_...` (rollback): after the refused tx
   `emails() == frozenset()`, expected `{person@example.test}`; `::test_p10_...` (holder dies before commit, next holder recovers): `after crash recovery share present? frozenset()`.
   Direction is fail-closed (a share or grant is lost, never added), and I grepped every caller (`access.py:83,92,94`, `video_access.py:93`, `routes_video_portal.py:135`,
   `store_mongo_video.py:49-51,112-114`): none does delete + insert of the same slotted id in one transaction, so it is latent. But the manifest and `store_mongo_video.py:5-6` promise
   "a refused or interrupted change is undone whole", and before this unit the same sequence raised on the duplicate rather than succeeding. Required before close-out: either make the
   `ins` replay restore a slot it took over from a hidden predecessor (for example record the predecessor stamp in the entry's `pre` and have `_hide_slot` put back the earlier entry's
   restore target), or record it as an accepted residual in the manifest and add a one-line guard that refuses a re-insert of a slot deleted earlier in the same transaction.

2. **Warning - the takeover compare-and-set and the same-epoch re-grant are untested; two of my mutants survive.** `store_mongo_fence.py:169-171`.
   OWN-A (drop `"_e": cur["_e"]` from the takeover filter) and OWN-B (`<= epoch` to `< epoch`) both leave `tests/test_auth_store_fence_slots.py` green (`8/10 killed`, output below).
   OWN-A is load-bearing: simulating it in `test_p11_...` (a stripped-guard `update_one` plus a recoverer that raises the stamp between the zombie's `find_one` and its CAS) printed
   `OWN-A simulated outcome: refused emails: frozenset({'person@example.test'})`: the zombie is told "refused" but its share is live afterwards, which is exactly the AT-1431 resurrection.
   With the real code the same interleaving (`test_p3_...`) stays `frozenset()`. So the code is right and the suite does not defend it. Add a test for the find/CAS race
   (probe p3 is a ready reproduction) and one for a grant-revoke-grant inside one transaction (OWN-B).

3. **Warning - D-129 wording not followed: the video operations are not behind the `AuthTx` protocol.** D-129 (`docs/DECISIONS.md:3080`, "behind the `AuthTx` protocol in `auth/store.py`").
   They live only on the concrete `MongoAuthTx` through `VideoOps` (`store_mongo_video.py:40`), reached by `video_tx()` which returns `Iterator[Any]` (`store.py:111-116`), and the SQLite SQL stays
   in `stages/video_access.py`, `video_requests.py`, `video_comments.py` behind 20 `if on_mongo():` branches. The maker disclosed it (manifest "Deviations"). Ruling: acceptable for U6c because
   `store_sqlite.py` and `store_mongo.py` are both at the cap and behaviour is proven equal by running the same assertions on both backends
   (`test_video_store_backends.py`, 7 tests parametrised over sqlite and mongo), and nothing here is a REJECTED approach; but it is a drift from the approved text, there is no type check on `tx`, and the next
   video change must touch two code paths. Needs a follow-up issue (move the SQLite SQL behind the protocol in a split of `store_sqlite.py`) and Umesh's note that the narrower step is accepted.

4. **Warning - the U8 importer skips the four video tables (gap for G1, not a U6c defect).** `auth/migrate_auth.py` imports users, groups, memberships, grants, sessions only; manifest "Deviations".
   Contract M45 (`qa/contracts/mongo-store.md:355`) names "users, hashes, generation, integer ids, seeded meta and allocator" and U8's dependency list (`:403`) is "U4, U5a, U6b, U7, U11", not U6c.
   If the `auth` area flips to `mongo` before this is closed, every share, share link (a holder of a live link is locked out), pending access request and comment starts empty. Ruling: not a Block for U6c;
   it must be recorded as an issue and as a G1 readiness-row precondition (M52 style) for the `auth` area, and U8's deps should add U6c.

5. **Ruling on the relaxed tests: honest.** (a) `test_auth_store_fencing.py` rename + `G:` assertion (grants are slotted now): the old property is covered by
   `test_a_zombie_insert_after_the_slot_was_re_granted_and_revoked_lands_nothing`, and the stale nodeid is tagged in `qa/evidence/mongo-store-u6bf/mutations.stale.json`.
   (b) `test_auth_store_contract.py:125-126`: the weaker assertion is slightly looser than before (it checks only that no `auth_grants` document has a slug), so I measured where `proj-` remains after `delete_user`:
   `PROJ HITS: {'auth_grants': [{'_id': 'proj-a|2|owner', 'slug': None, 'user_id': None, 'relation': None, '_e': 'G:00000007.000003'}, {'_id': 'proj-b|2|shared', ... 'G:00000007.000004'}]}`
   and nowhere else, and the deleted account's email is in no collection (`test_p12_...` passes). The slot id carries the project slug and the numeric user id, no address, no hash. (c) `test_auth_store_mongo.py` `_state` ignoring a hidden slot with `slug is None`:
   backed by `test_an_undone_insert_leaves_a_hidden_slot_with_none_of_its_data` (`test_auth_store_fence_slots.py:178-187`), which asserts every non-key field is `None` and the address is absent from the whole dump.
   Weakest point: `_blank_slot` keys on `slug is None`, so a hidden slot that kept other fields would be ignored by `_state`; that is covered only by the fence_slots test.

6. **Ruling on `store_mongo.py` at 300 lines: accepted, with a note.** `wc -l` = 300 (the cap is "<= 300", the doctor rule is green). It leaves zero headroom: the next change to
   `MongoAuthTx` needs a split and, by Lab Protocol, a new D-entry for any new file. Not a finding against this unit.

7. **Known reds confirmed pre-existing; the unit adds scheduler-side edges of the same kind. Not a Block, but the guard is now noisier.**
   `tests/test_cli_advice_resolves.py::test_the_collector_reports_what_it_could_not_resolve` fails identically at HEAD and at base 7ae3bba5 (run with `PYTHONPATH` on a `git archive 7ae3bba5 src` copy):
   one site, `store/mongo_backend.py:73`, a file this unit does not touch. `tests/test_schedule_tick.py::test_the_scheduler_side_reaches_no_browser_or_pipeline_module_even_transitively` also fails at both.
   I extracted `scheduler_side_violations()` and ran it against both trees: base = 3 (`store.mongo_routes -> browser.profiles`, `auth.store -> auth.store_mongo`, `auth.store_mongo -> auth.store_mongo_tx`);
   HEAD = 6 (adds `auth.store_mongo -> auth.store_mongo_video`, `auth.store_mongo_video -> auth.store_mongo_tx`, `auth.store_mongo_tx -> auth.store_mongo_fence`). The maker's "3 new edges" is exact, all three are
   inside the `auth.store_mongo*` chain, and none reaches a browser or pipeline module, so no new leak. The only real offender is the lazy `mongo_routes -> browser.profiles` import, which predates this unit.
   Carried since U6b: a red guard that lists violations cannot tell a new real leak from the known six. Recommend a coordinator decision: add the four `auth.store_mongo*` modules to `ALLOWED_OUTSIDE`
   (the U6a precedent at `tests/test_schedule_tick.py:158-159`) and fix or allow the one browser edge so the test goes green again.

8. **Info - small things.** (a) The manifest says `tests/test_video_store_backends.py -> 21 passed`; it collects and passes 20 (7 shared tests x 2 backends + 6 mongo-only). (b) After a committed delete whose
   post-commit sweep fails (store dies), the undo entry in `auth_users` still holds the plaintext `prior` (the deleted share's address) until the next writer sweeps: `test_p5_...` printed
   `LEFTOVER journal entries: 1 email in leftovers: True`, then `after next writer, email in dump: False`. Readers do not sweep a committed marker (`store_mongo_tx.py:65-72`, `dead_marker` ignores `committed`).
   By reading (not run): a committed delete of a NON-slotted document (comment, request) in the same situation leaves the hidden document with its full text until that sweep (`store_mongo_fence.py:141-145`).
   Transient, same window as the u6bf design, M30 is about hashes; worth one sentence in the contract. (c) `store/notification_prefs.py:24` still tests `db.store_exists()` (the SQLite file) in Mongo mode, so under Mongo
   notification preferences would never match and default to opted-out (safe direction); outside U6c's scope, belongs to the settings/prefs flip.

## Disabled accounts, every video and intake path (as asked)
- `access.principal_of` (`access.py:48-58`) returns None for a missing or disabled user; `schedule_owner.owner_principal` (`schedule_owner.py:23-33`), `intake_gate_auth.principal_for_email` (`:32-38`), `video_requests.approvers` (`:150-165`) all use it.
- `test_p6_...`: after `set_disabled`, `owner after disable: None None`. `test_p13_...` (own): an enabled-then-disabled second admin who is also the uploader drops out of `approvers` (`[ADMIN]` remains).
- Own mutant OWN-C (`store_mongo.py:48`, `disabled=False`) is killed by `test_principals_for_the_schedule_owner_and_the_intake_gate_come_from_the_seam[mongo]`.
- Store outage: `owner_principal` returns None (`schedule_owner.py:30-33`, refuses); `principal_for_email` lets `StoreUnavailable` propagate to `routes_runs._recheck_run_right` (`routes_runs.py:102`) and `AuthGate.recheck` (`intake_gate_auth.py:64`), which stops the run/job (fail closed by exception, as SQLite read errors did).
- Share-link resolve is anonymous by design and is token-hash only (`video_access.py:150-166`).

## Commands run and outputs (worktree D:/autoTesting/.claude/worktrees/mongo-u6c, `env -u ANTHROPIC_BASE_URL`, `-o addopts=`, at most 2 files per call, one call at a time)
```
tests/test_auth_store_contract.py + test_auth_store_seam.py            51 passed (276.55s)
tests/test_auth_store_mongo.py + test_auth_store_fence_slots.py        28 passed (16.39s)
tests/test_auth_store_recovery.py + test_auth_store_double_fault.py    25 passed (98.15s)
tests/test_auth_store_fencing.py                                       15 passed
tests/test_video_store_backends.py                                     20 passed   (manifest says 21)
tests/test_cli_store_auth_creds.py + test_schedule_owner_guard.py      20 passed
tests/test_intake_gate_auth.py + test_video_review_route.py            23 passed
uv run ruff check --no-cache src tests scripts                         All checks passed!
uv run autotester doctor > .work/doctor_b.txt                          exit 0, last line "doctor: clean" (advisory D-087 findings only)
tests/test_cli_advice_resolves.py   HEAD: 1 failed, 40 passed (mongo_backend.py:73)   base-src: 1 failed, 40 passed (same)
tests/test_schedule_tick.py         HEAD: 1 failed, 20 passed                         base-src: 1 failed, 20 passed (same test)
scheduler_side_violations()         base 7ae3bba5: 3    HEAD: 6    (listed in finding 7)
file sizes: store_mongo.py 300, store_mongo_fence.py 177, store_mongo_tx.py 238, store_mongo_video.py 145, video_access.py 206, video_requests.py 193, video_comments.py 163
```
New files under `src/`: exactly the two D-129 authorizes (`git diff --stat 7ae3bba5 HEAD`).

## Mutants (`scripts/mutation_check.py`, sandbox copy; specs derived from `qa/evidence/mongo-store-u6c/mutations-{fence,video}.json`)
Maker's, re-run by me: fence s1, s2, s3, s5, s7, s9, s10, s11 all KILLED on their named tests; video v2, v6, v7, v9, v10, v11 all KILLED (14/14). Where the maker listed two tests, both failed or the listed subset did.
Own: OWN-A (takeover CAS without the `_e` guard) SURVIVED, OWN-B (takeover `<=` to `<`) SURVIVED (`8/10 killed` for the fence run); OWN-C (mongo `User.disabled` forced False) KILLED (`7/7` for the video run). OWN-A and OWN-B are finding 2.

## Adversarial probes (scratch, not committed: `.work/probe/test_probe_b.py`, run with `PYTHONPATH=tests`)
p1 zombie share insert after recover + re-grant + revoke: refused, `emails()` empty, address absent from the dump. p2 two stalled holders of different epochs, one recoverer, re-grant, revoke: both refused, every slot `G:`-hidden.
p3 zombie paused between find_one and takeover CAS while a recoverer raises the stamp: refused. p4 undone insert and committed delete of a share, comment delete: no address, no comment text, journal empty.
p8 zombie `create_link` after recover + purge (non-slotted tombstone path): refused, link does not resolve. p9 delete then raise: share restored with every field. p5/p7/p10/p11 are findings 8b, 1, 1, 2.

## What the maker must do before the unit is closed
Fix or record findings 1 and 2 (a test for the find/CAS race and for same-transaction regrant are cheap), file issues for 3 and 4, and raise 7 with the coordinator. No code was edited by this checker.
