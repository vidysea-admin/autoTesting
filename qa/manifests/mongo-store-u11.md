# Manifest - mongo-store-u11

**Status:** checked-PASS (cycle 0, dual: qa/verdicts/mongo-store-u11.md + .b.md)
**Fix cycle:** 0
**Contract:** `qa/contracts/mongo-store.md` (ACTIVE 2026-10-29), unit U11 (credential store). **Criticality:** CRITICAL, dual check (U11 row).
**Authority:** D-123 (plain documents in `secrets`: no encryption, no key derivation, no `cryptography`, no crypto module, no new dependency; supersedes D-122 item 4), D-121, D-122 (module list). No `src/` module was added.
**Branch:** `feat/mongo-store-u11`, cut from master `4df612ca`. Not merged, not pushed.
**Base SHA:** `4df612ca`
**Code SHA:** see `git log` on the branch (the code + tests + evidence commit; this manifest is in the same commit, so the SHA is reported in the hand-back, not here).
**Criteria judged by U11:** M8 (store half), M31, M32, M33, M34, M35, M36, M37, M47 (no-crypto half). **M46 is U8's** (see "What is NOT built").

## What changed

| File | Kind | One job / change |
|---|---|---|
| `src/autotester/core/env.py` (298 lines) | E in place | READ SIDE. `credential_collection :234` is the ONE place the `secrets` collection is named (None unless `store_selection()["credentials"] == "mongo"`, so file mode imports no driver); `stored_secret_values :247`; `redaction_values :253` (file values plus every stored value under a `KEY@store` label); `resolve_credentials :259` (file, then process env for declared keys, then this project's own stored docs; every value a layer hides and every other project's doc goes to `shadow`, masked and never resolvable). Store off: returns exactly the old `(usable, shadow)`. |
| `src/autotester/ui/env_editor.py` (278 lines) | E in place | THE SECRET DOOR (module already documented as "the one write path to .env"). `CredentialRefused :39`; `_check_pair :83` (key shape, no newline; never echoes the value); `validate_env_values :99` is store-aware; `_rearm :201`; `_put_doc :208` (the ONLY `replace_one` on a credential doc); `put_credentials :213`; `save_credentials :233` (store OR `.env`, never both); `drop_credentials :244`; `snapshot_credentials :261` / `restore_credentials :268`. |
| `src/autotester/browser/secrets.py` (299) | E in place | `SecretStore.load :150` resolves through `core_env.resolve_credentials` (one resolver, no second read path). |
| `src/autotester/store/mongo_routes.py` (290) | E in place | `UNROUTED :28` is now `{"auth": ...}` only (credentials is routed); `repo_redactor :189` is built from `redaction_values(env) + Mongo URI + extra`. |
| `src/autotester/store/mongo_backend.py` (300, at the cap) | E in place | `default_backend :285` builds the backend with a lazy secret gate (breaks the recursion `default_backend -> repo_redactor -> stored_secret_values -> default_backend`); `default_store :299` hands the door the one connection. No second client. |
| `src/autotester/stages/role_onboarding.py` | E in place | `write_values :192` takes `slug` and calls `save_credentials`. |
| `src/autotester/ui/routes_role_accounts.py` (295) | E in place | `_env_now` reads file + store values; `_commit :208` snapshots stored docs (`:216`), writes through `ro.write_values(..., slug)` (`:219`), and on failure restores them in a `finally` (`:227`) so they go back even when the project restore itself raises. |
| `src/autotester/ui/routes_credentials.py` | E in place | both value writes go through `save_credentials` (`:177`, `:269`); the page's "present" set comes from `resolve_credentials` (`:216`). |
| `src/autotester/ui/app.py` | E in place | `_guard_intake :127` counts stored keys as present; the intake write is `save_credentials` (`:196`). |
| `src/autotester/ui/routes_project_edit.py` | E in place | `undeclare_secret :263` calls `drop_credentials(slug, [key])` (M37). |
| `src/autotester/sources/adapters.py`, `src/autotester/providers/litellm_provider.py` | E in place | the two redactors they build include store values (`:146`, `:62`), so a provider error or a PDF reading scrubs a stored credential too (M34). |
| `tests/credential_store_support.py`, `tests/test_credential_store_u11.py`, `tests/test_credential_store_u11_routes.py` | N | the rig (credentials area on mongo over `fake_mongo`), 22 unit tests, 10 route tests. |
| `qa/evidence/mongo-store-u11/mutations.json`, `mutation-run.txt` | N | C7 mutation spec (26 mutants) and its run. |

