# Manifest - at1305-capture-settle (AT-1305, medium)

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** qa/contracts/execute.md (E1-E5 held); unit criteria C1-C3 quoted from the build brief `.work/briefs/build-at1305-capture-settle.md`
**Goal task:** none (issue AT-1305, from the live T-136 r3 report `.work/t136-live-report-r3.md` section D2)
**Dual check:** no (touches only the capture wait in `stages/execute.py` and `browser/evidence.py`, plus tests; no auth, tenancy, secret-handling or data-write trigger; masking order is pinned by a test, not changed)
**Persona walk:** skip (no UI surface)
**Issues addressed:** AT-1305
**Executor:** claude-sonnet-subagent
**Base SHA:** 8f2b6df3 (worktree .worktrees/at1305-capture-settle, branch wave/at1305-capture-settle, base int/1017)
**Code SHA:** e9980de3

## Criteria (quoted from the brief)
- **C1** After a step action that triggers navigation or a pending network/loading state, the step screenshot is taken only after the page settles (load state + network idle or a bounded settle wait), with a hard upper bound so a page that never settles still gets captured and the step records that it did not settle.
- **C2** A page that is already settled is captured without added delay beyond the bound check (no fixed sleep).
- **C3** Existing capture behaviour (masking of secret inputs before capture, image privacy) is unchanged.

## What changed
- `src/autotester/browser/evidence.py` (+53, 190 lines): `settle_for_capture(session, label, step_order, bound_ms=CAPTURE_SETTLE_MS)` and `_capture_pending`. One `page.evaluate` DOM read reports pending when `document.readyState != complete`, an `[aria-busy=true]` / `[role=progressbar]` element exists, or a visible button/link/status control reads like "Logging in..." / "Signing in..." / "Loading..." (word plus ellipsis, so a plain "Loading" heading is not pending). Pending polls `wait_for_timeout(250)` through `session._timeout` (run-budget brake never swallowed) up to `CAPTURE_SETTLE_MS` = 4000. At the bound it records a DOM evidence row `page did not settle within 4000ms before capture: stepNN-action` (not an `assert ` row) and the shot is still taken. An unprobeable page (evaluate raises or is absent) counts as settled. Lives in evidence.py (the module that owns screenshot capture) because `browser/assertions.py` would pass the 300-line cap.
- `src/autotester/stages/execute.py` (+5, 287 lines): `_TRANSITIONING` (click, navigate, back, press_key, select) and one call in `_run_steps` immediately before `session.screenshot`, after the existing `session.settle` and assertion handling. Fill, wait, assert, hover, scroll, upload do not pay the check.
- `tests/test_execute_capture_settle.py` (new, 7 tests, fake page with virtual time; no live site).
- Untouched: `Session.screenshot` and its masking, `_recapture_blank`, `assertions.settle`, probe accounting (`step_probe_floor`: the capture check charges no probe), every contract.

## Judgement calls for the checker
1. The pending detector is DOM-based, not network-based: Playwright's `networkidle` is sticky once fired, so an XHR started by the click after the load event is invisible to `wait_for_load_state`; the D2 frames ("Logging in...") fit exactly that. Cost: a heuristic label list. It errs toward waiting at most 4 s, never toward blocking a capture.
2. The 4 s bound adds to `settle()`'s own bound (up to 8 s when no expectation is declared); worst case per step is bounded and the run budget still applies.
3. `autotester doctor` reports 4 violations on this tree and on the base alike (none in the touched files).
4. A first attempt put the helper in `assertions.py` (308 lines, over the cap); moved to `evidence.py` before commit.

