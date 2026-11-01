# Verdict (checker B, dual check) - e2e-fixes-e3 (AT-1417, AT-1418)

**Verdict: PASS**
**Cycle checked: 0**
**Branch / head:** `feat/e2e-e3` @ `5dcef390`, base `dccc65e9`. Worktree `D:/autoTesting/.claude/worktrees/e2e-e3`.
**Judged against:** `qa/contracts/e2e-fixes.md` E3.1-E3.6 and `qa/manifests/e2e-fixes-e3.md`.
**Focus (B):** adversarial / credentials security. No `.env` value was read or printed; every value below is a generated canary. My scratch is `.work/chkb/` (not committed).

## Commands and results (all re-run by me)

| Command (worktree, `env -u ANTHROPIC_BASE_URL`, `-o addopts=`, 2 files per call) | Result |
|---|---|
| `pytest tests/test_ui_test_account_login.py tests/test_ui_secrets_declaration.py` | 26 passed |
| `pytest tests/test_ui_env_labels.py tests/test_ui_env_editor.py` | 14 passed, 1 skipped |
| `pytest tests/test_ui_credential_safety.py tests/test_ui_credential_safety_project.py` | 29 passed |
| `pytest tests/test_ui_auth_policy_table.py tests/test_ui_auth_envkeys.py` | 25 passed |
| `pytest tests/test_role_accounts_routes.py tests/test_role_accounts_rescope.py` | 29 passed |
| `pytest tests/test_ui_project_intake.py tests/test_ui_onboard_a11y.py` | 18 passed |
| `pytest tests/test_ui_project_edit.py tests/test_ui_error_pages.py` | 22 passed |
| `pytest tests/test_ui_credential_exemption.py tests/test_ui_credential_exemption_scope.py` | 11 passed |
| `pytest tests/test_role_onboarding.py tests/test_credential_store_u11_routes.py` | 26 passed |
| `pytest tests/test_ui_credential_bidi.py tests/test_ui_credential_transforms.py` | 24 passed |
| `pytest tests/test_ui_credential_unicode.py tests/test_ui_auth_escalation.py` | 38 passed |
| `uv run ruff check src tests scripts` | All checks passed! |
| `uv run autotester doctor > .work/chkb/doctor.txt` | exit 0, last line `doctor: clean` (advisory decision-citation warnings only) |
| `git diff --stat dccc65e9..HEAD -- src/autotester/ui/credential_guard.py` (maker diff stat) | file absent from the diff: guard untouched (E3.5) |

The full suite was not run (low-memory rule).

## Mutation testing (`scripts/mutation_check.py`; it works on a copy outside the repo; spec `.work/chkb/mut.json`)

Result: 7/9 killed. Maker mutants re-run by me, all KILLED: m1 (key shape pre-check), m4 (resubmit duplicates), m7 (half login accepted), m8 (login keys prefilled for a view holder), m9 (pasted secret not scanned on /env/add), m13 (foreign scope accepted for login keys).
My own mutants:
- X1 `redisplayable_key` echoes any key text (AT-068 narrowing removed): KILLED by `test_a_rejected_key_is_never_echoed_back`. The regex is pinned.
- X2 `_save_login` skips `validate_env_values`: **SURVIVED** (W3). No test sends a login value that `.env` cannot hold.
- X3 `_intake_login` drops `refuse_pasted_secrets` on `/onboard`: **SURVIVED** (W3). The pasted-secret refusal is tested only on the Credentials page.

## Adversarial probes (TestClient, signed-in admin, canary values; `.work/chkb/adv.py`: 72 PASS, the 3 "FAIL" lines were my own wrong expectations, see below)

