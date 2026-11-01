# Verdict - e2e-fixes-e7 (checker A, independent)

**Verdict:** PASS
**Status:** PASS (with 3 non-blocking warnings, W1-W3 below)
**Cycle checked:** 0
**Reviewed SHA:** eaeab0af (base 70a7a486; branch head at commit time also carries another checker's verdict file, which I did not read). Checker A worked in `D:/autoTesting/.claude/worktrees/e2e-e7`; no `src/`, `tests/` or `docker/` file was left modified (probe files and mutants were temporary and removed; `git status --short` was empty before this commit).
**Scope:** `qa/contracts/e2e-fixes.md` E7.1-E7.5 (AT-1416 slug guard, AT-1420 stage token). I did not read any other checker's verdict on this unit.

## Commands re-run and results (`PYTHONPATH=<worktree>/src`, `env -u ANTHROPIC_BASE_URL uv run pytest <2 files> -o addopts=`)

| Command | Result |
|---|---|
| `test_credential_guard_server_key.py test_reachability_stage.py` | 46 passed |
| `test_target_probe.py test_run_unreachable_target.py` | 37 passed |
| `test_ui_auth_envkeys.py test_ui_auth_hardening.py` (AU21, unmodified) | 42 passed |
| `test_reachability_warning.py test_run_bounds_stop.py` (unmodified) | 14 passed |
| `test_role_accounts_routes.py test_role_accounts_rescope.py` | 29 passed |
| `test_credential_store_u11f.py test_state_sweep_u3b.py` | 37 passed |
| `test_credential_store_u11_routes.py test_platform_links.py` | 26 passed, 2 failed (`test_mp12_*`, see ruling 5) |
| `test_credential_store_u11.py` | 21 passed, 1 failed (`test_only_the_door_writes_secrets_and_no_crypto_exists`, see ruling 5) |
| `uv run ruff check src tests scripts` | All checks passed |
| `uv run autotester doctor > .work/doctor-chkA.txt` | exit 0, last line `doctor: clean` |
| `test_run_launcher_approval.py test_ui_runs.py` | 26 passed |

## Criteria

- **E7.1 PASS.** `ui/credential_guard.py:50` `held = (k for k in os.environ if k.upper() != MONGO_URI_ENV)`; `MONGO_URI_ENV` is defined once, `core/env.py:216` (`grep "MONGO_URI_ENV *="` finds one definition). `refuse_reserved_slug("pathlynks")` with only the URI set does not raise; onboarding `pathlynks` through the app returns 303 (my probe `test_onboard_clean_then_all_good`). `store/migrate_creds.py:60` is unchanged and still uses the same constant. The contract text "defined ONCE in `core/env.py`" is met by the existing constant; no new set was added (manifest call 1 accepted: `core/env.py` is at the 300-line cap and E5 owns it).
- **E7.2 PASS.** (a) URI + `PATHLYNKS_E2E_USER_PASSWORD` still refuses (mutants m2/cA1 killed). (b) AU21 suites unmodified and green (42). (c) `credential_guard.py:68-69` refuses the exact name, any case, with 403 (`refuse_foreign_key`), see ruling 3. (d) `mongo_uri()` resolved the URI after a `pathlynks` project existed in every one of my 29 probe cases (process variable); the maker's test covers the repo-root `.env` form.
- **E7.3 PASS.** `git diff -U0 70a7a486..HEAD -- src/autotester/ui/credential_guard.py` hunks: import (`:21`), `refuse_reserved_slug` (`:44`, `:50`), `refuse_foreign_key` (`:68`). Nothing else in the file changed; guard suites green.
- **E7.4 PASS.** `stages/reachability.py:140-160`. Direct call of `_failure_message` on a canary-laden exception per class: gaierror -> dns, `SSLCertVerificationError` -> tls, `RemoteDisconnected` -> http, `ConnectionRefusedError` -> tcp, `TimeoutError` -> timeout, `ValueError` and a non-unreachable `OSError` -> unknown; the canary (`10.9.8.7 QSECRET /path?x=1`) never appears. `HTTPException` is tested before `ConnectionError` (correct: `RemoteDisconnected` is both). Existing wording is kept as a prefix; `test_reachability_warning.py` and `test_run_bounds_stop.py` pass unmodified.
- **E7.5 PASS (vacuous).** The branch's commits do not touch `qa/issues.jsonl`. Note: `git show 70a7a486:qa/issues.jsonl` has no AT-1420 row at all (the row lives only in the uncommitted main checkout); the orchestrator should keep it `open` with the note "E7 gives the stage token; egress IP / allowlist is DevOps".

## Rulings requested

1. **Four test literals now end ` [stage=timeout]`: honest, nothing weakened.** `git diff` shows only the suffix added to `test_target_probe.py:33,104,188` and `test_run_unreachable_target.py:45`; each is still an equality assertion. I ran the master versions of both files against the branch source: exactly those 4 tests fail (`4 failed, 33 passed`), so "pass unmodified" is unsatisfiable for equality assertions once a suffix exists. The contract is internally inconsistent here (it says suffix, "substring", and unmodified); the checker should log an amendment: "equality pins carry the stage suffix". Not a maker defect.
2. **Lower-case store URI via `/env/add` gives 400, and it cannot be written anywhere.** `build_secret_ref` (`routes_project_edit.py:55`) refuses a non-UPPER_SNAKE key with 400 before `refuse_foreign_key`. My probe posted `pathlynks_mongo_uri`, `Pathlynks_Mongo_Uri`, full-width Unicode `PATHLYNKS_MONGO_URI`, and a NUL-suffixed name to `/projects/pathlynks/env/add`, `/projects/pathlynks/secrets`, `/projects/pathlynks/env` and `/onboard`: every one returned 400 or 403, with the canary value absent from the response and from `.env`, no declaration saved, `mongo_uri()` unchanged. The writers also independently require UPPER_SNAKE (`env_editor._KEY_RE`, `_check_pair`) and, with the credentials area on mongo, `_check_store_pair` refuses `key.upper() == MONGO_URI_ENV` (`env_editor.py:101`). Padded and tab/newline-suffixed exact names return 403.
3. **No project key can hijack or expose the real URI through a declaration route.** Probed with `PATHLYNKS_MONGO_URI` set in the process and a `pathlynks` project: `/onboard` (credential row), `/projects/pathlynks/env/add`, `/projects/pathlynks/secrets`, `/onboard/roles` (username and password key slots, new project) and `/projects/pathlynks/accounts` (existing project): all refused (403/400, role-account routes 400 with `"the store connection is set by the deployment, not in a project"`), nothing written, no declaration, `mongo_uri()` intact. A control role-accounts payload with benign keys returned 303, so the refusals are for the right reason. The "Test account login" block generates `<NS>USER_EMAIL`/`USER_PASSWORD` and so cannot name the URI. Every declaration route funnels through `build_secret_ref -> refuse_foreign_key` (`routes_project_edit.py:76`, `role_onboarding.py:185-188`). **One residual, W1 below.**
4. **The message holds no credential or URL query.** `probe_target` on base URLs `https://nx.invalid/signin?token=QSECRET123&pw=hunter2#frag` and `https://nx.invalid:8443/p/QPATH?k=QSECRET` returned `target nx.invalid could not be resolved (DNS) from this server [stage=dns]`: host only, no path, query, port, or exception text; a userinfo URL (`https://user:PWSECRET@nx.invalid/x`) is not probed at all (`None`, `host_of` returns empty).
5. **Pre-existing reds confirmed on master 70a7a486.** I exported master (`git archive`) and ran it in isolation: `test_platform_links.py::test_mp12_*` (both, `net::ERR_FAILED` to `a.localhost`) and `test_credential_store_u11.py::test_only_the_door_writes_secrets_and_no_crypto_exists` (`store/migrate_creds.py` calls `credential_collection(`) fail identically there. Neither touches a module this branch changed (`migrate_creds.py` is not in the diff).

## Mutation evidence (C7)

Maker's spec (`qa/evidence/e2e-fixes-e7/mutations.json`, 14 mutants) re-run by me with `scripts/mutation_check.py` plus 4 of mine: **17/18 killed.** All 14 maker mutants (m1, m2, m4-m15) KILLED. Mine: `cA1` exemption widened to every `PATHLYNKS_*` variable KILLED; `cB1` store-URI refusal tests the unstripped key (`key` instead of `name`) KILLED; `cB2` refusal returns instead of raising KILLED; **`cA2` exemption widened to any `*_URI` variable SURVIVED** (W2).

## Warnings (non-blocking; none is a contract criterion)

- **W1 (pre-existing on master, widened relevance).** `POST /projects/{slug}/env` (`routes_credentials.py:262-291`) refuses an undeclared key and `refuse_server_key`, but not the store URI. A project that *already* has `PATHLYNKS_MONGO_URI` in `project.json::secrets` (possible on master before this unit, because `refuse_foreign_key` had no such check) can overwrite the repo-root `.env` URI in file credential mode (probe: 303, `.env` overwritten; identical on master 70a7a486). New declarations are blocked by E7.2(c); a legacy one is not scrubbed. Suggested follow-up (separate unit, not E7): add the `MONGO_URI_ENV` check in `_check_pair`/`env_editor_submit`, or drop such a legacy declaration on load.
- **W2.** The tests do not pin that the slug-scan exemption is exactly one key: widening it to any `*_URI` variable (cA2) survives, because the only "project-shaped" fixture is `PATHLYNKS_E2E_USER_PASSWORD`. Adding a second fixture variable (for example `PATHLYNKS_E2E_API_URI`) would kill it. The contract's own mutation hint (whole-prefix filter) is killed.
- **W3.** The contract/test inconsistency in ruling 1 (suffix versus "pass unmodified") and the missing AT-1420 row in committed `qa/issues.jsonl` (E7.5) are checker-side bookkeeping, not maker defects.

## Not verified by me

Real public-host TLS/DNS failures (the tests use classified exceptions, a closed local port and `.invalid`); the full suite in one invocation (low-memory rule: 2 files per call); no `senior-software-engineer` review agent was dispatched.
