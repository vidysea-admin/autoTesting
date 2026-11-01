# Manifest - e2e-fixes-e7

**Status:** checked-PASS (cycle 0, dual: A ea2cfb1b, B 3007a583)
**Fix cycle:** 0
**Contract:** `qa/contracts/e2e-fixes.md`, unit E7 (AT-1416, AT-1420 diagnostic). **Criticality:** MEDIUM (credential guard is a C5 surface).
**Authority:** no new `src/` module, no `qa/contracts/` edit, `core/env.py` NOT edited (see judgement call 1).
**Branch:** `feat/e2e-e7` (worktree `D:/autoTesting/.claude/worktrees/e2e-e7`), cut from master `70a7a486`. Not merged, not pushed.
**Base SHA:** `70a7a486`
**Code SHA:** the commit that adds this file, `git log -1 feat/e2e-e7`
**Criteria judged by E7:** E7.1, E7.2 (a)-(d), E7.3, E7.4, E7.5.

## What changed

| File | Kind | One job / change |
|---|---|---|
| `src/autotester/ui/credential_guard.py` (223 lines) | E in place | import `MONGO_URI_ENV` `:21`; `refuse_reserved_slug :39` scans `held = (k for k in os.environ if k.upper() != MONGO_URI_ENV)` `:50` instead of all of `os.environ`; `refuse_foreign_key :57` gains ONE check `:68-69` (`name.upper() == MONGO_URI_ENV` -> 403, "the store connection is set by the deployment, not in a project"). Hunks are only in those two functions plus the import (`git diff -U0`). |
| `src/autotester/stages/reachability.py` (227 lines) | E in place | `_failure_message :140` returns `target <host> <existing wording> from this server [stage=<dns\|tcp\|tls\|http\|timeout\|unknown>]`; `_UNREACHABLE_ERRNOS :133` (ENETUNREACH/EHOSTUNREACH, plus the WSA names where Python defines them); `import errno`. Existing wording for each class is unchanged. |
| `tests/test_target_probe.py`, `tests/test_run_unreachable_target.py` | E (pins, judgement call 2) | the 4 exact-equality assertions on the timeout message gained the ` [stage=timeout]` suffix; nothing else changed |
| `tests/test_credential_guard_server_key.py` (17) | N | E7.1, E7.2(a)-(d) |
| `tests/test_reachability_stage.py` (29) | N | E7.4 |
| `docs/SNAPSHOT.md` | regenerated (`autotester snapshot`) | one line (`D-125` -> `D-130 2026-11-01 decision ACTIVE`): pre-existing drift on master that `autotester doctor` flags as `stale-generated`/`stale-committed`; regenerated so doctor is clean. Sibling units regenerate the identical line. |
| `qa/evidence/e2e-fixes-e7/mutations.json`, `mutation-run.txt`, `mutation-run-first.txt` | N | C7 mutation spec and runs |

## Criteria map

