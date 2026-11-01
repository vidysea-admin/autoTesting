# Verdict (checker-B) - e2e-fixes-e5 (E5, AT-1433), fix cycle 0

**Cycle checked:** 0
**Verdict:** PASS (with 4 Warnings the maker must carry into the close-out; no Block)
**Head checked:** 130e7cd6 on `feat/e2e-e5` (base master 70a7a486). Fresh and independent; no other checker's verdict on this unit was read.
**Criteria:** E5.1, E5.2, E5.3, E5.4, E5.5 of `qa/contracts/e2e-fixes.md`; `qa/manifests/e2e-fixes-e5.md`. Adversarial focus: what breaks live.

## Summary
The entrypoint selection does what the contract says and nothing more. I executed the real `select_mongo_store` (extracted from `docker/entrypoint.sh:46-62`) in a sandbox with
fake env: URI alone selects all nine areas on Mongo; an operator `AUTOTESTER_STORE=file` (or any `AUTOTESTER_STORE_AREAS`, even malformed) is kept whole; no or blank URI selects
nothing; an existing non-empty `auth.sqlite3` (default path or `AUTOTESTER_AUTH_DIR`) skips the whole selection; a fresh root selects Mongo, so a new Cloud Run instance gets it.
Required suites, ruff and doctor are as claimed; 16/16 of the maker's mutants die (re-run by me) and 3/3 of mine. The adversarial probes found no Block: a wrong URI does not 503 every
request, it stops start-up (fail-fast), and `AUTOTESTER_STORE=file` is a working escape. Four Warnings are about operability and documentation of that new coupling, not correctness.

## Commands and outputs (all in `D:/autoTesting/.claude/worktrees/e2e-e5`, `env -u ANTHROPIC_BASE_URL`, `-o addopts=`, at most 2 test files per call)
| Command | Result |
|---|---|
| `uv run pytest tests/test_storage_warning.py tests/test_container_entrypoint_behaviour.py -o addopts=` | 49 passed, 1 skipped (pre-existing non-exec python test) |
| `uv run pytest tests/test_mongo_deploy_u10.py tests/test_env_loading.py -o addopts=` | 35 passed |
| `uv run pytest tests/test_store_startup_u9.py tests/test_state_bypass_rule.py -o addopts=` | 87 passed |
| `uv run pytest tests/test_credential_store_u11.py -o addopts=` | 21 passed, 1 failed: `test_only_the_door_writes_secrets_and_no_crypto_exists` (`Extra items in the left set: 'store/migrate_creds.py'`). Confirmed pre-existing: `git diff --stat 70a7a486..HEAD -- src/autotester/store/migrate_creds.py tests/test_credential_store_u11.py` is empty, so neither file is touched by this branch and the failure is the same at master 70a7a486. Not E5's (E7 lists `migrate_creds.py:60`). |
| `uv run ruff check src tests scripts` | All checks passed! |
| `uv run autotester doctor > .work/doctor-e5-b.txt` | rc 1, 2 violations, both `docs/SNAPSHOT.md` (stale-generated, stale-committed): master drift as stated; no E5 file flagged (`core/env.py` at 300 lines = cap, allowed). |
| `git diff 70a7a486..HEAD -- tests/ \| grep -c '^-[^-]'` | 0 removed test lines: existing tests unmodified, only additions. |
| `uv run python qa/evidence/e2e-fixes-e5/run_mutation_e5.py $PWD qa/evidence/e2e-fixes-e5/mutations.json` | **16/16 mutations killed** (m1-m8, e1-e8), each by the test it names (harness checks the named test is the one that failed). |
| my 3 mutants (`mut_b.json`) via the same driver | **3/3 killed**: b1 URI echoed in the *operator-kept* line (killed by `test_e5_the_uri_value_is_never_printed`); b2 blank check strips only spaces so a tab-only URI selects (killed by `..._selects_nothing[uri2]`, the `"  \t "` case); b3 wrong default auth dir `.authx` (killed by `test_e5_an_existing_sqlite_user_store_is_not_locked_out`). |

