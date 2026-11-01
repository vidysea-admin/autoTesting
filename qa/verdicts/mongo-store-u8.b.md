# Verdict - mongo-store-u8 (checker B)

**Verdict: PASS** (cycle 0; no Block; four non-blocking warnings, three info items)
**Cycle checked: 0**
**Checked head:** `cb080764` on `feat/mongo-store-u8` (code commit `dd066e26`), worktree `D:/autoTesting/.claude/worktrees/mongo-u8`.
**Contract:** `qa/contracts/mongo-store.md` U8 row (dual): M9, M25, M36, M41-M46. D-127 (three modules + `cli_subapps` line), D-128 (CEO-benchmark list moves; only count and hash leave the store).
**Independence:** fresh checker; no other checker's verdict was read. Nothing connected to a real Mongo; no `.env` value was read or printed (the rig and my probe use tmp roots, the fake server and synthetic values; `.env` of the repo was never opened).

## Findings (numbered)

**F1 (Info, contract action) - M25 text still says "file-only"; code follows D-128.** `qa/contracts/mongo-store.md` M25 lists `.work/ceo-bench/` as not stored. D-128 (`docs/DECISIONS.md:3066`, Approved-by Umesh) reverses that for this list only and says the checker amends M25. The code is correct against D-128 (`store/migrate_state.py:27` `PRIVATE`, `:55-58`, `:204-205`; `cli_store.py:83`). The maker did not edit the contract (right). **The checker seat must amend M25 (CEO-bench clause only) to cite D-128 before U8 is closed out**; I did not edit it (this commit is the verdict file only). The M25 falsifier "the migrate dry-run lists any of these as a to-insert item" must be read as excluding `.work/ceo-bench/` after the amendment.

**F2 (Warning, non-blocking) - `auth/migrate_auth.py` depends on private helpers of the auth transaction.** It calls `MongoAuthTx._docs/_get/_one/_insert/_patch/_drop/_allocate/_writer` and the static `_grant` (`migrate_auth.py:44-50, 59-78, 88-96, 111`), and imports `store_mongo_tx.META` (`:42`). Judgement: acceptable for this cycle, because (a) the underscore helpers are the journalled write API of `MongoTxBase` (`auth/store_mongo_tx.py:86-137, 167`), the only way to write inside the lease and undo journal; there is no public bulk-import method; (b) the coupling fails loudly, not silently: `tests/test_cli_store_auth_creds.py` drives `import_auth` end to end against the real `MongoAuthStore` over the fake server (15 tests, incl. `test_a_failed_import_is_undone_whole`, `test_the_import_goes_through_the_lease_and_leaves_no_journal`), and a rename turns them red; (c) U8 did not edit `auth/store_mongo*.py`. It is still a layering smell: the next change to the auth transaction has to know a CLI importer reaches into it. Follow-up (u6bf owner, not U8): add a public `import_account/import_group` on `MongoAuthTx` and move `migrate_auth` onto it. Not a criterion; no cycle needed.

**F3 (Warning, non-blocking) - `_seed_allocator` writes the allocator document outside the undo journal.** `migrate_auth.py:44-50` uses `tx._writer(META)` directly (`insert_one` / CAS `update_one`), so the counter is not rolled back if the commit step fails after the loop. Consequence is a burned id range (harmless; `store_mongo_tx.py:167-169` says the same of rolled-back ids). Ids are only ever set above every imported id, so M45 holds. Noted, no action required.

**F4 (Warning, non-blocking) - an existing account with the same id and email but a different hash/generation counts as `unchanged` on `--apply`, but as `conflicting-id` in `verify`/`--check-remote`.** `_import_users` (`migrate_auth.py:89-90`) compares id and email only; `auth_status` (`:142-144`) compares id, generation, hash and disabled. Nothing is overwritten (the account is skipped), and `verify` reports the difference with exit 1, so M42/M45/M44 hold; but the `--apply` report understates it. Small fix: in `_import_users` compare the same four fields as `auth_status`. Suggest for the next touch of this file.

**F5 (Warning, non-blocking) - a binary file under a migrated `.work/` root is classified `blob` but the blob store always refuses it.** `classify_key` (`migrate_state.py:77-81`) sends any `BINARY` suffix to `blob`; `store/blobs.py:40,108-109` refuses any key containing a `.work` segment (`NOT_BLOB_SEGMENTS`). Measured: my probe planted `.work/ceo-bench/demo/shot.png`; `--apply` printed `gridfs ... refused=1`, exit 1, `verify` `mismatches: 1`, and it would repeat on every run. No leak and nothing written; the real CEO-benchmark inputs are JSON (`stages/bench_inputs.py`: `atomic-list.json`, `.pin.json`), so this does not hit today's data. Same applies to any media under `.work/drive-jobs/` or `.work/team/`. Fix when convenient: classify a `.work/` binary as `skip` (reported under M25) or document it.

