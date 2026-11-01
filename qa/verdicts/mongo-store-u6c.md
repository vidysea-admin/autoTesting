# Verdict - mongo-store-u6c (Checker A, functional / contract)

**Cycle checked:** 0
**Verdict:** PASS (no blocking finding; 3 warnings that should be folded in, see W1-W3)
**Unit:** U6c (`qa/contracts/mongo-store.md`, M30 CRITICAL, M29 for the fence change), folds in AT-1431 and AT-1432. Branch `feat/mongo-store-u6c`, head `51eeaeff` (code commit `5caadae6`), base `7ae3bba5`.
**Role:** Checker A. U6c is dual-checked; this is half of the PASS. I did not read any other checker's verdict on this unit.
**Method:** fresh context; every manifest claim re-run, not trusted; read-only toward `src/` and `tests/`; two test files per pytest call, one call at a time, `env -u ANTHROPIC_BASE_URL`; no `.env` value read or printed. Scratch (probe test, mutated copy, base tree) lives in the session scratchpad, not in the repo.

## Verdict basis in one paragraph

The AT-1431 design holds: an id slot of a re-created document (`auth_grants`, `video_shares`) is never empty again once used, a legitimate insert takes a hidden slot over only by compare-and-set on the stamp it read and only if that stamp's epoch is not later than its own, and a recoverer raises an older hidden stamp past the dead holder's epoch. I traced the stall points by hand (before the first insert, after the duplicate-key, after the `find_one`, after another holder's re-grant and revoke) and found no path on which a stalled older-epoch writer lands. 11 shipped mutants were killed on my re-run, 2 of my own were killed, and 1 of my own survived: that is a test gap, not a code defect (W1).

## Findings

### Blocking: none

### Warnings (fold in; none changes the verdict)

**W1. The stamp compare-and-set on slot takeover is untested (own mutant O1 survives every shipped test).**
`auth/store_mongo_fence.py:169-171`: the takeover is `coll.update_one({"_id": ..., "_e": cur["_e"]}, ...)`. I replaced the filter with `{"_id": doc["_id"]}` (a blind takeover) in a scratch copy of `src/`; `tests/test_auth_store_fence_slots.py` plus `tests/test_video_store_backends.py` stay green (harness: `SURVIVED O1 ... pytest exit 0`). The hazard is real: a zombie that already read hidden stamp `G:e1` (epoch not later than its own) and then stalls before `update_one`; a successor recovers it and raises the slot to `G:e2`; without the stamp condition the zombie's write still matches and the revoked grant comes back. The shipped zombie test stalls at `insert_one`, before the duplicate is seen, so it only exercises the epoch comparison. I wrote the missing test (scratch `probe/test_probe.py::test_takeover_stall_between_find_and_update`: grant, revoke, then stall the zombie at the `update_one` of a `G:` slot on `auth_grants` while a successor runs `set_display_name`; expect `AuthStoreBusy` and `_people() == {}`). It PASSES on the shipped code and FAILS on the O1 copy ("DID NOT RAISE AuthStoreBusy"). Fix: add that test (about 12 lines) to `test_auth_store_fence_slots.py` and add O1 to `mutations-fence.json`. The matching CAS in `_hide_slot` (`store_mongo_fence.py:102`) was not separately mutated by me; the same stall-after-read test shape applies.

**W2. Manifest statements that do not match the tree (small, but they are the claims a later reader trusts).**
(a) "21 collected" for `tests/test_video_store_backends.py`: the file has 20 tests (7 parametrised x 2 backends + 6 single); my run is `20 passed`. (b) "`store_sqlite.py` ... at the cap": it is 246 lines (`wc -l`); the true reason SQLite video SQL cannot move in is that about 100 lines of SQL would not fit the 54 lines of headroom, and `store.py` (126 lines) could take the protocol signatures. (c) The table row for `ui/intake_gate_auth.py` says store creation, `exists` and `reading` are "inside the fail-closed try": only `schedule_owner.py:25-31` has a try. `intake_gate_auth.py:31-36` has none; an outage raises `StoreUnavailable` out of `recheck`, which `ui/routes_intake.py:47-58` turns into a job `failed` ("Nothing was added"). That is still fail closed, so the code is fine; the sentence is wrong. (d) AT-1432 W3 (a no-op `store migrate --apply` takes the lease and bumps `auth_meta/epoch`) is NOT fixed (the manifest says so honestly); AT-1432 therefore stays open for that one item, W1/W2/W4 of it are delivered (s4, s5, s6 killed).

**W3. The scheduler-side import test is red at base and this unit adds three edges to it** (rulings below, item 7). Not blocking, but someone must own that gate before G1.

### Rulings asked for

**R1. Video operations only on the Mongo transaction, not on the `AuthTx` protocol (D-129 wording). Accepted as a documented deviation, not a block.**
D-129 (`docs/DECISIONS.md:3082`) says the module is the implementation "behind the `AuthTx` protocol in `auth/store.py`". It is not: `AuthTx` (`auth/store.py:23`) has no video method, `video_tx()` (`auth/store.py:111`) returns `Iterator[Any]`, and each public function in `stages/video_access.py`, `video_requests.py`, `video_comments.py` branches on `on_mongo()` ahead of the unchanged SQLite SQL. Consequences: two implementations of one concept live in the stage modules, and the typed seam is bypassed (the `Any`). What makes it acceptable: D-129 authorises exactly the two modules created and nothing else is new (`git diff --stat`: only `store_mongo_fence.py` and `store_mongo_video.py` are new under `src/`); SQLite behaviour is untouched (the only edits on that path are `db.store_exists()` -> `auth_store().exists()`, which is `store_sqlite.py:234-235`, and `approvers`, which now reads through `principal_of`); parity is tested on both backends (14 parametrised cases). Recommended follow-up, needs Umesh because it needs room: declare the video methods on `AuthTx` (store.py has 174 lines of headroom) and give SQLite a home for the SQL (a mixin module is a new file, so a D-entry). Until then the deviation should be written into the next DECISIONS entry so D-129 is not read as satisfied literally.

**R2. The three relaxed tests are honest in substance; one assertion is looser than it needs to be.**
- `tests/test_auth_store_fencing.py` rename + assertion (`any(... _e startswith "G:")`): honest. The behavioural part (the zombie is refused with `AuthStoreBusy`, "refused", and a later holder can grant again) is unchanged, and the stronger property is now in `test_a_zombie_insert_after_...`. The old nodeid is tagged in `qa/evidence/mongo-store-u6bf/mutations.stale.json` and doctor accepts it.
- `tests/test_auth_store_mongo.py::_blank_slot` (`_state` ignores a hidden blank slot of a slotted collection): honest. It exempts only a slot with `G:` stamp AND `slug is None`; a rollback that left a live document blanked, or failed to restore one, would still show as a difference against the "before" state.
- `tests/test_auth_store_contract.py:126-127`: the change is needed (a Mongo hidden slot keeps its id, which contains the slug) but the new line `"proj-" not in env.dump() or not any(d["slug"] for d in ...)` is an `or`: it passes if `proj-` appears in ANY collection as long as the grant documents are blank, and `d["slug"]` raises `KeyError` on a hidden slot that has no `slug` key. I measured where `proj-` actually is after the scenario (scratch probe `test_where_proj_remains_after_delete_user`, Mongo): only in two `auth_grants` documents, `{'_id': 'proj-a|2|owner', 'slug': None, 'user_id': None, 'relation': None, '_e': 'G:00000006.000002'}` and the same for `proj-b|2|shared`; nothing in any other collection. So the shipped state is clean; the assertion should say that (`set(collections containing "proj-") <= {"auth_grants"}` and every such document blank) instead of an `or`.
- Raw documents hold no email, hash or grant data: for the blanked hidden slot see the dumps above (all fields `None`); for shares `test_a_deleted_share_keeps_nothing_of_the_address_and_no_hash_is_in_a_video_collection` plus `test_an_undone_insert_leaves_a_hidden_slot_with_none_of_its_data` (asserts every non-`_id`/`_e` field is `None` and `"person@example.test" not in env.dump()`); `$argon2` appears only in `auth_users` (test asserts both directions). Two low notes: a share id carries an unsalted `sha256(email)` (`store_mongo_video.py:47`), so anyone with read access to the database can confirm a guessed address; and hidden slots are never reaped, so a deleted user's or project's slug stays inside a slot `_id` (`store_mongo_video.py:10-11` and the manifest both state this).

**R3. U8 importer skips the video tables: a follow-up gap with a mis-attribution to fix, not a U6c block.**
`auth/migrate_auth.py:8` says "`browser_sessions` and the video tables are not here (U12, U6c)", and `grep video_ auth/migrate_auth.py` finds nothing. The U6c row of the unit table (`qa/contracts/mongo-store.md:398`) lists the Mongo store side only; U8 (`:403`) owns "auth importer". So the docstring points the work at U6c, but the contract does not give it to U6c, and the manifest calls it a follow-up. Consequence if left: flipping the `auth` area at G1 starts with empty shares, links, requests and comments (existing share links stop resolving). Required: a tracked item (issue or U8 criterion) saying the importer must carry the four video tables (digest-keyed links verbatim, share ids recomputed with the same `sha256` rule, allocators set above existing ids), and the docstring owner corrected. G1 for `auth` must not be approved before that.

**R4. `store_mongo.py` at 300 lines: passes, no headroom.**
`wc -l` = 300 (base 299, +1 net: one import line, `store_mongo.py:22`). Doctor's rule is `> 300`, and `autotester doctor` is clean. Any further edit to that file will fail doctor, so the next auth-store change needs a split, which per D-122/D-129 needs a D-entry first.

### Other checks

5. **D-129 scope.** Only the two authorised files are new under `src/`; `docs/MAP.md` and `docs/SNAPSHOT.md` are regenerated; `stages/reachability.py`, `run_launcher.py`, `browser/video.py`, `ui/routes_video.py` are untouched (not in `git diff --stat`). Edits are in place (no `*_v2`/`*_new`).
6. **AT-1432 delivered items verified by mutants:** s4 (late committed sweep keeps its `_e G:<me>` condition), s5 (abort CAS before the marker read), s6 (`recover` only below its own epoch) all killed on re-run.
7. **Scheduler-side import test.** Static closure (`scheduler_side_violations`, same code as `tests/test_schedule_tick.py:202`, run against `git archive 7ae3bba5` and against the head tree):
   - BASE (3): `auth.store -> auth.store_mongo`; `auth.store_mongo -> auth.store_mongo_tx`; `store.mongo_routes -> browser.profiles`.
   - HEAD (6): the same three, plus `auth.store_mongo -> auth.store_mongo_video`, `auth.store_mongo_tx -> auth.store_mongo_fence`, `auth.store_mongo_video -> auth.store_mongo_tx`.
   So the test is red at `7ae3bba5` independent of this unit, and this unit adds exactly 3 edges, all between auth-store modules; none reaches a browser, runner or pipeline module (the only forbidden-direction edge, `store.mongo_routes -> browser.profiles`, is pre-existing). `schedule_owner.py` now imports `auth.store` instead of `auth.db`, both already allowed. Not blocking; the right fix is one allow-list decision for the four `auth.store_mongo*` modules plus a ruling on the lazy `browser.profiles` import, by whoever owns TS6.
8. **`test_cli_advice_resolves` red at base.** Run at head: `FAILED tests/test_cli_advice_resolves.py::test_the_collector_reports_what_it_could_not_resolve`, one item `(store/mongo_backend.py, 73)`. `advice_scan.unresolved_in_source` run on the base tree gives the same single site, and `git diff 7ae3bba5..HEAD -- src/autotester/store` is empty. Pre-existing, not from this unit.
9. **Fail closed.** `test_an_unreachable_store_fails_closed_on_every_video_call` and `test_the_schedule_owner_is_nobody_while_the_store_is_unreachable` pass; `schedule_owner.py:25-31` returns `None` on any read failure; `resolve_link` etc. raise `StoreUnavailable` rather than allow.
10. **Journal during a delete.** A slotted delete journals `prior` (the old email) inside the undo entry in `auth_users` until commit (`store_mongo_tx.py:139-140`); it is swept at commit (`store_mongo_fence.py:144`), and a failed sweep is cleaned by the next holder. Same retention class as the u6bf password-hash priors; noted, not a finding.

## Commands run and results (worktree `D:/autoTesting/.claude/worktrees/mongo-u6c`, `env -u ANTHROPIC_BASE_URL uv --directory <wt> run pytest <files> -o addopts=`)

| Command | Result |
|---|---|
| `tests/test_auth_store_contract.py tests/test_auth_store_seam.py` | `51 passed` |
| `tests/test_auth_store_mongo.py tests/test_auth_store_fence_slots.py` | `28 passed` |
| `tests/test_auth_store_recovery.py tests/test_auth_store_double_fault.py` | `25 passed` |
| `tests/test_auth_store_fencing.py` | `15 passed` |
| `tests/test_video_store_backends.py` | `20 passed` (manifest said 21, W2) |
| `tests/test_cli_store_auth_creds.py tests/test_schedule_owner_guard.py` | `20 passed` |
| `tests/test_intake_gate_auth.py tests/test_video_review_route.py` | `23 passed` |
| `tests/test_cli_advice_resolves.py tests/test_mongo_guard.py` | `1 failed, 56 passed` (the known red, item 8) |
| `uv run ruff check --no-cache src tests scripts` | `All checks passed!` |
| `uv run autotester doctor > scratch/doctor.txt` | exit 0, last line `doctor: clean` (advisory D-087 findings only) |
| `scheduler_side_violations()` base vs head | 3 vs 6 violations, listed in item 7 |

Mutation re-runs (`scripts/mutation_check.py`, sandbox copy, subsets of the maker's specs):
- Fence, `tests/test_auth_store_fence_slots.py`: `6/6 mutations killed` (s1, s3, s4, s5, s9, s10; each killed by a named test, s1 additionally by the recoverer test).
- Video, `tests/test_video_store_backends.py`: `5/5 mutations killed` (v1, v4, v7, v9, v11).
- Own mutants (both test files): `2/4 mutations killed`. KILLED O2 (undone slotted insert hides at epoch 0, killed by `test_a_recoverer_raises_an_older_hidden_stamp_...`); KILLED O3 (schedule owner returns an empty principal for a disabled account, killed by `test_principals_for_the_schedule_owner_and_the_intake_gate_come_from_the_seam[mongo]`, the disabled-principal check); SURVIVED O1 (blind slot takeover, W1); SURVIVED O4: this one is my own error, not a gap: it changed `epoch is not None and` to `epoch is None or`, which differs only when `epoch` is `None`, and `_log` (`store_mongo_tx.py:105-106`) raises before any write when there is no lease, so the branch is unreachable. Discarded as an equivalent mutant.
- Probe on the O1 copy: `1 failed ... DID NOT RAISE AuthStoreBusy`; probe on shipped code: `2 passed`.

Total: 11 shipped mutants re-run and killed (6 + 5), 2 own killed, 1 own survived (W1), 1 own equivalent.

## What the maker should do for the close-out

1. Add the W1 test and the O1 mutant. 2. Correct the four manifest statements in W2. 3. Tighten the contract-test assertion (R2). 4. Open an item for the importer (R3) and record the R1 deviation in the next DECISIONS entry.