- Scope tricks on the login block, all refused 400, nothing declared, no `.env` written, no value echoed: `pathlynks.vidysea.com.evil.com`, `evilpathlynks.vidysea.com`, `vidysea.com` (parent), `*.vidysea.com`, `https://pathlynks.vidysea.com`, `pathlynks.vidysea.com:443`, `pathlynks.vidysea.com.` (trailing dot), `pathlynks.vidysea.com, evil.example`, backslash-userinfo form, tab-joined host. `PATHLYNKS.Vidysea.COM` is accepted and stored lowercased; ` .pathlynks.vidysea.com` normalises to the same host (those two were my mistaken "should refuse" expectations; neither widens anything, `Project.allows_domain` and `browser/secrets.py::_host_matches` are unchanged).
- Key names via `/env/add` and `/secrets`: lowercase, spaces, hyphen, full-width, accented, 70-char, NUL, `;`, `<script>`, `'><img onerror>`: each a plain 400 with the new message, no raw pydantic text, no unescaped markup. Server keys (`OPENAI_API_KEY`, `AUTOTESTER_APPROVAL_KEY`) stay 403. A key with leading whitespace or a trailing newline around a valid name is stripped and accepted (same as before; my third "FAIL").
- Value injection: email or password holding a newline or CRLF plus `AUTOTESTER_APPROVAL_KEY=x` / `X=1` -> 400, nothing declared, `.env` untouched. A password holding both quote characters, a tab or NUL is stored without injection; `.env` afterwards held only the two generated keys.
- After a real save, GET `/projects/<slug>/env`, `/edit`, `/onboard`, `/onboard/roles`, `/projects/<slug>`, `/`, `/accounts`: neither stored value appears. Stored password or email forced into key, description, domains, login_scope on every 400 path of `/env/add`, `/secrets` and `/onboard`: no echo except W4. Logger capture at DEBUG: no value in the log.
- Onboarding: lookalike scope -> 400 inline, project not created; password pasted in the scope box -> refused, not echoed, project not created; half login -> 400 inline, nothing saved; wholly empty login still creates a login-less project (303); a custom row colliding with a generated key -> 400.
- Permission: `("POST", "/projects/{slug}/env/add")` stays `_CRED` (`credentials.edit`) in `src/autotester/auth/policy.py:120`; no route added; the policy-table and escalation tests pass unmodified.

## Criteria

- **E3.1 PASS.** Bad key re-renders with site chrome and the plain sentence naming `PATHLYNKS_E2E_` and an example (`routes_project_edit.py:58-62`); typed key, domains and description kept; value never echoed; project unchanged on disk. Real browser at 500px: message shown, typed key kept, `GeneratedValue-0042` not echoed, no `String should match pattern` (`qa/evidence/e2e-fixes-e3/bad-key-500px.png`).
- **E3.2 PASS.** Both pages carry one "Test account login" block (email-or-username text input, masked `autocomplete=new-password` password, scope); the custom card remains, retitled "extra keys only". One `login_keys` definition (`stages/role_onboarding.py:89`).
- **E3.3 PASS.** Exactly `PATHLYNKS_E2E_USER_EMAIL` / `PATHLYNKS_E2E_USER_PASSWORD`; resubmit replaces (`routes_credentials.py:135`), no duplicates; `refuse_foreign_key` runs through `build_secret_ref` (`routes_project_edit.py:76`); longer neighbour namespace still refused.
- **E3.4 PASS.** Scope defaults to `host_of(base_url)` (`routes_credentials.py:121`); the onboarding field follows the URL host until edited (browser-verified: `pathlynks.vidysea.com`); outside allowed domains refused inline.
- **E3.5 PASS** (with W1 and W4). Values never echoed on any path I could build; guard file unchanged; guard tests green.
- **E3.6 PASS (note I1).** Real app from this worktree on a free loopback port (`AUTOTESTER_ROOT` under `.work/`, `AUTOTESTER_EPHEMERAL_OK=1`, auth disabled, loopback only), Chromium headless at 500px (`qa/evidence/e2e-fixes-e3/credentials-500px.png`). Measured: both Save buttons at x=65.8..121.1 (viewport 500), rows stacked, zero elements inside `.cred-table` extend past x=501, Save is the hit-test target once scrolled to centre, clicking it posts to `/projects/<slug>/env` (absolute action, so it also works from the `/env/add` 400 page) and redirects without echoing the typed value.

## Findings

