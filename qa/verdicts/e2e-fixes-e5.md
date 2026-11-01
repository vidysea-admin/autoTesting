# Verdict - e2e-fixes-e5 (AT-1433), checker A

**Verdict:** PASS (with warnings, none blocking)
**Cycle checked:** 0
**Checker:** A (independent, fresh context; did not read any other checker's verdict)
**Code SHA judged:** 130e7cd6 (branch feat/e2e-e5, base master 70a7a486)
**Contract:** qa/contracts/e2e-fixes.md E5.1-E5.5. **Criticality:** CRITICAL (auth + credentials + deploy), dual check.

## Re-run results (worktree D:/autoTesting/.claude/worktrees/e2e-e5, env -u ANTHROPIC_BASE_URL, -o addopts=, 2 files per call)

| Command | Result |
|---|---|
| pytest tests/test_storage_warning.py tests/test_container_entrypoint_behaviour.py | 49 passed, 1 skipped (pre-existing mode-644 skip) |
| pytest tests/test_mongo_deploy_u10.py tests/test_env_loading.py | 35 passed |
| pytest tests/test_store_startup_u9.py tests/test_state_bypass_rule.py | 87 passed |
| pytest tests/test_credential_store_u11.py tests/test_ui_auth_envkeys.py | 44 passed, 1 failed: test_only_the_door_writes_secrets_and_no_crypto_exists |
| ruff check src tests scripts | All checks passed! |
| autotester doctor > .work/doctor-chkA.txt | rc 1; only violations: docs/SNAPSHOT.md stale-generated + stale-committed (master drift; no E5 file flagged). core/env.py = 300 lines (at cap, allowed) |

**Known red confirmed pre-existing.** `git diff --stat 70a7a486 HEAD` on `src/autotester/store/migrate_creds.py` and `tests/test_credential_store_u11.py` is empty (neither touched by E5). At 70a7a486, `migrate_creds.py:78` contains `credential_collection(` and `tests/test_credential_store_u11.py:68` allow-lists only `{core/env.py, ui/env_editor.py}`: the failure is independent of E5 (and belongs to E7's `migrate_creds.py:60` scope). The existing test files were only added to (diff is +117/+94, 0 deletions), so no existing case was loosened (E5.2 "pass unmodified" holds).

## Mutation re-run

- Maker's file, unchanged driver `qa/evidence/e2e-fixes-e5/run_mutation_e5.py` (adds docker/ to the harness sandbox; no repo file edited): **16/16 KILLED** (m1-m8, e1-e8), output `.work/mut-chkA.txt`. Each kill was by a test the harness required to be collected, with a green baseline.
- My own 3 mutants (`.work/mut-chkA.json`, same driver, run in the sandbox copy; worktree untouched, `git status` clean after):
  - x1 URI appended to the "operator store selection kept" message: KILLED by `test_e5_the_uri_value_is_never_printed`.
  - x2 blank-but-set URI selects Mongo (`${PATHLYNKS_MONGO_URI+x}` instead of non-blank): KILLED by `test_e5_no_uri_or_a_blank_one_selects_nothing[uri1]`, `[uri2]` and `test_e5_the_real_script_without_a_uri_selects_nothing`.
  - x3 operator guard ignores `AUTOTESTER_STORE_AREAS` (half-merge): KILLED by `..._wins_whole_and_is_not_half_merged[extra1]`, `[extra3]`.

## Direct execution of `select_mongo_store` (docker/entrypoint.sh:46-62), sandbox, `env -i`, fake URI `mongodb://fakeuser:fakepass-CANARY@fake-host.invalid/` (no real value used)

The function was extracted verbatim with sed and run under `set -euo pipefail` with `all_state_on_mongo` (:68) sourced beside it.

| Case | Output |
|---|---|
| URI, nothing else | "every state area selected on Mongo"; STORE=mongo; AREAS = all nine `<area>=mongo` (settings, projects, runs, crawls, approvals, auth, credentials, blobs, queue); `all_state_on_mongo` -> yes |
| URI + AUTOTESTER_STORE=file | "operator store selection kept ..."; STORE=file, AREAS unset; all_state_on_mongo -> no |
| no URI / URI of spaces | silent, both variables unset, return 0 |
| URI + `<root>/.auth/auth.sqlite3` non-empty | "existing SQLite auth store at <path>; Mongo not auto-selected"; both unset |
| URI + AUTOTESTER_AUTH_DIR pointing at a dir holding auth.sqlite3 | same skip (AUTH_DIR override honoured, matches `auth/db.py:22-32`) |
| URI + AUTH_DIR with no sqlite file | selects Mongo |
| canary grep over stdout+stderr of the selecting and the operator-kept runs | 0 hits |

Python cross-check (`.work/chkA_probe.py`): the generated AREAS value yields `store_selection()` all `mongo` over exactly the 9 `AREAS` of `store/mongo_routes.py:25`, and `auth.store.on_mongo()` True. With K_SERVICE set: all nine mongo + no mount table -> None; `AUTOTESTER_STORE=mongo` only -> "Cannot verify that ..." (auth still SQLite); invalid `AUTOTESTER_STORE_AREAS` -> warning, no exception; K_SERVICE unset + invalid -> None.

## Criteria

- **E5.1 PASS.** Selection precedes `warn_if_ephemeral` (call at :63 vs the later `warn_if_ephemeral || true`); all nine areas explicit; whitespace-only URI = absent (:48); operator choice wins whole with one line (:49-52); the per-area test asserts against `store.mongo_routes.AREAS` read from the module.
- **E5.2 PASS.** Blank/unset URI returns 0 before any export (:48); executed above; existing warn cases unmodified and green (u10, storage_warning).
- **E5.3 PASS.** Presence test only (`${uri//[[:space:]]/}` is never expanded into output); no `set -x`; canary absent in stdout/stderr in my runs and in the maker's stub-argv test; x1 killed.
- **E5.4 PASS.** `core/env.py:135` `on_cloud_run()` (K_SERVICE non-blank, single definition); `:151-177` `storage_warning` warns on ephemeral and on the unknowable branches on Cloud Run, quiet when all areas mongo, honours `AUTOTESTER_EPHEMERAL_OK=1`, never raises on a bad selection, unchanged off Cloud Run; `ui/admin_view.py:22` banner on `hosted() or on_cloud_run()`. All contract test-seam cases exist and pass; m1-m8 kill.
- **E5.5 PASS (option 3 of the three the contract names: skip when an existing SQLite user store is detected).** Executed above; `test_e5_an_existing_sqlite_user_store_is_not_locked_out` creates a real user via `accounts.bootstrap_admin`, runs the function, asserts neither variable set, `on_mongo()` False, user still found; mutation e5 kills it.

## Rulings on the maker's deviations

1. **`_all_areas_mongo` also requires `auth.store.on_mongo()` (core/env.py:140-148): ACCEPT.** Strictly more conservative than the contract text; `AUTOTESTER_STORE=mongo` alone leaves auth on SQLite (`auth/store.py:93-100`), so a quiet warning there would hide an ephemeral account store. Every contract case (all nine explicit) behaves identically; mutation m3 pins it; verified by my probe.
2. **Only `auth.sqlite3` is detected, not `projects/*` file state: ACCEPT as a WARNING (W1).** The contract names only the SQLite user store, and `projects/` is mkdir'd by the entrypoint at :34, so the directory's existence cannot be the test. The residual risk is real but narrow: it needs a persistent volume with `projects/*/project.json` (or runs/approvals) and NO `auth.sqlite3` (hosted auth never used), AND the URI in the process environment. The prod compose passes `.env` via `env_file` (`docker/compose.prod.yml:13`), so that path exists; any prod with hosted users has the SQLite file and is skipped. The dev compose (`docker-compose.yml:18`, bind-mounted repo as root) has no `env_file`, so a developer's `.env` URI is not in the entrypoint's environment (see 3) and does not trigger it. Suggested hardening (not required): also skip when `compgen -G "$root/projects/*/project.json"` matches; safe on Cloud Run because the entrypoint creates `projects/` empty. Flag to Umesh as the manifest already does.
3. **URI read from the process env only, not `.env`: ACCEPT.** It matches the contract wording ("`PATHLYNKS_MONGO_URI` is set and non-blank") and is the safe direction: an undetected URI means "no selection", which is the no-brick path (E5.2); and it keeps a developer's bind-mount `.env` from silently flipping the store. Cloud Run supplies the URI as an environment secret (DEPLOY.md:261). Consequence for VM operators who keep the URI only in `<data>/.env`: no auto-select; they set the two variables by hand.
4. **E5.5 skip-if-sqlite and a fresh Cloud Run instance: CONFIRMED it still selects Mongo.** On Cloud Run `/app` is not writable, so `AUTOTESTER_ROOT=/data` (entrypoint :28-30); a fresh container has no `/data/.auth/auth.sqlite3` (executed: URI + AUTH_DIR with no sqlite file -> selects). The skip triggers only where a populated SQLite file already persists (compose volume, or a GCS volume mounted at /data), which is the case the contract wants protected. A 0-byte file does not block the selection (`-s`), which is correct (no users). A supervised restart inside a container that ran with Mongo creates no sqlite file, so the decision is stable across restarts.

## Findings (file:line)

- **W1 (warning)** docker/entrypoint.sh:53-57: no detection of file state under `projects/` (ruling 2). Hardening suggested, not a defect against this contract.
- **W2 (warning, follow-up)** docker/DEPLOY.md:262-268 still says `auth` moves "only after its users are migrated" and "A fully flipped service sets both"; now partly stale because the entrypoint sets both when the URI is present and no SQLite store exists. Manifest item 7 already owes this; `tests/test_mongo_deploy_u10.py` pins phrases in that file, so edit both together.
- **W3 (note)** src/autotester/core/env.py is exactly 300 lines (doctor cap); the docstring reflow dropped historical prose only (diff reviewed: no code removed). The next addition there (E6.6 reuses `on_cloud_run`; E7 touches the same module) needs a split first.
- **W4 (process)** No `senior-software-engineer` review agent was run by the maker (brief forbade it); the lifecycle review stays owed to the orchestrator. I made no code edits.
- No defects against E5.1-E5.5 found. No `.env` value was read or printed; the only URI used was the fake literal above.
