# Verdict -- t171-goal-pin

**Cycle checked:** 0
**Date:** 2026-10-07
**Checker:** fresh-context Mode A, bound to D:/autoTesting/.worktrees/t171-goal-pin, HEAD 6d1a826b (Base bd2fe8f4; master e633bc69 merged)
**Policy-Version:** proportional-verification/2026-10-06.6

## Check plan (step 0)
- Diff `git diff master -- tests .goal` = exactly one line, tests/test_goal_contract_registration.py:42 (`test_permission_surface.py` -> `test_permission_coverage.py`). `git diff bd2fe8f4 -- tests .goal` additionally shows the goal.json/dashboard hunks, which the merge of master already carries (branch .goal equals master's .goal; judged below).
- Signals: protected test change (oracle expectation edited) -> TIER L, one checker, no dual (no security/auth/data write). No UI, no persona walk, no live browser.
- Checks: manifest verify commands, one full suite, ruff, doctor, the 2 falsification rows in throwaway copies, diff scope (4c), T-185 PASS verdict lookup.

TIER: L (protected test change: tests/test_goal_contract_registration.py:42 edits an expected oracle value; no product code in the diff)

## Evidence
1. Verify commands re-run in the bound tree: `pytest tests/test_goal_contract_registration.py tests/test_goal_done_checks.py tests/test_goal_done_check_shapes.py` -> 10 passed; `pytest tests/test_permission_coverage.py` -> 15 passed; ruff -> All checks passed; doctor -> 1 violation (stale-generated docs/MAP.md; docs/ and src/ are identical to master, so it predates the unit; filed ISS-t171-goal-pin-2, low). The manifest's 7-violation count was at the older base; merging master cleared the other 6.
2. Full suite (one run, no -q): 1 failed, 2200 passed, 5 skipped, 14 xfailed in 1510s. The one failure is tests/test_ui_runs_serial_entry_mix_live.py::test_a_serial_run_mixing_an_entry_case_with_ordinary_cases_does_not_500 (403 'no approval exists' from the live_case gate, routes_runs.py _require_live_case_approval, fix 1fdba241). It reproduces alone (1 failed in 2.77s), does not read goal.json, and src is identical to master, so it is not caused by this unit. Filed ISS-t171-goal-pin-1 (medium, stale test vs the approval gate). Not a criterion of this unit.
3. Pin is not weakened: the oracle still asserts `actual == expected` on the (deps, done_check cmd) of T-171; the expected file now exists on disk (tests/test_permission_coverage.py, 15 passed, T-171's checked-PASS test) whereas the old one never existed. goal.json T-171 cmd matches the pin, and test_no_done_task_has_a_done_check_naming_a_file_that_does_not_exist guards the same property.
4. Falsification (copies of the tree outside the bound root, venv python of the bound tree, single node each):
   - Row 'pin' (test_goal_contract_registration.py::test_revised_goal_contract_is_registered): copy green 1 passed; test line 42 reverted to test_permission_surface.py -> 1 failed (assert actual == expected dict mismatch); restored -> 1 passed.
   - Row 'goal.json cmd': copy green 2 passed (registration + done-check-file test); goal.json T-171 cmd -> test_permission_surface.py -> done-check test FAILED with "these DONE tasks' done_checks name a file that does not exist on disk: {'T-171': ['tests/test_permission_surface.py']}" and the registration test FAILED; restored -> 2 passed. Bound tree untouched (git status clean apart from my verdict/issues/checkpoint files).
5. Diff scope (4c): against master the diff touches only the one test line; against bd2fe8f4 everything else is master's own merged records (docs, qa, goal.json), none authored by this unit. Nothing deleted or renamed by the unit.
6. T-185 flip and progress block (82/59/23/72): not introduced by this branch relative to master (goal.json is byte-identical to master's). Independently: qa/verdicts/at408-416-scroll-reach.md is a cycle-1 PASS (committed edbee6b2), so a T-185 'done' flip is justified; progress counts are self-consistent with the tasks (the registration test asserts total/done/pending/percent and passes; dashboard shows 59/82, 72%, Remaining (23)).

```
VERDICT: PASS
SCOREBOARD: 2/2 criteria met (pin repoint; goal.json done_check names a real file), 0/0 invariants applicable
TIER: L (protected test change: tests/test_goal_contract_registration.py:42; no product code changed)
FAILURES (if any): none
CAPABILITY-COVERAGE: 2/2 rows reproduced in throwaway copies (green-before, red-after on the same node, restored)
LIVE-BROWSER: not-applicable (changed paths: tests/test_goal_contract_registration.py)
ISSUES-WRITTEN: ISS-t171-goal-pin-1 (medium, pre-existing stale live test), ISS-t171-goal-pin-2 (low, stale docs/MAP.md)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The pin now names tests/test_permission_coverage.py, which exists and passes 15/15, and both falsification rows go red on the named nodes when reverted. The T-185 flip and the progress block are already on master and backed by the T-185 cycle-1 PASS verdict. The one full-suite failure and the doctor MAP.md violation predate the unit and are ledger rows.
Metrics: start=2026-10-07T01:58:34+05:30 end=2026-10-07T02:28:00+05:30 wall_min=30 agent_min=unavailable blocked_min=0 suite_runs=1 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6
```

PASS closes no goal task: T-171 was already done (checked-PASS qa/manifests/t171-permission-surface-coverage.md) and this unit maps to no new task id.
