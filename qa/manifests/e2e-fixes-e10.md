# Manifest - e2e-fixes-e10

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** `qa/contracts/e2e-fixes.md`, unit E10 (E10.1, E10.2, E10.3). **Criticality:** HIGH (auth data and the revocation fence).
**Authority:** no new `src/` module, no `qa/contracts/` edit, no DECISIONS entry needed (E10.3 outcome A, a fix, not an accepted residual).
**Branch:** `feat/e2e-e10` (worktree `D:/autoTesting/.claude/worktrees/e2e-e10`), cut from master `6eb21a54`. Not merged, not pushed, `migrate --apply` never run (fake Mongo only).
**Code SHA:** the commit that adds this file, `git log -1 feat/e2e-e10`.

## What changed

| File | Kind | Change |
|---|---|---|
| `src/autotester/auth/migrate_auth.py` (227 lines) | E in place | header corrected; `COLUMNS` gains the four video tables (`video_shares`, `video_links`, `access_requests`, `video_comments`, every SQLite column verbatim); `read_auth` tolerates a file with no video table; new `_video_rows`, `_video_state` (one classifier for dry-run, apply and verify), `_import_video` (inside the SAME `MongoAuthStore.transaction()` as users, shares through `VideoOps.set_share`, the rest through `tx._insert` = journal + fence, never a raw collection; request and comment allocators seeded via the existing `_seed_allocator`); `import_auth` / `auth_status` now return `dict[row-name, Counter]` (`auth_users` + `auth_shares`, `auth_links`, `auth_access_requests`, `auth_comments`) |
| `src/autotester/cli_store.py` | E in place | `_auth_part` returns that dict; both callers `extra.update(...)`, so migrate and verify print one row per table and the existing exit rules (`conflicting-id`/`to_insert` -> 1) apply to every row |
| `src/autotester/auth/store_mongo_fence.py` (198 lines) | E in place (E10.3 fix only) | `_took` (new, reads the same transaction's earlier delete from the journal), `_hide_slot(..., back=)`, one added line in `replay`; module docstring gains the delete-then-recreate sentence |
| `tests/test_cli_store_auth_video.py` (9 tests) | N | E10.1 |
| `tests/test_auth_store_fence_slots.py` (+4 tests, 281 lines) | E | E10.2 |
| `tests/test_auth_store_fence_recreate.py` (6 tests) | N | E10.3 |
| `qa/evidence/mongo-store-u6c/mutations-fence.json` | E | O1, OWN-B, H1, A1, A2 added; `tests` is now the two fence files |
| `qa/evidence/e2e-fixes-e10/mutations-video.json`, `mutation-run-video.txt` | N | E10.1 mutants V1-V7 |
| `qa/evidence/mongo-store-u6c/mutation-run-fence-e10.txt`, `mutations-fence-ownb.json`, `mutation-run-fence-ownb.txt` | N | full fence run (16 mutants) and the single OWN-B re-run after one test fix (see judgement call 2) |

## Criteria map

| Crit | Code | Test (what it kills) |
|---|---|---|
| E10.1 fidelity, ids kept | `migrate_auth.py` `_video_rows`, `_import_video` | `test_every_row_comes_across_and_the_application_reads_it_back`: `VideoOps` reads (`share_emails`, `link_target`, `request_rows`, `comment_rows`) return the source rows column for column (ids 4/7/9 and 3/5/8, `granted_at`, `revoked_at`, `edited_at`, `pointer_line`); `written` per row = row count |
| E10.1 idempotent, never overwritten | `_video_state` | `test_a_second_apply_writes_nothing_and_never_replaces` (`written: 0`, `unchanged` = rows); V7 killed |
| E10.1 allocators | `_seed_allocator(tx, table)` | `test_the_allocators_start_above_every_imported_id` (target counters already at 2; new request gets 10, new comment 9); V2 killed |
| E10.1 counts only | no value is formatted anywhere | `test_the_report_and_logs_carry_counts_never_a_value` (canary email, token hash, comment text, requester absent from CLI output, capsys, caplog across dry run, apply, re-apply, verify); V4 killed |
| E10.1 dry run | `auth_status(remote=False)` never calls `default_store()` | `test_a_dry_run_opens_no_client_and_counts_each_table` (`rig.opened == 0`, `to_insert` per table; `--check-remote` opens one); V6 killed |
| E10.1 conflicts + verify row | `_video_state` -> `conflicting-id` | `test_a_differing_target_row_is_reported_and_verify_fails` (changed `granted_by`, flipped `revoked_at`, changed comment `text`: three rows report `conflicting-id=1`, requests row 0, verify exit 1; a re-apply writes 0 and replaces nothing); V3 killed |
| E10.1 one pending per person per video | `_video_state` pending twin | `test_a_pending_request_for_the_same_person_and_video_is_not_duplicated` (conflict reported, one pending row, other two rows written); V5 killed |
| E10.1 same transaction, journal + fence | `tx._insert` / `set_share` | `test_the_video_rows_are_journalled` (undo entries exist for all four collections at commit) and `test_a_failure_after_the_video_rows_were_written_undoes_them_whole`; V1 (raw collection) killed by both |
| E10.2 CAS between read and write | `insert_fenced` `store_mongo_fence.py` `update_one({"_id","_e": cur["_e"]})` | `test_a_zombie_stalled_between_the_slot_read_and_the_takeover_lands_nothing[grant\|share]`; O1 killed |
| E10.2 epoch `<=` | same | `test_a_slot_hidden_at_epoch_e_is_taken_by_a_writer_of_epoch_e_not_by_an_earlier_one` (same epoch takes, earlier refused, live duplicate raises) and the E10.3 refused tests; OWN-B killed |
| E10.2 `_hide_slot` CAS | `store_mongo_fence.py` `_hide_slot` | `test_a_stalled_recoverer_does_not_hide_a_later_holders_live_grant`; H1 killed (not equivalent) |
| E10.3 (A) fix, rollback | `_took` + `_hide_slot(back=)` | `test_a_refused_transaction_restores_the_original_share` / `_grant` (original `granted_by` present); A1 killed |
| E10.3 (A) fix, recovery | `replay` accepts the recoverer's hide stamp for a slotted restore | `test_a_holder_that_died_before_committing_leaves_the_original_present[share\|grant]`; A2 killed |
| E10.3 every crash point | both | `test_a_kill_at_every_call_point_never_loses_the_document[share\|grant]` (store dies at call 1..n, lease aged out, document present) |

## Evidence (exact commands)

```
.venv/Scripts/python.exe -m pytest <2 files> -o addopts= -q -p no:cacheprovider   (one pair at a time; machine low on memory)
tests/test_cli_store_auth_creds.py tests/test_cli_store_auth_video.py   24 passed
tests/test_cli_store_state.py                                           18 passed
tests/test_auth_store_fencing.py tests/test_auth_store_recovery.py      33 passed   (unmodified)
tests/test_auth_store_fence_slots.py tests/test_auth_store_fence_recreate.py   18 passed
tests/test_auth_store_double_fault.py tests/test_auth_store_mongo.py    27 passed   (unmodified)
tests/test_video_store_backends.py tests/test_auth_store_contract.py    58 passed   (unmodified)
tests/test_auth_store_seam.py                                           13 passed   (unmodified)
ruff check src tests scripts                                            All checks passed!
autotester doctor                                                       2 violations, both docs/SNAPSHOT.md stale-generated/stale-committed (see below); nothing about line caps, duplicates or the files above
```

Mutation (`scripts/mutation_check.py`, venv python):
- `qa/evidence/e2e-fixes-e10/mutations-video.json` -> `mutation-run-video.txt`: **7/7 killed** (V1 raw collection write, V2 no allocator seed, V3 conflict called unchanged, V4 prints rows, V5 second pending inserted, V6 dry run opens client, V7 share `granted_at` stamped).
- `qa/evidence/mongo-store-u6c/mutations-fence.json` -> `mutation-run-fence-e10.txt`: 15/16 killed on the first run: s1-s11 (the old eleven, all still killed) plus O1, H1, A1, A2 killed; OWN-B reported SURVIVED only for the extra test I had listed (`test_a_refused_transaction_restores_the_original_share`): its `pytest.raises(RuntimeError, match="refused")` also matched `AuthStoreBusy("...the change was refused")`. OWN-B was killed by the E10.2 test in that same run.
- After changing that test to a `ValueError("declined")`, `mutations-fence-ownb.json` -> `mutation-run-fence-ownb.txt`: **OWN-B killed by all of its claimed tests**.

## Judgement calls the checker should look at

1. **E10.3 outcome A, not B.** `_took` finds the same-transaction earlier delete by reading the journal (older entry, same `coll` and `doc_id`, `op == "set"`, `gone`), so no `store_mongo_tx.py` edit and no change to the entry vocabulary. Rollback (`by is None`): the re-inserted slot goes back to `G:<delete's me>`, which the delete's restore already matches. Recovery (`by` set): the slot is hidden at `hide_stamp(by)` exactly as before (a zombie of the dead epoch still cannot take it, its epoch is lower), and the restore of a slotted `set` entry now also accepts `hide_stamp(by)`. A chain ins0, del1, ins2 unwinds correctly because ins0 has no `gone` predecessor. The lease/epoch design (D-129) is unchanged.
2. **The OWN-B claim listed in the first fence run** named a test that could not tell the two errors apart; fixed in the test, not in the mutant list's meaning.
3. **`import_auth`/`auth_status` return shape** changed from one `Counter` to a dict of `Counter`s so verify prints a row per table "through the same `auth_status` path". Only `cli_store.py` called them; the `auth_users` row text is unchanged.
4. **Row names** are `auth_shares`, `auth_links`, `auth_access_requests`, `auth_comments` (the `video_` prefix dropped, `auth_` kept, matching `auth_users`).
5. **A SQLite file written before the video tables existed** reads as zero rows for them (`read_auth` checks `sqlite_master`; the file is still opened `mode=ro`).
6. **`docs/SNAPSHOT.md` was NOT regenerated.** `autotester doctor` flags it stale on this base (pre-existing drift, the same note as e2e-fixes-e7); four parallel worktrees regenerating it would only conflict. Regenerate once on master.
7. **Not run:** the full `uv run pytest` (machine low on memory, task rule); `uv` itself crashed with an access violation under memory pressure, so the venv python was used.

## Not done / out of scope

- No real `--apply`, no Mongo URI read, no `.env` value printed.
- No `review` agent dispatched from here (maker writes, checker judges).
