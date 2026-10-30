# Manifest - mongo-store-u7

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** `qa/contracts/mongo-store.md` (ACTIVE 2026-10-29), unit U7. **Criticality:** dual (U7 row is marked dual; M19, M20, M52, M53 are CRITICAL). Two independent checkers.
**Authority:** D-126 (hosts the path-level primitives in the new module `src/autotester/store/filestore_paths.py`; `store/mongo_bucket.py` only if GridFS code moved, and none moved); D-122/D-123 untouched.
**Branch:** `feat/mongo-store-u7` (cut from master `fe1ac6c8`). Not merged to master, not pushed.
**Base SHA:** `fe1ac6c8`
**Code SHA:** `13b793155360308465db331a6f0e07cae88484f8` (the only code commit; this manifest and `qa/evidence/mongo-store-u7/` are a second commit on top of it)
**Criteria judged by U7:** M19 and M20 at path level on all three backends, M52 (the READ-SIDE list), M53 (the U7 and `M53-gated` rows are removed, none moved to `permanent`).
Round cap: critical unit, D-014 cap of 2 fix cycles.

## What changed

| File | Kind | One job / change |
|---|---|---|
| `src/autotester/store/filestore_paths.py` (219 lines) | **N, D-126** | Path-level verbs routed like `filestore` (`_route` / `_holders`): `create_exclusive_path :44`, `put_if_path :51` (CAS), `read_text_path :58`, `read_bytes_path :64`, `digest_path :73`, `is_dir_path :79`, `rename_path :85` (`os.replace` file-to-file, else get/put/delete so a failure leaves the source), `delete_tree :100`, `touch_path :113`, `remove_stray_temps :125`, `remove_empty_dir :137`, `RevisionedFile :189` (whole-document file saved by CAS with a growing `rev`). Plus the **local-only** verbs `scratch_mkdir/children/mtime/rmtree/unlink :153-176` (fenced to outside the data root or under `.work/`, else `UnsafeName`) and `evidence_mkdir :178` (only under `qa/evidence/`). |
| `src/autotester/core/file_lock.py` | E in place | `create_new :33` (temp file + `os.link`, so the content is atomic and `os.link` refuses an existing name; `O_EXCL` fallback `_create_excl :56` on a volume without hard links). |
| `src/autotester/store/filestore.py` (291 lines) | E in place | `FileBackend.create_exclusive :71` now calls `create_new` (a reader can no longer see a half-written claim); `FileBackend.get_bytes :53`. `import os` dropped. |
| `src/autotester/delivery/inbox.py` | E | `_create_once` deleted; `append`/`claim` use `create_exclusive_path :89 :93`; `claimed_at :99` reads through `read_text_path`. |
| `src/autotester/stages/schedule_store.py` | E | claim `:55` = `create_exclusive_path`; `read_records :121` reads through the store; purge keeps its staged two-phase design on store verbs: manifest `create_exclusive_path :236`, moves `rename_path :239`, commit point `delete_path`, stage removal `delete_tree :244`; `_restore_stage :170-190` and `_recover_stages :195-199` read and list through the store. `import os`/`shutil` dropped. |
| `src/autotester/stages/orchestrate_checkpoint.py` | E | `_digest :174` = `digest_path`; `_load :205` = `read_text_path`; `flush :259` is a **compare-and-set** (`put_if_path(path, text, self._disk_hash)`; a loss raises the same "Checkpoint changed outside this instance" error), so the identity check no longer has a check-then-write window and holds on Mongo. |
| `src/autotester/core/trace.py` | E | `read_tool_spans :142`, `read_spans :156` read through `read_text_path`. |
| `src/autotester/store/team_store.py` | E | `create_marker :39` = `create_exclusive_path`; the raw `_create_exclusive` (a real O_EXCL on a state path, in the exempt `store/` dir) is gone. |
| `src/autotester/ui/run_queue.py` (297 lines) | E | queue file is a `RevisionedFile :84`: `_load :243`, `_save :261`. A save that loses the CAS writes nothing, logs "changed under this instance", adopts the stored state, and the next save lands. |
| `src/autotester/schema/run_queue.py` | E | `RunQueueFile.rev: int = 0` (`ge=0`). |
| `src/autotester/sources/intake_commit.py` | E | `intake_lock :70` is `create_exclusive_path(path, "")` (one holder on any backend); stale check `:55` via `mtime_path`; beat `:78` = `touch_path`; release = `delete_path`; staging and orphan sweep use the scratch verbs `:94-119`; `.tmp-*` and empty-folder cleanup use `remove_stray_temps`/`remove_empty_dir :104-105 :147`. |
| `src/autotester/sources/drive_intake.py`, `zip_intake.py` | E | `shutil.rmtree`, `.stat()`, `unlink` on fetch/extract scratch become `scratch_*` verbs. |
| `src/autotester/providers/config_migration.py` | E | `is_file`/`read_bytes` become `read_bytes_path` (`_stored` helper). |
| `src/autotester/stages/bench_inputs.py` | E | `load_pinned_list` reads through `read_bytes_path`; the `mkdir` is dropped (the write and `file_lock` create parents). |
| `src/autotester/stages/acceptance_baseline.py` | E | source config read through `read_bytes_path`; the `qa/evidence/t169-real/<mode>` skeleton uses `evidence_mkdir`. |
| `src/autotester/sources/drive_register.py`, `email_register.py` | E | redundant `target_dir.mkdir` dropped (`store_media` -> `FileBackend.put` creates parents). Their `read_bytes` rows are U5b's and are untouched. |
| `pyproject.toml` | E | **65 baseline rows deleted**: 32 tagged `U7` and 33 tagged `M53-gated`. No row added, none moved to `permanent`. |
| `docs/MAP.md` | regenerated by `autotester map` | one new module line. |
| `tests/test_filestore_paths_u7.py` | N | the verbs, per backend `[file, memory, mongo]`, 16-thread races. |
| `tests/test_coordination_u7.py` | N | the consumers on the memory and the (fake) Mongo backend with an EMPTY data root; every test ends on "no file on disk". |
| `tests/test_schedule_marker.py`, `test_schedule_purge_crash.py`, `test_zip_intake_atomic.py`, `test_sweep_u3a.py` | E (mechanical seam edits) | see judgement call 5. |
| `qa/evidence/mongo-store-u7/mutations.json`, `mutation-run.txt` | N | C7 mutation spec and its run. |