**W1 (WARNING, functional) - the new submitted-value scan refuses legitimate logins whose password or username is a substring of the scope host, with a bare JSON dead end.** `routes_credentials.py:99-108` (`refuse_pasted_secrets`) adds the submitted email and password to a throwaway `SecretStore` and runs `_refuse_unsafe_submission` on the scope. The exempt rule covers only a value equal to a stored field, so the joined-text check at the end of `_refuse_unsafe_submission` (`credential_guard.py`) trips. Reproduced: login block, scope `pathlynks.vidysea.com` (the prefilled default), password `vidysea`, `com` or `pathlynks` -> `400 {"detail":"a real credential appears to be split across the scope..."}` (bare error page, not the inline form). A username such as `pathlynks` takes the same path. It fails closed and is rare, but it is the dead-end shape AT-1417 removes. Suggested fix for the maker: scan only fields that are re-displayed, and skip the scope when it equals the URL-host default.

**W2 (WARNING) - no rollback of the project declaration when the `.env` write fails.** `_save_login` order is `validate_env_values` -> `store.save_project` -> `save_credentials` (`routes_credentials.py:136-139`); `_save_custom` likewise. I forced `save_credentials` to raise `InvalidEnvValue` after validation: response 400, yet both keys stay declared (`PATHLYNKS_E2E_USER_EMAIL`, `PATHLYNKS_E2E_USER_PASSWORD`, shown "Not set"). Same order as master (`env_add_credential`) and `/onboard`, so not a regression. In file mode `validate_env_values` makes the failure unreachable except for I/O errors; in credential-store mode `_check_store_pair` can still refuse afterwards (control character, connection string), and the inline 400 then implies "nothing saved". The brief's ".env first with rollback" is not what the code does.

**W3 (WARNING, test gap) - mutants X2 and X3 survive.** No test posts a login value `.env` cannot hold (newline) and asserts nothing is declared, and the `/onboard` pasted-secret refusal has no test. Behaviour is correct today (probed above); the pins are missing.

**W4 (LOW) - the re-render `typed` dict is not limited to the active block's fields.** `routes_credentials.py` (the `typed = {...}` lines at the end of `env_add_credential`) redisplays `domains`, `description`, `login_scope` and a letters-only `key` from the request whichever block was posted, while the scan list covers only that block's fields. A forged request can make the 400 page reflect a stored value it already knows (reproduced: block=login with the stored password in `description`). It discloses nothing the sender did not supply and the browser forms cannot produce it, so I do not block on it.

**I1 (INFO) - page-level horizontal scroll at 500px comes from the site nav, not this unit.** `scrollWidth` is 713 vs 500 on `/` (718), `/onboard` and the Credentials page alike; the first overflowing elements are `NAV` and `A.nav-live`. Nothing in `.cred-table` overflows. Outside E3's files; file separately if wanted.

## Rulings on the maker's judgement calls

1. **Generated login keys always write-only, even for a `credentials.view` holder: ACCEPT.** E3.5 requires the two values to appear in no response and also says `show_values` stays as today for the existing table; both cannot hold for these two keys and the stricter reading is the safe one. Pinned by m8. The narrowing is limited to `login_keys(slug)` in `env_table`; other keys behave as before.
2. **`redisplayable_key` regex `[A-Za-z][A-Za-z _-]{0,63}`: ACCEPT.** Text with digits or symbols (most tokens) is blanked. Letters-only text can come back, but a letters-only stored value is refused before display by the scan (key = stored password -> 400 bare, no echo), and anything merely typed returns only to its typist, escaped. The AT-068 test and my mutant X1 pin it.
3. **Login block posts to the existing `/env/add` with `block=login`: ACCEPT.** No new route, policy row unchanged, `credentials.edit` still required.
4. **View functions in `role_accounts_view.py`: ACCEPT** (no new module; `env_editor_view` stays put).
5. **Email masked in screenshots too: ACCEPT** (more private, no contract conflict).
6. **/onboard inline 400: ACCEPT** (saves nothing on a foreign scope or half login; typed non-secret fields kept; values never redisplayed). See W1 and X3.
7. **E3.6 not screenshotted by the maker: superseded** by my screenshot.

## Disposition

PASS for cycle 0 from checker B: no secret value is rendered, prefilled, logged or echoed on any path tested; exact-host scoping and `credentials.edit` are intact; nothing is saved on a half login or foreign scope. W1-W3 are non-blocking recommendations; they are not failures of E3.1-E3.6.

**Artifacts:** `qa/evidence/e2e-fixes-e3/credentials-500px.png`, `qa/evidence/e2e-fixes-e3/bad-key-500px.png`.
