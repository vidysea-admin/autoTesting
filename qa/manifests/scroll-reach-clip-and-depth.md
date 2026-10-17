# Manifest — scroll-reach-clip-and-depth
**Contract:** qa/contracts/ui.md (U14a scroll-invariance)
**Goal task:** none
**Date:** 2026-10-17
**Fix cycle:** 0 of max 2
**Hold fix cycles:** 0 of 2
**Hold-reopens:** 0
**Resume-reset:** unused
**Capability-redispatch:** 0
**Dual check:** no
**Persona walk:** skip (browser detector JS and tests, no screen added or changed)
**Issues addressed:** AT-417, ISS-at408-416-1
**Executor:** claude-sonnet-subagent
**Executor rationale:** S-M single-file fix plus fixtures; fits one Sonnet build agent.

## What changed
- src/autotester/browser/visual_order_reach.js:86-100 — `reachOf`: scroll flags are now computed BEFORE the clip-path branch; a clip-path box that also scrolls falls through to the scroller handling (offset accumulated, segment closed, own box becomes the reference) instead of `continue`-ing and testing a hard clip against the glyph's moving rect (AT-417 C1).
- tests/test_browser_scroll_reach_at408_416.py:86-150 — three new tests: AT-417 clip-path scroller, 3 scroller crossings under one clip, 2 independent clip boundaries in one chain (+ negative control) (C1, C2).
- tests/fixtures/bidi_site/at417_clip_scroller.html, at408_416_three_scrollers.html, at408_416_two_clips.html — the three fixtures (new, test data).
- tests/test_browser_scroll_invariance.py:_open_defects — **outside the declared scope, forced by the fix**: its 14 AT-417 shapes were `xfail(strict=True)` and all XPASS(strict) once AT-417 is fixed (14 failed, 41 passed measured before this edit). `_open_defects` now derives no defect; the hook is kept. Nothing else in the file changed.
- Criteria: C1 = AT-417 (accumulate/handle scroll for a clip-path scroller); C2 = ISS-at408-416-1 (committed fixtures at N=3 scroller crossings and 2 independent clip boundaries).

## Verification scope
Policy-Version: proportional-verification/2026-10-15.12
Tier: M (single browser-detector file, no security trigger)
Base / checked state: 69ebfae7 / b4fc3a5f (branch wave/scroll-reach-clip-and-depth)
Gate answers: none (no gate applies; no new module, qa/contracts and qa/issues.jsonl untouched)
Affected tests / full-suite trigger: tests/test_browser_scroll_reach_at408_416.py, tests/test_browser_scroll_invariance.py (56-case corpus, includes the 14 formerly-xfail AT-417 shapes); full suite trigger: none. The builder ran no full suite.
Pre-check[C1]: b4fc3a5f uv run pytest tests/test_browser_scroll_reach_at408_416.py -k at417 -> 1 passed t=58 blobs=tests/test_browser_scroll_reach_at408_416.py:e413416
Pre-check[C2]: b4fc3a5f uv run pytest tests/test_browser_scroll_reach_at408_416.py -k "three_scroller or two_independent" -> 2 passed t=24 blobs=tests/test_browser_scroll_reach_at408_416.py:e413416
Metrics: start=2026-10-17T18:55:00 end=2026-10-17T19:30:00 wall_min=35 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=3 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal

## How to verify (commands + expected)
- `uv run pytest tests/test_browser_scroll_reach_at408_416.py tests/test_browser_scroll_invariance.py` → expected: 55 passed (no xfail/XPASS)
- `uv run ruff check src tests scripts` → expected: All checks passed!
- `uv run autotester doctor` → expected: doctor: clean

## Actual outputs (from maker's own run)
- pytest (both files, after fix): `55 passed, 1 warning in 72.22s`
- before the fix hunk, same two files with the new tests present: AT-417 test FAILED (`assert 'AT417_LAST_LINE' in 'CONTROL_AT417_ALWAYS_VISIBLEAT417_FIRST_LINE'`); after the fix but before the invariance-file edit: `14 failed, 41 passed` (14 x XPASS(strict) AT-417).
- ruff: `All checks passed!`; doctor: `doctor: clean` (2 advisory known-disputed D-087 findings, non-blocking).

## Capability coverage (each new claim -> its isolating falsification)
Falsified in a throwaway copy at scratchpad/mut (outside the worktree), PYTHONPATH pointed at the copy; same node ids green on the unmutated copy first (`3 passed, 2 deselected`).

| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| C1 | a clip-path box that is also a scroller keeps its scroll offset; both lines reported at rest and after scrolling | tests/test_browser_scroll_reach_at408_416.py::test_at417_a_clip_path_box_that_is_also_a_scroller_keeps_its_scroll_offset | visual_order_reach.js: `if (style.clipPath !== "none" && !scrollsX && !scrollsY) {` -> `if (style.clipPath !== "none") {` (the old continue-first behaviour) | green@fix: `1 passed`; red@mutant: `AssertionError: ('AT417_LAST_LINE', 'CONTROL_AT417_ALWAYS_VISIBLEAT417_FIRST_LINE')` |
| C2 | segment chain holds at 3 scroller crossings under one clip | ...::test_iss_at408_416_1_three_scroller_crossings_under_one_clip_are_scroll_invariant | visual_order_reach.js: `refBox = box;` -> `refBox = refBox \|\| box;` (keep inner scroller's box as reference) | green@fix: `3 passed`; red@mutant: `AssertionError: ('S2_TOP_SENTINEL', 'CONTROL_3S_ALWAYS_VISIBLES1_TOP_SENTINELS1_FAR_SENTINEL')` |
| C2 | segment chain holds with 2 independent clip boundaries | ...::test_iss_at408_416_1_two_independent_clip_boundaries_are_scroll_invariant | visual_order_reach.js: delete `clip = null;` at the scroller crossing | green@fix: `3 passed`; red@mutant: `assert ['2', 'A', 'A...'A', 'A', ...] == ['2', 'A', 'A...'A', 'A', ...]  At index 6 diff: 'B' != 'A'` (scroll-dependent glyph set) |

## Live browser evidence
Real headless Chromium via the `page_factory` fixture in every test above (visual_text against served fixtures, console not captured). No separate qa/evidence directory: the instrument is the pytest run itself; pasted runner output is in the sections above.

## Status: ready-for-check