## Sandbox execution of the real function (fake URI `mongodb://fakeuser:fakepass-CANARY@127.0.0.1:1/x`; the canary never appeared in any output)
| Case | Output |
|---|---|
| URI, nothing else | `every state area selected on Mongo`; `AUTOTESTER_STORE=mongo`; AREAS = `settings=mongo,projects=mongo,runs=mongo,crawls=mongo,approvals=mongo,auth=mongo,credentials=mongo,blobs=mongo,queue=mongo`; rc 0 |
| URI + `AUTOTESTER_STORE=file` | `operator store selection kept`; STORE=file, AREAS unset; rc 0 |
| URI + `AUTOTESTER_STORE_AREAS=zzz` (malformed) | kept; STORE unset, AREAS=zzz (not touched, not half-merged); rc 0 |
| no URI / whitespace-only URI | no output, both unset, rc 0 |
| URI with trailing spaces | selects Mongo (the app strips it: `core/env.py:227`) |
| URI with literal surrounding quotes | selects Mongo (see Finding 4) |
| URI + non-empty `<root>/.auth/auth.sqlite3` | `existing SQLite auth store at ...; Mongo not auto-selected`; both unset |
| same via `AUTOTESTER_AUTH_DIR` | skipped the same way (bash default matches `auth/db.py:25-32`: empty override counts as unset in both) |
| URI + 0-byte `auth.sqlite3` | selects Mongo (`-s`: an empty file holds no users) |
| URI + fresh root (what a new Cloud Run instance has) | selects Mongo |
| URI + `projects/p1/project.json` on the root, no `auth.sqlite3` | **selects Mongo** (Finding 2) |

