# Verdict - e2e-fixes-e10 (checker A, independent; focus E10.1 and E10.2)

**Verdict:** PASS
**Status:** PASS (3 non-blocking warnings, W1-W3 below)
**Cycle checked:** 0
**Reviewed SHA:** 47e08fd9 (base 6eb21a54), worktree `D:/autoTesting/.claude/worktrees/e2e-e10`. No `src/`, `tests/` or `docker/` file was modified by me (mutants ran in the harness's scratch copy; `git status --short` was empty before this commit). I did not read any other checker's verdict.
**Scope:** `qa/contracts/e2e-fixes.md` E10.1 and E10.2 in depth. E10.3 (the `_took` / `_hide_slot(back=)` / `replay` change) was left to the other checker; I only ran its tests and mutants A1/A2 as part of the fence run.

## Commands re-run (`.venv/Scripts/python.exe -m pytest <2 files> -o addopts= -q -p no:cacheprovider`, TMP under `.work/tmp-chkA`)

| Command | Result |
|---|---|
| `tests/test_cli_store_auth_creds.py tests/test_cli_store_auth_video.py` | 24 passed |
| `tests/test_cli_store_state.py tests/test_auth_store_fence_slots.py` | 30 passed |
| `tests/test_auth_store_fence_recreate.py tests/test_auth_store_fencing.py` | 21 passed |
| `ruff check src tests scripts` | All checks passed |
| `autotester doctor > file` | 2 violations, both `docs/SNAPSHOT.md` (stale-generated / stale-committed). Nothing about line caps, duplicates or the changed files. |

The SNAPSHOT staleness is pre-existing and not caused by this branch: `autotester snapshot --print` against the committed file differs only by decision rows (`D-126` missing from the regeneration, `D-131` missing from the file), and the branch touches no `docs/`. The full suite was not run (task rule, low memory).

## E10.1 - the importer carries the four video tables

- **Same transaction, journal and fence, not raw collections.** `migrate_auth.py:174-190` calls `_import_video` inside the one `sm.MongoAuthStore(...).transaction()` that imports users. Shares go through `tx.set_share` (`:158`), the other three through `tx._insert` (`:162`), the journalled writer. `test_the_video_rows_are_journalled` and `test_a_failure_after_the_video_rows_were_written_undoes_them_whole` pin it.
- **Fidelity.** `COLUMNS` (`:28-32`) lists every SQLite column of the four tables verbatim (including `granted_by`, `granted_at`, `token_hash`, `revoked_at`, `decided_*`, `at_s`, `edited_at`, `pointer_line`); request and comment ids are kept (`_video_rows` maps the key column to `_id`, `:121-126`); a share keeps `VideoOps.set_share`'s deterministic slot id. `test_every_row_comes_across_and_the_application_reads_it_back` reads the rows back through `VideoOps` (`share_emails`, `link_target`, `request_rows`, `comment_rows`), compares column for column, and asserts a revoked link stays revoked.
- **Idempotent, never overwritten, conflicts reported.** `_video_state` (`:129-145`) returns `to_insert` / `unchanged` / `conflicting-id`; only `to_insert` writes (`:155-163`). Second apply writes 0 (`test_a_second_apply_writes_nothing_and_never_replaces`); an altered `granted_by`, flipped `revoked_at` and changed comment `text` are each `conflicting-id=1`, `verify` exits 1, a re-apply writes 0 and the altered values survive (`test_a_differing_target_row_is_reported_and_verify_fails`). A pending request for the same (slug, video, requester) as an existing pending row is reported `conflicting-id`, not duplicated, and the other two requests still come across (`:142-144`, `test_a_pending_request_...`).
- **Allocators.** `_seed_allocator` for `access_requests` and `video_comments` (`:164-165`); the test pre-advances the target counters and asserts new ids 10 and 9 (`max+1`), not a collision.
- **Counts only.** No format string in the importer touches a value. The canary test runs dry run, apply, re-apply and verify and checks stdout, stderr (`capsys`) and `caplog` against the canary email, token hash, comment text, requester and `pointer_line` text: absent.
- **Dry run opens no client.** `auth_status(remote=False)` (`:216-221`) returns before `default_store()` is called; `rig.opened == 0` is asserted and `--check-remote` opens one.
- **Verify rows.** `cli_store._auth_part` now returns the dict and both callers `extra.update(...)` (diff of `cli_store.py`), so `migrate` and `verify` print `auth_shares`, `auth_links`, `auth_access_requests`, `auth_comments` beside `auth_users`; the existing `bad += sum(to_insert + conflicting-id)` rule covers every row. The module header's "not here" sentence is corrected (`:8-11`).
- **Hidden (deleted) share slots are not mistaken for live rows**: `tx._docs` filters `hidden` docs (`store_mongo_tx.py:81-82`).

### My own mutation runs (harness `scripts/mutation_check.py`, mutants of my own choosing, scratch copy)

6/6 killed, each by the test that names the behaviour: Ma requests allocator unseeded; Mb `pointer_line` not read; Md dry run undercounts comments; Mg a revoked link written live; Ml verify never flags a video conflict; Mn share compared on email only. I did not re-run the maker's V1-V7 file; the maker's run (`qa/evidence/e2e-fixes-e10/mutation-run-video.txt`, 7/7) is consistent with my results and none of my mutants overlap V3-V6 weakly.

## E10.2 - takeover compare-and-set pinned

Re-ran the contract's mutants and the maker's H1 myself on the real fence tests (harness, scratch copy): **O1 KILLED** (both `[grant]` and `[share]` of `test_a_zombie_stalled_between_the_slot_read_and_the_takeover_lands_nothing`), **OWN-B KILLED** (`test_a_slot_hidden_at_epoch_e_is_taken_by_a_writer_of_epoch_e_not_by_an_earlier_one` plus the E10.3 refused tests), **H1 KILLED** (`test_a_stalled_recoverer_does_not_hide_a_later_holders_live_grant`, not recorded as equivalent). A1 and A2 (E10.3) also killed. The new zombie test is not vacuous: it stalls exactly at the takeover `update_one` filtered on the stamp it read, lets a successor epoch raise the slot to `G:<later>`, then asserts `AuthStoreBusy`, a still-revoked grant/share and a later legitimate re-grant working. The diff to `tests/test_auth_store_fence_slots.py` is additions only (existing zombie/slot/journal tests unmodified). `qa/evidence/mongo-store-u6c/mutations-fence.json` has O1, OWN-B, H1 (plus A1, A2) added.

## Warnings (non-blocking)

- **W1.** Nothing asserts the SQLite file is byte-identical after `--apply` (contract: "the SQLite file is not modified"). `read_auth` opens it `mode=ro` (`:43`) and the code never writes, so the property holds by construction; a one-line hash-before/after assertion would pin it.
- **W2.** The `access_requests` pending-twin conflict makes `migrate --apply` exit 1 while still writing the non-conflicting rows (test pins this: `written == 2`). That matches the `auth_users` rule and the contract, but an operator will see a partial import with exit 1; worth a line in the runbook.
- **W3.** The maker's claim of V1-V7 is met by their own file; I note the manifest's `qa/evidence/mongo-store-u6c/mutations-fence.json` now holds both files under `tests`, so a full fence run is two files per mutant (memory-heavy on this machine). Not a defect.

## Not checked by me

E10.3 correctness beyond its tests passing and A1/A2 being killed (the other checker's focus); the full `uv run pytest`; any real `--apply` (none run, none needed).
