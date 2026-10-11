T-204 sub-check B (blind, read-only) at aa6fec2e. Result: every verify command passes on a fresh run. 34 of 38 mutants were killed and 4 survived, all of them test gaps rather than product defects.

**Not delivered as asked:** `D:/autoTesting/qa/evidence/t204-team-login-B/verify/summary.md` was not written. The Write tool refused it because subagents must return findings as text, so the tables are below. The runner and raw data are in that directory: `falsify.py`, `part1.sh`, `part1b.sh`, `part2.sh`, `group.py`, `probe_refused_audit.py`, `results.jsonl` (38 rows with file:line, edit, green/red output, assertion text and timings). The scratch dir is deleted. The worktree is untouched (`git status` clean). No secrets are in any evidence file.

## Part 1: fresh re-run, no failures
| Command | Result | Wall |
|---|---|---|
| 10 auth test files plus `test_ui_origin_guard.py`, all `-k` sets, one process | 249 passed | 342 s |
| `test_permission_coverage.py`, `test_credential_run_approval.py`, `test_env_loading.py` | 46 passed | 56 s |
| AU25, 5 UI files, one process | 55 passed, 1 skipped (`tests/test_ui_env_editor.py:88`, POSIX permission bits, Windows) | 42 s |

Per-criterion collected, all passed, none with 0 tests:

| Criterion | Tests | Criterion | Tests |
|---|---|---|---|
| AU1 | 2 | AU13 | 3 |
| AU2 | 7 | AU14 | 3 |
| AU3 | 15 | AU15 | 1 |
| AU4 | 2 | AU16 | 10 |
| AU5 | 8 | AU17 | 2 |
| AU6 | 3 | AU18 | 12 |
| AU7 | 11 | AU19 | 101 (includes the origin-guard file) |
| AU8 | 4 | AU20 | 1 |
| AU9 | 2 | AU21 | 13 |
| AU10 | 7 | AU22 | 4 |
| AU11 | 1 | AU23 | 1 |
| AU12 | 21 | AU27 | 10 |

**Manifest discrepancy:** it claims 150 passed for the AU25 five-file command. Those files hold only 56 tests (55 passed, 1 skipped).

## Part 2: falsification
Every row was green before the edit and restored afterwards. Each criterion AU1-AU23, AU25 and AU27 has at least one row. The six criteria that needed a second mutant (AU3, AU5, AU9, AU16, AU21, AU27) have one.

