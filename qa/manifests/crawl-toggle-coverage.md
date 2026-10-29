# Manifest — crawl-toggle-coverage

**Unit:** follow-up to `crawl-record-gaps` (dual PASS closed at `5b09e417`): verdict warnings
A-W1/W2, B-W1/W2/W4 (`qa/verdicts/crawl-record-gaps.md`, `.b.md`).
**Contract:** `qa/contracts/explore.md` X3 (identity), X4 (bounds), X11 (coverage books balance);
`qa/contracts/core-invariants.md` C1, C3.
**Branch:** `fix/crawl-record-gaps` (worktree `.claude/worktrees/crawl-gaps`)
**Date:** 2026-10-29
**Fix cycle:** 0
**Status:** ready-for-check
**Dual check:** no
**Not changed (as instructed):** `core/urls.py` templating. No real crawl; whole suite not run.

## Criteria

1. **A toggle's reveals are explored, on the same node (A-W2, B-W4).** After a layout toggle is
   recorded SAME_SCREEN, `explore_return.note_revealed` (`stages/explore_return.py:147`) adds every
   control now visible that the node did not know (by role+selector, layout toggles excluded) to the
   SAME node's `elements` (persisted with `update_node`, so coverage counts them) and remembers the
   toggle as its revealer (`ExploreRuntime.revealed_by`). `_click_loop` now works from a queue
   (`explore_node.py:241-243`) that takes the newly revealed controls in the same loop, within the
   same per-node cap and the same policy checks. A reload hides them again, so
   `explore_return.press_revealer` (`:167`, called at `explore_node.py:160`, inside the `try` so a
   failure is an ERRORED edge with its cause) presses the toggle first. `_mark` now reads the latest
   node from `rt.nodes` so a status write cannot drop the grown elements. No node is minted; node ids
   are unchanged. Test: `test_controls_a_layout_toggle_reveals_are_explored_without_a_new_node`
   (fixture page whose collapsed nav hides a link and a button that raises unless the nav is open:
   one `/` node, `a.reports` + `button.panel` in its elements, `Toggle navigation` = SAME_SCREEN,
   `Reports` and `Open reports panel` = NAVIGATED, `/reports` and `/panel-result` nodes exist).
   Shown RED by disabling the `note_revealed` call (assertion on `a.reports` fails).
2. **`api_responses` cannot grow unbounded (A-W1, B-W1).** `PageObserver` keeps at most
   `MAX_BUFFERED_API_RESPONSES=2000` (oldest dropped, `browser/observe.py:34,116`), and
   `execute._drain_network_evidence` drains it every step (`stages/execute.py:102`). Tests:
   `test_api_response_buffer_is_capped_and_keeps_the_newest`,
   `test_a_case_run_step_drains_the_api_buffer_too`.
3. **Constant-size per-screen tally (B-W2).** `rt.api_seen` is now
   `node id -> {(METHOD, path pattern, status): count}`, filled at `take_responses` time by
   `network_capture.count_api_calls` (`stages/network_capture.py:62`): a poll adds 1 to a counter, at
   most `MAX_API_CALLS_PER_NODE=100` distinct keys per screen (a new key past the cap is dropped, an
   existing one still counts). `api_rows` (`:81`) turns it into `ApiCall` rows;
   `apply_api_calls` uses it; `api_inventory` kept as a thin wrapper (used by tests). Test:
   `test_api_tally_does_not_grow_with_repeated_calls_and_caps_distinct_paths`.
4. **Design rules.** `explore_node.py` is exactly 300 lines (the `visit_node` docstring's history
   was condensed to its two facts to make room; `explore_return.py` 201). No new src module. No schema
   change (`docs/MAP.md` regenerated, no diff).

## Files changed

`src/autotester/browser/observe.py`, `stages/execute.py`, `stages/explore_node.py`,
`stages/explore_return.py`, `stages/explore_runtime.py`, `stages/explore_summary.py`,
`stages/network_capture.py`, `tests/test_crawl_toggle_coverage.py` (new, 4 tests), this manifest.

## Tests run (`uv run pytest <2 files> -o addopts=`, one at a time)

- RED first: `tests/test_crawl_toggle_coverage.py` -> ImportError (`MAX_BUFFERED_API_RESPONSES`);
  after the buffer fix, toggle test red with `note_revealed` disabled.
- `tests/test_crawl_toggle_coverage.py tests/test_crawl_record_gaps.py` -> `23 passed`.
- `tests/test_explore.py tests/test_explore_error_causes.py` -> `27 passed`.
- `tests/test_explore_traversal.py tests/test_explore_modal.py` -> `15 passed`.
- `tests/test_explore_node_recovery.py tests/test_explore_return_determinism.py` -> `6 passed`.
- `tests/test_observe.py tests/test_network_assertions.py` -> `22 passed`.
- `tests/test_explore_typing.py tests/test_explore_secret_scrubbing.py` -> `13 passed`.
- `uv run ruff check src tests` -> `All checks passed!`
- `uv run autotester doctor`: only `docs/SNAPSHOT.md` stale (generated, pre-existing, untouched).

## For the checker to weigh

- Revealed controls are found from the observation taken right after the toggle press; a control
  that appears only after a further interaction is not chased.
- If a site keeps the opened state across a reload, `return_to` can fail to match the node's
  signature (same risk as any persisted UI state before this unit); it would surface as the existing
  `ABORTED_ERROR` + NAVIGATION issue, not silently.
- Unnamed controls a collapse reveals (the Pathlynks icon-only buttons) now appear as
  `skipped_unnamed` edges/holes: more honest coverage, slightly more rows.