**F6 (Info) - judgement calls in the manifest accepted.** (i) `credentials_on()` (`migrate_creds.py:26-38`) sets `AUTOTESTER_STORE_AREAS` for the process only and restores it in `finally`; the test `test_env_is_never_edited_and_the_area_flag_is_not_left_on` and mutant m27 cover it. (ii) `--check-remote` is the only way a dry run connects (`cli_store.py:130-131`). (iii) The manifest's pre-existing failure is real and not U8's (F7).

**F7 (Info) - `tests/test_cli_advice_resolves.py::test_the_collector_reports_what_it_could_not_resolve` fails, pre-existing.** Reproduced: `1 failed, 44 passed` for `tests/test_cli_subapp_hook.py tests/test_cli_advice_resolves.py`; the extra items are `auth/store_mongo_tx.py:109` and `store/mongo_backend.py:73`. Neither file is in `git diff e0a6beb5..HEAD` (the U8 diff touches only the five src files listed in the manifest), so U8 did not cause or worsen it; no U8 file appears in the failure.

**F8 (Info) - unsafe private key shown as `<private>` (`migrate_state.py:108`) was verified by reading only.** I could not create a key that fails `safe_key` on this Windows host (`ABCDEF~1.json` passed `safe_key`; `:` makes an NTFS stream). The manifest's tests do not reach that line either. The code path is a one-line conditional and the other private-name paths were exercised (F-table below), so no action.

## Criteria

| Crit | Result | Evidence |
|---|---|---|
| M41 dry run default, no connection | MET | `cli_store.py:128-131`: `_open()` only when `apply or check`. Probe: `migrate` -> exit 0, `opened 0`, fake server `databases == {}`, source tree hash unchanged. Test `test_dry_run_loads_no_driver` (subprocess: no `pymongo`/`bson`). |
| M42 `--apply` idempotent, conflicts reported never overwritten | MET | Probe (fake server): APPLY1 exit 0 `written: 21`; APPLY2 `written: 0`, document count identical. Then I (a) grew a source row file -> only the new row written, (b) changed a stored credential value -> `secrets conflicting-id=1`, stored value still the altered one, (c) edited a stored `projects` doc -> `conflicting-id=1`, `written: 0`, exit 1, `verify` `mismatches: 2`. Write only on `status == "to_insert"` (`migrate_state.py:207`); no source write path exists. |
| M43 signed rows verbatim | MET | `EXACT` set (`migrate_state.py:34,136`) skips canonicalisation; rows appended as written (`:146-150`); `verify_approvals` `:213-237`. Probe: approvals + revocations `unchanged=1` after apply, `verify` `mismatches: 0`. Tests `test_signed_rows_arrive_byte_identical_and_verify`, `test_verify_catches_one_flipped_byte_in_a_signed_row`. |
| M44 verify | MET | Probe: `verify` exit 0 `mismatches: 0` after a clean apply; exit 1 `mismatches: 2` after I altered a document and a credential. |
| M45 auth, sessions excluded by default | MET | `migrate_auth.py:100-122`: one `transaction()` (lease + journal), ids/hash/generation verbatim, sessions only `--include-sessions` and `until > now`. Probe with `--include-sessions`: auth imported, **zero** `browser_sessions` documents, only database `autotester` created. Source SQLite opened `?mode=ro` (`:32`). See F2-F4 for non-blocking notes. |
| M46 / M36 credentials | MET | `credential_pairs` (`migrate_creds.py:52-64`) takes only keys a project DECLARES that `.env` sets, drops `PATHLYNKS_MONGO_URI` (any case) and `is_server_key` keys before the door, counts them without naming. Probe: `.env` held declared keys for two projects, an undeclared `STRAY_KEY` and `UNDECLARED_X`, `AUTOTESTER_APPROVAL_KEY`, `PATHLYNKS_MONGO_URI`, `GEMINI_API_KEY` (the last three declared by a project in mixed form); stored `secrets` = exactly `B_USER` (bproj), `DEMO_PASS`, `DEMO_USER` (demo) with the right `p`; report says `3 declared key(s) found in .env; 5 deployment secret(s) left out (never stored, never named)`. Writes go through `ui/env_editor.py::put_credentials` (`:88`), never a raw collection; a stored key is never replaced (`:81-83`). Probe `.env` unchanged (8 lines). |
| M9 no URI anywhere | MET | `_safely` (`cli_store.py:113-120`) prints `type(exc).__name__` only. Probe A: patched `migrate_state` to raise `RuntimeError(f"connect to {URI} failed; also {CEO}")` for `migrate --apply`, `--check-remote`, `verify`, plain `migrate`: output is `store ... failed: Boom`, exit 1; no canary in stdout/stderr or the root log handler (DEBUG). Probe B: client factory raising `Boom(f"cannot reach {uri}")` for apply, verify, check-remote: `store ... failed: StoreUnavailable`; no leak. |
| M25 families stay out | MET | `SKIP` (`:30`), `classify_key` (`:69-82`), `_count_scratch`. Probe report: `never moved (M25): .env=1, .work-scratch=1, .xlsx=1, chunks=1, crawl_summaries=1, exports=1, profiles=1`; none stored. Test `test_m25_families_are_reported_and_never_stored`. |
| M25 as amended by D-128 | MET (code); contract text needs amendment, see F1 | Probe: `.work/ceo-bench/` held 4 files (two projects, `.json` and `.jsonl`, a file named `ABCDEF~1.json`, `secret-answers.json`), item text a planted canary `CHKB-CEO-ITEM-Qq8-zzz`. Migrated into `server_state` (second apply `written: 0`). Every report across dry run, `--check-remote`, apply x3, verify, tamper and the two failure modes contains one line `ceo-bench (private, D-128): N file(s), content hash <sha256>`; the canary, the strings `ceo-bench/`, `secret-answers`, `ABCDEF~1`, `atomic-list` appear in no output and no log record. Names are kept out of "largest documents" (`migrate_state.py:52`) and the unsafe list (`:108`). |
| C-limits | MET | New src files 188 / 237 / 145 / 92 lines; longest function 26 lines (AST count). No `*_v2`/`*_new`. `git diff e0a6beb5..HEAD --name-only` lists no src file beyond the five D-127 allows (`cli_store.py`, the three modules, the one `cli_subapps.py` registration). |
| Real Mongo / `.env` | NOT TOUCHED | Rig sets `AUTOTESTER_ROOT` to tmp and routes the driver through `fake_mongo.seams`; my probe asserts `repo_root()` is the tmp root and sets `PYTEST_CURRENT_TEST`. |

