# Verdict (checker B) - mongo-store-u7

**Verdict: PASS with warnings**
**Cycle checked:** 0
**Head checked:** 876e553e on feat/mongo-store-u7 (code 13b79315, base fe1ac6c8). Checker B, independent; no other checker's verdict was read.
**Criteria judged:** M19, M20, M52, M53 (CRITICAL, dual) and the U7 unit row. Nothing connected to Mongo; the hand-written fake stood in.

## Result per criterion

| Crit | Result | Evidence |
|---|---|---|
| M19 one winner, all 3 backends | PASS | Own race `.work/chkb_race.py`: 200 reps x 16 threads released on a barrier, per leg (file, memory, fake-Mongo): 0 reps with other than one winner, winner's text kept, 0 exceptions. FileBackend path is `core/file_lock.py:33 create_new` (temp file + `os.link`). Probe `.work/chkb_half.py` (20 MB body, concurrent reader, 15 reps): real code 0/15 partial reads. |
| M20 CAS, lost write lands nothing | PASS | Own race: 200 reps x 16 threads on the same digest, per leg: exactly one winner, stored text equals the winner's. `RevisionedFile` (`filestore_paths.py:189`): 100 reps x 12 instances loaded on the same base, per leg: one winner, `rev == 1`, doc equals the winner's, loser adopts and its next save lands `rev == 2`. Checkpoint `flush` (`orchestrate_checkpoint.py:259`) is a CAS; the stale-instance refusal still fires on memory/Mongo (test_coordination_u7). |
| M52 READ-SIDE | PASS | `core/trace.py:142,156`, `orchestrate_checkpoint.py:174,205`, `schedule_store.py:121,170,195`, `inbox.py:99` all read through `read_text_path`/`digest_path`; grep of those four files finds no raw read verb. Heartbeat read was already `read_json`. |
| M53 rows removed, none hidden | PASS | `git diff fe1ac6c8..HEAD -- pyproject.toml`: 65 rows deleted (re-counted by tag: 32 `U7`, 33 `M53-gated`), 0 added. Baseline 98 -> 33 (U5b 14, U9 2, U11 17); `permanent` 27 -> 27 (the diff touches no `permanent` line). No U7 or M53-gated tag is left. Doctor reports no stale row and no new bypass. The new module is the D-126 module; no other module was added. |

## Commands run (worktree D:/autoTesting/.claude/worktrees/mongo-u7, env -u ANTHROPIC_BASE_URL, -o addopts=)

```
pytest tests/test_filestore_paths_u7.py tests/test_coordination_u7.py        -> 81 passed
pytest tests/test_state_bypass_rule.py tests/test_sweep_u3a.py               -> 84 passed
pytest tests/test_schedule_purge_crash.py tests/test_schedule_marker.py      -> 18 passed
pytest tests/test_run_queue.py tests/test_run_queue_resilience.py            -> 24 passed
pytest tests/test_inbox_delivery.py tests/test_zip_intake_atomic.py          -> 12 passed
pytest tests/test_run_trace.py tests/test_team_store.py                      -> 60 passed
pytest tests/test_state_sweep_u3c.py tests/test_state_sweep_u3b.py           -> 17 passed
pytest tests/test_cli_orchestrate_resume.py tests/test_orchestrate.py        -> 11 passed
ruff check src tests scripts                                                 -> All checks passed!
autotester doctor > .work/chkb-doctor.txt                                    -> exit 1, "2 violation(s)": stale-generated and stale-committed docs/SNAPSHOT.md only
python scripts/mutation_check.py qa/evidence/mongo-store-u7/mutations.json --repo .  -> 11/11 mutations killed
wc -l: filestore_paths.py 218, filestore.py 291, ui/run_queue.py 297 (all <= 300); doctor lists no function-length or line-cap finding.
```
Not run: the full suite and `test_role_port_authz.py` (outside the unit). My probes (all in `.work/`, untracked): chkb_race.py, chkb_fence.py, chkb_half.py, chkb_junc.py.

## Findings

1. **WARNING (close before U9 flips an area): the scratch and evidence fences are defeated by `..`.** `store/filestore_paths.py:145-150 _scratch` tests `_rel(path)` (a lexical `relative_to`, `filestore.py:161`) against the prefix `.work/`, so `root/.work/../projects/p` has key `.work/../projects/p` and passes. Measured on a temp root: `scratch_rmtree`, `scratch_unlink`, `scratch_mkdir`, `scratch_children` and `scratch_mtime` are all ALLOWED on `.work/../projects/...` (the state dir and file were deleted). `filestore_paths.py:181 evidence_mkdir` checks `"qa/evidence/" in posix` as a substring anywhere, so `root/qa/evidence/../../projects/evmk`, `root/projects/p/qa/evidence/x` and `C:/Temp/anything/qa/evidence/x` are ALLOWED. A Windows junction `.work/lnk -> projects` also lets `scratch_unlink` and `scratch_rmtree` delete state. Direct state paths, the root, `.work` itself and `.WORK/x` are refused. No live caller can reach this today (callers pass ulid/uuid names, or zip names vetted by `zip_names`), so it is latent. But the manifest presents these verbs as a fence ("the fence test does"), and the fence test never tries `..`. Fix: reject any `..` segment and compare `os.path.normpath`/`resolve()` before the prefix test, anchor the evidence check at the data root, and add the `..` and junction cases to the fence test. Mutant m10 only removes the whole fence, so it does not cover this.

