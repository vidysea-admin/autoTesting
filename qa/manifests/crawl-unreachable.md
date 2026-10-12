# crawl-unreachable — AT-113 (high), AT-889 (medium)

Status: ready-for-check
Fix cycle: 0
Issues: AT-113, AT-889
Branch: wave/crawl-unreachable (from origin/master 99960519)

Stall check: at113-crawl-completion is closed (cycle 4 PASS, merged; AT-745 verified). No live branch; started fresh. Master already filed an issue and ended ABORTED for the entry and mid-loop return failures; the remaining hole was the destructive-last drain.

Changes:
- explore_traversal.drain_deferred: a screen it cannot re-enter now files a NAVIGATION issue and is marked ABORTED_ERROR, so the crawl ends ABORTED (was completed / 0 issues).
- explore_login.py (new, extracted from explore.py): bootstrap_login re-checks the URL after the login case fails, so a redirect landing after the precheck still counts as authenticated; a real failure names the case outcome and error in stop_reason.
- explore.py now delegates to explore_login (286 -> 210 lines).

Tests: tests/test_crawl_unreachable.py (3). Also green: test_explore_node_recovery, test_explore_return_determinism, test_explore_login_bypass, test_explore_blocked, test_explore.
