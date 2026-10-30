# Manifest - mongo-store-u11f

**Status:** checked-PASS (cycle 0, dual: qa/verdicts/mongo-store-u11f.md + .b.md)
**Fix cycle:** 0
**Contract:** `qa/contracts/mongo-store.md` (ACTIVE), unit U11 follow-up. Criteria M31-M37 and M34, closing the warnings of the U11 dual check (`qa/verdicts/mongo-store-u11.md`, `.b.md`). **Criticality:** CRITICAL rows (M31-M36), so the follow-up is dual-checked like U11.
**Authority:** D-120, D-122, D-123. No new `src/` module (D-122/D-123 list untouched); no crypto, no new dependency.
**Branch:** `feat/mongo-store-u11f` in `D:/autoTesting/.claude/worktrees/mongo-u11f`, cut from master `890f79a4`. Not merged, not pushed.
**Base SHA:** `890f79a4`
**Code SHA:** `d5f996d3db34b7532a9600a20177bc6e575d0160` (code, tests, mutation evidence; this manifest is a second commit on top)
U12 runs in parallel on `browser_sessions`: nothing under `browser/` or session code was touched. `auth/store_mongo.py` untouched.

## What changed (edit in place; five source files, no new module)

| File (lines, cap 300) | Change |
|---|---|
| `ui/env_editor.py` (292) | New `_check_store_pair :92` = `_check_pair` + non-empty + no control character (`unicodedata` category `Cc`) + deployment secret refused in any letter case + a value equal to the Mongo URI refused under any key (`value.strip() == mongo_uri()`, only when a URI is set). `put_credentials :231` runs it on the whole batch first (`:239`), then the other-project check, then writes; `validate_env_values :116` (store on) uses the same check (`:123`) so an intake that validates first never passes a batch the door refuses. `save_credentials :249` drops its duplicate pre-loop (the door does it). `_rearm :218` now calls `default_backend().rearm()` (`:223`) instead of dropping the whole backend. |
| `core/env.py` (300) | `is_server_key :55` compares upper-cased, so `autotester_approval_key` is a server key. |
| `ui/routes_project_edit.py` (272) | `undeclare_secret :265-271`: `snapshot_credentials([key])`, `drop_credentials`, then `save_project`; on a failed save `restore_credentials(held)` and re-raise. Store down raises before anything changed (the 503 is true, nothing orphaned); a re-declaration cannot revive a value. |
| `store/mongo_backend.py` (300) | `MongoBackend.rearm :246` sets the cached secret gate to rebuild on the next write; the backend, its one `GuardedStore`/client and its indexes stay. Cap kept by two equivalent condensations: `mtime` (`max(..., default=None)`) and `delete_row` (`bool([delete_one ...])`, the idiom `delete :144` already uses). |
| `store/run_store.py` (236) | `blob_store :126-136` read `mongo_backend.URI_ENV`, which does not exist (AttributeError with `blobs=mongo`). Now `core.env.mongo_uri()` and `MONGO_URI_ENV`; the `GuardedStore` import stays lazy. |

## Criteria map

| Crit | Code | Test (falsifier it kills) |
|---|---|---|
| M31/M36 door shape and deployment secrets | `env_editor.py:92-106`, `:239`, `core/env.py:55-59` | `test_credential_store_u11f.py`: `test_a_server_key_is_a_server_key_in_any_letter_case` (4), `test_the_door_refuses_a_server_key_in_any_letter_case` (3), `test_the_door_itself_refuses_a_malformed_pair_and_writes_nothing` (11 pairs: lowercase key, space, digit-first, dash, empty key, newline, CR, NUL, bell, DEL, empty value; each asserts nothing written, tree unchanged, no value in the error), `test_a_value_equal_to_the_mongo_uri_is_refused_under_any_key_name` (plain and space-padded; also via `save_credentials`, no `.env`), `test_the_validation_only_gate_agrees_with_the_door` |
| M37 lifecycle / M32 truthful 503 | `routes_project_edit.py:265-271` | `test_a_store_outage_on_undeclare_is_a_503_and_nothing_changed` (declaration and stored value both still there), `test_a_failed_project_save_on_undeclare_puts_the_stored_value_back`, `test_redeclaring_an_undeclared_key_does_not_revive_the_old_value`; existing `test_removing_a_declaration_deletes_its_stored_value` still passes |
| M34 redaction at the two unpinned sites | `providers/litellm_provider.py:56-62` (untouched), `sources/adapters.py:142-147` (untouched) | `test_the_litellm_guard_withholds_a_value_held_only_in_the_store` (value in the store only: `_env_secret_values`, `_secret_values`, `guard_text` raises `ProviderError` without the value), `test_a_pdf_reading_is_scrubbed_of_a_value_held_only_in_the_store` (no `.env`; text and reading both scrubbed) |
| One client, indexes once | `env_editor.py:218-223`, `mongo_backend.py:246` | `test_credential_writes_reuse_one_client_and_build_indexes_once` (two writes, snapshot, restore, read: 1 client factory call, 1 `ensure_indexes`), `test_the_secret_gate_still_rebuilds_after_each_credential_write` (gate refreshed after every write, M34) |
| `blob_store` with blobs=mongo | `run_store.py:126-136` | `test_blob_store_builds_on_the_fake_with_blobs_on_mongo` (builds, is cached, put/get round trip on the fake), `test_blob_store_without_a_uri_is_a_named_selection_error` |

