# Verdict (checker B) - mongo-store-u12 (session store, CRITICAL, dual)

**Cycle checked:** 0
**Verdict:** PASS (with 6 warnings; W1 is the one I would not carry past the G1 credentials/sessions flip)
**Checked:** worktree `.claude/worktrees/mongo-u12`, branch `feat/mongo-store-u12` head `93e6d4d2` (master `3c74e476` merged). Contract `qa/contracts/mongo-store.md` M38, M39, M40, M37, U12 row. Focus: wiring, lifecycle, file-mode equivalence. I did not read the other checker's verdict.
**Environment:** Windows, Git Bash, `env -u ANTHROPIC_BASE_URL`, `-o addopts=`, two test files per call, one call at a time, no full suite. No `.env` value read or printed. No `src/` or `tests/` edit. Scratch (probes, mutation spec) lives outside the repo in `.../scratchpad/chkB_u12/`.

## Commands run and results

| Command | Result |
|---|---|
| `uv run pytest tests/test_session_store_u12.py tests/test_session_store_u12_redaction.py -o addopts=` | `24 passed, 2 warnings`, rc 0 |
| `uv run pytest tests/test_store_outage_u9.py tests/test_credential_store_u11f.py -o addopts=` | `44 passed, 2 warnings`, rc 0 |
| `uv run ruff check src tests scripts` | `All checks passed!` rc 0 |
| `uv run autotester doctor` (redirected to a file) | `doctor: clean`, rc 0 (only non-blocking D-087 advisories) |
| `uv run python scripts/mutation_check.py qa/evidence/mongo-store-u12/mutations.json --repo .` | `24/24 mutations killed`, rc 0 (24 `KILLED` lines counted) |
| `wc -l` on the six edited src files | profiles 239, secrets 300 (cap, not over), mongo_routes 292, run_execution 299, multi_role_session 205, manual_login 50 (all <= 300) |
| Own mutation spec (6 wiring mutants, `scripts/mutation_check.py <spec> --repo .`) | B4, B5, B6 killed by other tests (the named test was a placeholder); **B1, B2, B3 SURVIVED with pytest exit 0** (see W1) |
| Own probe file (10 tests, `PYTHONPATH=tests uv run pytest <probe> -o addopts= -s`) | every behavioural probe below passed; prints quoted inline |

## What I verified (own probes, not the maker's tests)

1. **Store unset, nothing touched (M13, file-mode equivalence).** A subprocess with `AUTOTESTER_STORE`/`AUTOTESTER_STORE_AREAS` unset and a session whose `_context` and `secrets` raise on any attribute access: `capture_session`, `restore_session`, `load_session`, `save_session`, `forget_session`, `stored_session_values` returned `False False None None False {}`; afterwards `pymongo` and `gridfs` are not in `sys.modules` (`False False`). Cause: `profiles.py:60-68` `_collection` returns `None` before any store access; `capture_session :215` and `restore_session :227-231` return before using the context. The existing `tests/test_manual_login.py`, `tests/test_multi_role_session.py` still pass (manifest: 13 passed; my mutation runs include test_manual_login green on unmutated code).
2. **Restore points.** `multi_role_session.py:132` restores after `session.start()` on the account's own thread, keyed by `account.id`; on any exception the session is closed and the error re-raised (`:133-136`). `run_execution.py:178` restores `MAIN_ACCOUNT` only inside `if lent is None` (the shared-profile session). Probe: with a stored `_project` session, `_run_normal_cases` with `pool.lend() -> None` put cookie `sid` into the context (`normal run restored cookies: ['sid']`) and the value was masked in `secrets.redactor()`; with a lent entry session (`pl-entry-test` paths) the cookie list stayed `[]` and no new session was made.
3. **Entry runs never restore.** The entry pool (`run_execution.py:98-112`) never calls `restore_session`; `restore_session :229` additionally refuses any session whose `paths.slug` ends `-entry-test`. `orchestrate_execute._start_session` (`:111-127`) wipes the entry profile and has no restore call, entry or not. B6 (guard removed) is killed by `test_an_entry_run_never_restores_a_login`.
4. **Save points.** `multi_role_session.py:203` captures after `settle()` inside `_login` (role account id); `manual_login.py:48` captures under `MAIN_ACCOUNT` after the human returns, inside the `try` so `session.close()` still runs. Probe: manual login stored exactly `['pl|_project']`.
5. **Fail closed on outage, no crash, no leak.** Fake server `down=True`:
   - `RoleSessions.open()` -> `StoreUnavailable: state store unavailable (AutoReconnect)`; sessions closed; data-root tree hash unchanged; no URI/canary text.
   - `RoleSessions.sign_in` capture -> `StoreUnavailable state store unavailable (AutoReconnect)`; `role_session_port.login` turns it into `RoleLoginFailed` with the type name only.
   - `_run_normal_cases` -> case `ERRORED`, error `StoreUnavailable: state store unavailable (AutoReconnect)` (caught at `run_execution.py:182-183`, scrubbed), no cookie value, no URI.
   - `manual_login` after the human finishes -> raises `StoreUnavailable` (no value in text), window closed by `finally`.
