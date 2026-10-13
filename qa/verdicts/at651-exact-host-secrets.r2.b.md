# at651-exact-host-secrets r2 checker B: PASS

Cycle checked: 1

Sha (full): 3b7e5c1456d2d93dc9b0e0eacdbd6d74e73d6293

## Evidence
- Own matcher probes (host_of + _host_matches vs app.example.com): exact, uppercase scheme/host, one trailing dot and port match; double trailing dot, leading dot, parent, sibling, child, lookalike suffix, host-in-path/query, credentials (both forms), backslash, data:, about:blank, file:, empty, IPv6 literals (with port), Cyrillic homograph and punycode lookalike all refused. IDN: unicode scope matches unicode host, punycode scope matches punycode host, cross-form refused (fails closed). Exact IPv4 literal matches only itself.
- Fill-time recheck: session.fill resolves against self.page.url at fill time. Own probe with page.url set to data:, about:blank, host.evil, credentials, child host, host@evil after "redirect": all raise SecretScopeError, nothing filled (6 passed).
- Fill-path audit: only callers are session.fill (page.url), session.goto via resolve_for_navigation (checks resolved host vs each key's domains), and core/consent validate_account_scope; all use _host_matches. select_option/press_key/scroll/set_input_files take no secret resolution. No browser-use backend in src.
- include_subdomains is inert in _host_matches; still passed by 3 callers, no widening.
- projects/pathlynks/project.json: user secrets scoped to pathlynks.vidysea.com (real login host), counsellor secrets to dev-new.vidysea.com: still match their own hosts.
- Mutations: (1) suffix matching restored -> test_secret_host_mode_binds_both_resolution_paths fails; (2) fill-time recheck removed (resolve against base_url) -> test_fill_refuses_secret_when_page_has_drifted_off_domain fails. Both reverted, tree clean.
- Observation (non-blocking): test_suffix_match_mutation_is_caught is self-referential and the `navigation` param in test_prod_secret_refused_on_any_other_host is unused; coverage still comes from other tests.
- ruff check src tests scripts: clean. autotester doctor: clean.
- Full suite: 5 failed, all symlink noise (test_discover symlink_escape, 2 test_report_export symlink, test_ui_crawls symlink, test_ui_video_route_traversal symlink). 42 errors in test_cli_video_review_exits in the first run were my missing ffmpeg PATH; rerun with ffmpeg: 42 passed. No asyncio or flake failures seen.
