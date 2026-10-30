# Verdict - mongo-store-u7 (checker A)

**Verdict: FAIL** (one blocking finding, F1; every other claim verified)
**Cycle checked: 0**
**Checked head:** `876e553e` on `feat/mongo-store-u7` (code commit `13b79315`, base `fe1ac6c8`). Worktree `D:/autoTesting/.claude/worktrees/mongo-u7`.
**Contract:** `qa/contracts/mongo-store.md` U7 row (dual): M19, M20, M52, M53. D-126 authorizes `store/filestore_paths.py`.
**Method:** fresh checker, own probes and mutants, nothing from another checker read. No `.env` value read or printed. Probes live in `.work/` (gitignored).

## Summary

M19, M20, M52 and M53 hold on file, memory and fake-Mongo. The one thing that does not hold is the maker's own stated fence on the new `scratch_*` / `evidence_mkdir` verbs (judgement call 2): `..` traversal, a symlink and a substring match all escape it, and `scratch_rmtree` / `scratch_unlink` then delete state. The 14 `M53-gated` scratch rows were removed on the strength of that fence, so the removal route is not yet honest. The fix is about five lines plus tests; a cycle-1 re-check is narrow.

## Findings

**F1 (BLOCK) - the scratch and evidence fences are escapable.** `store/filestore_paths.py:145-150` (`_scratch`) tests `_rel(path).startswith(".work/")` on the un-normalised path; `:181` (`evidence_mkdir`) tests the substring `"qa/evidence/" in path`. Probe `.work/probe_fence.py`, data root = a temp dir, `AUTOTESTER_ROOT` set:
- `scratch_rmtree(root/".work"/".."/"projects"/"p")` ALLOWED, `projects/p/state.json` gone.
- `scratch_unlink(root/".work"/".."/"projects"/"p"/"state.json")` ALLOWED, file gone.
- `scratch_mkdir(root/".work"/".."/"projects"/"q")` ALLOWED, `projects/q` created. `scratch_children(root/".work/../projects")` ALLOWED and lists state.
- A symlink `root/.work/lnk -> root/projects`: `scratch_rmtree(lnk/"p")` ALLOWED, state gone.
- `scratch_rmtree(root/".work"/"team"/"schedule"/"claims")` ALLOWED. `.work/team/**`, `.work/run_queue.json`, `.work/audit.jsonl`, `.work/drive-jobs/**`, `.work/notification_prefs/**` are Mongo-routed STATE in `mongo_routes.py:81-88`, so "under `.work/`" is not "scratch".
- `evidence_mkdir(root/"qa/evidence/../../projects/e")` ALLOWED (created `projects/e`); `root/projects/p/qa/evidence/z` ALLOWED; `root/xqa/evidence/y` ALLOWED; `<outside root>/qa/evidence/o` ALLOWED.
- Refused as intended: direct `projects/p`, `.WORK/x`, `.work` itself, `QA/EVIDENCE/x` (these refusals are by string compare only).
Why it blocks: these verbs live in `store/`, which the state-bypass rule exempts, and 14 baseline rows (drive_intake x4, intake_commit x9 including `commit_video:rmdir`, zip_intake x1) were removed by pointing the calls at them. The module docstring (`:14-16`) and the manifest promise that any in-root path outside `.work/` is refused; a `..` defeats it. The current callers (`intake_commit.py:94-119`, `drive_intake.py:85-146`, `zip_intake.py:218`) build paths from `ulid()` and vetted member names, so it is latent, not exploitable today; but a delete-capable verb whose only guard is a prefix string is the shape the contract's M53 "nothing invented" and the whole M16 rule exist to prevent.
Required fix (cycle 1): normalise before comparing (`os.path.normpath` or `Path.resolve()` of both the path and `repo_root()`; reject if the resolved path leaves `root/.work/<allowed subtree>`), narrow the allow-list to the real scratch subtrees (`.work/intake`, `.work/drive-fetch`, `.work/gws`) instead of all of `.work/`, anchor `evidence_mkdir` on `repo_root()/"qa"/"evidence"` after resolving, and add tests for `..`, symlink and the `xqa/evidence` form. The existing fence test (`tests/test_filestore_paths_u7.py:218`) only uses three plain state paths; the mutation m10 only removes the fence entirely, so a normalisation mutant would survive.