| Crit | Code | Test (falsifier it kills) |
|---|---|---|
| E7.1 server-owned key no longer blocks the slug | `credential_guard.py:50` (`k.upper() != MONGO_URI_ENV`); the server-owned name is `core/env.py:216 MONGO_URI_ENV`, the single definition | `test_credential_guard_server_key.py::test_the_server_mongo_uri_does_not_block_the_slug_pathlynks` (monkeypatch `PATHLYNKS_MONGO_URI`; `refuse_reserved_slug("pathlynks")` does not raise); `::test_onboarding_pathlynks_succeeds_with_the_mongo_uri_in_the_environment` (POST `/onboard` -> 303, project exists); `::test_a_lower_case_spelling_of_the_name_does_not_block_either` (characterisation, equivalent mutant, see call 3). Mutant m1 (revert the filter) killed. |
| E7.2(a) project-shaped variable still refused | same line: ONE key filtered, not the prefix | `::test_a_project_shaped_variable_still_blocks_the_slug` (URI + `PATHLYNKS_E2E_USER_PASSWORD` -> 400). m2 (filter the whole prefix) killed. |
| E7.2(b) AU21 cases unchanged | provider keys and `SERVER_PREFIX` branches untouched | `tests/test_ui_auth_envkeys.py` + `tests/test_ui_auth_hardening.py` pass unmodified (42); `::test_a_slug_covering_a_server_key_is_still_refused_with_the_uri_set[anthropic,autotester,ollama,openai,gemini]`; `::test_a_slug_covering_another_held_variable_is_still_refused`. m7 (provider scan dropped) killed. |
| E7.2(c) the exempted key is not claimable | `credential_guard.py:68-69` | `::test_a_project_cannot_declare_the_store_uri_as_its_credential[exact, lower, padded]` (403 at the gate); `::test_env_add_refuses_the_store_uri_with_no_write_and_no_declaration[PATHLYNKS_MONGO_URI-403]` (through `/projects/pathlynks/env/add`: 403, canary absent from response and `.env`, no declaration). m4 (check removed), m5 (case-sensitive), m6 (400 instead of 403) killed. |
| E7.2(d) `mongo_uri()` unaffected | `core/env.py` not edited | `::test_mongo_uri_still_resolves_after_a_pathlynks_project_exists` (process variable, then repo-root `.env`) |
| E7.3 secret-paste rules untouched | `git diff -U0` hunks: import, `refuse_reserved_slug`, `refuse_foreign_key` only | guard suites unmodified and green (Verify) |
| E7.4 stage token | `reachability.py:140-158` | `test_reachability_stage.py::test_each_failure_class_carries_its_stage_token_and_keeps_its_wording[13 classes]` (gaierror->dns; refused/reset/ENETUNREACH/EHOSTUNREACH->tcp; SSLError and SSLCertVerificationError->tls; RemoteDisconnected/BadStatusLine->http; URLError(TimeoutError)/TimeoutError->timeout; ValueError/URLError(str)->unknown); `::test_the_message_names_only_the_host[13]` (canary IP and exception text absent); `::test_a_closed_local_port_is_stage_tcp`; `::test_an_unresolvable_name_is_stage_dns`; `::test_the_token_reaches_the_run_every_case_and_the_page_message` (through `launch_run`: `Run.preflight_warnings == [message]`, every verdict note carries it, no browser). m8-m15 killed. |
| E7.4 existing wording and tests | wording strings kept; suffix only | `test_reachability_warning.py`, `test_target_probe.py`, `test_run_unreachable_target.py`, `test_run_bounds_stop.py` pass (see call 2 for the 4 equality pins) |
| E7.5 AT-1420 stays open | n/a | `qa/issues.jsonl` is not touched by this branch's commit; AT-1420 is infrastructure (egress IP/allowlist, DevOps). **This unit does not close it**; the first live run after it lands names the failing stage. |

## Things the checker should look at (judgement calls)

