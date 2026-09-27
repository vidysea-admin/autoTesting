# Verdict — at334-index-alias

**Date:** 2026-09-26
**Cycle checked:** 1
**Checker:** /checker (standing checker session, orchestrator plus 2 fresh-context lenses; the decisive finding was reproduced by the orchestrator itself)
**Contract:** qa/contracts/explore.md (screen identity), qa/contracts/coverage.md V1 (both sides of a coverage diff normalised the same way); issue AT-334
**Branch / code commit:** at334-index-alias · 78a144d (manifest aece107)

```
VERDICT: FAIL
SCOREBOARD: 1/2 criteria met (AT-334 node identity folds: met; one identity across the Screen/coverage seams: NOT met), 2/3 invariants hold (C2 caps and C7 sabotage rows hold; coverage.md V1 same-normalisation broken)
FAILURES:
- [coverage.md V1 / AT-334] sev: high · the fold is applied at node identity only (screen_identity.node_from, urls.screen_url_pattern). explore_merge.screen_from:73, coverage._path_of:30 and merge_flowspec:172 still call url_template unfolded, so an index-first crawl persists Screen.url_pattern '/index.html', and a run visiting '/' is reported as a false CoverageGap. That is a regression: on master both paths were known screens · pass fold_index=True at every call that produces or compares a screen identity (or derive Screen.url_pattern from the already-folded node template without its host), and add a test where an index-first crawl plus a '/' visit gives no gap, in both orders · issue: AT-618
CAPABILITY-COVERAGE: 2/2 manifest rows reproduced + 1 extra checker row (node_from with fold_index=False turns test_index_html_and_directory_root_collapse_to_one_node_identity red, so the second site is pinned)
LIVE-BROWSER: SKIP (deferred to cycle 2: the unit already fails on a reproduced code-level regression, and Mode D on tests/fixtures/modal_site runs against the fixed cycle)
ISSUES-WRITTEN: AT-618
EXECUTOR: maker builder (checker: claude-opus orchestrator + sonnet subagents)
EXPLANATION: The fold itself is correct and well-pinned: 16 tests, the edge cases behave, both sabotage rows kill, and the opt-in default that protects scripts/migrate_url_patterns.py::repair is a reasonable disclosed choice. But folding identity at 2 of the 5 seams creates exactly the disagreement coverage.md V1 forbids, and the reproduction shows it turns a covered page into a reported gap.
```

## Reproduction (orchestrator, real functions; master vs branch, same venv)

```
node_from(http://127.0.0.1:8765/index.html) then node_from(.../), dedupe by node id (first seen wins),
screen_from each, coverage._known_paths, then ask whether a run visiting '/' is a gap:
master  nodes: 2 screen patterns: ['/', '/index.html'] | run visits '/': gap = False
at334   nodes: 1 screen patterns: ['/index.html'] | run visits '/': gap = True
```

`grep -rn "url_template(" src/ scripts/` on the branch lists these callers:
- They pass `fold_index=True`: urls.py:170 and screen_identity.py:70.
- They do NOT: coverage.py:30, explore_merge.py:73 and merge_flowspec.py:172.
- The disclosed exception: scripts/migrate_url_patterns.py:101.

## What passed

- Targeted: `tests/test_urls.py tests/test_screen_identity.py tests/test_migrate_url_patterns.py` gave 66 passed. ruff reported `All checks passed!` and doctor reported `doctor: clean`.
- Row 1 (fold removed) gave 8 red on the named index assertions. Row 2 (over-broadened to `*.html`) gave 3 red, including `test_myindex_html_is_not_folded` and the case-sensitivity test.
- Edge cases: `/index.html?x=1`, `#frag`, `/INDEX.HTML` (not folded, case-sensitive), `/docs/index.htm`, `/index.html/`, `/a/index.html.bak` and `/myindex.html` all follow the documented rule.
- 4c: only urls.py, screen_identity.py, two test files and the manifest changed, with no deletions and the caps held.
- The full suite was started on the tip. Its result is appended below when it lands; it cannot change this FAIL.

- **Addendum:** the full-suite run was stopped by the checker after the FAIL was established, to free RAM for the next unit in the queue. Cycle 2 re-runs the full suite and Mode D.

---

# Verdict — at334-index-alias, cycle 2

**Date:** 2026-09-27
**Cycle checked:** 2
**Checker:** /checker (standing checker session: orchestrator plus 3 fresh-context lenses — rows, end-to-end repro + scope, Mode D)
**Contract:** qa/contracts/explore.md (screen identity), qa/contracts/coverage.md V1; issues AT-334, AT-618
**Branch / code commit:** wave/at334-index-alias · 7f051eb (manifest c2764e4, flip a23ec9b)

```
VERDICT: PASS
SCOREBOARD: 2/2 criteria met (AT-334 node identity folds; one identity across all Screen/coverage seams), 3/3 invariants hold (C2 caps, C3 one fold helper in core/urls.py, coverage.md V1 same normalisation on both sides)
FAILURES: none
CAPABILITY-COVERAGE: 5/5 rows reproduced, each in its own copy, green before / red on the named assertion after (urls.py fold removed; fold over-broadened; coverage.py:36, explore_merge.py:78, merge_flowspec.py:175 each un-folded → false CoverageGap / duplicate Screen (2 == 1) / VideoRequest stays open)
LIVE-BROWSER: qa/evidence/browser-at334-index-alias-2026-09-27-checker/report.json (on master)
ISSUES-WRITTEN: none (AT-618 fixed by this unit; flip after merge)
EXECUTOR: maker builder (checker: claude-opus orchestrator + subagents)
EXPLANATION: Every seam the cycle-1 FAIL named now folds, and an independent end-to-end reproduction (node_from → screen_from → diff_crawl, both visit orders, nested /docs/index.html, /about still a gap, /index.php not folded) shows no false gap. The only unfolded caller left is the disclosed, gated scripts/migrate_url_patterns.py:101. In a real headed Chromium on modal_site, '/' after '/index.html' gives no CoverageGap, and the modal clicks changed state on both visits.
```

**Re-ran:**
- `uv run ruff check src tests scripts`: clean.
- `uv run autotester doctor`: clean.
- The 13 targeted test files: 175 passed.
- Full `uv run pytest`: 1957 passed, 2 failed, 6 skipped, 32 xfailed (15m58s). Neither failure is charged:
  - `test_flake_probe_real_process…grandchild` is AT-518, and fails on master too.
  - `test_browser_visual_order…[table-header-group]` was `net::ERR_NO_BUFFER_SPACE` on page.goto, meaning the Windows socket buffers ran out under concurrent load. When the same test module was re-run alone on this branch it gave 20 passed. The unit does not touch the browser or visual-order code.
- Diff scope `28cc326..a23ec9b`: exactly the 6 files in What changed plus the manifest. Nothing removed.
