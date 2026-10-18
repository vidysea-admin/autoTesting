# Verdict - t210-session (T-210, MP11 MP12 MPI3)
Date: 2026-10-18 - Cycle checked: 0 - Checker: Mode A, single, bound to d:/autoTesting/.worktrees/t210-session
Policy-Version: proportional-verification/2026-10-18.15 - Checked: code 42fc8dc9, HEAD 9958beb6 (adds only the manifest). Base per git merge-base HEAD int/1017 = 36a87037 (dispatch named cff3ffe6, T-211 head; this branch does not contain it, so the diff is judged from 36a87037).

## Check plan
Diff = 3 new src files + 3 new test files, no UI, no deletions. Tier L (threads and per-role executors, real Chromium). Steps: re-run verify commands; one falsification per criterion in git-archive copies outside the worktree; MPI3 diff check; step 4c scope; read the src for MPI1/MPI5 and containment defects; note which oracle CORE-REQUESTs exist.

VERDICT: PASS
SCOREBOARD: 3/3 criteria met (MP11, MP12, MPI3), 3/3 invariants hold (MPI2, MPI3, MPI5; MPI1 not touched: finding is value-free)
TIER: L (concurrency: one thread and executor per role, multi_role_session.py:56-181; no auth boundary, so single checker stands)
FAILURES: none
CAPABILITY-COVERAGE: 2/2 rows reproduced (MP11, MP12)
LIVE-BROWSER: not-applicable (no UI surface); the live tests drive headless Chromium against the local fixture and ran green twice
ISSUES-WRITTEN: ISS-t210-session-1 (low), ISS-t210-session-2 (low)
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)

## Evidence
- Verify: pytest tests/test_multi_role_session.py tests/test_platform_links.py -> 27 passed, run twice (deterministic, no flaky claim, no repeat sweep needed). ruff on the 6 files clean; doctor 2 violations, both stale-generated MAP/SNAPSHOT as the manifest says; files 56-280 lines.
- MP11: live test drives two accounts on one host with the same cookie name: distinct sid values, 2 server sessions, per-context localStorage, 2 distinct existing profile dirs, and after alice logs out bob stays signed in (tests/test_multi_role_session.py:193-220).
- MP12: judge_hops matrix 7 cases; the live fixture follows 7 links in declaration order (redirect, SSO meta-refresh, control click, off-platform direct, off-platform mid-chain, 404, no account = not_reached); the off-platform ones carry a MultiRoleFinding of class OFF_PLATFORM_HOP (platform_links.py:214-227, value-free template, no host).
- Falsification MP11 (copy, green before 2 passed): manifest mutant (shared profile slug, multi_role_session.py:79) -> 2 failed but on the open() guard ValueError (:104), which reddens everything; so I also ran the same edit with the guard bypassed -> red on the named assertions (3 sessions but 1 distinct profile dir; profiles[0] != profiles[1]).
- Falsification MP12 (copy, green before 8 passed): judge_hops off-platform test -> if False -> red on test_judge_hops_matrix[off_platform_direct] and [off_platform_mid_chain] (stray-host assertion) and the live 7-link test.
- MPI3: git diff --name-only 36a87037..42fc8dc9 lists 6 new files, not schema/multi_role_enums.py nor schema/enums.py; LinkStatus lives in schema/link_outcome.py.
- MPI5/MPI2: sign_in types only {{SECRET:KEY}} placeholders and refuses a host outside the account platform before the browser moves (multi_role_session.py:183-202, test asserts placeholders and the refusal); fixture passwords are synthetic strings.
- Step 4c: 6 files, all listed in What changed, 0 lines removed, nothing renamed; no T-207/T-209 file, browser/session.py or parallel_run.py touched.
- RoleSessionPort: RoleSessions does NOT implement it (no perform/observe; schema/oracle_context.py is on int/1017 only). Not an MP11/MP12 criterion. Oracle CORE-REQUESTs filed against this session: fill_field (t219), TextSurface/LayoutSurface (t216), NetworkLogPort (t214); ReadTransport not found. Row ISS-t210-session-1.
- Full output: qa/evidence/t210-session/falsification.md

## Non-blocking
- ISS-t210-session-1 low: no RoleSessionPort adapter and the CORE-REQUESTs above have no wiring owner.
- ISS-t210-session-2 low: a mid-chain redirect contacts the stray host once (disclosed, test-pinned). Question, not a finding: a hop opened in a new tab is not watched (route is page-scoped, platform_links.py:149); I ran no probe.

EXPLANATION: Both criteria are met on my own re-runs, and each falsification went green then red on the named assertion; the diff adds six files and removes nothing. The two limits are disclosed or outside MP11/MP12, so they are ledger rows. Tests ran serially in one worktree, no shared lock.
Metrics: start=2026-10-18T20:28:17Z end=2026-10-18T20:37:33Z wall_min=7 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=420 mutants=1 defects_unit=0 defects_6c=0
