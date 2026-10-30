# Manifest - mongo-store-u12

**Status:** checked-PASS (cycle 0, dual: A 764ff1e2, B 52d15363)
**Fix cycle:** 0
**Contract:** `qa/contracts/mongo-store.md` (ACTIVE), unit U12 (session store), criteria M38, M39, M40; leans on M8, M31-M37. **Criticality:** CRITICAL, dual check (two fresh checkers, D-100).
**Authority:** D-120, D-121, D-122, D-123 (plain storage, no crypto). No new `src/` module: the session half lives in the existing `browser/profiles.py` (its module docstring says so). D-122 file list untouched.
**Branch:** `feat/mongo-store-u12`, cut from master `890f79a4`. Not merged, not pushed.
**Base SHA:** `890f79a4`
**Code SHA:** `d5ad4f3dfa5dd4959555c34008fc2209c4b9a060` (two code commits: `b98e3542` the unit, `d5ad4f3d` the `_project` account id; this manifest is a third commit on top)
Round cap: D-014, 2 fix cycles.

## What changed

| File | Kind | Change |
|---|---|---|
| `src/autotester/browser/profiles.py` (239 lines) | E in place | `wipe_entry_profile` untouched. New session half: `session_id :54`, `_collection :60` (the store gate: `store_selection()["credentials"] == "mongo"`, else `None`), `_put_session :71` (the ONLY write of a session document, `replace_one` by `_id`, then `reset_default_backend` so the write gate rebuilds, M34), `scope_state :83`, `save_session :104`, `load_session :128`, `forget_session :148`, `session_values :167`, `stored_session_values :183`, `_origin_script :197`, `capture_session :211`, `restore_session :224`. |
| `src/autotester/browser/secrets.py` (300, cap 300) | E in place | `SecretStore.mask_also :246` (adds values to the masked-never-resolvable shadow). Two docstrings shortened to stay at the cap; no behaviour change. |
| `src/autotester/store/mongo_routes.py` (292) | E in place | `repo_redactor :189-197` also unions `stored_session_values()` (the run-wide redactor and the M8 write gate). |
| `src/autotester/stages/multi_role_session.py` | E in place | `_start :132` restores after `session.start()`; `sign_in :203` captures after the sign-in settles. Both run on the account's own thread. |
| `src/autotester/stages/manual_login.py` | E in place | `:48` captures under `MAIN_ACCOUNT` after the human finishes (M39). |
| `src/autotester/ui/run_execution.py` (299) | E in place | `_run_normal_cases :178` restores `MAIN_ACCOUNT` for the shared-profile (non-entry) session only. |
| `docs/MAP.md` | generated | `autotester map`. |
| `tests/session_store_support.py`, `tests/test_session_store_u12.py`, `tests/test_session_store_u12_redaction.py` | N (tests) | 24 tests. |
| `qa/evidence/mongo-store-u12/` | N | `mutations.json`, `mutation-run.txt`, `regression-pairs.txt`. |

