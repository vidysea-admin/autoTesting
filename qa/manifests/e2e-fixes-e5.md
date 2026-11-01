# Manifest - e2e-fixes-e5

**Status:** checked-PASS (cycle 0, dual: A 48149208, B ca720c59)
**Fix cycle:** 0
**Contract:** `qa/contracts/e2e-fixes.md`, unit E5 (AT-1433). **Criticality:** MEDIUM-HIGH (a wrong selection 503-bricks the site; a wrong auth flip locks users out).
**Authority:** Umesh 2026-11-01 (the Mongo URI is already in the live environment; live must persist without DevOps). D-122/D-123 and the write fence are not re-opened. No new `src/` module (CLAUDE.md: a new module needs an Umesh D-entry), no `qa/contracts/` edit.
**Branch:** `feat/e2e-e5` (worktree `D:/autoTesting/.claude/worktrees/e2e-e5`), cut from master `70a7a486`. Not merged, not pushed (D-130 holds pushes).
**Base SHA:** `70a7a486`
**Code SHA:** the commit that adds this file, `git log -1 feat/e2e-e5`.
**Criteria judged by E5:** E5.1, E5.2, E5.3, E5.4, E5.5.

## What changed

| File | Kind | Change |
|---|---|---|
| `docker/entrypoint.sh` (127 lines) | E in place | new `select_mongo_store` `:46-62`, called `select_mongo_store \|\| true` `:63` BEFORE `all_state_on_mongo` / `warn_if_ephemeral \|\| true`. Exports `AUTOTESTER_STORE=mongo` `:58` and `AUTOTESTER_STORE_AREAS` (all nine `<area>=mongo`, `auth` and `credentials` included) `:59` only when the URI is non-blank, neither store variable is set, and no SQLite auth store exists. Never exits, never echoes the URI. |
| `src/autotester/core/env.py` (300 lines, at the cap) | E in place | `on_cloud_run()` `:135` (the one `K_SERVICE` detector); `_all_areas_mongo()` `:140` (lazy imports of `store_selection` and `auth.store.on_mongo`); `storage_warning` `:151` extended. To stay at 300 lines the module docstring, the `load_repo_env` docstring and the `PUBLIC_ENV_KEYS` docstring were reflowed (prose condensed, no code or meaning removed except wording). |
| `src/autotester/ui/admin_view.py` | E in place | `storage_banner` `:22` shows when `hosted() or env.on_cloud_run()`. |
| `tests/test_container_entrypoint_behaviour.py` (227 lines) | E | 14 `test_e5_*` cases (sandboxed bash, the real script). |
| `tests/test_storage_warning.py` (268 lines) | E | 14 Cloud Run / banner cases, plus an autouse fixture that clears `K_SERVICE`, `AUTOTESTER_STORE`, `AUTOTESTER_STORE_AREAS` for the file. Existing tests unmodified. |
| `qa/evidence/e2e-fixes-e5/` | N | `mutations.json`, `mutation-run.txt`, `run_mutation_e5.py` (driver, see judgement call 5), `e5-entrypoint-tests.txt` |

## Criteria map

