# Verdict - e2e-fixes-e3 (checker A, credentials/security seat)
Verdict: PASS (with 2 WARNINGs, no blocker)
Cycle checked: 0
Head tested: 5dcef390 (feat/e2e-e3), base dccc65e9. Contract: qa/contracts/e2e-fixes.md E3.1-E3.6. Worktree D:/autoTesting/.claude/worktrees/e2e-e3. No .env value read or printed; only generated test values used. No src/tests edits left behind (`git status` clean of tracked changes after every mutant).

## Evidence (all re-run by me; `env -u ANTHROPIC_BASE_URL uv run pytest <2 files> -o addopts= -q`)
- test_ui_test_account_login + test_ui_secrets_declaration: 26 passed. test_ui_env_labels + test_ui_env_editor: 14 passed, 1 skipped.
- Neighbours, all green: credential_safety + _project 29; credential_exemption + _scope 11; role_accounts_routes + role_onboarding 36; ui_project_intake + auth_envkeys 38; credential_store_u11_routes + auth_policy_table 12; credential_bidi + _transforms 24; credential_unicode + onboard_a11y 20.
- `uv run ruff check src tests scripts`: All checks passed. `uv run autotester doctor > .work/chkA_doctor.txt`: exit 0, last line "doctor: clean" (advisory D-087 warnings only).
- `git diff dccc65e9..HEAD -- src/autotester/ui/credential_guard.py`: empty (E3.5 guard untouched). No route added; auth policy table test passes unmodified; `/env/add` and `/secrets` stay `_CRED` (auth/policy.py:120).
- Maker mutants re-run with scripts/mutation_check.py: 13/13 KILLED (output .work/chkA/maker_mut.txt); each named test actually failed.

## My own checks (probe files in .work/chkA/, run with PYTHONPATH=tests -p conftest)
- P2 a letters-only password stored earlier, then pasted into the Key box of /secrets: 400, value absent from body+headers (known-value scan works).
- P3/P6 password inside the scope box (first submit) or in the onboarding Name box with a foreign scope: 400, password and email absent, nothing saved.
- P4 script/img payloads in domains and description on a refused /env/add: escaped in the redisplay.
- P5 /onboard with email only / password only: 400, the other value absent from body, headers, URL; project not created.
- P7 `block=login` with a smuggled `key`/`value`/`domains`: only the two generated keys are declared.
- P8 scope `vidysea.com` and `pathlynks.vidysea.com.evil.example`: 400. Default scope is `host_of(base_url)` (exact host), see F4.
- P9 with login gate ON: anon POST 401; tester 404 (project not visible); developer-owner 303; password never in any response. P10: a custom key value is shown to a viewer as before, the generated login email/password never are.
- E3.6, browser: server from the worktree on 127.0.0.1:18474 (AUTOTESTER_ROOT under .work/, AUTOTESTER_EPHEMERAL_OK=1, auth off), Playwright headless, seeded project with the two generated keys + one custom key. At 500px every Save button and value box lies inside the viewport (Save right edge x=121, value box right edge 434 of 500). At 1280px the layout is unchanged. Screenshot: qa/evidence/e2e-fixes-e3/checkerA-credentials-500px.png. Server stopped afterwards.

## Mutants I wrote
1. `redisplayable_key` returns `key.strip()` unconditionally (re-opens AT-068 echo): KILLED by tests/test_ui_secrets_declaration.py::test_a_rejected_key_is_never_echoed_back (1 failed, 25 passed).
2. `refuse_pasted_secrets` drops the values of this very submission (`fresh = {}`, routes_credentials.py ~line 103): SURVIVED the maker's tests and test_ui_credential_safety (29 passed); KILLED by my probes P3 and P6 (password echoed in the 400 page). See F1.
3. `theme.form_error` stops escaping (theme.py:122): survived tests and probe, because no submitted text reaches that message today (messages are fixed strings or an UPPER_SNAKE key name). Equivalent in effect now; defence-in-depth only (F5).

