# Verdict - at889-login-session-race (Mode A, repair check)

Date: 2026-10-17 · Cycle checked: 1 · Bound to: D:/autoTesting/.worktrees/at889-login-session-race
Policy-Version: proportional-verification/2026-10-15.12 · Base: 69ebfae7 (git merge-base HEAD master) · Repair base: 0a88215b (ancestor of HEAD, verified) · Head checked: d655bb90 (code 97e918ae)
Archived: cycle-0 verdict renamed (git mv) to qa/verdicts/at889-login-session-race.r0-1.md; its narrative was not read.

## Check plan
Tier S confirmed (single file explore.py + one test file, no data write, no schema/public API; crawler login stage of a test target, not the product's own auth; one checker per manifest). Plan: (1) re-run the failed criterion C1 and the cycle-0 C2 tests plus the login test files the repair touched; (2) read the repair diff in full and scan the whole-unit diff for out-of-scope files; (3) one falsification per repaired criterion, in a copy outside the worktree; (4) ruff + doctor. No UI, no walks (not UI-touching).

## Evidence (all run by this checker)
- `uv run --no-sync pytest tests/test_explore_login_bypass.py tests/test_explore_login_wall.py tests/test_explore_login_wall_bounds.py` -> 33 passed (26.5 s). Includes `test_a_two_step_login_whose_second_fill_fails_off_the_login_path_is_login_failed` (the cycle-0 failing shape: NAVIGATE /signin, FILL id, CLICK, FILL password fails -> LOGIN_FAILED, stop_reason names "password"), `test_a_live_session_still_drains_a_login_api_401_before_proceeding`, and the cycle-0 C1/C2 tests (race redirect after precheck still reaches the crawl; stop_reason names the case error).
- `ruff check src tests scripts` -> All checks passed. `autotester doctor` -> clean (two known D-087 advisories only). explore.py = 300 lines (limit 300).
- Repair diff read in full (src/autotester/stages/explore.py:84-87, :105-111; tests). `_live_session_midcase` now returns True only when the failing step is a FILL, the case has a login NAVIGATE target, every step before the failing one is NAVIGATE/WAIT/ASSERT, and the current path differs from the login path. A live-session reading no longer returns early: it falls through to the AT-528 401 drain (explore.py:96-103). Read at lines 84-111 in this check.
- Contract compare (AT-889 issue text, qa/issues.jsonl): "a persistent profile with a live session proceeds to the crawl" -> met for the issue's shape (NAVIGATE then FILL; cycle-0 C1 test green); "a login_failed stop_reason names the login case's error" -> met (explore.py:86-87 and :200; C2 test green).

## FALSIFY (C1, the repaired criterion)
Copy outside worktree: scratchpad chk889c1 (git archive of src, tests, scripts, pyproject; PYTHONPATH pinned to the copy, module path verified).
- green in copy @97e918ae: the two new tests -> 2 passed.
- explore.py := `git show 0a88215b:...` -> both RED on `assert <CrawlStatus.COMPLETED> is <CrawlStatus.LOGIN_FAILED>` (named assertion, not an import error): 2 failed.
CAPABILITY-COVERAGE: 1/1 repaired criterion reproduced (plus the second new test, same revert).

## DIFF-SCOPE (step 4c)
Repair diff 0a88215b..HEAD touches only explore.py, tests/test_explore_login_bypass.py and the manifest. Whole-unit diff 69ebfae7...HEAD: explore.py, the test file, manifest, cycle-0 verdict/checkpoint/evidence only; no unlisted product file. Removed lines: the cycle-0 early `return True` inside the failing branch (replaced by the guarded condition + fall-through), no function/class/test/export deleted.

## Non-blocking observation (not a FAIL)
PROPOSED-ISSUE: {"severity": "low", "feature": "explore", "type": "race", "title": "AT-889 live-session reading (explore.py:_live_session_midcase) requires every step before the failing FILL to be NAVIGATE/WAIT/ASSERT, so a login case that CLICKs to reveal the form before its first FILL still ends login_failed when the race redirect lands after the precheck", "evidence": "explore.py:105-111 read in this check; conservative by design after the cycle-0 FAIL, not run as a failing command"}
(Id not minted here to avoid colliding with other worktrees appending to qa/issues.jsonl; the maker mints it.)

VERDICT: PASS
SCOREBOARD: 2/2 criteria met (C1, C2), 0/0 invariants touched beyond core-invariants (no schema, no secrets, file <= 300 lines)
TIER: S (single file in the explorer login stage, no data write/schema/public API)
FAILURES: none
CAPABILITY-COVERAGE: 1/1 repaired criterion reproduced
LIVE-BROWSER: not-applicable (src/autotester/stages/explore.py, tests/test_explore_login_bypass.py)
ISSUES-WRITTEN: none (one PROPOSED-ISSUE low above)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: The cycle-0 FAIL shape (two-step login whose second FILL fails off the login path) now ends LOGIN_FAILED with the case error named; the race shape from AT-889 still reaches the crawl and a live session still drains the AT-528 401. Both new tests go red on the cycle-0 explore.py and green on the repair, so the fix is isolated by the named assertion.
Metrics: start=2026-10-17T16:36:00Z end=2026-10-17T16:44:00Z wall_min=8 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=1 cycle=1 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=480 mutants=0 defects_unit=0 defects_6c=0
