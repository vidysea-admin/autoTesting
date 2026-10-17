# Verdict - at858-hook-utf8 (AT-858, D-103)

Cycle checked: 0
Date: 2026-10-18 | Checker: claude-sonnet-subagent | Bound root: .worktrees/at858-hook-utf8 | Base 9aaf1fe5 (git merge-base HEAD int/1017) | Head 664fe839 (product 209bcb86)

## Plan
Tier L (enforcement-path hook, single checker, no dual trigger). Lane: not applicable (L, hook). Checks: (1) scope vs D-103 Changes-authorized; (2) re-run manifest verify commands; (3) one falsification for C1; (4) step 4c diff-scope read.

VERDICT: PASS
SCOREBOARD: 1/1 criteria met (AT-858), core-invariants touched: none broken
TIER: L (qa/hooks/mc-sessionstart.ps1 is an enforcement-path hook; one checker, no security/auth/tenancy/prod-write trigger)
FAILURES: none
CAPABILITY-COVERAGE: not-applicable (hook + test only)
LIVE-BROWSER: not-applicable (changed paths: qa/hooks/mc-sessionstart.ps1, tests/test_mc_sessionstart_loop_status.py)
ISSUES-WRITTEN: ISS-at858-chk-1 (low)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Evidence
- Scope (D-103 Changes-authorized: the hook "UTF-8 output encoding set before first output" and the UTF-8 decode test; "no hook logic, directive text or exit behaviour changes"): `git diff --name-only 9aaf1fe5 HEAD` = the two authorized files + the manifest only. Hook diff: +1 line `[Console]::OutputEncoding = UTF8` at file top (hook line 6), -1 line from the SNAPSHOT tail, +2 lines on the loop-status child (`PYTHONIOENCODING=utf-8`, `StandardOutputEncoding = UTF8`, hook lines 154-155). No directive text, branch, or `exit 0` change (tail still `exit 0`). The child lines are encoding configuration of the hook's own output and are necessary: in a copy with only them removed the new test went red on `the non-ASCII separator was lost or mangled`. Judged inside D-103 scope, not logic.
- C1 / AT-858 expected text (hook forces UTF-8 AND one test pins a non-ASCII byte AND decode utf-8/replace): met. Hook line 6 precedes the first Write-Output; test `test_hook_output_is_utf8_with_the_non_ascii_separator_intact` pins `ticks: 1 · last:` and no U+FFFD; `_run_hook` decodes `encoding="utf-8", errors="replace"`.
- Verify (my own runs, worktree, AUTOTESTER_TIMING_SCALE=4): `uv run pytest tests/test_mc_sessionstart_loop_status.py tests/test_mc_sessionstart_unclosed.py` run 1 = 16 passed, 1 failed (test_hook_prints_the_report_and_exits_zero_on_a_healthy_log: no `ticks: 1`, returncode 0) on a 90-100% CPU host; that test + the new one alone = 2 passed (50 s); rerun of all 17 = 17 passed (165 s). The red is the hook's fixed 15 s loop-status bound (hook line 138) tripping under load (symptom-consistent, not captured); not related to encoding. Filed as low ISS-at858-chk-1.
- `uv run ruff check src tests scripts` = All checks passed. `uv run autotester doctor` = exit 0 (only 2 advisory known-disputed warnings). Test file 298 lines, hook 192.
- Falsification F1 (copy under session scratchpad `.../scratchpad/fal858`, git-archive of HEAD, never the worktree): new test green in copy (1 passed) -> encoding line moved back to the SNAPSHOT tail -> RED on `AssertionError: the non-ASCII separator was lost or mangled` (`ticks: 1 U+FFFD last:`), restored (copy is the throwaway). Extra probe: child-encoding lines removed -> same red.
- Step 4c diff-scope: nothing removed except the relocated encoding line; no assertion removed or weakened (existing tests only gain the decode kwargs in `_run_hook`; one test added); no skip/xfail; no unlisted file.

EXPLANATION: The hook now sets UTF-8 before its first output and on its loop-status child, so the session-start lines leave as UTF-8 and the new test pins the non-ASCII separator; the extra child-encoding lines are encoding config required for the criterion and sit within D-103. One load-induced red of an existing test was not reproduced (rerun green) and is filed low. No push by the checker (instructed).

Metrics: start=2026-10-17T20:28:52Z end=2026-10-17T20:46:00Z wall_min=17 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-17.13 lane=normal check_s=1030 mutants=0 defects_unit=0 defects_6c=0