## Commands run and outputs (head `cb080764`, in the worktree)

```
env -u ANTHROPIC_BASE_URL uv run pytest tests/test_cli_store_state.py tests/test_cli_store_auth_creds.py -o addopts= -p no:cacheprovider
  -> tests\test_cli_store_state.py ..................  tests\test_cli_store_auth_creds.py ...............   33 passed, 2 warnings in 9.07s

uv run ruff check src tests scripts                      -> All checks passed!
uv run autotester doctor > .work/doctor-chkB.txt         -> exit 0; last line "doctor: clean" (D-087 advisories non-blocking)
uv run python scripts/mutation_check.py qa/evidence/mongo-store-u8/mutations.json --repo . > .work/mut-chkB.txt
  -> exit 0; last line "36/36 mutations killed"; each KILLED line's "actually failed" matches the named test (m1, m2, m3, m30 read)
env -u ANTHROPIC_BASE_URL uv run pytest tests/test_cli_subapp_hook.py tests/test_cli_advice_resolves.py -o addopts= -p no:cacheprovider
  -> 1 failed, 44 passed; FAILED test_the_collector_reports_what_it_could_not_resolve (store_mongo_tx.py:109, mongo_backend.py:73: not U8 files, F7)
uv run python <scratchpad>/probe/probe_u8.py   (my own adversarial probe, fake Mongo + tmp dirs, planted canaries)
  -> DRY exit 0 opened 0 tree same True | CHECK exit 0 opened 1 | APPLY1 exit 0 written: 21 | APPLY2 written: 0 doc count same True
     secrets: B_USER/bproj, DEMO_PASS/demo, DEMO_USER/demo | browser_sessions docs: 0 | VERIFY exit 0 mismatches: 0
     TAMPER apply exit 1 projects conflicting-id=1, secrets conflicting-id=1, written: 0 | TAMPER verify exit 1 mismatches: 2
     RAW/FACTORY failures: "store <cmd> failed: Boom|StoreUnavailable", no leak | ALL OUTPUT leaks: [] log leaks: []
```
The test files were run two at a time, one call each, no full suite. The five `tests/test_role_port_authz.py` environmental failures were not in scope and not run. The probe is outside the repo (scratchpad); nothing under `src/` or `tests/` was edited. The earlier first probe pass (with a PNG inside `.work/ceo-bench/`) is what exposed F5.

## What the maker should do (none blocks PASS)

1. Checker seat: amend M25 to cite D-128 (F1) at close-out.
2. Optional, next touch: F4 (compare the same four fields), F5 (classify `.work/` binaries as `skip`), F2 (public import method on `MongoAuthTx`, u6bf).

First real `migrate --apply` remains G1 (Umesh runs it); nothing in this check ran it.
