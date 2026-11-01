# Verdict (checker-B) - e2e-fixes-e10, focus E10.3 and the fence (`auth/store_mongo_fence.py`), fix cycle 0

**Cycle checked:** 0
**Verdict:** PASS (with 1 Warning the maker must carry; no Block). Scope of this verdict: E10.3 and E10.2 as they live in `store_mongo_fence.py`, the fence tests, and all 16 fence mutants. E10.1 (`migrate_auth.py`, `cli_store.py`) is checker A's seat and is not judged here.
**Head checked:** 47e08fd9 on `feat/e2e-e10` (base 6eb21a54). Fresh and independent; no other checker's verdict on this unit was read.
**Criteria:** `qa/contracts/e2e-fixes.md` E10.2, E10.3 (outcome A), core-invariants C12, D-129.

## Summary
The outcome-A fix does what E10.3 (A) names: a refused transaction and a single holder that died before committing both leave the ORIGINAL share/grant present, on a
fake store killed at every call point. All 16 fence mutants die on re-run (the maker re-ran only OWN-B after its test edit; I re-ran the whole spec). One real
hole outside the two named end states: a recovery that is itself killed at one specific call leaves the original document lost (fail-closed, 14 of 911 nested
kill points, both share and grant). It is narrower than what the base code did (every rollback lost the document), it fails closed, and the contract's two
end states hold, so it is a Warning, not a Block.

## Re-run evidence (my commands, venv python, machine-low-memory rules: 2 files per call, TMP/basetemp under `.work`)
```
.venv/Scripts/python.exe -m pytest tests/test_auth_store_fence_slots.py tests/test_auth_store_fence_recreate.py -o addopts=   -> 18 passed
.venv/Scripts/python.exe -m pytest tests/test_auth_store_fencing.py tests/test_auth_store_recovery.py -o addopts=             -> 33 passed (unmodified files)
.venv/Scripts/python.exe -m ruff check src tests scripts                                                                      -> All checks passed!
.venv/Scripts/autotester.exe doctor > .work/doctor-b.txt                                                                      -> 2 violations, both docs/SNAPSHOT.md stale-generated / stale-committed (pre-existing drift; nothing on line caps or duplicates)
.venv/Scripts/python.exe scripts/mutation_check.py qa/evidence/mongo-store-u6c/mutations-fence.json                           -> 16/16 mutations killed
```
Mutation run, per mutant (all `KILLED`, each by at least one of its claimed tests, full text in `.work/mut-b.txt`): s1-s11, O1, OWN-B, H1, A1, A2.
The previously surviving claim is fixed: OWN-B is now killed by BOTH claimed tests (`test_a_slot_hidden_at_epoch_e_...` and `test_a_refused_transaction_restores_the_original_share`).
A1 (revert `_took`) is killed by the two rollback tests; A2 (drop the `hide_stamp(by)` line in `replay`) by the two recovery tests AND the two every-call-point sweeps, so the new `replay` line is load-bearing and tested. The diff of `tests/test_auth_store_fence_slots.py` is additions only (E10.2 adds 4 tests, nothing existing edited), and the existing fencing/recovery/double-fault files are unmodified.

## Review of the E10.3 code (`store_mongo_fence.py:90-136`)
- `_took` (`:114-121`) reads same-epoch, same `coll`/`doc_id` journal entries with a smaller `_id` (zero-padded, so string order is write order) and returns `G:<me>` of the newest one only if it is a `set` with `gone`. Traced by hand and by the sweep: delete->recreate, delete->recreate->delete->recreate (each ins goes back to the previous delete's stamp, each delete's restore then matches), insert->delete->recreate (the first ins has no `gone` predecessor so it hides at the epoch stamp as before). No hole found in the rollback path.
- Rollback (`by is None`) puts the slot back at `G:<delete's me>`, same epoch as the live holder, so a zombie of a lower epoch is still refused by `insert_fenced` (`stamp_epoch(cur["_e"]) <= epoch`). Fence property unchanged; `back` is applied only when the landed document is "mine" (`stamp in mine["$in"]`, `:108`), so a later holder's live document is still left alone (H1 killed).
- Recovery (`by` set): hide stays at `G:<by>.000000` (the dead epoch's zombie cannot retake it), and the new line `:131-132` lets the delete's restore also match `G:<by>.000000`. Because replay is newest-first, every later entry on that id is already undone when a `set` entry is replayed, so matching the recoverer's own hide stamp restores the right pre-state. No fail-open path: the restored document carries `F:<pre>`, so a stalled writer of the dead epoch still fails its stamp condition.
- Module docstring and `_hide_slot` docstring describe the new behaviour; the file is 198 lines and doctor raises nothing on it.

## Findings (numbered)

1. **Warning - a recoverer that is itself killed between hiding the re-inserted slot and replaying the earlier delete loses the original document (nested crash, fail-closed).**
   `replay` accepts only `hide_stamp(by)` for the CURRENT recoverer (`:131-132`). If recoverer R1 (epoch 5) replays the ins entry (slot -> `G:00000005.000000`, entry deleted, `close_epoch` `:150`) and dies before the delete entry's restore, the next recoverer R2 (epoch 6) matches `{me, G:me, F:me, G:00000006.000000}`, not `G:00000005.000000`; the delete entry's restore finds nothing, is then dropped, and the document is gone for good. Reproduced with a probe (kept out of the repo, `.work/probe/test_probe_double.py`): the E10.3 transaction killed at call k, its lease aged out, the recovery killed at call j, a last holder runs, using the repo's own `_kill_at` and `_age_out_lease` helpers. Result: 911 nested points, 14 lose the original, identical for share and grant (first kill 17..23, second kill 15 or 16). Single-point probe (kill 17 then 15): after both deaths the slot is `('G:00000005.000000', None)` with one `set gone` entry left; after the last holder the share set is empty and the slot is unchanged.
   Direction is fail-closed (access denied, never granted), no data leaks, the base code lost the document on EVERY rollback and recovery so this is not a regression, and E10.3 (A) names only the rollback and the single-holder recovery, both of which pass. It is still the project's own bar to pin a recovery that is killed again (`tests/test_auth_store_double_fault.py` B1 does it for every other collection), and the new `test_a_kill_at_every_call_point_never_loses_the_document` kills only once. Carry as a follow-up issue: add the nested-kill sweep for the recreate scenario and widen the restore to any hide stamp `G:<n>.000000` with `n` at least the entry's epoch (read the slot, then compare-and-set on the stamp read), or have the recoverer record the stamp it hid at. Not a G1 or HUMAN_GATE item.
2. **Note - the E10.3 tests exercise the in-memory fake only.** The `_hide_slot` retry loop (4 attempts, silent fall-through, pre-existing) is not covered for real Mongo timing by this unit; a silent fall-through would also leave a re-inserted document unhidden. Unchanged from before E10, mentioned so it is not read as newly proven.
3. **Note - manifest evidence is accurate on the points I could check.** Counts (18 and 33 passed), the 15/16-then-OWN-B-fixed story and the doctor result match my runs. I did not run the full `uv run pytest` (machine rule); the fence suites above are the relevant ones.

## What I could not falsify
Stalled-writer safety under rollback and recovery (a lower-epoch writer retaking a slot hidden at the same or later epoch), E10.2's CAS between read and write (O1) and the `_hide_slot` CAS (H1) were attacked through the existing sweeps and mutants; no fail-open interleaving found.

## Disposition
PASS cycle 0 for E10.3 and E10.2 on the fence. The maker carries finding 1 (follow-up issue and test); no re-check needed for this verdict. No code, test or contract edited by this checker.