**W1 (WARN) - the half-written-claim property is not pinned by a test that bites.** `FileBackend.create_exclusive` -> `core/file_lock.py:33 create_new` (temp file + `os.link`) is correct: I read a 500 KB body with 3 concurrent readers over 40 files, zero partial reads, zero `.tmp-*` leftovers, on all three backends. But `tests/test_filestore_paths_u7.py::test_an_exclusive_create_never_shows_a_reader_a_half_written_file` (one reader, 200 KB) does not kill the mutant "write in place under `O_EXCL`" (`_create_excl` called directly): 0 partial reads in 5 of 5 runs of that shape (`.work/probe_mut.py`), while 5 MB with 3 readers sees partial reads 4 times. The 11 mutants in `qa/evidence/mongo-store-u7/mutations.json` have no such mutant (m1 is "overwrites instead of linking"). The property is real in the code but only weakly guarded.

**W2 (WARN) - the M25 gap lost its only marker.** The three `bench_inputs` baseline rows (`load_pinned_list:exists`, `:read_bytes`, `save_atomic_list:mkdir`) were not M53 primitive gaps; their text said "M25 wants this list file-only but no route implements that ... no unit owns the M25 file-only routing yet". U7 routed read, write and mkdir through the store (`stages/bench_inputs.py:62,79`), which makes the CEO-bench private answer list consistently stored in Mongo (`server_state`/`settings`), the opposite of M25 ("`.work/ceo-bench/` file-only, private by design"). The write side already went to Mongo on `fe1ac6c8`, so U7 did not worsen the stored data, and it fixed a real read/write split in Mongo mode; but deleting the rows removes the only baseline reminder. The maker says so (manifest note 4). It needs an owner and an `qa/issues.jsonl` row before this unit closes, or a D-entry amending M25. Not a U7 criterion; not blocking.

**W3 (WARN) - local lock sidecars stay under the data root in Mongo mode.** `.work/probe_m52.py`: with the fake Mongo backend on every area, one claim plus `purge_project` leaves `.work/team/schedule/.p.jsonl.lock` on disk (`stages/schedule_store.py` `file_lock(_lock_path(records_path))`, `_APPEND_LOCK`); `bench_inputs.save_atomic_list` and `FileBackend.put_if` likewise create `.lock` files. `tests/test_coordination_u7.py:63-66` (`_files`) exempts every `*.lock`. M52 falsifier (a) says "creates ... a file under the data root state paths". These are advisory empty files, not state, and the purge lock is a process-local mutex, so cross-instance purge exclusion is not provided (consistent with M28 `--max-instances 1`). The contract needs one sentence ruling that sidecar locks are exempt, otherwise M52(a) is literally unmet.

**I1 (INFO) - purge is a staged move on store verbs, not a literal `delete_many`.** Ruling: acceptable. The U7 row text ("purge as `delete_many`") cannot give the property `test_schedule_purge_crash.py` pins (claims and records go together or not at all across two collections) because there are no multi-document transactions (contract, "Amendments applied"). `purge_project` (`schedule_store.py:228-244`) creates a manifest (`create_exclusive_path`), moves each file (`rename_path`), commits by `delete_path(manifest)`, then `delete_tree(stage)` -> per-key `delete_prefix`. Tests cover interrupt and hard-kill recovery on memory and Mongo (`test_an_interrupted_purge_puts_every_file_back`, `test_a_purge_killed_mid_way_is_put_back_by_the_next_recovery`; mutant m9 killed). The contract row should be amended to "purge on store verbs".

