# Manifest — at889-login-session-race

**Contract:** `qa/contracts/explore.md` (login bootstrap, X10, X18) · `qa/contracts/core-invariants.md`
**Goal task:** none (issue-driven, AT-889)
**Date:** 2026-10-17
**Status:** ready-for-check
**Fix cycle:** 0 of max 2
**Dual check:** no
**Issues addressed:** AT-889
**Executor:** claude-sonnet-subagent
**Executor rationale:** Tier S single-file fix inside `explore.py`; no external executor warranted.

## What changed
- `src/autotester/stages/explore.py:84-90` — `_bootstrap_login`: when the login case does not complete, first ask `_live_session_midcase`; if true return True (proceed to the crawl); else set `stop_reason` to `login case did not complete (AT-889): <RawResult.error>`.
- `src/autotester/stages/explore.py:106-112` — new `_live_session_midcase`: the failing step is a FILL and the page is no longer on the login path -> a live session appeared after the one-shot precheck (race with a client-side redirect).
- `src/autotester/stages/explore.py:200` — `_login_failed_reason` keeps the case error in `stop_reason` (precheck cause still appended; AT-528 verbatim path unchanged). File is exactly 300 lines.
- `tests/test_explore_login_bypass.py` — two tests: `test_a_session_redirect_after_the_precheck_still_reaches_the_crawl` (C1), `test_a_login_failed_stop_reason_names_the_login_case_error` (C2). Deterministic: the redirect is bound to the second visit of /signin, no sleeps.

Status: ready-for-check

## Verification scope
Policy-Version: proportional-verification/2026-10-15.12
Tier: S (auth-adjacent crawler login, single file) — single checker
Base / checked state: base 69ebfae7, fix 05595c71, clean worktree
Gate answers: none (no new module; `qa/gates/new-module-authorization.md` not needed)
Affected tests / full-suite trigger: `tests/test_explore_login_bypass.py`, `tests/test_explore_login_wall.py`, `tests/test_explore_login_wall_bounds.py` (31 passed); none for full suite. The builder runs no full suite.
Pre-check[C1]: 05595c71 uv run pytest tests/test_explore_login_bypass.py::test_a_session_redirect_after_the_precheck_still_reaches_the_crawl -> 1 passed t=23 blobs=tests/test_explore_login_bypass.py:a74b68a
Pre-check[C2]: 05595c71 uv run pytest tests/test_explore_login_bypass.py::test_a_login_failed_stop_reason_names_the_login_case_error -> 1 passed t=21 blobs=tests/test_explore_login_bypass.py:a74b68a
Metrics: start=2026-10-17T12:30:00Z end=2026-10-17T12:46:00Z wall_min=16 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=44 mutants=2 defects_unit=0 defects_6c=0

## How to verify (commands + expected)
- `uv run pytest tests/test_explore_login_bypass.py tests/test_explore_login_wall.py tests/test_explore_login_wall_bounds.py` -> expected: 31 passed
- `uv run ruff check src tests scripts` -> expected: All checks passed!
- `uv run autotester doctor` -> expected: `doctor: clean`

## Actual outputs (from maker's own run)
- the three login test files: `31 passed, 2 warnings in 29.04s`
- `uv run ruff check src tests scripts`: `All checks passed!`
- `uv run autotester doctor`: `doctor: clean` (only the two known advisory D-087 notes)
- `wc -l src/autotester/stages/explore.py`: 300

## Capability coverage (each new claim -> its isolating falsification)
Falsifying edit for both rows: in a throwaway copy OUTSIDE the worktree (scratchpad `fals889/`), `src/autotester/stages/explore.py` replaced by `git show 69ebfae7:...` (the fix hunks reverted), then restored.

| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| C1 | A persistent profile with a live session always proceeds to the crawl, even when the redirect lands after the precheck | `tests/test_explore_login_bypass.py::test_a_session_redirect_after_the_precheck_still_reaches_the_crawl` | revert `_bootstrap_login` + `_live_session_midcase` to base | green@05595c71: `7 passed` (file). red@base: `FAILED ...::test_a_session_redirect_after_the_precheck_still_reaches_the_crawl` — `AssertionError: assert <CrawlStatus.LOGIN_FAILED: 'login_failed'> is <CrawlStatus.COMPLETED: 'completed'>` |
| C2 | A `login_failed` stop_reason names the login case's error | `tests/test_explore_login_bypass.py::test_a_login_failed_stop_reason_names_the_login_case_error` | same revert | green@05595c71: `7 passed`. red@base: `FAILED ...::test_a_login_failed_stop_reason_names_the_login_case_error` — `AssertionError: assert 'locator not found' in 'login case did not complete'` |

Base run summary: `2 failed, 5 passed` (the five pre-existing tests stay green on base, so the two reds isolate the fix).

## Live browser evidence
Not UI-touching — no surface changed: `src/autotester/stages/explore.py` (crawler login stage) and `tests/test_explore_login_bypass.py` only; behavior covered by the fake-session tests above.