| Crit | Code | Test (falsifier it kills) |
|---|---|---|
| E5.1 URI alone selects Mongo for every area | `entrypoint.sh:58-59` | `test_e5_uri_alone_selects_mongo_for_every_area` (asserts against `store.mongo_routes.AREAS`, read from the module, plus `auth=mongo` and `credentials=mongo`); `test_e5_the_generated_selection_is_one_the_store_accepts` (feeds the generated values to `store_selection()` and `auth.store.on_mongo()`: all nine mongo, auth really flipped); `test_e5_the_real_script_exports_the_selection_and_leaks_no_uri` (the real script, stubbed exec sees `AUTOTESTER_STORE=mongo`, prints "every state area is on Mongo", no ephemeral warning) |
| E5.1 operator choice wins whole | `entrypoint.sh:49-52` | `test_e5_an_operator_choice_wins_whole_and_is_not_half_merged[extra0..3]` (`AUTOTESTER_STORE=file`; only `AUTOTESTER_STORE_AREAS=blobs=mongo`; `AUTOTESTER_STORE=mongo`; `AUTOTESTER_STORE_AREAS=auth=file`: neither variable changed, "operator store selection kept" printed) |
| E5.1 whitespace-only URI is absent | `entrypoint.sh:48` | `test_e5_no_uri_or_a_blank_one_selects_nothing[uri0,uri1,uri2]` (unset, empty, whitespace) |
| E5.2 no URI, no selection, no brick | `entrypoint.sh:48` returns 0 before any export | same test; `test_e5_the_real_script_without_a_uri_selects_nothing` (real script, `AUTOTESTER_STORE` empty in the exec'd process, rc 0); the existing `tests/test_storage_warning.py` warn cases and `tests/test_mongo_deploy_u10.py` warn cases pass unmodified |
| E5.3 URI never printed / echoed / on a command line | presence test only (`${uri//[[:space:]]/}` is a local, never expanded into output or an exec) | `test_e5_the_uri_value_is_never_printed` (canary in stdout/stderr, with and without an operator selection); `test_e5_the_real_script_exports_the_selection_and_leaks_no_uri` (canary absent from stdout, stderr and the stub-recorded `STUB-ARGS`) |
| E5.4 `storage_warning` warns on Cloud Run | `env.py:135` `on_cloud_run`, `:140` `_all_areas_mongo`, `:151-177` `storage_warning` (the unreadable / no-`/` branches raise into the existing `except Exception`, which now returns the "Cannot verify that ..." sentence on Cloud Run and `None` off it) | `test_cloud_run_with_no_mount_table_warns_instead_of_going_quiet`, `..._with_an_unreadable_mount_table_warns` (no `/` entry), `..._on_a_verified_volume_is_quiet`, `..._ephemeral_root_keeps_the_existing_sentence`, `..._with_every_area_on_mongo_is_quiet_even_without_mounts`, `..._opt_out_is_quiet`, `test_off_cloud_run_an_unknowable_root_stays_quiet`, `test_an_invalid_store_selection_warns_and_never_raises` (no exception), `test_on_cloud_run_is_one_non_blank_variable`, `test_cloud_run_with_any_area_on_files_still_warns[...]` and `..._one_area_on_mongo_and_the_rest_on_files_warns` |
| E5.4 banner | `admin_view.py:22` | `test_banner_shows_on_cloud_run_without_the_hosted_flag` (K_SERVICE set, `AUTOTESTER_HOSTED` unset, the banner HTML contains the sentence); existing `test_no_banner_when_not_hosted` passes unmodified |
| E5.5 auth flip honest about existing accounts | `entrypoint.sh:53-57`: when `${AUTOTESTER_AUTH_DIR:-${AUTOTESTER_ROOT:-/app}/.auth}/auth.sqlite3` is non-empty (the file `auth/db.py:auth_db_path` names), the whole selection is skipped with one line | `test_e5_an_existing_sqlite_user_store_is_not_locked_out` (see the section below) |

## E5.5: what happens to a container that already holds SQLite users

Chosen path: **the selection is skipped when an existing SQLite auth store is detected** (the third option the contract names). Reason: with the URI present and an existing `auth.sqlite3`, flipping `auth` onto an empty Mongo collection locks every existing user out, and the "first-admin bootstrap works on the empty Mongo" path would let whoever signs in first claim admin on a deployment that already has an owner. Skipping the WHOLE selection (not only `auth`) keeps the stores consistent: projects/approvals written by the same deployment stay with its accounts. The operator migrates (`autotester store migrate`, the G1 step) and then sets the variables by hand, which the operator-wins rule respects.

Command and output (`.work`-free: pytest, tmp root):

```
env -u ANTHROPIC_BASE_URL uv run pytest tests/test_container_entrypoint_behaviour.py -o addopts= -k e5 -v
test_e5_an_existing_sqlite_user_store_is_not_locked_out PASSED
```

The test creates the user with `accounts.bootstrap_admin(...)` (a real `auth.sqlite3` under the tmp `AUTOTESTER_ROOT`), runs the entrypoint function with the URI present, asserts both store variables stay unset and the line "existing SQLite auth store" is printed, then asserts `on_mongo()` is False, `auth_store()` is a `SqliteAuthStore`, and `accounts.find_user(...)` still finds the user. Mutation e5 (detection removed) kills it. Full per-test output: `qa/evidence/e2e-fixes-e5/e5-entrypoint-tests.txt`.

On Cloud Run a fresh instance has no `auth.sqlite3` (the root is ephemeral), so the skip does not trigger and the selection is made, which is the premise of the unit. If a GCS volume is mounted at the data root with a populated SQLite file, the skip correctly protects it.

## Things the checker should look at (judgement calls)

1. **Skip vs migrate (E5.5).** Skipping is deliberately the conservative reading. A deployment that is half-migrated (SQLite present AND the operator wants Mongo) must set the variables itself; the entrypoint prints which file it saw.
2. **Only the auth store is detected; file state under `projects/` is not.** A compose deployment with a volume holding `projects/*` but NO `auth.sqlite3` (auth never used) and the URI present would flip `projects` to Mongo and hide those projects until migrated. The contract names only the SQLite user store, and on Cloud Run `projects/` is created empty by the entrypoint at `:34`, so a generic "root is non-empty" test would be wrong there. Not built; flagged for Umesh. This is the same risk the G1 text in `docker/DEPLOY.md` describes.
3. **The URI is read from the process environment only** (contract: "`PATHLYNKS_MONGO_URI` is set and non-blank"). A URI that lives only in a `.env` file inside the data root is loaded by the app AFTER the entrypoint, so it does not trigger the selection (`core/env.py:mongo_uri` would still read it). Cloud Run supplies the URI as an environment secret, which is the stated premise.
4. **`_all_areas_mongo` requires `auth` through its own entry**, not only through `store_selection()` (it also calls `auth.store.on_mongo()`, the public wrapper over `_auth_on_mongo`). The contract text says "not every store area is `mongo` (`store_selection()`)", but `AUTOTESTER_STORE=mongo` alone leaves auth on SQLite (A-W1, `auth/store.py:93-100`), and a warning that went quiet there would hide an ephemeral account store. The contract's own cases (all nine explicit) behave identically. Mutation m3 pins the difference.
5. **Mutation harness gap.** `scripts/mutation_check.py::_sandbox` copies only `scripts/`, `tests/`, `src/`, so a mutant of `docker/entrypoint.sh` (and any test that reads it at import, which includes the pre-existing `tests/test_storage_warning.py`) cannot be collected there ("MUTATION RUN INVALID: cannot collect"). I did not edit the shared harness: `qa/evidence/e2e-fixes-e5/run_mutation_e5.py` imports it unchanged, wraps `_sandbox` to also copy `docker/` and `Dockerfile`, and calls its own `main`. Same checks, same refusals (named tests must be collected, green baseline, kill must be the named test).
6. **`core/env.py` is exactly 300 lines.** Any later addition there needs a split first.
7. **`docker/DEPLOY.md` still says** "The volume stays required until every state area is on MongoDB ... Flipping is a human gate (G1)" and "set both variables". That text is now partly stale (the entrypoint sets them when the URI is present). Not edited: `docker/DEPLOY.md` is not a file this unit owns and `tests/test_mongo_deploy_u10.py` pins phrases in it. Owed as a follow-up.
8. **Line endings.** The working tree is CRLF (autocrlf); the mutation harness rewrites restored files with LF. `git diff` is unaffected (the repo blobs are LF).

## Verify (run in `D:/autoTesting/.claude/worktrees/e2e-e5`, `env -u ANTHROPIC_BASE_URL`, `-o addopts=`, at most 2 files per call)

| Command | Result |
|---|---|
| `uv run pytest tests/test_storage_warning.py tests/test_container_entrypoint_behaviour.py -o addopts=` | 49 passed, 1 skipped (the pre-existing non-executable-python test on a filesystem that reports mode 644 as executable) |
| `uv run pytest tests/test_mongo_deploy_u10.py tests/test_storage_warning.py -o addopts=` | 58 passed |
| `uv run pytest tests/test_env_loading.py tests/test_env_dollar_warning.py -o addopts=` | 16 passed |
| `uv run pytest tests/test_store_startup_u9.py tests/test_store_outage_u9.py -o addopts=` | 26 passed |
| `uv run pytest tests/test_ui_error_pages.py tests/test_state_bypass_rule.py -o addopts=` | 87 passed |
| `uv run pytest tests/test_credential_store_u11.py tests/test_ui_auth_envkeys.py -o addopts=` | 44 passed, **1 failed: `test_only_the_door_writes_secrets_and_no_crypto_exists`, PRE-EXISTING on master `70a7a486`**: `src/autotester/store/migrate_creds.py` (added by U8, `dd066e26`) contains `credential_collection(` and the test's allow-list is `{core/env.py, ui/env_editor.py}`. Not caused by E5 and not in E5's file list (E7 lists `migrate_creds.py:60`). |
| `uv run ruff check src tests scripts` | All checks passed! |
| `uv run autotester doctor > .work/doctor-e5.txt` | exit 1, 2 violations, both `docs/SNAPSHOT.md` (stale-generated, stale-committed): master drift (the snapshot lacks D-130 and still lists D-125); regenerating (`autotester snapshot`) shows exactly that diff. Left unregenerated so sibling branches do not conflict; no E5 file is flagged. `core/env.py` is 300 lines (cap). |
| `uv run autotester map` | no change to `docs/MAP.md` |
| `uv run python qa/evidence/e2e-fixes-e5/run_mutation_e5.py D:/autoTesting/.claude/worktrees/e2e-e5 qa/evidence/e2e-fixes-e5/mutations.json` | **16/16 mutations killed** (`mutation-run.txt`): m1-m8 (`env.py`, `admin_view.py`), e1-e8 (`entrypoint.sh`) |

The full suite was not run (low-memory rule). No `senior-software-engineer` review agent was dispatched (the brief forbids dispatching agents); the lifecycle review step is owed to the checker/owner.
