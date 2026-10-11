# t204-team-login seat A sub-checker: falsification (aa6fec2e)

Each mutant: one single-hunk edit of one file in a throwaway copy (`t204A-row-<id>-m<k>`, copied from a pristine copy of src/ tests/ scripts/ docs/ docker/ + config; no .git/.venv/.env), run with the worktree venv, `PYTHONPATH=<copy>/src`, cwd=rootdir=copy, PYTHONDONTWRITEBYTECODE=1. `autotester.__file__` printed per row (column proof). Logs: `falsification-logs/<row>-green.txt|-red<k>.txt`.


| row | autotester.__file__ inside the copy | file edited | edit | green (p/f) | red-after (p/f/err) | failing assertion | verdict |
|---|---|---|---|---|---|---|---|
| AU1 | True | `src/autotester/auth/passwords.py` | weak argon2 cost (t=1, m=1 MiB) | 1/0 | 0/1/0 | E   AssertionError: assert (1024 >= (19 * 1024)) / E    +  where 1024 = int('1024') | VERIFIED |
| AU1 | True | `src/autotester/auth/passwords.py` | store the password as given | 1/0 | 0/1/0 | E   AssertionError: <!doctype html><title>Sign in — AutoTester</title> / E   <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin> | VERIFIED |
| AU2 | True | `src/autotester/ui/routes_auth.py` | unknown email gets a distinct body ('No such user.') | 1/0 | 0/1/0 | E   assert 2 == 1 / E    +  where 2 = len({b'<!doctype html><title>Sign in \xe2\x80\x94 AutoTester</title>\n<link rel="preconnect" href="https://fonts.gstatic.c...utton></form><p style=\'margin-top:14 | VERIFIED |
| AU3 | True | `src/autotester/ui/routes_auth.py` | session cookie loses HttpOnly | 1/0 | 0/1/0 | E   AssertionError: assert ('httponly' in 'at_session=<redacted>; max-age=43200; path=/; samesite=lax') | VERIFIED |
| AU3b | True | `src/autotester/auth/sessions.py` | expiry check dropped from session lookup | 4/0 | 3/1/0 | E   AssertionError: assert 200 == 401 / E    +  where 200 = <Response [200 OK]>.status_code | VERIFIED |
| AU4 | True | `src/autotester/ui/routes_auth.py` | logout route no longer ends the server-side session | 1/0 | 0/1/0 | E   AssertionError: assert 200 == 401 / E    +  where 200 = <Response [200 OK]>.status_code | VERIFIED |
| AU5 | True | `src/autotester/auth/ratelimit.py` | per-address limit check removed | 1/0 | 0/1/0 | E   AssertionError: assert False / E    +  where False = blocked('fresh@x.test', '9.9.9.9') | VERIFIED |
| AU6 | True | `src/autotester/auth/passwords.py` | minimum password length 10 -> 1 | 1/0 | 0/1/0 | E   AssertionError: assert 303 == 400 / E    +  where 303 = <Response [303 See Other]>.status_code | VERIFIED |
| AU6b | True | `src/autotester/ui/auth_middleware.py` | zero-permission check in the gate removed | 1/0 | 0/1/0 | E   AssertionError: ('GET', '/', 200) / E   assert 200 == 403 | VERIFIED |
| AU7 | True | `src/autotester/auth/accounts.py` | hosted + unset FIRST_ADMIN_EMAIL promotes the first signup (like local) | 11/0 | 8/3/0 | E   AssertionError: assert ['Admin/CEO'] == [] / E | VERIFIED |
| AU7 | True | `src/autotester/auth/config.py` | fixed email compared case-sensitively | 11/0 | 10/1/0 | E   AssertionError: assert [] == ['Admin/CEO'] / E | VERIFIED |
| AU8 | True | `src/autotester/auth/accounts.py` | admin password reset keeps the user's sessions | 1/0 | 0/1/0 | E   AssertionError: assert 200 == 401 / E    +  where 200 = <Response [200 OK]>.status_code | VERIFIED |
| AU9 | True | `src/autotester/auth/db.py` | last-admin guard ignores 'enabled' (disable allowed) | 1/0 | 0/1/0 | E   AssertionError: assert 303 == 400 / E    +  where 303 = <Response [303 See Other]>.status_code | VERIFIED |
| AU10 | True | `src/autotester/ui/routes_admin.py` | group delete skips the confirm/how-many-members step | 1/0 | 0/1/0 | E   assert (303 == 200) / E    +  where 303 = <Response [303 See Other]>.status_code | VERIFIED |
| AU11 | True | `src/autotester/auth/db.py` | seed runs every start with REPLACE (resets edits) | 1/0 | 0/1/0 | E   AssertionError: assert (['comment.cre....view@shared'] == ['live.view'] / E | VERIFIED |
| AU12 | True | `src/autotester/auth/access.py` | 'assigned' scope always true | 20/0 | 16/4/0 | E   AssertionError: assert True == ('owner' in {'assigned'}) / E    +  where True = authorize(Principal(user_id=1, email='me@team.test', display_name='', permissions=frozenset({'live.view', 'project.r | VERIFIED |
| AU13 | True | `src/autotester/ui/auth_middleware.py` | unviewable project answers 403 instead of the missing-project 404 | 2/0 | 1/1/0 | E   AssertionError: ('sub', 'beta') / E   assert 403 == 404 | VERIFIED |
| AU14 | True | `src/autotester/ui/auth_middleware.py` | route with no policy row is let through | 1/0 | 0/1/0 | E   AssertionError: assert 200 == 403 / E    +  where 200 = <Response [200 OK]>.status_code | VERIFIED |
| AU15 | True | `src/autotester/ui/routes_crawls.py` | admin (project.run@all) gets a different refusal than a developer | 1/0 | 0/1/0 | E   assert 200 == 403 / E    +  where 200 = <Response [200 OK]>.status_code | VERIFIED |
| AU16 | True | `src/autotester/auth/policy.py` | GET / becomes public | 1/0 | 0/1/0 | E   AssertionError: ('GET', '/', 200) / E   assert 200 == 401 | VERIFIED |
| AU16b | True | `src/autotester/ui/auth_middleware.py` | safe_next accepts //host | 6/0 | 5/1/0 | E   AssertionError: assert ('evil.example' not in '<!doctype h.../main></div>' / E | VERIFIED |
| AU17 | True | `src/autotester/auth/config.py` | auth-disabled honoured even when hosted | 1/0 | 0/1/0 | E   assert not True / E    +  where True = auth_disabled() | VERIFIED |
| AU18 | True | `src/autotester/ui/helpers.py` | Origin port-numeric check removed | 3/0 | 0/3/0 | E   assert (303 == 403) / E    +  where 303 = <Response [303 See Other]>.status_code | VERIFIED |
| AU18b | True | `src/autotester/ui/helpers.py` | repeated Origin header allowed | 2/0 | 2/0/0 |  | SURVIVED |
| AU19 | True | `src/autotester/ui/helpers.py` | loopback host test becomes a prefix match | 3/0 | 1/2/0 | E   assert (200 == 403) / E    +  where 200 = <Response [200 OK]>.status_code | VERIFIED |
| AU20 | True | `src/autotester/auth/config.py` | hosted allow-list key misspelt in the startup check | 1/0 | 1/0/0 |  | SURVIVED |
| AU21 | True | `src/autotester/ui/routes_credentials.py` | every signed-in user may view credential values | 1/0 | 0/1/0 | E   AssertionError: sub / E   assert ('Sentinel-Value-93ad1c' in '<!doctype html><title>Vault — credentials — AutoTester</title>\n<link rel="preconnect" href="https://fonts.gstatic.co...d\'><h2>Approv | VERIFIED |
| AU22 | True | `src/autotester/ui/auth_middleware.py` | audit path field holds the full URL incl. query | 1/0 | 0/1/0 | E   assert ('Query-Canary-77' not in '{"ts": "202...tus": 303}\n' / E | VERIFIED |
| AU23 | True | `.dockerignore` | root '.auth/' line dropped from .dockerignore | 1/0 | 0/1/0 | E   AssertionError: assert ('.auth/' in ['# Contract: qa/contracts/docker.md D6 -- `.env`, `projects/` and `profiles/` are bind-mounted', '# from the host and..., '# snapshots) would ship inside every | VERIFIED |
| AU25 | True | `src/autotester/ui/auth_middleware.py` | 'member' routes (/, favicon) refused for an authorised admin | 18/0 | 18/0/0 |  | SURVIVED |
| AU27a | True | `src/autotester/auth/access.py` | users.manage holder may touch an Admin account | 1/0 | 0/1/0 | E   AssertionError: password / E   assert 303 == 403 | VERIFIED |
| AU27b | True | `src/autotester/auth/access.py` | held-permission check skipped (_held always true) | 1/0 | 0/1/0 | E   AssertionError: Peek / E   assert 303 == 403 | VERIFIED |
| AU27c | True | `src/autotester/auth/access.py` | non-admin holder may grant admin-only keys | 1/0 | 0/1/0 | E   AssertionError: settings.manage / E   assert 303 == 403 | VERIFIED |
| AU27d | True | `src/autotester/auth/access.py` | Admin/CEO membership change not admin-only | 1/0 | 1/0/0 |  | SURVIVED |
| AU20b | True | `src/autotester/auth/config.py` | hosted allow-list startup check disabled entirely | 1/0 | 0/1/0 | E   Failed: DID NOT RAISE AuthConfigError | VERIFIED |
| AU25b | True | `src/autotester/ui/auth_middleware.py` | 'member' routes (/, favicon) refused for an authorised admin | 12/0 | 10/2/0 | E   assert 403 == 200 / E    +  where 403 = <Response [403 Forbidden]>.status_code | VERIFIED |
| AU27e | True | `src/autotester/auth/access.py` | Admin/CEO membership change not admin-only (whole p5 set + au10 escalation) | 10/0 | 9/1/0 | E   AssertionError: groups / E   assert 400 == 403 | VERIFIED |
| AU3c | True | `src/autotester/auth/sessions.py` | server-side session lifetime x1000 | 10/0 | 10/0/0 |  | SURVIVED |
| AU18c | True | `src/autotester/ui/helpers.py` | repeated Host header allowed | 2/0 | 1/1/0 | E   assert (303 == 403) / E    +  where 303 = <Response [303 See Other]>.status_code | VERIFIED |
| AU23b | True | `.gitignore` | .gitignore loses '.auth/' | 3/0 | 3/0/0 |  | SURVIVED |
| AU13b | True | `src/autotester/auth/access.py` | project list shows every project (visible_slugs filter off) | 1/0 | 0/1/0 | E   assert ("/projects/beta'" not in '<!doctype h.../main></div>' / E | VERIFIED |

## Per-criterion roll-up

| AU | mutants | verdict |
|---|---|---|
| AU1 | AU1:VERIFIED, AU1:VERIFIED | VERIFIED |
| AU2 | AU2:VERIFIED | VERIFIED |
| AU3 | AU3:VERIFIED, AU3b:VERIFIED, AU3c:SURVIVED | VERIFIED (with survivor mutants listed) |
| AU4 | AU4:VERIFIED | VERIFIED |
| AU5 | AU5:VERIFIED | VERIFIED |
| AU6 | AU6:VERIFIED, AU6b:VERIFIED | VERIFIED |
| AU7 | AU7:VERIFIED, AU7:VERIFIED | VERIFIED |
| AU8 | AU8:VERIFIED | VERIFIED |
| AU9 | AU9:VERIFIED | VERIFIED |
| AU10 | AU10:VERIFIED | VERIFIED |
| AU11 | AU11:VERIFIED | VERIFIED |
| AU12 | AU12:VERIFIED | VERIFIED |
| AU13 | AU13:VERIFIED, AU13b:VERIFIED | VERIFIED |
| AU14 | AU14:VERIFIED | VERIFIED |
| AU15 | AU15:VERIFIED | VERIFIED |
| AU16 | AU16:VERIFIED, AU16b:VERIFIED | VERIFIED |
| AU17 | AU17:VERIFIED | VERIFIED |
| AU18 | AU18:VERIFIED, AU18b:SURVIVED, AU18c:VERIFIED | VERIFIED (with survivor mutants listed) |
| AU19 | AU19:VERIFIED | VERIFIED |
| AU20 | AU20:SURVIVED, AU20b:VERIFIED | VERIFIED (with survivor mutants listed) |
| AU21 | AU21:VERIFIED | VERIFIED |
| AU22 | AU22:VERIFIED | VERIFIED |
| AU23 | AU23:VERIFIED, AU23b:SURVIVED | VERIFIED (with survivor mutants listed) |
| AU25 | AU25:SURVIVED, AU25b:VERIFIED | VERIFIED (with survivor mutants listed) |
| AU27 | AU27a:VERIFIED, AU27b:VERIFIED, AU27c:VERIFIED, AU27d:SURVIVED, AU27e:VERIFIED | VERIFIED (with survivor mutants listed) |

## Survivors (loud)
- **AU18b** repeated `Origin` header: test `test_au18_a_repeated_origin_or_host_header_is_refused_on_login[origin]` sends `Origin: http://testserver` twice; that single origin is refused anyway (`_origin_allowed('http://testserver')` is False: loopback or ALLOWED_ORIGINS only), so the AT-761 Origin-count rule is not isolated. The Host variant is isolated (AU18c VERIFIED). Gap in AU18 clause "more than one Origin header is refused".
- **AU20** (misspelt `ALLOWED_HOSTS` key in the startup check) survives `test_au20_hosted_needs_an_allow_list`: the test only sets ALLOWED_ORIGINS for the passing case, never ALLOWED_HOSTS alone. AU20b (check disabled) is caught, so the raise-when-neither half is tested; the ALLOWED_HOSTS-only half is not.
- **AU25** with `test_ui_error_pages.py` + `test_ui_healthz.py` only: survives; the same mutant is caught by `tests/test_ui.py` (AU25b VERIFIED: 2 failed). My node choice was too narrow, not a product gap.
- **AU27d** `require_may_regroup` Admin-membership check skipped, test `test_p5_users_manage_cannot_add_itself_to_admin`: survives because adding to Admin/CEO is independently refused by `require_may_grant` (Admin carries users.manage, admin-only). The REMOVE-from-Admin path is isolated by `test_p5_users_manage_cannot_reset_disable_or_delete_an_admin` (AU27e VERIFIED, 400 instead of 403).
- **AU3c** server-side session lifetime x1000 (`sessions.create_session` expires_at) survives all 10 `test_au3_*` login tests: `test_au3_lifetime_is_bounded` only checks `session_hours()`, not the stored `expires_at` or cookie `max-age`. Gap in AU3 "absolute lifetime <= 12 h".
- **AU23b** `.gitignore` loses `.auth/`: survives `tests/test_auth_deploy_files.py` (no test checks `git check-ignore`; a grep of tests/ for gitignore / check-ignore / 0o600 / st_mode in the auth tests finds nothing, contradicting the manifest's AU23 line "gitignore entry and posix modes are covered in the AU1/AU3 files").

