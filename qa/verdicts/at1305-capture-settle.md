# Verdict - at1305-capture-settle (AT-1305)
Date: 2026-10-19 · Cycle checked: 0 · Checker: claude-sonnet-subagent (Mode A, single, tier M) · Base 8f2b6df3 (merge-base int/1017 verified) · Head checked 3f6efdfb (code e9980de3)

VERDICT: PASS
SCOREBOARD: 3/3 criteria met, 3/3 invariants hold (E1-E5 untouched; masking order pinned)
TIER: M (multi-file timing behaviour: evidence.py, execute.py, one new test file)

## Plan and evidence
- Scope: `git diff 8f2b6df3..HEAD --name-only` lists exactly the manifest, src/autotester/browser/evidence.py, src/autotester/stages/execute.py, tests/test_execute_capture_settle.py (no foreign worktree files from the stash incident). Diff read in full (step 4c).
- Re-ran: new file 7 passed; with test_execute.py 16 passed; the 12-file Pre-check[C3] set 162 passed (27 s); `ruff check src tests scripts` clean; `autotester doctor` 4 violations, same as base, none in touched files. evidence.py 190 lines, execute.py 287 (cap 300).
- C1 met: `settle_for_capture` polls the DOM pending probe in 250 ms steps up to CAPTURE_SETTLE_MS=4000; at the bound it records a DOM row "page did not settle within 4000ms before capture: stepNN-action" (not an `assert ` row) and the shot is still taken (execute.py:155-158). Falsified: `_capture_pending -> False` -> red 3 (2 s case, never-settles, budget); bound `bound_ms*100` -> red `test_page_that_never_settles...` (total wait != 500+4000).
- C2 met: settled page adds one DOM read and no sleep (events exactly wait/mask/shot, timeouts == [500]); fill never pays the check (_TRANSITIONING). Falsified: fixed `wait_for_timeout(300)` before the loop -> red `test_already_settled_page_is_captured_with_no_added_wait`.
- C3 met: Session.screenshot and masking untouched in the diff; test pins mask-then-shot after the last wait. Falsified: removing the mask call in Session.screenshot -> red on both mask-order tests.
- Budget brake: settle_for_capture's own `session._timeout()` calls and `except RunBudgetExceeded: raise` are not swallowed (test passes; mutant c1 turns it red).
- Detector in real Chromium on static HTML (no live site): heading "Loading" False, "Saving tips" link False, button "Logging in..." True, unicode ellipsis True, hidden control False, aria-busy True, "Loading... please wait" paragraph False.

## Judgement: static "Loading..." label
A permanent visible `<a>Loading...</a>` (or button/status) reads as pending (probed True). Cost is the 4 s bound per transitioning step plus one DOM note row; capture is never blocked, the row is not an assertion input, and the run budget still applies. Not a correctness defect against C1-C3 (the bound is the specified safety); filed as low AT-1330.

FAILURES: none
CAPABILITY-COVERAGE: not-applicable (no capability rows; timing behaviour covered by criteria falsification)
LIVE-BROWSER: not-applicable (no route/template/static asset changed); detector probed in headless Chromium on static HTML
ISSUES-WRITTEN: AT-1330 (low, static Loading label costs the bound each step), AT-1331 (low, _capture_pending `except Exception` also swallows RunBudgetExceeded from session.page; benign since screenshot re-raises it)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: All three criteria are evidenced by re-run tests and one green-before/red-after falsification each in copies under D:/autoTesting/.work/tmp/at1305-chk. The diff is confined to the declared files; two low rows filed, neither blocks.
Metrics: start=2026-10-19T00:00:00Z end=2026-10-19T00:00:00Z wall_min=unavailable agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=4 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=unavailable mutants=0 defects_unit=0 defects_6c=0