**I2 (INFO) - heartbeat without CAS.** Ruling: acceptable. `write_heartbeat` (`schedule_store.py:249`) stays one atomic `write_text`; the tick is the single writer and nothing in M20's falsifier names the heartbeat (the falsifier is a stale write landing, or the checkpoint identity check skipped; both verified below). M20's parenthetical "(... heartbeat)" should be reworded, or a CAS added when a second writer exists.

**I3 (INFO) - `put_if` cannot match text containing a raw `\r`.** `FileBackend.get` reads text mode (universal newlines), so `put_if_path(p, "a\r\nb", None)` followed by `put_if_path(p, ..., text_sha("a\r\nb"))` loses on the file backend, and `create_exclusive` round-trip is unequal (`.work/probe_nl.py`). Pre-existing property of `get`; every U7 caller writes JSON (no raw CR), an empty lock body or a manifest, so none is affected.

**I4 (INFO) - not touched.** `delivery/email.py:104-110` raw `os.link` into an outbox directory (not a baseline row; the directory is injected) and `_lock_is_stale` double-takeover race (pre-existing, manifest note 9) are unchanged. `docs/SNAPSHOT.md` is stale (see doctor below).

## Criteria

- **M19 (one winner), PASS.** My own race `.work/probe_race.py`, 16 threads released at one barrier, 200 repetitions each, on file, memory and fake-Mongo: `create_exclusive_path` bad rounds 0/0/0; `put_if_path` (16 racers, same digest) bad rounds 0/0/0, and a CAS loser never left the old value; `RevisionedFile` with 8 loaded copies, 50 rounds: exactly one save lands per round, final `rev == 2`, 0/0/0 bad. The maker's 25x16 is therefore supplemented to the contract's 200 reps; real-server behaviour (unique `_id` -> `StoreDuplicateKey`) stays SERVER-GATED and was not claimed. Consumers confirmed routed through `create_exclusive_path`: `delivery/inbox.py:89,93`, `schedule_store.py:55,236`, `team_store.py:39`, `intake_commit.py:70`.
- **M20 (compare-and-set), PASS.** `put_if_path` with a stale digest writes nothing (probe above; `test_put_if_a_stale_digest_writes_nothing...`). `orchestrate_checkpoint.py:259` flush is now `put_if_path(path, text, self._disk_hash)` and raises the same "Checkpoint changed outside this instance" error; `test_the_checkpoint_write_is_a_compare_and_set_not_a_check_then_write` switches the pre-check off so only the CAS can refuse. `RunQueue` saves via `RevisionedFile` (`ui/run_queue.py:84,261`); a lost save writes nothing, warns, and the next lands (`test_a_run_queue_save_that_lost_the_race_writes_nothing_and_says_so`). Legacy queue files without `rev` load (default 0).
- **M52 (READ-SIDE), PASS with W3.** Every listed site is routed: `core/trace.py:142,156`, `orchestrate_checkpoint.py:174,205`, `schedule_store.py:121,170-199`, `delivery/inbox.py:99`, plus `config_migration.py`, `bench_inputs.py`, `acceptance_baseline.py`. The heartbeat read was already `read_json`. `tests/test_coordination_u7.py` write-then-read workloads on the memory and fake-Mongo backends find no state file on disk (lock sidecars excepted, W3).
- **M53 (rows removed, nothing invented), PASS with F1.** `git diff fe1ac6c8..HEAD -- pyproject.toml`: 65 `-` lines, 0 `+` lines; grepping the file at HEAD: 0 rows tagged `| U7`, 0 `M53-gated`; the `permanent` list is unchanged (no `permanent` line in the diff). Only `store/filestore_paths.py` was added under `src/` (D-126; `git diff --stat` lists no other new module; `mongo_bucket.py` and `state_bypass.py` are absent). I re-derived the removals row by row (grouped by file:kind) against the HEAD sources and `autotester doctor`: no stale row, no un-baselined violation, so no raw call survives and none was hidden in a rule-exempt place other than the `store/` verbs judged in F1. Line caps: `filestore_paths.py` 218, `filestore.py` 291, `ui/run_queue.py` 297, all <=300; doctor reports no function-length finding.

