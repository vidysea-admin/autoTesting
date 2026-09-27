# Verdict — at299b-hostless-url

**Date:** 2026-09-26 · **Cycle checked:** 1 · **Checker:** claude-sonnet-subagent + orchestrator re-run

```
VERDICT: FAIL
SCOREBOARD: hostless multi-segment paths fixed (core target met); AT-299b's expected clause NOT met for a bare dotted token: the ingest result is still '/' for a raw url that is not root-shaped
FAILURES:
- [AT-299b] sev: medium · Through the composition every caller uses, url_template(absolute_url(x), keep_host=False) (stages/ingest.py:137, stages/explore_status.py:52, stages/product_map.py:40,61), a bare dotted token with no slash still collapses to '/': 'file.html', 'sitemap.xml', 'report.pdf', 'robots.txt', 'a.b' → '/'. That is the false site-root claim AT-299b exists to kill. The expected clause's own mechanism ("after templating, if the result is '/' while the raw observed url was not root-shaped, store url_pattern=None") is not implemented, and the new tests cover only dot-free prose ('Sign in page'). · Fix: implement the clause at the ingest boundary. A slash-free token is ambiguous ('example.com' vs 'file.html' cannot be told apart by shape, AT-287), so when templating gives '/' and the raw string had no '/' after its host (no path and no trailing slash), store url_pattern=None. Keep '/' only for an explicit root ('example.com/', 'https://x.y', '/'). Do NOT stop promoting slash-free tokens to hosts: that turns a real bare host 'example.com' into the pattern '/example.com'. Add tests for 'file.html', 'example.com' → None and 'example.com/' → '/'. · issue: AT-299b
CAPABILITY-COVERAGE: 5/5 declared rows reproduced (copy c299-1: mutant_no_guard, mutant_dot_only, mutant_colon_only, mutant_no_scheme_guard each red on the named test; fixed module 19 passed); the "prose no longer claims root" row holds for its input only (see FAILURES)
LIVE-BROWSER: not-applicable (core/urls.py, tests/test_urls.py)
ISSUES-WRITTEN: none new (AT-299b stays open)
EXECUTOR: maker (checker: claude-sonnet-subagent; FAILURE re-run by the orchestrator in the worktree)
EXPLANATION: The guard correctly stops a hostless path such as 'erp/trainers' losing its first segment, and it keeps stripping dotted and ported hosts. But a filename-shaped observation still claims the site root, and the ingest-boundary None guard the issue asked for was replaced by a shape guard that cannot resolve the single-token case. Also, low: the docstring (urls.py:65-69) says 'localhost/students' "still reads as a host", but the guard leaves it unchanged (a path, '/localhost/students'); correct that sentence.
```

Orchestrator re-run in the worktree (`uv run python`): 'file.html' → '/', 'example.com' → '/', 'www.example.com' → '/', 'Sign in page' → '/Sign in page'. Base absolute_url (merge-base) prepended https:// unconditionally, so 'file.html' → '/' is not new, but it is exactly what AT-299b's expected clause asks this unit to stop.
Subagent evidence: targeted 8 files 76 passed · ruff clean · doctor clean · diff = urls.py, test_urls.py, manifest only.

---

# Verdict — at299b-hostless-url, cycle 2

**Date:** 2026-09-26 · **Cycle checked:** 2 · **Checker:** claude-sonnet-subagent

```
VERDICT: PASS
SCOREBOARD: AT-299b met: screen_url_pattern (core/urls.py:109-148) returns None whenever templating gives '/' and the raw string does not explicitly name the root; all 3 producers are wired to it (ingest.py:137, product_map.py:40/59, explore_status.py:52)
FAILURES: none
CAPABILITY-COVERAGE: 3/3 rows reproduced in separate copies: dropping the None guard makes 'file.html' give '/' (row 1 red only); dropping the explicit-root branches makes 'example.com/' give None (row 2 red only); dropping the templated != '/' early return makes 'erp/trainers' give '/' (row 3 red only)
LIVE-BROWSER: not-applicable (core/urls.py, stages/*, tests/test_urls.py; the product-map card was rendered through ui.routes_product_map._screen_card with a None pattern: it shows the em-dash, never 'None')
ISSUES-WRITTEN: none
EXECUTOR: maker (checker: claude-sonnet-subagent)
EXPLANATION: 20-input table: 'file.html', 'sitemap.xml', 'example.com', 'www.x.io', '127.0.0.1', 'localhost:3000' → None; 'example.com/', 'https://x.y', 'localhost:3000/', '/' → '/'; real paths are unchanged. No false root claim remains, and no explicit root is lost. Bare hosts giving None is the ambiguity AT-299b's clause accepts ("'no pattern' is strictly better than a false claim"). Every url_pattern consumer is None-safe (coverage, crawl_coverage, explore_merge, merge_flowspec, explore_status, portal_persona, 3 UI renderers), and a real build_screen_map → UI render path was driven. 4c: cycle 2 changes absolute_url's docstring only (its code is byte-identical to cycle 1). The one master sentence removed ("This is NOT the host-shape guessing…"), removed in cycle 1, became false once the guard began inspecting dots and ports, so its removal is required.
```

Evidence: worktree targeted 8 files 80 passed · ruff clean · doctor clean · urls.py 148 lines, screen_url_pattern 40, absolute_url 43 · test_urls.py diff is additive only.
