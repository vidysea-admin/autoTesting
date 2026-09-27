# Verdict — at477-explore-invalid-flowspec

**Date:** 2026-09-26 · **Cycle checked:** 1 · **Checker:** claude-sonnet-subagent (Mode A + Mode D)

```
VERDICT: PASS
SCOREBOARD: AT-477 met: an invalid flowspec.json no longer 500s the crawl page or POST /explore; both routes render a stated read failure
FAILURES: none
CAPABILITY-COVERAGE: 2/2 rows reproduced (copy c477-cap, own venv): bypassing _load_flowspec_safe in _coverage_card → the crawl-page test red with the AT-477 ValueError (filestore.py:49); the same bypass in _queue_coverage_gap → the POST /explore 303 test red with the same ValueError; both reverted byte-identical and green
LIVE-BROWSER: qa/evidence/browser-at477-explore-invalid-flowspec-2026-09-26-checker (visible Chromium via Python Playwright; branch: 5 steps, crawl page 200 with "the FlowSpec could not be read" card, Explore again 303 → 200, 0 console errors; master 67b0df3 control: same steps → 500 twice, 2 console errors, the second crawl saved despite the 500, reproducing AT-477 exactly)
ISSUES-WRITTEN: AT-593 (low: the POST /explore path discards the flowspec read error with no log)
EXECUTOR: maker (checker: claude-sonnet-subagent)
EXPLANATION: Both unguarded store.load_flowspec() calls (master routes_crawls.py:154, :251) now go through _load_flowspec_safe, and the crawl page surfaces the error to the user. On the POST path the error is captured and dropped, with no logger anywhere in routes_crawls.py. The user still sees it on the redirect target, but a server-side trace is lost versus the pre-fix traceback, so it is filed low (AT-593) and does not block.
```

Evidence: targeted 6 files 69 passed · ruff clean · doctor clean · routes_crawls.py 296 lines, _coverage_card 24, start_crawl 49 · `git diff --stat bb4be39..HEAD` = routes_crawls.py, test_ui_crawls.py, test_ui_crawl_approval.py (+100/-25), no renames or deletions · local fixture site only (127.0.0.1), all servers stopped afterwards.