## Existing-test edits (item 5): no weakening

`tests/test_schedule_marker.py`, `test_schedule_purge_crash.py` change `monkeypatch.setattr(schedule_store.os, "replace", ...)` to `os, "replace"` (and `schedule_store.shutil.rmtree` to `shutil.rmtree`): `schedule_store.os` was the global `os` module object, so the patched attribute is identical; assertions and call counts unchanged (18 passed). `test_zip_intake_atomic.py` likewise (`intake_commit.os` -> `os`, unused import dropped). `test_sweep_u3a.py` removes three `LEFT` entries (`schedule_store`, `drive_intake`, `intake_commit`); the test is a pin that must equal the raw calls left, so removing entries whose last raw call is gone is required, not a loosening (14 passed with the pin active).

## Commands run (worktree, `env -u ANTHROPIC_BASE_URL uv run pytest <2 files> -o addopts= -q`)

```
tests/test_filestore_paths_u7.py tests/test_coordination_u7.py          -> 81 passed
tests/test_schedule_marker.py tests/test_schedule_purge_crash.py        -> 18 passed
tests/test_sweep_u3a.py tests/test_zip_intake_atomic.py                 -> 14 passed
tests/test_state_bypass_rule.py tests/test_state_sweep_u3d.py           -> 81 passed
tests/test_run_queue.py tests/test_run_queue_resilience.py              -> 24 passed
tests/test_inbox_delivery.py tests/test_delivery_failure.py             -> 24 passed
tests/test_schedule_tick.py tests/test_schedule_catchup.py              -> 43 passed
tests/test_team_store.py tests/test_acceptance_baseline.py              -> 74 passed
tests/test_drive_intake.py tests/test_ui_intake.py                       -> 45 passed
tests/test_provider_migration.py tests/test_bench_inputs_stage.py       -> 8 passed
tests/test_state_backend_contract.py tests/test_run_trace.py            -> 342 passed, 1 skipped
uv run ruff check src tests scripts                                     -> All checks passed!
uv run autotester doctor > .work/doctor-checkerA.txt                    -> exit 1, 2 violations: stale-generated and stale-committed docs/SNAPSHOT.md only; MAP.md clean; no state-bypass, line-cap, function-length or design-rule finding; only the D-087 advisories
python scripts/mutation_check.py qa/evidence/mongo-store-u7/mutations.json --repo .  -> 11/11 mutations killed (m1..m11, claimed and actual failing tests identical)
.work/probe_race.py  (200 reps x 16 threads x file|memory|mongo)        -> create bad 0, cas bad 0, half-written 0, RevisionedFile bad 0, tmp leftovers 0 on all three
.work/probe_fence.py                                                    -> F1 (see above)
.work/probe_mut.py   (in-place O_EXCL mutant, 200 KB, 1 reader)         -> 0 partial reads x5 (W1); 5 MB, 3 readers -> 4
.work/probe_m52.py                                                      -> files: ['.work/team/schedule/.p.jsonl.lock'] (W3)
```

The SNAPSHOT staleness is the generated-doc drift the maker reported (D-126 was appended after the last snapshot; master's later commit `54db88c6` regenerates it); it is not a code finding. `tests/test_role_port_authz.py` was not run (not touched by this unit).

## Not verified

The full suite in one invocation (memory rule); real-server Mongo behaviour (SERVER-GATED); the second dual checker's view.

## What cycle 1 needs

Fix F1 with tests (`..`, symlink, `xqa/evidence`, state-routed `.work/team`, plus a normalisation mutant in the spec). Ideally add the W1 mutant, and give W2 and W3 an owner or a one-line contract ruling. Nothing else needs to change; M19, M20, M52, M53 evidence above stands for the unchanged code.