| Crit | Mutant (file:line) | Red-after (test and assertion) | Verdict |
|---|---|---|---|
| AU1 | `auth/passwords.py:15`, hasher memory_cost 1024 | `test_au1_password_is_argon2id_and_never_stored`: `1024 >= 19*1024` | killed |
| AU2 | `auth/accounts.py:96`, drop the disabled check | `test_au2_failures_are_identical`: `{303,401}=={401}` | killed |
| AU3a | `ui/routes_auth.py:36`, httponly=False | `test_au3_cookie_flags_plain_http` | killed |
| AU3b | `auth/sessions.py:45`, lifetime x100 | none (15 passed) | **SURVIVED** |
| AU3c | `auth/sessions.py:65`, drop `expires_at > ?` | `test_au3_bad_cookie_is_refused_and_creates_nothing[expired]`: 200 == 401 | killed |
| AU4 | `auth/sessions.py:84`, logout no longer deletes | `test_au4_logout_ends_the_session`: 200 == 401 | killed |
| AU5a | `auth/ratelimit.py:54`, account key check broken | `test_au5_the_window_passes` | killed |
| AU5b | `ui/routes_auth.py:53`, `if False:` | `test_au5_lock_after_failures_even_with_the_right_password`: 303 == 429 | killed |
| AU5c | `auth/ratelimit.py:18`, limit 5 -> 50 | none (3 passed) | **SURVIVED** |
| AU6 | `auth/passwords.py:23`, length check removed | `test_au6_signup_normalizes_and_validates`: 303 == 400 | killed |
| AU7 | `auth/config.py:51`, drop `.lower()` on the fixed email | `test_d074_the_fixed_email_is_compared_case_insensitively` | killed |
| AU8 | `ui/routes_admin.py:67`, disable/enable inverted | `test_au8_admin_disables_enables_renames_and_regroups`: 200 == 401 | killed |
| AU9a | `auth/db.py:158`, last-admin guard on the wrong key | `test_au9_last_admin_cannot_be_locked_out`: DID NOT RAISE LastAdmin | killed |
| AU9b | `auth/db.py:157`, drop `u.disabled = 0` | same test: 303 == 400 | killed |
| AU10 | `auth/sessions.py:76`, group join broken | `test_au10_union_and_untick`: 403 == 200 | killed |
| AU11a | `auth/defaults.py:17`, drop `COMMENT_CREATE` from the shared read set | none (23 passed) | **SURVIVED** |
| AU11b | `auth/db.py:89`, seeded marker not written | `test_au11_seeded_once_edits_survive_restart`: UNIQUE constraint groups.seed | killed |
| AU12 | `auth/access.py:29`, assigned scope returns True | `test_au12_scope_table` (4 params failed) | killed |
| AU13 | `auth/access.py:68`, project filter `if True` | `test_au13_four_users_two_projects`: `/projects/beta` leaked | killed |
| AU14a | `auth/policy.py:44`, drop a POST /onboard row | `test_au14_every_route_has_a_policy_row` | killed |
| AU14b | `ui/auth_middleware.py:91`, denial returns None | `test_au14_an_undeclared_route_is_refused`: 200 == 403 | killed |
| AU15 | `ui/routes_crawls.py:255`, approval error no longer 403 | `test_au15_admin_and_developer_get_the_same_missing_approval_refusal`: 303 == 403 | killed |
| AU16a | `ui/auth_middleware.py:81`, session routes treated as public | `test_au16_only_the_public_set_answers_unsigned_in`: `('GET','/auth/waiting',200)` | killed |
| AU16b | `ui/auth_middleware.py:51`, drop `startswith("//")` | `test_au16_login_page_drops_unsafe_next[//evil.example]` | killed |
| AU17 | `auth/config.py:40`, disabled flag ignores loopback bind | `test_au17_disabled_flag_is_refused_when_hosted` | killed |
| AU18a | `ui/helpers.py:211`, drop the `parts.port` check | `test_au18_a_non_numeric_origin_port_is_refused...`: 303 == 403 (3 failures) | killed |
| AU18b | `ui/helpers.py:279`, repeated-Origin count `>1` -> `>99` | none in `test_ui_auth_host_and_consent.py` | **SURVIVED there** |
| AU18c | same mutant | `tests/test_ui_origin_guard.py::test_more_than_one_origin_or_host_header_is_refused[origin-pairs1]`: 404 == 403 | killed |
| AU19 | `ui/helpers.py:231`, loopback host match -> startswith | `test_au19_a_foreign_host_gets_no_login_page_and_no_session[localhost.evil.com]`: 200 == 403 | killed |
| AU20 | `auth/config.py:68`, hosted check inverted | `test_au20_hosted_needs_an_allow_list`: DID NOT RAISE AuthConfigError | killed |
| AU21a | `ui/routes_credentials.py:60`, always show the value | `test_au21_values_only_for_credentials_view` | killed |
| AU21b | `ui/routes_settings.py:37`, `show = True` | `test_au21_settings_page_hides_values_and_counts_env_keys` | killed |
| AU21c | `ui/routes_settings.py:41`, drop `or key in in_env` | same test | killed |
| AU22 | `ui/auth_middleware.py:149`, log the raw path | `test_au22_audit_line_holds_the_template_not_the_query_string` | killed |
| AU23 | `.dockerignore:23`, remove `**/.auth/` | `test_au23_dockerignore_excludes_the_auth_state_at_any_depth` | killed |
| AU25 | `auth/access.py:42`, every permission check False | 13 failures in `test_ui_project_intake.py` and others | killed |
| AU27a | `auth/access.py:114`, scope@all no longer needed to grant | `test_p5_a_new_group_cannot_carry_more_than_its_creator_holds`: 303 == 403 | killed |
| AU27b | `auth/access.py:159`, admin-group change check weakened | `test_p5_users_manage_cannot_reset_disable_or_delete_an_admin`: 400 == 403 | killed |

## Surviving mutants (test gaps, not product defects)
1. **AU3b:** no test pins the real `expires_at` or cookie Max-Age to `session_hours()`.
2. **AU5c:** the literal limits (5 failures per account) are not pinned. Tests reuse the module constant.
3. **AU11a:** the default Tester/Developer grant table is not asserted on its own. Dropping `COMMENT_CREATE` from the shared read set goes unnoticed.
4. **AU18b:** `test_ui_auth_host_and_consent.py` does not exercise the repeated-Origin refusal. `tests/test_ui_origin_guard.py` kills it (AU18c), so it is covered overall.

## Contract clauses with no test evidence
- **AU1:** the argon2-cffi pin in `uv.lock`, and a response-body canary that the password never echoes.
- **AU7:** the hosted double-signup race for the first admin.
- **AU16:** the healthz detail is covered only in `tests/test_ui_healthz.py`, outside the AU16 `-k` set.
- **AU20:** the own-origin allow-list clause.
- **AU23:** the gitignore entry, file permissions, and `extra="forbid"` on the auth models.
- **AU27, refused-attempt audit:** I ran a probe (`probe_refused_audit.py`, one pytest run in the copy). A refused escalation (HTTP 403) writes only the request-log line `{email, method, path: "/admin/users/{user_id}/{action}", status: 403}`. No `{actor, target, action}` line exists for the refused attempt; the only action line is the earlier `login`. If AU27 requires an action-audit line for refusals, it is not implemented. The probe passed in the copy, which was then deleted.

## Not run
- AU24 and AU26 (not in the brief).
- Whole-directory and full-suite pytest (RAM rule).

## Timings and failure text
- Mutant rows took 5-17 s each for green and 5-13 s for red.
- Part 1 took about 7 minutes in total.
- No test failed in Part 1, so there is no failure text.