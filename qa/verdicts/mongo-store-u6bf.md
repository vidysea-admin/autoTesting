# Verdict - mongo-store-u6bf (U6b/U6bf, fix cycle 1) - checker A

**Cycle checked:** 1
**Verdict: PASS** (with 4 WARNINGs, none blocking). Dual-checked unit: this is checker A only; the unit closes on both checkers, and I read no other checker's verdict.
**Checked:** branch `feat/mongo-store-u6bf`, head `023d07e2` (code head `375b2774`, master `468b3832` merged as `6b1e20d0`), worktree `D:/autoTesting/.claude/worktrees/mongo-u6bf`.
**Criteria judged:** M29 (admin/last-admin invariants under no-transaction Mongo), M30 (hashes stay inside `auth_users`), and the five cycle-0 items plus A2/A3/B1/B2/B4 in the manifest. Every command ran in the worktree as `env -u ANTHROPIC_BASE_URL uv run ... -o addopts=`, at most 2 test files per call. No `.env` value was read or printed.

## Commands and outputs

| Command | Result |
|---|---|
| `pytest tests/test_auth_store_double_fault.py` | run 1: 1 failed, 6 passed (60.8 s, machine contended; failure text not captured, see W1). Then 9 consecutive full-file runs: 7 passed each (one run aborted at conftest import with `MemoryError`, environmental) |
| `pytest tests/test_auth_store_fencing.py tests/test_auth_store_recovery.py` | 33 passed |
| `pytest tests/test_auth_store_mongo.py tests/test_auth_store_contract.py` | 58 passed |
| `pytest tests/test_cli_store_auth_creds.py tests/test_cli_store_state.py` | 33 passed |
| `pytest tests/test_auth_store_double_fault.py tests/test_auth_store_fencing.py` x4 | 22 passed each time (7.8-10.6 s) |
| `pytest tests/test_auth_store_seam.py tests/test_ui_auth_accounts.py` / `test_ui_auth_survivors + escalation` / `test_ui_auth_groups + login` | 26 / 25 / 54 passed (the `accounts.py` reset/bootstrap reorder does not regress the SQLite path) |
| `ruff check --no-cache src tests scripts` | All checks passed |
| `autotester doctor > .work/chkA-doctor.txt` | `doctor: clean` (advisory D-087 findings only) |
| `pytest tests/test_cli_advice_resolves.py` on the branch | 1 failed (`test_the_collector_reports_what_it_could_not_resolve`), left-over item `store/mongo_backend.py:73`; 40 passed |
| same test on master `468b3832` (`git archive 468b3832 src tests scripts pyproject.toml` into scratch, `PYTHONPATH=<scratch>/src`) | 1 failed, 40 passed; the extra items there are `auth/store_mongo_tx.py:109` and the same site, so it is pre-existing and the branch removed one site. `git diff --stat 468b3832 HEAD -- src/autotester/store/mongo_backend.py` is empty. Not counted against this unit. |
| line caps | `store_mongo_tx.py` 300, `store_mongo.py` 299, test files 234-298; no new `src/` module (`git diff --stat 468b3832 HEAD` lists only `accounts.py`, `store_mongo.py`, `store_mongo_tx.py` under `src/`); D-126 is ACTIVE at `docs/DECISIONS.md:3040` |

## Mutants re-run by me (`scripts/mutation_check.py`, specs and outputs in `.work/chkA-mut*.txt`)

Specs taken from `qa/evidence/mongo-store-u6bf/mutations.json`, restricted to the test file(s) that carry the claimed killers. The harness refuses an uncollected kill name and a red baseline.

| Mutant | Result | Failed tests (exactly the claimed ones unless noted) |
|---|---|---|
| f10 replay oldest first | KILLED | `insert_then_a_patch...`, `recovery_killed_at_any_call...` |
| f11 dead holder's doc not fenced | KILLED | `...successor_ran[before-a-delete]`, `[before-a-patch]` (and no other case) |
| f12 undo ignores the `F:` stamp | KILLED | `...successor_ran[before-its-second-write]` |
| f23 rollback without owning the lease | KILLED | `a_rollback_that_lost_its_lease_writes_nothing` |
| f25 write not fenced by the lease | KILLED | `a_stalled_holder_writes_nothing_once_the_lease_is_gone` |
| b2c deleted doc stays readable | KILLED | `...kill_at_every_call_point[delete_user]` |
| b1 recoverer-specific undo stamp (cycle-0 B1 rule) | KILLED | `a_recovery_killed_at_any_call_is_finished_by_the_next_one` |
| b2a replay of a delete re-inserts | KILLED | both `...does_not_bring_back_an_account_deleted_since[...]` |
| **own2** `_resolve` deletes the journal entry BEFORE `_replay` (a crash then loses the undo) | KILLED | `recovery_killed_at_any_call`, both `deleted_since[...]`, more |
| **own1** committed sweep (`_resolve`, store_mongo_tx.py:100-102) deletes the `G:` doc without the `_e` stamp condition | KILLED, but only incidentally (see W2) | in `double_fault` + `recovery` it SURVIVED; in `fencing` it is killed by `a_committed_journal_whose_sweep_failed...[delete]`; in `contract`/`cli_store_auth_creds` it survives |