## Verification scope
Policy-Version: proportional-verification/2026-10-18.15
Tier: M (multi-file behaviour with timing; execute.py, evidence.py, one new test file)
Round: 2 src files + 1 test file, 3 criteria, est 40 min
slow-plan: none needed; the unit's whole suite slice runs in about 30 s
mutant-cap-raise: none; 3 mutants (below) cover the three behaviours
Owners: none
Base / checked state: 8f2b6df3 / e9980de3, clean tree (manifest only added after)
Gate answers: none required
Affected tests / full-suite trigger: tests that drive `run_case` or `settle`/`screenshot` (execute, assertions, new actions, settle, probe floor, blank retry, failing-step bundle, flake probe, multi-role session, scroll invariance, browser). No full suite (no shared schema or dispatch change).
Tests[C1]: tests/test_execute_capture_settle.py::test_login_button_shows_logging_in_for_2s_the_shot_waits_for_it_to_clear — the new pending-wait path; (frame taken only after the pending state cleared, at least 2000 ms waited), ::test_page_that_never_settles_is_still_captured_and_the_step_says_so (total wait exactly 500 grace + 4000 bound, shot taken, one DOM row naming the step, not an `assert ` row), ::test_capture_settle_never_swallows_the_run_budget_deadline, ::test_page_whose_dom_cannot_be_probed_is_captured_without_waiting.
Tests[C2]: tests/test_execute_capture_settle.py::test_already_settled_page_is_captured_with_no_added_wait — a settled page adds no wait (events are exactly settle's 500 ms grace, mask, shot; one load-state call; no capture sleep), ::test_typing_into_a_field_does_not_pay_the_capture_settle_check; tests/test_execute.py::test_click_and_navigate_settle_before_the_screenshot_but_other_actions_do_not (load-state calls unchanged).
Tests[C3]: tests/test_execute_capture_settle.py::test_secret_inputs_are_masked_after_the_settle_wait_and_right_before_the_shot — pins mask-then-shot order after the wait; tests/test_browser.py and tests/test_screenshot_blank_retry.py (unchanged, green).
Falsification[C1]: scratch edits to evidence.py, restored from a saved good copy (scratchpad/at1305/evidence.py.good): `_capture_pending` made to return False -> red 3 (the 2 s case, the never-settles case, the budget case; 3 failed, 4 passed); the bound check `if elapsed >= bound_ms` -> `if False` -> red `test_page_that_never_settles_is_still_captured_and_the_step_says_so` (loop never ends, test killed by timeout/fail); pre-implementation run of the new file: 3 failed, 4 passed (the same three).
Falsification[C2]: the same `_capture_pending -> False` edit leaves the settled-page and fill tests green (4 passed), as expected; the settled-page test would fail if a sleep were added before the check (its event list is exact).
Falsification[C3]: real-Chromium probe of the detector script (scratchpad/at1305/probe_js.py): settled dashboard with "Loading" heading and "Saving tips" link -> not pending; `button disabled "Logging in..."` -> pending; "Signing in..." with unicode ellipsis -> pending; aria-busy -> pending; progressbar -> pending; hidden "Logging in..." button -> not pending (6 of 6 as expected). Masking order pinned by the test above.
Pre-check[C1]: e9980de3 uv run pytest tests/test_execute_capture_settle.py -> 7 passed t=1 blobs=tests/test_execute_capture_settle.py
Pre-check[C2]: e9980de3 uv run pytest tests/test_execute_capture_settle.py tests/test_execute.py -> passed t=2 blobs=tests/test_execute_capture_settle.py,tests/test_execute.py
Pre-check[C3]: e9980de3 uv run pytest tests/test_execute_capture_settle.py tests/test_execute.py tests/test_execute_assertions.py tests/test_execute_new_actions.py tests/test_browser_settle.py tests/test_probe_floor_matches_runtime.py tests/test_screenshot_blank_retry.py tests/test_failing_step_bundle.py tests/test_flake_probe.py tests/test_multi_role_session.py tests/test_browser_scroll_invariance.py tests/test_browser.py -> 162 passed t=29 blobs=tests/test_execute_capture_settle.py
Lint: e9980de3 `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> 4 violations, identical to base (none in touched files).
Metrics: start=2026-10-19T00:00:00Z end=2026-10-19T00:00:00Z wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=2 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=unavailable mutants=3 defects_unit=0 defects_6c=0 tests=7 tests_min=1

## How to verify (commands + expected)
- `uv run pytest tests/test_execute_capture_settle.py` -> 7 passed.
- the Pre-check[C3] list -> 162 passed.
- `uv run ruff check src tests scripts` -> All checks passed.

## Incident note
A `git stash` / `git stash pop` run in this worktree interleaved with a sibling builder's stash (the stash list is shared across worktrees) and briefly swapped uncommitted files between the at1305 and at1304-trace-redact trees. Verified afterwards: at1304 holds its own four files again (it had continued editing; its copy differs from the swapped snapshot, saved at scratchpad/at1305/at1304-foreign.patch), this tree's commit contains only the three files above.

## Live browser evidence
Not UI-touching - no route, template or static asset changed. The detector script was exercised in headless Chromium against static HTML (see Falsification[C3]); a live re-run of T-136 is not done here.

## Status: ready-for-check
