# Verdict — crawl-toggle-coverage (Checker B, adversarial)

**Checked by:** /checker (combined A+B seat, fresh context, no builder reasoning)
**Date:** 2026-10-29
**Branch / head:** `fix/crawl-record-gaps` @ `98db81fb` (worktree `.claude/worktrees/crawl-gaps`)
**Contract:** `qa/contracts/explore.md` X3 (identity), X4 (bounds), X11 (coverage books); `core-invariants.md` C1, C3
**Manifest:** `qa/manifests/crawl-toggle-coverage.md`, `Status: ready-for-check`, Fix cycle 0

**Cycle checked: 0**

## Verdict: FAIL (1 blocking finding, 3 non-blocking warnings)

Criteria 2, 3, 4 hold. Criterion 1 is met for its own fixture but introduces a regression the fixture
cannot see: a revealed control that does not navigate turns a crawl that COMPLETED on the previous
head into an ABORTED crawl with an abandoned duplicate screen.

## What I re-ran myself

| Command | Result |
|---|---|
| `uv run pytest tests/test_crawl_toggle_coverage.py tests/test_crawl_record_gaps.py -o addopts=` | 23 passed |
| `tests/test_crawl_coverage.py tests/test_crawl_coverage_bounds.py` | 24 passed |
| `tests/test_execute.py tests/test_observe.py` | 19 passed |
| `uv run ruff check src tests` | All checks passed |
| line counts | `explore_node.py` 300, `explore_return.py` 201, `network_capture.py` 93 (rule holds) |

## Falsification (each fix reverted in memory, `.work/probe_b_revert.py`, 5 passed)

Each case patches the fix out and asserts the unit's own test goes RED (`AssertionError`):
`explore_node.note_revealed` -> no-op (red); `explore_node.press_revealer` -> no-op (red, `Open reports
panel` raises "hidden"); `observe.MAX_BUFFERED_API_RESPONSES` -> 1e9 (red); `PageObserver.drain_api_responses`
-> `[]` so the case-run drain does nothing (red); the tally cap lifted (red). The tests do bite.

## Findings

### B-1 (BLOCKING) A revealed control that does not navigate mints a duplicate "open" screen that cannot be returned to; the crawl ends ABORTED

Probe `.work/probe_b_toggle.py::test_one_nonnav_reveal` (same harness as the maker's test: toggle opens the
nav, a goto/reload collapses it). The toggle reveals one ordinary button, `Reports submenu` (a sub-menu
expander; it does not change the URL).

| Head | Result |
|---|---|
| `5b09e417` (before this unit, via `git archive` + `PYTHONPATH`) | `completed`, 4 nodes, all `explored`, `stop=frontier empty` |
| `98db81fb` | `aborted`, 5 nodes, second `/` at depth 1 is `aborted_error`, `stop=abandoned visits: aborted_error (/)`, 2 issues |

Mechanism, all in the diff:

1. `press_revealer` (`explore_return.py:167`, called at `explore_node.py:160`) opens the nav, then the
   control is pressed and the page stays in the OPEN state. That state has a different structural
   signature from the collapsed node, and `same_screen` (`screen_identity.py:57-60`) only forgives
   `is_layout_toggle(pressed)`, not a revealed control. So `try_action` records `NAVIGATED` and `_enqueue`
   mints a second `/` node (the nav-open screen). This is exactly the "layout toggle state is not a
   screen" duplicate that `crawl-record-gaps` removed (X3), re-introduced one click later.
2. Visiting that node calls `return_to`, which `goto`s `/` (collapsed, signature mismatch) and then
   `_replay_discovery` -> `explore_replay.perform(edge)` (`explore_replay.py:174-211`), which clicks
   `edge.target` directly. The replay path was not taught about `rt.revealed_by`, so the control is hidden,
   the click raises, and the node is `ABORTED_ERROR` with a NAVIGATION issue. In a real browser that click
   waits out Playwright's actionability timeout before failing.
3. `crawl.status` becomes `aborted`. A sidebar with any non-navigating item (sub-menu expander, filter chip,
   accordion) is common, so this is not exotic. The maker's fixture only has revealed controls that
   navigate away, which is the one shape that avoids it.

Fix direction (checker does not edit): either record a revealed control that lands on the open-state of the
same URL as SAME_SCREEN (extend `same_screen` / the `try_action` branch for `node.id in rt.revealed_by`
keys), or make `explore_replay.perform` call `press_revealer` first. A regression test needs a revealed
control that does not navigate.

### B-W1 (warning) Revealer press is not budgeted and not guarded by the persisted-toggle case

`press_revealer` clicks via `rt.session.click` outside `rt.frontier.actions_used` and outside the per-node
cap (probe `test_many_reveals_cap`: 60 revealed controls, 23 toggle clicks, per-node cap 25 held, no loop,
`max_actions=200` not exceeded). So the budget is undercounted, never double-counted or looped; bounded by
the cap, acceptable. Separately, a toggle that PERSISTS across reload (`test_persisted_toggle`) ends the
node `aborted_error` on both heads (baseline identical), so that is a pre-existing limit the manifest
already states, not a regression. A persisted toggle would also make the re-press close the nav; this is
untested.

### B-W2 (warning) Distinct-key cap now keeps the first 100 seen, not the first 100 sorted

`network_capture.count_api_calls` (`:62-80`) drops a NEW key once 100 exist; the old `api_inventory`
sorted then cut. Output is still sorted and capped, but which 100 survive now depends on arrival order.
Test `test_api_tally_does_not_grow...` pins the cap and the poll counter, not which keys win. Non-blocking.

### B-W3 (warning) Selector-keyed `revealed_by`

`revealed_by` is keyed `(node id, selector)` (`explore_return.py:157`) while "known" uses `(role, selector)`.
A revealed control that shares a selector with an existing control of a different role would make the
existing control also trigger the toggle press. Selectors from `enumerate.js` are `data-testid`, id,
aria-label or `role=...[name=...] >> nth=N`; nth shifts after a reveal could produce spurious "fresh"
controls. Not reproduced, flagged only.

## Items checked and found sound

- Allowed domains and deny-list (`test_offdomain_and_deny`, passed with assertions): a revealed off-domain
  link recorded `off_domain_refused` and `https://evil.test/x` never entered the page history; a revealed
  `Delete account` was `denied_policy` and never clicked. Revealed controls go through `_candidate_denial`
  like any other (`explore_node.py:~254`).
- No loop: `press_revealer` runs once per `try_action`; the queue only grows from newly revealed controls,
  per-node cap and `stop_reason` checks apply (`explore_node.py:241-262`).
- Case-run oracles: `api_responses` is read only by the crawl (`explore_runtime.py:104`); `execute` still
  drains `responses` exactly as before, so `expected.network` evidence is unaffected. The 2000 cap applies
  to `api_responses` only, not `responses`.

## Required before PASS

Fix B-1 with a regression test (revealed non-navigating control; crawl must stay `completed`, no second `/`
node), re-run the 23-test set plus `tests/test_explore_node_recovery.py tests/test_explore_return_determinism.py`.