Not edited (U11f's files): `ui/env_editor.py`, `core/env.py`, `ui/routes_project_edit.py`, `store/run_store.py`, `providers/litellm_provider.py`, `sources/adapters.py`. `store/mongo_guard.py` and `auth/store_mongo.py` untouched. `drop_credentials` (`env_editor.py:244-256`) already deletes `browser_sessions` by `p`; U12 only exercises it in a test.

## Design, said plainly

- Gate: the `credentials` area on mongo (there is no separate sessions area in `AREAS`, and the unit table flips "credentials and browser sessions" together). Store off: every function returns before touching the context or the store; `test_with_the_store_off_nothing_is_read_written_or_touched` asserts no cookie or script call and an unchanged tree.
- Document: `{_id: "<slug>|<account_id>", p, state, saved_at, expires_at, hosts}`, plain. A `|` in the slug or account id is refused. Role accounts use `RoleAccount.id`; the project-level login (manual login, the shared-profile run) uses `MAIN_ACCOUNT = "_project"`, which `ROLE_ACCOUNT_ID_PATTERN` (`^[a-z]...`) can never produce, so no collision.
- Export is `context.storage_state()` with no `path=` (in memory; a mutant that passes `path=` is killed).
- localStorage restore is an `add_init_script` that sets a key only when absent and only when `location.origin` matches a stored origin; cookies by `add_cookies`.
- The profile gate uses `store_selection()` and not `credential_collection(`, so U11's pin `test_only_the_door_writes_secrets_and_no_crypto_exists` (users of `credential_collection(` are exactly `core/env.py` and `ui/env_editor.py`) is unchanged and green.

## Criteria map

| Crit | Code | Tests (falsifier it kills) |
|---|---|---|
| M38 plain, scoped in and out | `profiles.py:83-91` `scope_state` (`_host_matches` against `allowed_domains`; cookie domain `lstrip(".")`; origin via `host_of`; malformed entries dropped), applied in `save_session :115` and again in `load_session :140`; `_put_session :71` the only writer; collection `browser_sessions` only | `test_an_exported_state_is_stored_plain_scoped_and_nowhere_else` (doc shape, plain, evil and parent-domain cookies and evil origin absent, canaries in no other collection, no file, no `.env`), `test_scope_uses_the_projects_allowed_domains_and_fails_closed`, `test_a_restore_re_scopes_what_the_store_holds`, `test_a_state_with_nothing_in_scope_stores_nothing_and_drops_the_old_one` |
| M39 restore semantics | `load_session :128-145` (foreign `p` ignored, not deleted; expired or unreadable deleted; `MAX_AGE_S` cap `:122`); `restore_session :224-239` (`ENTRY_SUFFIX` guard; keyed by account); `forget_session :148`; `save_session :111` refuses a foreign document | `test_an_expired_state_is_deleted_and_never_restored`, `test_an_expired_cookie_is_dropped_and_the_age_is_capped`, `test_a_foreign_document_is_ignored_not_used_not_deleted_not_overwritten`, `test_one_accounts_state_never_reaches_another_account`, `test_an_entry_run_never_restores_a_login`, `test_a_logout_removes_the_state_so_nothing_restores_it`, `test_removing_a_project_removes_its_sessions_only`, `test_an_ambiguous_session_id_is_refused` x4, `test_the_project_level_account_id_cannot_collide_with_a_role_account`, `test_role_sessions_save_after_sign_in_and_restore_per_account` |
| M40 never leaves the door | `session_values :167` (cookie and localStorage values, JSON string leaves, >= 8 chars, longest first, 200 cap); `capture_session :211` and `restore_session :224` call `SecretStore.mask_also` (`secrets.py:246`); `mongo_routes.py:195-197` unions stored sessions into the run-wide redactor and the write gate; `_put_session` rebuilds the gate | `test_a_captured_session_joins_the_redactor_and_the_prompt_gate` (scrub, `guard_prompt`, exception text, JSON leaf), `test_a_restored_session_joins_the_redactor`, `test_the_run_wide_redactor_and_the_write_gate_cover_stored_sessions` (`StoreSecretRefused` on any other write), `test_short_values_are_not_masked_and_the_set_is_capped` |
| Fail closed (M26/M32 flavour) | store errors propagate as `StoreUnavailable`; no file fallback | `test_an_unreachable_store_raises_and_changes_no_file` |
| Store unset = unchanged | `_collection :60-68`, early returns | `test_with_the_store_off_nothing_is_read_written_or_touched` |

## Judgement calls and gaps the checker should weigh

1. **`_host_matches` is EXACT, not suffix** (`browser/secrets.py`, AT-651/D-087). The brief and `CLAUDE.md` say "suffix"; the code says exact. U12 follows the contract text (`_host_matches` against `allowed_domains`): a cookie on `.pl.test` is dropped when the project allows only `app.pl.test`, and `evil.pl.test` is dropped when only `pl.test` is allowed. Stricter than `Project.allows_domain` (suffix); it fails closed (a dropped cookie means a re-login, never a leak). Pinned by `test_scope_uses_the_projects_allowed_domains_and_fails_closed`. If the checker reads M38 as suffix semantics, this is a one-line change in `_in_scope`.
2. **Mask floor 8 chars and cap 200.** The `Redactor` has no minimum length, so registering `1`, `en` or `true` would wreck every trace and make the M8 gate refuse legitimate writes. Values under 8 chars are not masked: a deliberate narrowing of M40's "cookie and localStorage values". A short real token is not covered.
3. **24 h age cap** (`MAX_AGE_S`) on top of the earliest persistent-cookie expiry; session cookies (expires -1) carry no expiry of their own, so the cap is their bound. Not in the contract text; stricter.
4. **Sign-in saves whatever the context holds.** `capture_session` runs after the sign-in click and settle; a failed sign-in stores an anonymous state (or deletes the document when nothing is in scope) and can replace a good one. No login-success signal exists to gate on.
5. **Normal runs only restore, never save.** Only `RoleSessions.sign_in` and `manual_login` save. A login performed inside a normal run is not re-saved.
6. **Entry guard is by profile name** (`paths.slug` ends `-entry-test`, the convention `run_execution._entry_pool` and `orchestrate_execute._start_session` use). The entry pool in `run_execution.py` never calls `restore_session`; the guard is defence in depth. `orchestrate_execute._start_session` (the orchestrate path) was not wired for restore.
7. **Real Chromium not exercised with the store on.** `add_cookies` and `add_init_script` run against a fake context. `tests/test_role_session_port*.py` (live Chromium, store off) pass, which shows the store-off path unchanged.
8. **Review agent not dispatched** (`senior-software-engineer`): the brief says no checkers. The owner may want it before dispatching the dual check.

## Verify (worktree `D:/autoTesting/.claude/worktrees/mongo-u12`, `-o addopts=`, 2 files per call, `env -u ANTHROPIC_BASE_URL`)

```
pytest tests/test_session_store_u12.py tests/test_session_store_u12_redaction.py   -> 24 passed
pytest tests/test_credential_store_u11.py tests/test_credential_store_u11_routes.py -> 32 passed
pytest tests/test_manual_login.py tests/test_multi_role_session.py                 -> 13 passed
uv run ruff check src tests scripts                                                -> All checks passed!
uv run autotester doctor  (redirected to .work/doctor-u12.txt, exit 0)             -> doctor: clean (only non-blocking D-087 advisories)
uv run python scripts/mutation_check.py qa/evidence/mongo-store-u12/mutations.json --repo .  -> 24/24 mutations killed
```

Wider regression pairs (`qa/evidence/mongo-store-u12/regression-pairs.txt`, run before the `_project` rename; the `_project` commit only changed a constant and was followed by the 24-test pair above): manual_login+secrets 33; secrets_host_match+multi_role_session 12; role_session_port+role_session_port_login 18 (live Chromium, store off); entry_browser_reuse_run+lent 20; mongo_backend_fence+blobs_mongo 35; mongo_guard_scan+surface 56; ui_runs_serial_entry_order+resilience 29; run_trace+ui_runs 18; entry_browser_reuse_serial+relogin_reset_fallback 11; state_signatures+mongo_backend_layout 77. All passed. One first-pass failure (U11's pin test, because `profiles.py` called `credential_collection(`) was fixed in the code, the test untouched, and re-run green. Not run: the full suite (low-memory rule); `tests/test_role_port_authz.py` (5 known environmental failures).

## Mutation evidence

`qa/evidence/mongo-store-u12/mutation-run.txt`: 24 mutants, all killed. They cover cookie scoping removed, origin scoping removed, restore not re-scoped, expiry ignored, age cap removed, expired cookie kept, foreign document used, overwritten, or deleted by logout, `|` allowed in ids, entry guard removed, logout leaves state, capture or restore not masking, run-wide redactor omitting sessions, write gate not rebuilt, mask floor 0, mask cap removed, JSON leaves not masked, store-off still reading the store, role restore or save wiring removed, export written to a path, and the project-level account id colliding with a role id. An earlier run had 2 survivors (a syntax-breaking mutant, exit 4, and an over-claimed `kills` entry); the spec was corrected, not the tests.