## Criteria
- E3.1 PASS. Bad key on /env/add and /secrets returns 400 with the site chrome, the rule text with the project namespace and example, typed key/domains/description kept, value canary absent, no pydantic text, nothing written (test + my P4).
- E3.2 PASS. Both pages carry one "Test account login" block (email-or-username text, masked password, autocomplete new-password); custom card retitled "(extra keys only)"; single `login_keys` definition (stages/role_onboarding.py:89), role-accounts pairing untouched.
- E3.3 PASS. Exactly `<NS>USER_EMAIL` / `<NS>USER_PASSWORD`, password masked, resubmit replaces (routes_credentials.py `_save_login` `kept`), no duplicates, neighbour-namespace claim still refused.
- E3.4 PASS (see F4). Scope defaults to the URL host, foreign scope refused inline on both pages, nothing saved.
- E3.5 PASS. No value in any response, header, URL or log (maker's test + P5/P6/P9/P10); credential_guard.py unchanged; its tests pass.
- E3.6 PASS for the credential controls (screenshot). See F6 for page-level overflow.

## Rulings on the maker's judgement calls
1. Generated login keys always write-only on the table: ACCEPT. The contract's E3.5 first sentence (no value in any render) and its "table as today" clause conflict for a credentials.view holder; the maker chose the fail-safe side and limited it to the two generated names (role_accounts_view.py `blind`). Mutant m8 pins it. Cost: a viewer cannot reveal the test login; the "Set" pill still shows status.
2. `redisplayable_key` regex `[A-Za-z][A-Za-z _-]{0,63}`: ACCEPT with WARNING F2.
3. Login block posting to the existing /env/add with hidden `block=login`: ACCEPT (no new route, permission row shared).
4. Email also `mask_in_screenshot=True`: ACCEPT (stricter than required, harmless).
5. /onboard inline 400 with typed fields: ACCEPT; the retry path scans every redisplayed field against the submitted email/password (app.py `_intake_login`).
6. E3.6 not screenshotted by the maker: done by me above.

## Findings
- F1 WARNING (test gap, behaviour correct). The "values of this very submission" half of `refuse_pasted_secrets` (routes_credentials.py ~99-108, the `fresh` dict) has no test: mutant 2 survives. Without it a password typed into the scope box on a first submit would be echoed in the 400 page. Maker m9 only removes the whole call. Owed: one test posting the password as `login_scope` on a project with no stored value (my P3) and one for /onboard (P6). Non-blocking because the code is right and my probes pin it today; fold into the next unit that touches these files.
- F2 WARNING (residual echo, accepted by E3.1). A refused Key box is shown again when it is letters, spaces, hyphens only (role_accounts_view.py `redisplayable_key`). On /secrets, which has no Value box, a pasted passphrase such as `correct horse battery` or `Sunshine` that is not yet stored comes back in the response body (P1 observed: echoed True; a digit-bearing entry is blanked). It reaches only the submitter and no log. AT-068's own test passes unmodified. Honouring AT-068 fully would contradict the contract's own example ("pathlynks password"), so not a defect against it.
- F3 INFO. `_save_login` saves project.json then `.env` (routes_credentials.py ~129-136), the same order as master's `env_add_credential`; there is no rollback. With the `.env` backend, `validate_env_values` runs first so a bad value saves nothing. With the credentials store on, store-only refusals (control character, deployment-secret key) are raised inside `save_credentials` after the declaration is saved, leaving declared-but-unset keys; resubmit repairs it. Read from code, not exercised (no store in this run). Not a regression.
- F4 INFO. Scope is accepted if inside `Project.allows_domain`, which admits subdomains of an allowed host (P8: `evil.pathlynks.vidysea.com` was accepted). Pre-existing `build_secret_ref` behaviour shared with the custom card; the secret itself still fills only on that exact host (`_host_matches`, AT-651), so the boundary is not widened. Default for generated keys is the exact URL host.
- F5 INFO. `form_error` escape is untested (mutant 3); safe today because no user text reaches it.
- F6 INFO. At 500px the document still scrolls horizontally (scrollWidth 713 vs 500) on /env, /projects/<slug> and /onboard; the only overflowing elements are the global top nav links, not the credential table (the diff does not touch the nav). The AT-1417 controls are reachable inside the viewport; the nav overflow is separate and pre-existing.
- F7 INFO. The "A login is saved already" hint shows when the keys are declared even if no value is stored (seeded case showed "Not set" pills). Wording only (role_accounts_view.py `account_login_card`, `declared`).
- Permission: I could not construct a principal who sees the project yet lacks credentials.edit (non-owners get 404, anon 401). Enforcement rests on the unchanged `_CRED` policy rows and the passing pinned policy-table test, not a direct 403 observation.

## Not done
Full suite not run (low-memory rule); the checker-B seat and the cross-unit sweep are not covered here.