## Notes the checker should look at

1. **One behaviour change with the store unset:** `is_server_key` is now case-insensitive, and `load_repo_env` / `ui/credential_guard.py` call it. A lower-case `.env` key such as `anthropic_api_key` is now treated as a server key (exported, refused as a project credential). The brief required this; upper-case keys, every `set_env_values` / `.env` write path and `save_credentials` in file mode are unchanged (their tests pass untouched). File-mode `undeclare_secret` now calls `snapshot_credentials` (returns `{}`) and `drop_credentials` (returns 0) before `save_project`: no observable difference.
2. **Control-character rule is store-only.** `_check_pair` (shared with file mode) is unchanged; `_check_store_pair` adds `Cc` refusal, so file-mode `.env` writes are byte-identical to before. A tab in a stored value is refused (category `Cc`).
3. **Lowercase server keys are refused by the shape check first** (`InvalidEnvValue`: UPPER_SNAKE_CASE); the case-insensitive `is_server_key` is exercised directly and matters for `credential_guard` and `load_repo_env`.
4. **Residual not closed here:** `undeclare_secret` is two writes (store, then project file). If the process dies between them the value is gone and the declaration remains, which is the safe side (the user re-enters it). `GuardedStore` has no `close()` (`mongo_guard.py` is at the 300-line cap); the fix removes the per-write client rather than adding one. `mypy` reports one pre-existing error at `env_editor.py:267` (`browser_sessions` `delete_many` on an `InsertOnlyCollection` type), untouched by this unit and U12's area.
5. The default backend is still cleared by `reset_default_backend()` in tests and on process end only; nothing in `src/` calls it any more.

## Verify (worktree `D:/autoTesting/.claude/worktrees/mongo-u11f`, `PYTHONPATH=<worktree>/src`, main `.venv` python, `-o addopts=`, 2 files per call, `env -u ANTHROPIC_BASE_URL`)

```
pytest tests/test_credential_store_u11f.py                                    -> 30 passed
pytest tests/test_credential_store_u11.py tests/test_credential_store_u11_routes.py -> 32 passed (unchanged)
pytest tests/test_ui_env_editor.py tests/test_env_loading.py                  -> 19 passed, 1 skipped
pytest tests/test_ui_secrets_declaration.py tests/test_role_onboarding.py     -> 28 passed
pytest tests/test_ui_auth_envkeys.py tests/test_env_dollar_warning.py         -> 30 passed
pytest tests/test_mongo_backend_layout.py tests/test_mongo_backend_fence.py   -> 80 passed
pytest tests/test_media_blobs.py tests/test_media_sources_blobs.py            -> 19 passed
pytest tests/test_state_selection.py tests/test_state_sweep_u3b.py            -> 31 passed
pytest tests/test_store_outage_u9.py tests/test_store_startup_u9.py           -> 26 passed
pytest tests/test_litellm_guard.py tests/test_litellm_provider.py             -> 39 passed
pytest tests/test_ui_credential_safety_project.py tests/test_ui_credential_exemption_scope.py -> 21 passed
pytest tests/test_state_bypass_rule.py tests/test_state_signatures.py         -> 89 passed
pytest tests/test_credential_store_u11f.py tests/test_ui_project_intake.py    -> 45 passed
pytest tests/test_state_wrappers.py tests/test_ui_auth_policy_table.py        -> 85 passed
pytest tests/test_ui_auth_surface.py tests/test_ui_auth_hardening.py          -> 42 passed
pytest tests/test_ui_settings.py tests/test_ui_error_pages.py                 -> 20 passed
pytest tests/test_core.py tests/test_gemini_media_guard.py                    -> 32 passed
ruff check src tests scripts                                                  -> All checks passed!
autotester doctor (redirected to .work/doctor-u11f.txt, exit 0)               -> doctor: clean (only non-blocking D-087 advisories)
python scripts/mutation_check.py qa/evidence/mongo-store-u11f/mutations.json --repo .  -> 15/15 mutations killed
```

Full mutation output: `qa/evidence/mongo-store-u11f/mutation-run.txt`; spec: `qa/evidence/mongo-store-u11f/mutations.json` (15 mutants: door shape check removed, control-char check removed, case-sensitive `is_server_key`, URI-equality check removed, URI padding not stripped, empty value accepted, validation-only gate weakened, undeclare old order, undeclare restore removed, litellm store values dropped, PDF scrub store values dropped, whole-backend reset per write, re-arm removed, `blob_store` wrong URI name, `blob_store` without URI check). Not run: the full suite in one invocation (low-memory rule). Canaries are planted synthetic values only; no `.env` value was read or printed.
