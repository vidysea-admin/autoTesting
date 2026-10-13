# at651-exact-host-secrets r2 checker A: PASS

Cycle checked: 1
SHA: 3b7e5c1456d2d93dc9b0e0eacdbd6d74e73d6293 (origin/wave/at651-exact-host-secrets)

## Evidence
- All 9 r1 regressions pass (full suite: 5598 passed). Fixture diffs only change scope domains to the exact host (app.pathlynks.test, pathlynks.vidysea.test, etc.); no assertion weakened, none re-enables suffix matching. test_execute_new_actions, test_browser_settle, test_network_assertions also exact-host.
- Subdomain test inverted: tests/test_secrets_host_match.py::test_subdomains_of_a_scoped_domain_are_refused asserts SecretScopeError for child and bare parent.
- Quirks fixed: "host.." refused, ".host" refused, "host." matches.
- Adversarial host probe (scope pathlynks.vidysea.com), all REFUSED: dev-new sibling, bare parent, .evil.com suffix, evil- prefix / evil concat, child host, userinfo (both forms), backslash, punycode and Cyrillic lookalikes, IPv4/IPv6 literal, empty host, "host..", ".host". ALLOWED only: exact, :port, one trailing dot, mixed case.
- Mutation (suffix endswith restored in a separate worktree): 16 failures across test_browser_navigation_secrets (incl. refusal, bare-parent, mutation tests). Reverted/discarded.
- No SecretScopeError failures anywhere in the suite.
- Gate: `pytest -o addopts=` 5 failed (all known symlink noise: test_discover symlink_escape, test_report_export x2, test_ui_crawls symlink, test_ui_video_route_traversal), 5598 passed, 7 skipped, 14 xfailed. ruff clean. doctor clean.