6. **`drop_credentials` scope.** `env_editor.py:258-272`, `keys=None` path: `browser_sessions.delete_many({"p": slug})`. Probe with slugs `pl`, `pl-x`, `zz` each holding a session: `drop_credentials("pl")` left `['pl-x|t1', 'zz|t1']` (no prefix bleed). B4 (line removed) is killed by `test_removing_a_project_removes_its_sessions_only`.
7. **Expired / unreadable / foreign.** `profiles.py:136-145`: foreign `p` or id mismatch -> `None`, not deleted; expired, non-numeric `expires_at`, or non-dict `state` -> deleted; save refuses a foreign document (`:114-115`). Covered by `test_an_expired_state_is_deleted_and_never_restored`, `test_a_foreign_document_is_ignored_not_used_not_deleted_not_overwritten` (both ran green; mutants for them killed in the maker's 24/24).
8. **`_project` cannot collide.** `RoleAccount(id="_project")` and `id="t1|x"` both raise (probe `role id collisions refused`); `session_id` refuses `|` in slug or account (`profiles.py:54-57`); `ROLE_ACCOUNT_ID_PATTERN` is `^[a-z]...`.

## Findings

**W1 - Two of the four wiring points have no test at all (Warning, fix before the G1 flip).** Mutating `src/autotester/stages/manual_login.py:48` (delete the `capture_session` line, or capture under `'t1'`) and `src/autotester/ui/run_execution.py:178` (delete the `restore_session` line) leaves `tests/test_session_store_u12.py`, `tests/test_session_store_u12_redaction.py` and `tests/test_manual_login.py` fully green (`>>> SURVIVED B1/B2/B3 ... pytest exit 0 ... actually failed: (nothing)`). The maker's 24 mutants cover `multi_role_session` restore/save but none of these two, and the manifest does not disclose it. The code is correct today (probes 2 and 4 above pass), but M39 "a human-run login is saved after the human finishes" and the normal-run restore can be silently lost by a refactor. Needed: one test each (a `manual_login` call with a patched `BrowserSession` whose context holds a state, asserting `['pl|_project']`; a `_run_normal_cases` call with `lend() -> None` asserting cookies restored and a lent entry session not). My probe `test_run_execution_restore_wiring`, `test_run_execution_lent_entry_session_never_restored`, `test_manual_login_wiring` in `.../scratchpad/chkB_u12/probe_b.py` can be lifted nearly as is.

**W2 - Sign-in state is saved before the login is proven (Warning).** `multi_role_session.py:203` captures right after `settle()`; the proof (`role_probe.appears(signed_in_target)`) runs afterwards in `role_session_port.py:111-113`. A wrong password or a transient failure therefore stores an anonymous in-scope state and replaces a previously good document (`profiles.py:123`), or, with nothing in scope, deletes it (`:118-120`). Manifest judgement call 4 admits the missing signal. It is fail-safe for secrecy, not for usefulness. Suggest capturing from `RoleSessionPort.login` after `proven` is true.

**W3 - A malformed stored document breaks more than its own restore (Warning, low likelihood).** Probe: a document with `state.cookies = 5` makes `load_session` raise `TypeError` instead of being deleted as "unreadable" (`profiles.py:86`, `scope_state`); a document with a non-dict `localStorage` item makes `repo_redactor()` raise `AttributeError` (`session_values :171-172` via `stored_session_values :183-191`). `repo_redactor` is the run-wide redactor and the M8 write gate (`mongo_routes.py:189-197`), so one bad document can fail every gated write until it is removed by hand. Only a writer with direct database access can create it (Playwright output is well formed and `scope_state` drops non-dict cookies), hence Warning. Harden `scope_state`/`session_values` against non-list/non-dict shapes and let `load_session` delete such a document.

**W4 - `forget_session` has no caller (Warning).** `grep` finds no use outside `profiles.py` and the tests. There is no role-account delete route (`routes_role_accounts.py` only merges), no project delete route, and `drop_credentials(slug, [key])` for a removed SecretRef (`routes_project_edit.py:266`) deletes the `secrets` document but not the account's session, which then lives until `expires_at` (at most 24 h, `MAX_AGE_S`). M37/M39 "after an explicit logout/delete" has no live trigger today; the function and the `keys=None` project path are tested APIs, not wired behaviour. Acceptable now because those operations do not exist; record it so the first delete route calls them.

**W5 - Restore into a persistent profile can overwrite fresher cookies with older ones (Warning, not exercised with real Chromium).** Normal runs only restore (`run_execution.py:178`), so `add_cookies` can replace a cookie the profile refreshed since the last sign-in capture. Manifest items 5 and 7 touch this; not measured. Low impact in hosted mode (profile is empty), possible regression on a local profile that rotates tokens.

**W6 - The orchestrated path does not restore (Warning, functional gap, safe direction).** `orchestrate_execute.py:111-127` starts normal sessions without `restore_session`, so a login saved by `manual_login` or role sign-in is not reused there. Entry runs correctly never restore, which is the property M39 requires; the gap is only that non-entry orchestrated runs ignore the store. Manifest item 6 states this.

No Block-level finding. Secrecy properties I probed all hold: values reach `browser_sessions` only, cookies/origins outside `allowed_domains` are dropped on save and on restore (maker tests plus mutants 1-3 killed), restored and captured values join `session.secrets` and the run-wide redactor, outage text carries only the exception class, and file mode is a no-op.

## Judgement on the two items the brief asked about

- **Unwired `orchestrate_execute._start_session` restore:** accept. Not restoring is the safe direction for RU5; the cost is a missing convenience on one path (W6).
- **Normal runs never save:** accept. Saving after a normal run could persist a mid-run or post-failure state; the contract asks for saves after sign-in and after the human finishes only (M38, M39). Revisit with W5.

## Result

PASS, cycle 0, with W1-W6 recorded. Not merged, not pushed.
