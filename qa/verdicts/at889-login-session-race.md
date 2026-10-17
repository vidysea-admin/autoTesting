# Verdict: at889-login-session-race
Cycle checked: 0
Date: 2026-10-17 · Bound to: D:/autoTesting/.worktrees/at889-login-session-race · Base 69ebfae7 (git merge-base HEAD master) · Head checked 05595c71 (+ manifest commit fafa2d1d)

## Check plan
Tier S as dispatched; raised to L-class scrutiny for the timing/auth-adjacent login path (checker may raise, never lower). Logic changed only: re-run the 3 login test files, ruff, doctor; one falsification per criterion (C1, C2) in a copy; step 4c diff read in full; targeted counterexample for the dispatch hint (real login failure read as a live session). No UI, no persona walk, no live browser (crawler stage, fake-session tests). Lane: normal (lane disabled; Lane exit: none claimed, normal check run).

## Evidence (all produced by this checker)
- `uv run pytest tests/test_explore_login_bypass.py tests/test_explore_login_wall.py tests/test_explore_login_wall_bounds.py` -> 31 passed
- `uv run ruff check src tests scripts` -> All checks passed!; `uv run autotester doctor` -> doctor: clean; explore.py = 300 lines
- Falsification (copy outside worktree, explore.py := `git show 69ebfae7:...`): `test_a_session_redirect_after_the_precheck_still_reaches_the_crawl` red on `assert LOGIN_FAILED is COMPLETED`; `test_a_login_failed_stop_reason_names_the_login_case_error` red on `'locator not found' in 'login case did not complete'`; both green on the fix. Floor met.
- Diff scope (4c): 3 files (explore.py, test file, manifest); only removed line is the `reason = "login case did not complete"` literal. Nothing else removed.
- Counterexample (hint): evidence/at889-login-session-race/probe-result.md. A login case NAVIGATE /signin, FILL id, CLICK submit, FILL password, where the submit lands the app on a non-login path and the password field is absent: base = LOGIN_FAILED, fix = `completed | frontier empty`.

## Finding
`explore.py:109-111` (read in this check): `_live_session_midcase` treats ANY failing FILL step as "live session" when the page path differs from the login path. It does not require that the case has not itself navigated the page. After the case's own CLICK/submit, a FILL failure off the login path is a real login failure (rejected or locked login that redirects, a multi-step flow whose next step's selector broke), not a pre-existing session. The branch also returns True before the AT-528 401 guard (`explore.py:96-102`), so a first-party 401 is never consulted. Result: a never-authenticated crawl reads COMPLETED, the exact false success X18 and AT-528 forbid (`qa/contracts/explore.md` X18: a crawl that never gets past login never reads COMPLETED).

VERDICT: FAIL
SCOREBOARD: 1/2 criteria met (C2 met; C1 met for the issue's own scenario but introduces a correctness regression), invariants: X18/AT-528 intent violated for multi-step login cases
TIER: S dispatched; scrutinised as L (auth-adjacent timing path)
FAILURES:
- [C1] sev: medium · `explore.py:109-111`+`:85-86`: FILL failure after the case's own submit, page off login path, is read as a live session and the crawl reports COMPLETED (reproduced, probe above, base=LOGIN_FAILED, fix=COMPLETED) · fix direction: only accept the live-session reading when the failing FILL precedes every CLICK/other page-changing step of the case (e.g. no earlier non-NAVIGATE step ran), and run the AT-528 401 drain before returning True; add a test for a two-step case whose submit leaves the login path · issue: AT-889 (reopened, same row; no new id minted to avoid a ledger collision in the worktree)
CAPABILITY-COVERAGE: 2/2 rows reproduced (green on fix, red on base)
LIVE-BROWSER: not-applicable (src/autotester/stages/explore.py, tests/test_explore_login_bypass.py; fake-session tests)
ISSUES-WRITTEN: none
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: C2 and the issue's literal redirect-after-precheck scenario work, but the new helper is broader than the evidence it relies on: it cannot tell a pre-existing session from a login the case itself just failed. A reproducible counterexample turns a base LOGIN_FAILED into COMPLETED. Lane exit: none (lane disabled, normal check).
Metrics: start=2026-10-17T14:05:00Z end=2026-10-17T14:20:00Z wall_min=15 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=900 mutants=0 defects_unit=1 defects_6c=0