`auth/` was not touched (U6b). No other `src/` module was added.

## Criteria map

| Crit | Code | Test (falsifier it kills) |
|---|---|---|
| M19 one winner | `create_exclusive_path` (`filestore_paths.py:44`) -> `FileBackend.create_exclusive` (`filestore.py:71`, `file_lock.create_new :33`), `InMemoryBackend`, `MongoBackend.create_exclusive`. Consumers: delivery claim/record (`inbox.py:89,93`), slot claim (`schedule_store.py:55`), purge manifest, marker (`team_store.py:39`), intake lock (`intake_commit.py:70`) | `test_filestore_paths_u7.py::test_sixteen_racers_for_one_exclusive_create_yield_exactly_one_winner[file\|memory\|mongo]` (16 threads released together, 25 repetitions each = 400 contenders per leg, exactly one winner and the winner's text kept), `::test_an_exclusive_create_never_shows_a_reader_a_half_written_file`; `test_coordination_u7.py::test_a_slot_claim_has_one_winner_among_sixteen_and_lists_back`, `::test_delivery_claims_and_records_are_exclusive_in_the_store` (16 racers), `::test_a_team_marker_has_one_winner_in_the_store` (16 racers), `::test_the_intake_lock_is_a_store_key_with_one_holder_and_a_stale_takeover`. |
| M20 compare-and-set | `put_if_path :51`; checkpoint `flush :259`; `RevisionedFile.save :210` used by the run queue (`run_queue.py:261`) | `test_filestore_paths_u7.py::test_put_if_a_stale_digest_writes_nothing_and_the_current_one_lands`, `::test_sixteen_racers_with_the_same_digest_yield_exactly_one_compare_and_set` (x 25 repetitions, 3 legs); `test_coordination_u7.py::test_a_stale_checkpoint_instance_is_refused_on_a_document_backend`, `::test_the_checkpoint_write_is_a_compare_and_set_not_a_check_then_write` (the `_check_disk` pre-check is switched OFF so only the CAS can refuse, and the stored text is asserted unchanged), `::test_the_run_queue_file_carries_a_rev_that_grows_with_every_save`, `::test_a_run_queue_save_that_lost_the_race_writes_nothing_and_says_so` (stored rev/entries untouched, warning logged, next save lands rev+1). |
| M52 READ-SIDE | `trace.py:142,156`; `orchestrate_checkpoint.py:174,205`; `schedule_store.py:121,170,195`; `inbox.py:99`; `config_migration.py` (`_stored`, `plan_legacy_roles`); `bench_inputs.py load_pinned_list`; `acceptance_baseline.py`; heartbeat read was already `read_json` | every test in `test_coordination_u7.py` asserts the data root holds no file (sidecar `.lock` files excepted) after a write-then-read workload on the memory and Mongo backends; the trace, records, claims, checkpoint, delivery, pinned-list and migration-plan reads are all read back from the store, not the disk. |
| M53 rows removed, nothing invented | 65 rows deleted from `pyproject.toml`; the module is the D-126 module | `autotester doctor` (below): `check_state_bypass` reports no stale row and no new violation; `test_state_bypass_rule.py` passes. |

## Things the checker should look at (judgement calls)

1. **"Purge as `delete_many`" is realised as the existing staged purge on store verbs, ending in `delete_tree`**, not as a literal single `delete_many`. `MongoBackend.delete_prefix` deletes per victim (and refuses the insert-only families), which is what `delete_tree` calls on Mongo. I kept the two-phase stage because the existing `test_schedule_purge_crash.py` pins its crash semantics (all-or-none across a hard kill). If the contract meant a literal one-call `delete_many`, that is a Mongo-backend change in `mongo_backend.py` (at the 300-line cap) and is not done.
2. **The scratch verbs are local-only and are a design choice.** Staging and drive-fetch folders hold video bytes, which M25 says must not become state documents, so `scratch_*` act on the local disk, never on a backend, and refuse (`UnsafeName`) an in-root path outside `.work/`. They are the removal route for the 14 "scratch" rows. Falsify by pointing one at `projects/...` (the fence test does). `evidence_mkdir` is the same idea for checked-in evidence (M49) and refuses anything outside `qa/evidence/`.
3. **Heartbeat has no CAS.** `write_heartbeat` stays `write_text` (atomic whole-document write, one writer: the tick). M20's parenthetical lists the heartbeat among CAS users; I did not add one because no second writer exists. Say so in the verdict if you want one.
4. **The M25 CEO-bench list is still not file-only.** `bench_inputs` read and write now both go through the store, but `mongo_routes` sends `.work/ceo-bench` to server_state/settings, so M25's "file-only" is not implemented by anyone. Unowned; not closed here.
5. **Existing tests edited (assertions unchanged, mechanical).** `test_schedule_marker.py`, `test_schedule_purge_crash.py`: `schedule_store.os` / `schedule_store.shutil` -> `os` / `shutil` (the modules no longer import them; the patches hit the same global `os.replace`, which `rename_path` still uses, so call counts are identical; `import shutil` added to the purge-crash test). `test_zip_intake_atomic.py`: `intake_commit.os` -> `os`, unused import dropped. `test_sweep_u3a.py`: the three `LEFT` entries for `schedule_store`, `drive_intake`, `intake_commit` removed because their last raw calls are gone (the table is the pin that says what is left).
6. **Run queue behaviour change.** Before, a save always overwrote; now a save that loses the CAS is dropped (loudly) and the next one lands against what is stored. With no base yet (a queue built without `recover()`), the first save reads the current digest, so it still overwrites like before. `ui/run_queue.py` is 297 lines (cap 300); `RevisionedFile` lives in `filestore_paths.py` partly for that reason.
7. **Mongo legs run on the hand-written fake (`tests/fake_mongo.py`)**, as in U4; no real server was touched. The "200 repetitions" falsifier of M19 is not run in CI: 25 repetitions x 16 threads per leg. The checker may loop it.
8. **Not touched, said plainly.** `delivery/email.py:109` has a raw `os.link` (the file outbox transport, an `.eml` drop folder, outside the rule). `acceptance_baseline._input_bytes` (`read_bytes` of an owner-supplied input file) and `prepare_baselines`' `destination.mkdir` are not baseline rows and are unchanged. The `drive_register`/`email_register` `read_bytes` rows are U5b's. The first-admin claim and the M29 lease question are in `auth/`, U6b's.
9. **`_lock_is_stale` race is pre-existing** (two waiters can both judge a lock stale, the second delete can remove the first's fresh lock). Unchanged.
10. **Doctor.** `docs/MAP.md` is regenerated and committed here. `docs/SNAPSHOT.md` still reports stale (generated and committed); I did not regenerate it (its inputs, `.goal/` and the decisions list, move outside this unit; D-126 was appended after the last snapshot). This is not a design-rule or state-bypass violation. Not verified on a pristine master.
11. **Not run:** the full suite in one invocation (low-memory rule); no senior-software-engineer review agent was dispatched (the brief said no checkers); the wider suite beyond the pairs below.

## Verify (run in `D:/autoTesting/.claude/worktrees/mongo-u7`, `-o addopts=`, at most 2 files per call)

```
pytest tests/test_filestore_paths_u7.py          -> 51 passed
pytest tests/test_coordination_u7.py             -> 30 passed
pytest tests/test_inbox_delivery.py tests/test_delivery_failure.py          -> 24 passed
pytest tests/test_delivery_records_for_run.py tests/test_inbox_scope.py     -> 13 passed
pytest tests/test_state_sweep_u3b.py tests/test_state_sweep_u3c.py          -> 17 passed
pytest tests/test_state_sweep_u3d.py tests/test_sweep_u3a.py                -> 14 passed, 1 failed (the LEFT pin, before its three entries were removed)
pytest tests/test_sweep_u3a.py tests/test_coordination_u7.py               -> 39 passed (after the LEFT edit)
pytest tests/test_zip_intake_atomic.py tests/test_zip_intake_limits.py      -> 14 passed
pytest tests/test_zip_intake_names.py tests/test_zip_intake_register.py     -> 95 passed
pytest tests/test_drive_intake.py tests/test_drive_verify.py                -> 39 passed
pytest tests/test_media_sources_blobs.py tests/test_bench_inputs_stage.py   -> 12 passed
pytest tests/test_ui_bench_inputs.py tests/test_provider_migration.py       -> 31 passed
pytest tests/test_acceptance_baseline.py tests/test_team_store.py           -> 74 passed
pytest tests/test_run_queue.py tests/test_run_queue_resilience.py           -> 24 passed
pytest tests/test_team_run_queue_seam.py tests/test_run_trace.py            -> 13 passed
pytest tests/test_trace_numeric_secret.py tests/test_state_bypass_rule.py   -> 81 passed
pytest tests/test_schedule_tick.py tests/test_schedule_catchup.py           -> 43 passed
pytest tests/test_schedule_wiring.py tests/test_schedule_inbox.py           -> 19 passed
pytest tests/test_schedule_failures.py tests/test_schedule_overlap.py       -> 25 passed
pytest tests/test_schedule_marker.py tests/test_schedule_purge_crash.py     -> 18 passed
pytest tests/test_ui_intake.py tests/test_ui_intake_drive.py                -> 36 passed
pytest tests/test_ui_project_intake.py tests/test_cli_intake.py             -> 23 passed
pytest tests/test_state_backend_contract.py tests/test_filestore_paths_u7.py -> 383 passed, 1 skipped
ruff check src tests scripts                      -> All checks passed!
autotester doctor (redirected to .work/doctor-u7.txt) -> exit 1, 3 violations, all generated docs: stale-generated SNAPSHOT.md, stale-committed MAP.md (cleared by committing the regenerated file in this branch) and SNAPSHOT.md; no state-bypass, line-cap or design-rule finding; only the non-blocking D-087 advisories otherwise
python scripts/mutation_check.py qa/evidence/mongo-store-u7/mutations.json --repo .  -> 11/11 mutations killed
```

Mutants (all KILLED by the named tests; first run had m6 SURVIVE because rev still grew by an offset, retargeted at the "remember the rev I wrote" line): m1 `create_new` overwrites instead of linking; m2 `create_exclusive_path` always writes; m3 `put_if_path` ignores the digest; m4 checkpoint flush compares against a fresh read; m5 `RevisionedFile` compares against a fresh read; m6 it forgets the rev it wrote; m7 slot claim overwrites; m8 intake lock never waits; m9 an interrupted purge does not roll back; m10 scratch fence removed; m11 team marker not exclusive. Full output: `qa/evidence/mongo-store-u7/mutation-run.txt`.

Doctor output: `.work/doctor-u7.txt` (not committed).