## Rulings on the maker's deviations
1. **`_all_areas_mongo` also requires `auth.store.on_mongo()` (`core/env.py:140-148`): ACCEPT.** The contract's cases (all nine explicit) behave identically; with `AUTOTESTER_STORE=mongo` alone auth stays on SQLite (`auth/store.py:93-100`), so the stricter test never goes quiet over an ephemeral account store. It can only warn more, never less. Mutation m3 pins it.
2. **Only `auth.sqlite3` is detected, not `projects/*`: ACCEPT with Warning W2.** Sandbox confirms a root holding `projects/p1/project.json` and no `auth.sqlite3` is switched to Mongo and that file state is then invisible until migrated. Reachable only when URI is in the process env, no store variable is set, AND the auth store was never created; every hosted deployment creates `auth.sqlite3`, so this is narrow (an auth-disabled loopback dev container). A cheap guard is available that is safe on Cloud Run (the entrypoint makes `projects/` empty at `:34`): also skip when any `$AUTOTESTER_ROOT/projects/*/project.json` exists. Not required by the contract.
3. **URI read from the process environment only: ACCEPT, with Warning W3.** A URI that lives only in `<root>/.env` yields no selection, which fails safe (today's behaviour). The inverse is the problem: `load_repo_env` never overrides a variable already set (`core/env.py:~205`, `os.environ.get(key)` -> continue), and `.env.example:29-32` documents setting `AUTOTESTER_STORE` / `AUTOTESTER_STORE_AREAS` in `.env`. An operator who keeps `AUTOTESTER_STORE=file` in the data-root `.env` while the URI comes from the platform's env gets Mongo, because the entrypoint exports first and the file value is then ignored. "Operator's choice wins whole" holds only for the process environment. (By code reading; I did not run a container.)
4. **E5.5 skip-if-sqlite: ACCEPT, and a fresh Cloud Run instance still selects Mongo.** Verified: a fresh root has no `.auth/auth.sqlite3`, so the selection is made (sandbox row above); `AUTOTESTER_ROOT` is set to `/data` at `entrypoint.sh:30-32` before `select_mongo_store` at `:63`. A GCS volume holding a populated `auth.sqlite3` correctly stays on SQLite with the warning intact. `test_e5_an_existing_sqlite_user_store_is_not_locked_out` runs the real `accounts.bootstrap_admin` and asserts the user is still found; mutation e5 and my b3 kill it. This satisfies the contract's third option.

## Adversarial probes (what breaks live)
- **URI present but wrong or unreachable: start-up fails, requests are not 503'd.** Probe `lifespan -> validate_store_env()` (`ui/app.py:_lifespan`, `store/filestore.py:152`) with the selection the entrypoint generates: unreachable host raises `StoreUnavailable: state store unreachable (StoreUnavailable); areas on mongo: settings, projects, ...` after ~5.8 s (with `serverSelectionTimeoutMS=1500`); `notAUri` and a URI wrapped in literal quotes raise `StoreConfigError: the store connection string is not a valid mongodb:// URI` in <1 s. Neither message contains the URI (M9 holds). `uvicorn` therefore exits and `docker/supervise.py:91-103` restarts the stack ("container service exited; restarting stack"). On Cloud Run that means the new revision never passes the startup probe and traffic stays on the previous revision (fail-closed, and arguably better than silently running ephemeral); on a VM/compose host it is a crash loop until the operator acts.
- **Escape hatch works.** Same bad URI with `AUTOTESTER_STORE=file`: sandbox prints "kept", and `validate_store_env()` returns `ping OK` in 0.0 s (the URI is never opened). So an operator can recover by setting `AUTOTESTER_STORE=file` in the process env (not in `.env`, see W3).
- **Trailing-space URI:** selection and app agree (stripped on both sides). **Quoted URI:** selection happens, app refuses, crash loop (W4).
- **Malformed `AUTOTESTER_STORE_AREAS`:** operator-owned, kept untouched by the entrypoint; the app then stops start-up with `StoreSelectionError` exactly as before E5.
- **First-admin on an empty Mongo auth store:** E5 skips the flip whenever SQLite users exist, so the contract's lockout case is closed. On a genuinely fresh Mongo auth store the usual bootstrap rules apply (`auth/accounts.py:45-65`): with `AUTOTESTER_FIRST_ADMIN_EMAIL` unset on a public-facing server no signup becomes admin, but `_claim_refusal` (`:61-70`) then lets ANY signed-in account claim Admin/CEO while the group is empty. That is the existing D-109 behaviour and the live SQLite store already had it after every deploy; E5 does not widen it (it makes the window one-time instead of per-deploy). Recorded as N1, not a defect of this unit. (By code reading.)

## Findings
1. **Criteria E5.1-E5.5: all met.** E5.1 `entrypoint.sh:46-62,63` (before `warn_if_ephemeral` at the later call), E5.2 `:48` returns before any export, E5.3 presence-only test (`${uri//[[:space:]]/}`, no expansion into any echo or `exec`; sandbox and the canary tests agree), E5.4 `core/env.py:135-177` and `ui/admin_view.py:22`, E5.5 `entrypoint.sh:53-57`.
2. **Warning W2 - file state under `projects/` is not detected** (`docker/entrypoint.sh:53-57`). A root with `projects/*` and no `auth.sqlite3` plus the URI in env hides those projects (sandbox row). Carry to Umesh or add the one-line guard above. Not a contract criterion.
3. **Warning W3 - operator choice in the data-root `.env` does not count** (`entrypoint.sh:49` reads the process env only; `core/env.py` `load_repo_env` never overrides). Document it in DEPLOY.md, or have the entrypoint read the two store keys from `$AUTOTESTER_ROOT/.env` presence-only.
4. **Warning W4 - a wrong, unreachable, IP-not-allow-listed or quoted URI now stops start-up** where it was inert before E5. Behaviour is fail-fast and recoverable with `AUTOTESTER_STORE=file`, but neither the manifest nor `docker/DEPLOY.md` says so, and DEPLOY.md:261 notes Cloud Run needs network access to the allow-listed Mongo host. First deploy after merge should be watched; the entrypoint selection line is the only breadcrumb.
5. **Warning W5 (carried, from the manifest) - `docker/DEPLOY.md:266-268` is stale** ("auth moves only with its own entry ... only after its users are migrated", "set both variables"). Not edited by the unit (a test pins phrases in it); follow-up owed, together with W3 and W4 text.
6. **Info - `core/env.py` module and `load_repo_env`/`PUBLIC_ENV_KEYS` docstrings were condensed** to fit the 300-line cap (the AT-228 narrative and the AT-086 rationale lost sentences, no code changed). Acceptable; the file is at the cap, so the next change there needs a split.
7. **Info (N1)** - `AUTOTESTER_FIRST_ADMIN_EMAIL` should be set on the live service before the first start on an empty Mongo auth store (`docker/DEPLOY.md:96`); otherwise the first signed-in account can claim admin. Pre-existing.

## Scope and limits
No code, merge or push by me; the working tree was not modified except `.work/` scratch and this file. I did not run a container or a real Mongo; the start-up failure modes are from the real `validate_store_env()` against an unreachable fake host. Lifecycle review by `senior-software-engineer` remains owed to the owner. `.work/` scratch (`mut-b.txt`, `mut-b2.txt`, `doctor-e5-b.txt`) is untracked.