1. **`core/env.py` was not edited.** The contract's "server-owned set defined once in `core/env.py`" is `MONGO_URI_ENV` itself (`core/env.py:216`, the contract says "today exactly `core/env.py::MONGO_URI_ENV`"); the guard imports it and compares directly, so no second definition or new set exists (`grep MONGO_URI_ENV src` finds one definition). `core/env.py` is at the 300-line cap and E5 owns edits to it, so adding a named tuple there would have broken doctor or collided. `store/migrate_creds.py:60` is behaviourally unchanged (still `key.upper() == MONGO_URI_ENV or is_server_key(key)`); it was not edited.
2. **Four exact-equality pins gained the suffix.** The contract says the E4 tests "pass unmodified" because the token is a suffix, but `test_target_probe.py:33,104,188` and `test_run_unreachable_target.py:45` assert `message == "..."` / `preflight_warnings == [message]`. A suffix on a message that reaches `preflight_warnings` cannot satisfy equality, so those four literals now end ` [stage=timeout]`. No assertion was weakened (still equality). `test_run_bounds_stop.py:112` builds its own message and was untouched.
3. **Case-insensitivity of the exemption is not observable.** The slug scan's `k.startswith(ns)` is case-sensitive and `ns` is upper-case, so a lower-case held variable could never collide; removing `.upper()` from the filter is an equivalent mutant (mutant m3 was dropped from the spec; first run `mutation-run-first.txt` shows it survived). The `.upper()` follows the contract's wording and `is_server_key`. The test kept is a characterisation (plain dict standing in for a case-sensitive environment; Windows folds `os.environ` keys).
4. **E7.2(c) "lower-case `/env/add` -> 403" is 400 through the route.** `build_secret_ref` (`ui/routes_project_edit.py`, E3's) refuses a non-UPPER_SNAKE_CASE key with 400 before `refuse_foreign_key` runs, so `pathlynks_mongo_uri` never reaches the 403 check there; nothing is written or declared either way (pinned: 400, canary absent, no declaration). The 403 for the lower-case/padded spelling is pinned at `refuse_foreign_key` itself. Closing the gap through the route would mean editing E3's file.
5. **`ConnectionError` classification.** `http.client.RemoteDisconnected` is both an `HTTPException` and a `ConnectionResetError`; the contract puts "closed before an HTTP answer" in `http`, so `HTTPException` is checked before `ConnectionError` (m11). A plain `ConnectionError` (reset/aborted) stays `tcp` with the old "closed the connection" wording. A generic `OSError` without an unreachable errno stays `unknown`.
6. **Windows errnos.** `_UNREACHABLE_ERRNOS` is built with `hasattr`, so `WSAENETUNREACH`/`WSAEHOSTUNREACH` are included only where Python defines them.
7. **`docs/SNAPSHOT.md` regenerated** (not this unit's file; a one-line generated change, identical in every sibling).
8. **Not done / not verified**: the full suite in one invocation (low-memory rule). `tests/test_platform_links.py::test_mp12_*` (2 tests) fail here with a real-Chromium `net::ERR_FAILED` to `a.localhost`; they touch neither changed module and I did not confirm against bare master (no second tree, memory). No `senior-software-engineer` review agent was dispatched (the brief forbids dispatching agents). Real TLS/DNS failures on public hosts were not exercised: tests use classified exceptions, the local closed port and the reserved `.invalid` name.

## Verify (run in `D:/autoTesting/.claude/worktrees/e2e-e7`, `PYTHONPATH=<worktree>/src`, `env -u ANTHROPIC_BASE_URL uv run pytest <2 files> -o addopts=`)

```
tests/test_credential_guard_server_key.py tests/test_reachability_stage.py   -> 46 passed (25 failed before the change)
tests/test_target_probe.py tests/test_run_unreachable_target.py              -> 37 passed
tests/test_reachability_warning.py tests/test_run_bounds_stop.py             -> 14 passed
tests/test_ui_auth_envkeys.py tests/test_ui_auth_hardening.py                -> 42 passed (unmodified)
tests/test_state_sweep_u3b.py tests/test_credential_store_u11f.py            -> 37 passed
tests/test_run_launcher_approval.py tests/test_ui_runs.py                    -> 26 passed
tests/test_role_accounts_routes.py tests/test_role_accounts_rescope.py       -> 29 passed
tests/test_credential_store_u11_routes.py (+ test_platform_links.py)         -> 26 passed, 2 failed (test_platform_links mp12, real browser, call 8)
uv run ruff check src tests scripts                                          -> All checks passed!
autotester snapshot; autotester doctor (> .work/doctor-e7b.txt)              -> only stale-committed SNAPSHOT.md before the commit; clean after (checker to confirm)
```

## Mutation evidence (C7)

`uv run python scripts/mutation_check.py qa/evidence/e2e-fixes-e7/mutations.json` -> **14/14 killed** (`mutation-run.txt`). The first run (`mutation-run-first.txt`) was 13/15: m3 (equivalent mutant, call 3, dropped) and m7 (its kills list named the `anthropic` case, which another `ANTHROPIC_*` variable in the test process also refuses, so the provider-key scan is not the only thing killing it; the list was narrowed to the `gemini`, `ollama`, `openai` cases that failed). 14 mutants over the guard (filter reverted, whole prefix filtered, foreign-key check removed, case-sensitive, wrong status, provider scan dropped) and the stage mapping (tls, dns, timeout, HTTPException order, errnos, fallthrough, exception text in message, token dropped).