Not touched: `auth/`, `store/mongo_guard.py`, `store/filestore.py`, `pyproject.toml`, `uv.lock`. No dependency added.

## Criteria map

| Crit | Code | Test (falsifier it kills) |
|---|---|---|
| M31 plain, one place, one door | doc shape `{_id, p, value, updated_at}` written at `env_editor.py:208-230`; collection named only at `core/env.py:244` | `test_the_door_stores_a_plain_document_in_secrets_and_nowhere_else` (a)(no other collection, no GridFS, no `.env`); `test_only_the_door_writes_secrets_and_no_crypto_exists` (b)(c): `credential_collection(` is used by exactly `core/env.py` and `ui/env_editor.py`, one `replace_one` in the door, no `cryptography` import, no `secret_box`, `cryptography` not in `pyproject.toml`; `test_project_b_cannot_overwrite_or_read_a_key` (d) |
| M32 no key, closed on outage | no code path reads `AUTOTESTER_APPROVAL_KEY` in the door or the resolver; outage = `StoreUnavailable` from the guard, nothing caught | `test_credentials_do_not_depend_on_the_approval_key` x3 (unset, empty, rotated); `test_an_unreachable_store_raises_and_falls_back_to_nothing` (save and `SecretStore.load` raise `StoreUnavailable`, data-root digest unchanged, no `.env`); route twin `test_a_store_outage_on_save_is_a_503_and_no_file_is_written` |
| M33 scoping and order | `resolve_credentials core/env.py:259-278` | `test_a_project_resolves_only_the_keys_it_declares`; `test_the_store_beats_the_process_environment_which_beats_the_file`; `test_a_deleted_credential_no_longer_resolves`. The B5-B9 tests in `test_secrets.py` / `test_secrets_host_match.py` are unedited and pass. |
| M34 redaction union and refresh | `redaction_values :253`, `repo_redactor mongo_routes.py:189`, `_rearm env_editor.py:201` | `test_the_redactor_covers_env_and_store_values_and_refreshes_on_a_write` (trace line, exception text, `Redactor.scrub`, `guard_prompt`); `test_a_stored_value_is_refused_in_every_other_document` (the backend's cached gate is rebuilt after a credential write, M8) |
| M35 UI surface | all UI writes via `save_credentials`; file mode untouched | `test_role_onboarding_puts_every_login_in_the_store_and_none_in_env`; `test_the_credential_editor_saves_to_the_store_and_the_page_shows_set` (dev and tester pages never contain the value); `test_adding_a_custom_credential_...`; `test_onboarding_with_a_credential_row_stores_it_in_the_store`; `test_a_malformed_pair_is_refused_without_echoing_the_value`; `test_with_the_store_off_everything_is_the_env_path` |
| M36 deployment secrets | refusal at `put_credentials env_editor.py:221` | `test_deployment_secrets_are_refused_and_the_batch_writes_nothing` x5 (Mongo URI, approval key, two provider keys, harness password); route twin `test_a_deployment_key_is_refused_with_a_400_and_nothing_is_stored` |
| M37 lifecycle | `drop_credentials :244` (every delete carries `p`), `snapshot/restore :261/:268`, `_commit`, `undeclare_secret` | `test_dropping_a_key_deletes_only_that_projects_document`; `test_dropping_a_project_deletes_its_secrets_and_sessions`; `test_a_snapshot_puts_the_previous_document_back_unchanged` (same doc incl. `updated_at`, data-root digest unchanged); `test_a_failed_commit_puts_the_previous_stored_documents_back`; `test_removing_a_declaration_deletes_its_stored_value` |
| M8 (store half) | repo redactor and backend gate include store values | as M34, plus `test_role_onboarding_refuses_a_key_the_store_already_holds`, `test_onboarding_refuses_a_key_the_store_already_holds` |
| M47 no crypto | nothing added | `test_only_the_door_writes_secrets_and_no_crypto_exists` |

## Things the checker should look at (judgement calls and gaps, said plainly)

1. **M46 is not built here.** `store migrate`'s credential step belongs to U8. U11 supplies what it needs: `put_credentials` (the door, which refuses the M36 classes by name) and `resolve_credentials` / `parse_env` for reading `.env`. U8 must call `put_credentials`, never `collection("secrets")` (the M31(b) test would fail it).
2. **Door lives in `ui/env_editor.py`, read side in `core/env.py`.** No new module (the task's "STOP" condition did not trigger). Cost: three files sit at 295-300 lines (`mongo_backend.py` is at exactly 300 and `__all__` was deliberately not extended with `default_store`).
3. **No role-account or project deletion route exists in the code.** `drop_credentials(slug, None)` (secrets and `browser_sessions`, both `delete_many({"p": slug})`) is built and tested but has no caller until such a route exists; the only wired lifecycle delete is `undeclare_secret`. M37's "role account" and "project" clauses are therefore met by the primitive, not by a route. Say so in the verdict if that is not enough.
4. **Another running instance's cached secret gate** refreshes only on its own restart or its own credential write (`_rearm` resets this process's backend). Deployment is `--max-instances 1` today; a multi-instance deployment needs a short TTL or a change counter (not built).
5. **`browser_sessions` writer is U12's.** U11 only deletes from it.
6. **No explicit index on `secrets`** beyond `_id` (the door looks up by `_id` and filters by `p` in memory). Fine at this size.
7. **Resolve order has a deliberate asymmetry:** in file mode the process environment is NOT a resolution layer (byte-identical to today); in mongo mode it is, below the store (M33).
8. **Intake order:** `onboard_submit` saves the project before the credential write (as before for `.env`), so a credential write that fails after the guard leaves the project without its value; unchanged shape from file mode, and the guard (`_guard_intake`) makes the refusals unreachable in normal use.
9. **A bug found and fixed while testing:** in `_commit` the stored-document restore ran after `_restore`, so a failing project restore would have skipped it; it is now in a `finally` (`routes_role_accounts.py:224-228`), pinned by `test_a_failed_commit_puts_the_previous_stored_documents_back` (mutant "route never restores" is killed).
10. **Test order, honest:** the door and resolver code were written before the tests (a context reset happened mid-unit), so the tests were not written red-first. Their non-vacuity is the mutation run below, which found and led to fixing four weak tests (a shallow `before` copy, a survivable intake test, two missing positive assertions).
11. **State-bypass baseline:** no U11 rows were retired. Every row still names a function that reads or checks `.env` (file mode, non-credential keys, the approval key, the settings page's server-key presence); doctor reports none stale. `.env` stays the home of deployment secrets (M36).
12. **Line endings:** the working tree is CRLF under `core.autocrlf`; every touched file was checked for lone CR / lone LF (0 each).

## Verify (run in `D:/autoTesting/.claude/worktrees/mongo-u11`, `-o addopts=`, at most 2 files per call)

```
pytest tests/test_credential_store_u11.py tests/test_credential_store_u11_routes.py -> 32 passed
pytest tests/test_state_selection.py tests/test_secrets.py                          -> 53 passed
pytest tests/test_secrets_host_match.py tests/test_ui_env_editor.py                 -> 13 passed, 1 skipped
pytest tests/test_role_onboarding.py tests/test_role_accounts_routes.py             -> 36 passed
pytest tests/test_role_accounts_rescope.py tests/test_ui_secrets_declaration.py     -> 21 passed
pytest tests/test_ui_credential_exemption.py tests/test_mongo_backend_fence.py      -> 21 passed
pytest tests/test_mongo_backend_layout.py tests/test_blobs_mongo.py                 -> 81 passed
pytest tests/test_store_startup_u9.py tests/test_store_outage_u9.py                 -> 26 passed
pytest tests/test_container_redaction.py tests/test_check_no_secrets.py             -> 75 passed, 1 skipped
pytest tests/test_litellm_guard.py tests/test_litellm_provider.py                   -> 39 passed
pytest tests/test_pdf_teaching.py tests/test_provider_factory.py                    -> 43 passed, 1 skipped
pytest tests/test_gemini_media_guard.py tests/test_ui_learn_vendor_echo.py          -> 18 passed
uv run ruff check src tests scripts                                                 -> All checks passed!
uv run autotester doctor  (redirected to .work/doctor-u11.txt)                      -> doctor: clean (advisories only)
uv run python scripts/mutation_check.py qa/evidence/mongo-store-u11/mutations.json  -> 26/26 mutations killed (qa/evidence/mongo-store-u11/mutation-run.txt)
```

Not run: the full suite in one call (low-memory rule), `tests/test_role_port_authz.py` (5 known environmental failures), the auth envkeys tests (U11 does not touch `auth/`).
No `.env` value was read or printed; every value in the tests is a planted synthetic string.
