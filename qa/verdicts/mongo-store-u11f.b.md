# Verdict - mongo-store-u11f (checker B)

**Verdict:** PASS
**Cycle checked:** 0
**Checker:** checker-B (fresh context; focus failure paths and resources; did not read any other checker's verdict on this unit)
**Code SHA checked:** `d5f996d3` (manifest commit `770d8699`), branch `feat/mongo-store-u11f`, base `890f79a4`
**Contract:** `qa/contracts/mongo-store.md` M31-M37, M34, plus the U11 dual-check warnings listed in the manifest.

## Result per focus item

| Item | Result | Finding |
|---|---|---|
| undeclare under outage at each step: 503 true, nothing orphaned, restore runs, no revival | MET (one double-fault caveat, finding 3) | 1-3 |
| credential writes/snapshot/restore/read: one client, indexes once | MET | 4 |
| `rearm` resets the secret gate immediately | MET | 5 |
| `blob_store` with blobs=mongo builds on `mongo_uri`, round-trips; no URI = named error, no value | MET | 6 |
| condensed `mtime` / `delete_row` identical | MET | 7 |
| store unset = master, except the declared `is_server_key` case change | MET | 8 |
| files <=300, functions <=50, ruff, doctor, mutations | MET | 9 |

## Findings

1. **Undeclare, steps 1 and 2 (outage before anything changed): 503 is truthful.** Probe `probe_b.py::test_step1_snapshot_fails` makes every `find_one` on `secrets` raise `AutoReconnect` (persistent, so the 3-try retry in the guard cannot hide it); `test_step2_drop_fails` does the same for `delete_one`. Both: HTTP 503, no value and no canary in the body, declaration still `["PL_PASS"]` (`ProjectStore.load_project`), `secrets` documents byte-identical to before. Code: `ui/routes_project_edit.py:265-271` (`snapshot_credentials` then `drop_credentials` then `save_project`), so both raise before the project file is touched. The same probes run on master `890f79a4` FAIL (declaration gone, value orphaned: `assert ([] == ['PL_PASS']`), so the probes discriminate.
2. **Step 3 (project save fails): the restore really runs and puts the document back unchanged.** `test_step3_save_fails_restore_runs` spies on the name `routes_project_edit.restore_credentials`: called exactly once, the `secrets` documents afterwards equal the pre-image including `updated_at` (list equality on the fake's docs), declaration kept, the `OSError` still propagates (`raise`, `:270-271`). Foreign-project case (`test_foreign_project_doc_untouched`): another project's document under the same `_id` is neither deleted by the `p`-scoped drop nor altered by the restore. Re-declaring after a successful undeclare leaves `secrets == []`, `stored_secret_values() == {}`, and the old value is no longer scrubbed by the redactor (`test_redeclare_after_failed_paths`).
3. **Caveat, not blocking: double fault.** `test_step3b_save_fails_and_store_down_for_restore`: save raises and the store goes down before the restore. Result: HTTP 503, declaration kept, `secrets == []` (value gone). So the 503 text ("nothing was changed") is not literally true in that one case, but it is the safe side (the user re-enters the value; nothing is orphaned or revived). The manifest note 4 already names the two-write residual. No fix required; a later hardening could be to log that the restore failed.
4. **One client, indexes once.** `test_one_client_full_cycle_via_routes` (own probe, wider than the maker's): fake `client_factory` and `MongoBackend.ensure_indexes` counted over: UI declaration, two `put_credentials`, `snapshot_credentials`, `restore_credentials`, `stored_secret_values`, the undeclare route, `drop_credentials(slug)` (the `browser_sessions` + `secrets` path through `default_store`), then a backend `put` and `get`. Output `CLIENTS 1 ENSURE 1`. Same probe on master: `CLIENTS 6 ENSURE 6`. `test_rearm_does_not_reopen_client`: `default_backend()` is the same object and `_store` is the same object after a write. `grep reset_default_backend src` has no caller outside `mongo_backend.py`. Note: `run_store.blob_store()` builds its own `GuardedStore(uri)` (`store/run_store.py:136`), so with blobs=mongo there is a second client for blobs; that is by design (separate cache `_BLOBS`) and outside the credential-write claim.
5. **`MongoBackend.rearm` (`store/mongo_backend.py:246`).** `test_rearm_scrubs_immediately_and_after_drop`: after `put_credentials`, the very next backend write containing the value is refused with `StoreSecretRefused` (message carries no value); after `drop_credentials` the gate is rebuilt again and the value is no longer refused; the backend instance is the same throughout. Mutant "re-arm removed" killed (finding 9). Residual (inherent, max-instances 1, M28): another process writing a credential does not rearm this process's gate.
6. **`blob_store` (`store/run_store.py:126-136`).** `test_blob_store_builds_and_roundtrips`: with `AUTOTESTER_STORE_AREAS=blobs=mongo` and the URI in the process environment it builds on the fake, is cached, and `put`/`get` round-trips; `test_blob_store_uri_only_in_repo_env`: URI present only in the repo-root `.env` also works (`core.env.mongo_uri` reads it). `test_blob_store_no_uri_message`: no URI raises `StoreSelectionError`, message printed was `PATHLYNKS_MONGO_URI is not set; blobs=mongo needs it` (name only, no `mongodb://`, no canary), and nothing is cached in `_BLOBS`. Master fails all three with `AttributeError: module 'autotester.store.mongo_backend' has no attribute 'URI_ENV'` (`run_store.py:132`), confirming the defect existed.
7. **Condensed `mtime` / `delete_row` (`store/mongo_backend.py:158`, `:227`).** Diff against `890f79a4` read: `max(gen, default=None)` and `bool([delete_one(...) for hit in hits])` are semantically the original (same `find`, same one `delete_one` per hit in order, same exception propagation, `bool` of a non-empty list is True whenever there was a hit regardless of the result values). Differential probe `test_diff_mtime_delete_row` (no hit False; 2 hits of 3 rows deleted, True; second call False; mtime None for a missing key, float for a stored one) passes on the branch AND on master with identical results (`DIFF OK` both). `tests/test_mongo_backend_layout.py` + `tests/test_mongo_backend_fence.py`: 80 passed.
8. **Store unset.** Diff of `core/env.py:55-59`: only `is_server_key` upper-cases (declared change; callers `core/env.py:209`, `ui/credential_guard.py:33`, `ui/env_editor.py:101`). Run with no store env: `snapshot_credentials -> {}`, `drop_credentials -> 0`, `restore_credentials({}) -> None`, `'pymongo' in sys.modules` False, `'gridfs'` False (M13); `validate_env_values` unchanged for file mode (`a_b` still `InvalidEnvValue`); `is_server_key('anthropic_api_key')` True, `('pl_pass')` False. File-mode `undeclare_secret` therefore runs the same save then nothing. `_check_pair` unchanged, so file-mode `.env` writes are unchanged. Low-severity observation: `_check_store_pair` (`ui/env_editor.py:92-106`) refuses a value equal to the Mongo URI after `strip()`, not one that merely contains it; a value embedding the URI inside a longer string passes the door (M36 as written speaks of the URI "stored", so I do not count it as a miss).
9. **Residuals noted, not caused by this unit:** (a) `put_credentials` batches are validated whole before writing (`:239`) but the writes themselves are not atomic: `test_batch_partial_write_on_outage` with the second `replace_one` failing leaves the first document stored and raises `StoreUnavailable` (output `PARTIAL StoreUnavailable ['PL_A']`). That is the U11 "non-atomic batch" residual in its outage form; no transactions are assumed (contract amendment table). (b) the foreign-project check in `put_credentials:241-244` is find-then-replace, a TOCTOU between two projects writing the same key name; keys are namespaced per project, so low risk. (c) `restore_credentials` removes a snapshot-absent key by `_id` only (`env_editor.py:285`, no `p`), unchanged from U11. I did not examine the "diagnose script" warning (outside my focus).

## Commands run (worktree `D:/autoTesting/.claude/worktrees/mongo-u11f`, main `.venv` python, `PYTHONPATH=<worktree>/src`, `-o addopts=`, `env -u ANTHROPIC_BASE_URL`, two files per call)

```
pytest tests/test_credential_store_u11f.py tests/test_credential_store_u11_routes.py   -> 40 passed
pytest tests/test_store_outage_u9.py tests/test_media_blobs.py                         -> 23 passed
pytest tests/test_mongo_backend_layout.py tests/test_mongo_backend_fence.py            -> 80 passed
probe_b.py (14 own probes; scratch, not committed)                                      -> 14 passed on the branch
probe_b.py on master 890f79a4 (git archive)                                             -> 9 FAILED (steps 1-3, one-client, rearm x2, blob_store x3), diff_mtime/delete_row passed
ruff check src tests scripts                                                            -> All checks passed!
autotester doctor (redirected to .work/doctor-b-u11f.txt)                               -> exit 0, "doctor: clean" (only non-blocking D-087 advisories)
python scripts/mutation_check.py qa/evidence/mongo-store-u11f/mutations.json --repo .  -> 15/15 mutations killed
wc -l: core/env.py 300, ui/env_editor.py 292, store/mongo_backend.py 300, ui/routes_project_edit.py 272, store/run_store.py 236 (all <= 300; function length enforced by doctor, clean)
git status after all runs: clean (no src/ or tests/ file touched by me)
```

No `.env` value was read or printed; every value in the probes is a synthetic canary. The full suite was not run (low-memory rule).

## Verdict

PASS for checker B. No blocking finding. Findings 3 and 9 are warnings for the record (double-fault wording of the 503; batch write atomicity under outage), neither is a regression introduced by U11f and neither falsifies M31-M37 as written. Dual-check closure needs checker A's verdict as well.
