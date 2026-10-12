# Verdict - at651-exact-host-secrets, checker A (blind, cycle 0)

Cycle checked: 0
Bound to: worktree .worktrees/chk-at651-A, detached at origin/wave/at651-exact-host-secrets = ceaf43716e7ee90918afebe635ccee8f60d44927. Date 2026-10-12.

VERDICT: FAIL

## Why
The security change itself is correct, but the maker updated only 3 test files. Nine tests in three other files still use suffix-scoped fixtures and now fail; they are not baseline noise. The reason is the same in each: `SecretScopeError: 'KEY' is scoped to ['pathlynks.test'] and may not be used on 'app.pathlynks.test'` (or staging.pathlynks.test).
- tests/test_secrets.py (5): test_resolve_substitutes_on_an_allowed_host, test_subdomains_of_a_scoped_domain_are_allowed (asserts the removed behaviour; needs inverting), test_resolve_for_navigation_substitutes_a_bare_placeholder, test_resolve_for_navigation_substitutes_a_placeholder_embedded_in_a_url, test_at005_non_strict_load_still_fails_closed_at_resolve
- tests/test_execute.py (3): test_completed_run_composes_session_methods_and_screenshots_every_step, test_missing_secret_blocks_for_a_human_instead_of_erroring, test_a_secret_value_inside_an_exception_message_is_scrubbed_before_persisting
- tests/test_browser_actions.py (1): test_fill_receipt_observes_values_but_never_reads_secrets[placeholder]
Fix: scope those fixtures to the exact host, and invert the test_secrets subdomain test.

## Exact-host probes (own, via host_of + _host_matches vs scope pathlynks.vidysea.com)
- MATCH (correct): exact; mixed case; one trailing dot; :443 and :8443 port (host_of drops the port).
- REFUSED (correct): dev-new.vidysea.com; bare vidysea.com; pathlynks.vidysea.com.evil.com; evil-pathlynks.vidysea.com; a.pathlynks.vidysea.com; user@host (host_of returns empty); host@evil.com; backslash trick; evil.com#@host (host evil.com); xn-- lookalike; Cyrillic a; fullwidth p; ideographic dot U+3002; IP 127.0.0.1; [::1]; empty; "https://"; "//"; %2e trick; empty domain vs empty host (False).
- Quirks (low risk, not a bypass): `rstrip(".")` strips ALL trailing dots and `lstrip(".")` strips leading dots, so "host.." and ".host" match the scope. A browser's page.url would not yield those as a different server. Suggest one trailing dot only and no leading-dot strip on the host side.
- Wide-scope check: _host_matches("dev-new.vidysea.com","vidysea.com",True) is False.

## Code paths
Secrets resolve only via SecretStore.resolve (session.fill, using page.url at FILL time, so a redirect is re-checked) and resolve_for_navigation (after substitution, against result host). Both go through _value_for or _host_matches. consent.py and schedule_gate.py call _host_matches. Other fill sites (explore_replay, explore_typing, execute) call session.fill. No other secret-bearing fill/type path found. include_subdomains no longer widens anywhere (arg ignored). projects/pathlynks/project.json: secrets already exact (dev-new.vidysea.com counsellor, pathlynks.vidysea.com user, include_subdomains false); base_url host pathlynks.vidysea.com matches the user secrets, so the schedule gate still PROVISIONED and the real login is not broken. projects/erp lists vidysea.com and www.vidysea.com, base www.vidysea.com, still OK.

## Fixture changes
test_browser.py, test_browser_navigation_secrets.py, test_onboard_pathlynks.py only narrow scope to the exact host; assertions not weakened. Note: the new test_prod_secret_refused_on_any_other_host parametrizes `navigation` but never uses it, so resolve_for_navigation is not exercised by it.

## Mutation
Restored suffix match: test_secret_host_mode_binds_both_resolution_paths[child.auth.pathlynks.test] FAILED. Caught. Reverted (worktree clean).

## Gate
- Full suite `uv run pytest -o addopts=` (ffmpeg on PATH): 14 failed, 5546 passed, 7 skipped, 14 xfailed. Baseline-type: 5 symlink (test_discover x1, test_report_export x2, test_ui_crawls x1, test_ui_video_route_traversal x1). The 9 above are regressions from this unit. No asyncio or flake failures this run.
- ruff check src tests scripts: clean.
- autotester doctor: clean.