2. **WARNING: the "no half-written claim" test is vacuous; a mutant survives.** `tests/test_filestore_paths_u7.py::test_an_exclusive_create_never_shows_a_reader_a_half_written_file` (200 KB body, one create) still passes when `core/file_lock.py:33 create_new` is replaced by the old open(`O_EXCL`)-then-write path (mutant: `return _create_excl(path, text)` at the top of `create_new`; 3 of 3 runs green). My probe (20 MB body, reader thread, 15 reps) sees a partial or empty read in 10/15 reps on that mutant and 0/15 on the real code. The implementation is right; the shipped test does not guard it. Enlarge the body (or hold the writer mid-write) so the old behaviour fails the test, and add the mutant to `mutations.json`. (The source tree was restored after the mutant; `git status` clean.)

3. **WARNING: purge is not crash-atomic on a document backend, and a half-finished move can resurrect purged claims.** `filestore_paths.py:85-97 rename_path` on Mongo/memory is `put(dst)` then `delete(src)`, two calls. A hard kill between them leaves the claim in both places with the manifest present. I injected that state (manifest + stage copy + the original claim): `_recover_stages` returns 0 and the stage stays (`schedule_store.py:_restore_stage` sees `exists_path(dest)` and keeps `clean=False`). A later `purge_project` then removes the claim, and the next `_recover_stages` returns 1 and RE-CREATES the purged claim `p:fixed:s1`. Verified on the fake-Mongo leg (the memory leg behaves the same). The file backend is unaffected (`os.replace` is atomic). Mitigation: in `_restore_stage` treat "dest exists with the same text as the held copy" as already moved and drop the held copy, or have recovery re-verify before restoring. The existing crash tests simulate the kill only by in-process exceptions or on files, so this window is untested.

4. **Rulings on the maker's flags.**
   - Purge as staged `delete_tree` instead of a literal single `delete_many` (judgement 1): ACCEPTED as realising the unit row, with finding 3 as the cost. The unit row text is descriptive, not a numbered criterion; M19/M20/M52/M53 do not require a one-call delete, and the crash semantics pinned by `test_schedule_purge_crash.py` hold on files. A literal `delete_many` needs a `mongo_backend.py` change (at its cap) and would drop the staged rollback.
   - Heartbeat without CAS (judgement 3): ACCEPTED. `write_heartbeat` is a single-writer atomic whole-document write; M20's falsifier names a stale write landing and the checkpoint identity check, both covered. If a second writer is ever added it needs `put_if_path`.
   - M25 CEO-bench list file-only (judgement 4): not a U7 criterion; confirmed unowned (`mongo_routes` sends `.work/ceo-bench` to the store). Needs an owner (U9 or U5b) from Umesh or the plan; not closed here.
   - M19 "200 repetitions": I ran 200 x 16 per leg myself (table above), with the Mongo leg on the fake. The maker's 25 x 16 in CI is thinner but the property holds. Real-server behaviour (unique `_id` insert, `replace_one({_id,h})`) is SERVER-GATED and was not exercised.
   - Scope: D-126 names "create_exclusive, put_if, read, rename, delete-tree". The module also holds `scratch_*`, `evidence_mkdir`, `touch_path`, `remove_stray_temps`, `remove_empty_dir`, `RevisionedFile`. They sit in the authorised module, so M53's "new module" falsifier is not triggered. But the `scratch_*`/`evidence_mkdir` verbs are local-disk fs calls moved into the rule-exempt `store/` directory (about 14 of the 65 rows), and their safety rests on finding 1. Umesh should know this when reading the row count.

5. **Existing-test edits do not weaken anything.** `test_schedule_marker.py`, `test_schedule_purge_crash.py`, `test_zip_intake_atomic.py`: the patch target moved from `schedule_store.os`/`.shutil`/`intake_commit.os` to the global `os`/`shutil`, the same objects (those modules no longer import them); assertions unchanged, and `rename_path` still calls global `os.replace`, so call counts match (18 + 12 passed). `test_sweep_u3a.py` LEFT: only the entries for `schedule_store`, `drive_intake`, `intake_commit` were removed, and the pin test passes, so those files hold no raw call. The `config_migration`, `bench_inputs` and `acceptance_baseline` diffs are behaviour-neutral (the dropped `mkdir` sits under a path the write creates; `evidence_mkdir` runs under a fresh `destination.mkdir(exist_ok=False)`).

6. **Doctor.** Only the two `docs/SNAPSHOT.md` freshness violations remain; `docs/MAP.md` is clean in HEAD. SNAPSHOT was regenerated on master (`54db88c6`) after this branch was cut. No design-rule, line-cap, function-length or state-bypass finding. I did not run doctor on a pristine fe1ac6c8.

7. **Minor, no action needed for PASS.** `stages/schedule_store.py:3-7` module docstring still describes the old `os.open`/`os.replace` design. `remove_stray_temps` (`filestore_paths.py:125`) deletes every `.tmp-*` in a folder, which would also remove an in-flight `create_new` temp of another process in that folder (it is only called on source folders). The `_lock_is_stale` double-takeover race is pre-existing (judgement 9).

## Summary
M19, M20, M52 and M53 hold on all three backends under my own adversarial races (200 x 16 per leg). The 65 rows are really gone, none added or moved to `permanent`, the maker's 11 mutants are killed, and every re-run passes. Three warnings stand and belong on the fix list: the `..`/junction hole in the scratch and evidence fences (1), the vacuous half-written test (2), and the non-atomic rename that can resurrect a purged claim on a document backend after a hard kill (3). None breaks a numbered criterion, so PASS; findings 1 and 3 should be closed before any area flips to Mongo at G1. If checker A Blocks on any of these, I would not object.