Additional probes I wrote (scratch, `<scratchpad>/probe/test_chkA_probe.py`, not committed; hook-fired assertion included so they are not vacuous):
- P1: a committed delete of a grant stalls before its physical delete; a successor sweeps it and re-creates the same grant id; the stalled sweep resumes. The recreated grant survives and no journal remains. PASS (the `_e: G:<me>` condition works).
- P2: `delete_user(c)` then `insert_user(same email)` in one transaction. Raises (`StoreDuplicateKey`/`AuthStoreBusy`), whole transaction rolled back, shape unchanged, no journal left, the next write works. PASS (loud, clean, as claimed).

## The three judgement calls

1. **U8 test excludes only the epoch counter** (`tests/test_cli_store_auth_creds.py:77-97`). Accepted. `_without_the_epoch` removes just `auth_meta/epoch` and the test still requires the epoch advanced, everything else (accounts, groups, grants, allocator, lease doc) byte-equal. `test_dry_run_with_auth_opens_no_connection` still passes, so only `--apply` takes the lease. The vacuous line-89 assertion is replaced by a spy on `MongoTxBase.commit` that requires an `open` marker at commit (`assert ["open"] in open_at_commit`) and no `kind == "tx"` left. Honest, not weakening. (W3: a no-op `--apply` now writes one counter and takes the lease; that is the price of fencing before reading under the lease.)
2. **Delete-then-reinsert of one id or unique key in a transaction is unsupported.** Audited every caller of `delete_*`, `insert_*`, `remove_project_relation`, `replace_project_owner` in `src/` (grep above): `access.py:70` `replace_project_owner` was the only one doing it and is rewritten at `store_mongo.py:223-225` (drop other owners with `user_id $ne`, then add if missing; same observable result as the SQLite delete-all-then-insert). `accounts.py:167,179,189,242,253-256` delete sessions but never re-insert the same digest (random tokens); `groups.py:63,105` create or delete, never both in one transaction; `migrate_auth.py` `_import_groups` drops seeded groups only after all inserts and patches; `_import_users` inserts only absent ids. No other caller has the pattern, and P2 shows the failure mode is loud and clean.
3. **f11 kill list narrowed to `[before-a-patch]`, `[before-a-delete]`.** Confirmed honest. Under f11 the harness reports exactly those two failing and `[before-its-second-write]` passing. Reason holds: for two writes to one document, newest-first replay undoes entry 1 (stamp `me1` -> `F:pre1`) and that already blocks the stalled second write, so entry 2's own fence is redundant there; the fence is observable only when the entry is the first write to its document, which the two retained cases cover. Nothing was weakened; f12 owns the second-write case.

## Findings (numbered)

No Block. Warnings:

- **W1 (flake, unresolved).** The first full run of `tests/test_auth_store_double_fault.py` failed one test (`test_an_insert_then_a_patch_of_one_document_is_recovered_whole_or_absent`, 60.8 s versus 8-30 s normally while other agents ran) and I did not save the failure text. It passed in isolation immediately after and in 13 later runs (single, whole-file x9, with fencing x4); one other run died at conftest import with `MemoryError` (`.work/chkA-df1.txt:43`). The scenario `_bootstrap_new` hashes with argon2, which the manifest says it saw fail with `Memory allocation error` on this machine, so a resource failure is the likely cause, but I did not prove it. The scenarios are single-threaded and use an explicit `_age_out_lease`, with no sleeps. Recommend the second checker keep the failure text if it sees it again.
- **W2 (incidental kill).** The semantic property "a stalled committer's late sweep must not delete a re-created document" (the `_e: G:<me>` condition at `store_mongo_tx.py:101-102`) has no test of its own. Mutant own1 is killed only because `test_a_committed_journal_whose_sweep_failed...[delete]` injects its fault by matching `"_e" in flt` (`tests/test_auth_store_fencing.py:221-222`), not by checking the property. My probe P1 (above) passes on the real code. Suggest adding P1-style case; not blocking because the code is correct and a mutant is killed.
- **W3 (U8).** A no-op `store migrate --apply` writes `auth_meta/epoch` and takes then releases the lease (see judgement call 1).
- **W4 (liveness only).** `recover()` resolves `seen - {epoch}` (`store_mongo_tx.py:112`), i.e. also HIGHER epochs. A recoverer that stalled between `_next_epoch` and `recover` for longer than the 30 s lease could abort a live successor's journal; the successor then gets `AuthStoreBusy` ("the change was undone") at commit. Fails closed, no data corruption (the aborted journal is replayed by stamp-conditional writes), so not a Block; `< epoch` would be tighter. Also unchanged from before and stated in the manifest: a crashed holder's refused change stays visible to readers until its 30 s lease expires.

## Cycle-0 findings, status

| Finding | Status |
|---|---|
| B1 double fault keeps a refused grant | closed: recoverer-independent `F:<pre>` chain (`store_mongo_tx.py:74,82`); nested kill sweep passes; b1 mutant killed |
| B2 late replay resurrects a deleted account | closed: delete is a `G:` update, every replay a CAS; b2a/b2c killed, P1/P2 pass |
| A2 f10, f12 survivors | closed: f10 and f12 KILLED by the tests the manifest names |
| A3/B4 tombstone unique-name null clash | closed: placeholders at `store_mongo_tx.py:78-79`; fake uses non-sparse null semantics (`tests/fake_mongo.py:69`); both stalled-creation tests pass |
| U8 integration break | closed (judgement call 1) |

Reader window, rehash parity, sweep leftovers and the stronger recovery assertion: covered by tests that pass (`test_auth_store_fencing.py`, `test_auth_store_recovery.py`) and by killed mutants f17/f18/f19-f22 recorded in the manifest evidence (not re-run by me beyond those listed above).
