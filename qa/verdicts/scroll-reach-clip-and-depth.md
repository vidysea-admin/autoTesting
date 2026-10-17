# Verdict - scroll-reach-clip-and-depth
Cycle checked: 0
Bound to: D:/autoTesting/.worktrees/scroll-reach-clip-and-depth  Head: 6867f481  Base: 69ebfae7 (git merge-base HEAD master)

## Plan
Logic changed (visual_order_reach.js reachOf) -> affected tests + 1 falsification per criterion (C1 AT-417, C2 ISS-at408-416-1; C2 has two tests, one falsification each).
Not UI (browser detector JS, no screen): no Mode D / persona walk. Lane: normal (quick lane off, no lane.enabled). Tier M.

VERDICT: PASS
SCOREBOARD: 2/2 criteria met, 0/0 invariants touched (core-invariants not implicated)
TIER: M (single shared browser-detector file, no L trigger; tests/fixtures only otherwise)
FAILURES: none
CAPABILITY-COVERAGE: 3/3 rows reproduced (green in copy before, red on the named assertion after)
LIVE-BROWSER: not-applicable (browser JS detector; tests drive real headless Chromium via page_factory)
ISSUES-WRITTEN: none (AT-417 and ISS-at408-416-1 stay open for the maker to close on PASS)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Evidence (my own runs)
- `uv run pytest tests/test_browser_scroll_reach_at408_416.py tests/test_browser_scroll_invariance.py` -> 55 passed, 0 xfail/XPASS, exit 0 (67.9 s).
- `uv run ruff check src tests scripts` -> All checks passed. `uv run autotester doctor` -> doctor: clean (2 advisory D-087 notes).
- Falsification, each in a throwaway copy under the scratchpad (outside the worktree), PYTHONPATH on the copy; green first: the 3 named nodes -> `3 passed, 2 deselected`.
  - C1 `if (style.clipPath !== "none" && !scrollsX && !scrollsY)` -> `!== "none"`: red `assert 'AT417_LAST_LINE' in 'CONTROL_AT417_ALWAYS_VISIBLEAT417_FIRST_LINE'`.
  - C2 three-scroller `refBox = box;` -> `refBox = refBox || box;`: red `assert 'S2_TOP_SENTINEL' in 'CONTROL_3S_ALWAYS_VISIBLES1_TOP_SENTINELS1_FAR_SENTINEL'`.
  - C2 two-clips delete `clip = null;` at scroller crossing: red on the scroll-invariance equality (`sorted(seen) == sorted(at_rest)`).
  All reds are on the named assertion, not import/setup.
- Contract compare: AT-417 expected "accumulate the node's scroll offset before the clipPath continue" -> reachOf (visual_order_reach.js:88-101) computes scrollsX/Y first and only hard-clips when the box does not scroll. ISS-at408-416-1 expected committed fixtures+tests for 3+ scroller crossings and 2+ independent clips -> both present (test file lines 135-150, fixtures in tests/fixtures/bidi_site/).

## Hint ruling: test_browser_scroll_invariance.py::_open_defects
Not a protected test change. No assertion deleted or weakened, no threshold lowered, no skip/xfail added: the edit removes the condition that marked the 14 AT-417 shapes strict-xfail, which became 14 strict XPASS failures once AT-417 is fixed (the file's own docstring says the rule is enforced in both directions). They now run as ordinary passing tests (55 = 41 + 14), strictly stronger. It is a legitimate retirement, declared in the manifest as outside the stated scope. C2 tests are coverage (they bite under the mutant above), not red-first; that is acceptable.

## Diff scope (4c)
`git diff 69ebfae7..HEAD --stat`: reach.js (14 lines), 3 new fixtures, 2 test files, the manifest. Removed lines: the old early `clipPath` continue and the `overflow === "visible"` line, both rewritten in place. No def/class/export/test deleted, no unlisted file.

## Low findings (non-blocking, wording)
- tests/test_browser_scroll_invariance.py:~135 docstring still says "Post-fix expectation (unverified): 14 red shapes, all AT-417", now stale. Wording only, no ledger row written (checker leaves it to the maker's close-out).

Metrics: start=2026-10-17T20:13:00 end=2026-10-17T22:01:00 wall_min=11 agent_min=unavailable blocked_min=97 suite_runs=0 repeat_runs=0 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=660 mutants=0 defects_unit=0 defects_6c=0
(blocked_min = rate-limit wait mid-check; wall_min is active time: affected run 2.4 min, copies+falsifications ~2 min.)
