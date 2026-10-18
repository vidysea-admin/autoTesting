# Verdict - t211-crossrole (T-211, G11-5)

Cycle checked: 0
Date: 2026-10-18 (checker, Mode A, single check, bound to D:/autoTesting/.worktrees/t211-crossrole)
Policy-Version: proportional-verification/2026-10-18.15
Checked state: code 4425f762, HEAD cff3ffe6 (manifest-only commit above it). Base 36a87037 verified as an ancestor of HEAD.
`git merge-base HEAD int/1017` = 722bf3df, earlier than the named Base (sibling T-207/T-209 commits sit between). Judged on 36a87037..HEAD as dispatched; the unit's own range is 2 commits.
Checkpoint: qa/checkpoints/t211-crossrole.md

## Check plan
Logic + timing change, no UI, no data write, no auth: affected tests (3 new files, nothing existing edited), 1 falsification per criterion (MP13, MP14, MP15) in copies outside D:/autoTesting, step 4c diff-scope read, MPI1 and MPI3 invariants, independent timing probes on the injected clock (plus a real-clock sanity pass). No UI surface, no personas, no full suite. Lane check n/a (L).

## Evidence
- Step 3: `uv run pytest tests/test_cross_role_runner.py tests/test_oracle_registry.py tests/test_cross_role_schema.py` -> 56 passed (3.2 s). `uv run ruff check src tests scripts` -> All checks passed. `uv run autotester doctor` -> 2 violations, both `stale-generated` (docs/MAP.md, docs/SNAPSHOT.md), as the manifest says; no design-rule violation in the new files.
- MPI3: `git diff --name-only 36a87037..4425f762` lists the 10 files of the manifest and not `schema/multi_role_enums.py`.
- Step 4c: 11 files in 36a87037..HEAD (10 + manifest), 1158 insertions, 0 deletions; nothing removed or renamed; every file is in "What changed".
- Falsification (copies in scratchpad/t211chk, each green first in the copy, then the edit, then red on the named assertion):
  - MP13: window widened by 2.5 s (break condition and sleep bound) -> `test_mp13_same_view_fails_at_window_1_with_window_and_last_observation` green -> red at `assert outcome.verdict is AssertVerdict.FAILED` (got PASSED, observed_s=2.0).
  - MP14: early break at within_s-1 plus the elapsed-window guard removed -> `test_mp14_absent_passes_only_after_the_full_window_with_no_match` green -> red at `assert outcome.observed_s == approx(4.0)` (got 3.0).
  - MP15: `not built` reported as `not run` -> `test_mp15_one_absent_module_is_reported_not_built_and_not_omitted` green -> red at `by_oracle[ABSENT].state is OracleState.NOT_BUILT`.
- Timing probes on the fake clock (probe.py, not in the repo): present, window 2, view at 2.0 -> passed observed_s 2.0; at 2.01 -> failed. Absent, window 4, thing at 4.0 -> failed ("appeared at 4s"); at 4.01 -> passed with observed_s 4.0. A frozen clock cannot pass an absent assertion (test). Real SystemClock, 30 runs (present at 0.25 s, window 1; absent window 0.4): 0 odd, so perf_counter sleeps never ended an absent window early.
- MPI1: a phone-shaped observation is recorded as `[withheld: looks like personal data]`; step errors and oracle errors are exception types only (tests plus probe).

## Criteria
- [MP13] met. Role-tagged steps run in order, assertion names observer/channel/expectation/within_s, polls on the injected clock, records `observed_s`; 2 s fixture passes at 5, fails at 1 with window and last observation.
- [MP14] met. `absent` passes only at elapsed >= within_s with no match and no observer error; `present` never matched fails with window and last observation.
- [MP15] met. All 13 `OracleName` values are in every summary (validator refuses an omission); an absent module is `not built`; real tree lists 13 x `not built`.
- [MPI1] holds. [MPI2] holds (synthetic fixtures). [MPI3] holds.

## Judgement calls in the manifest
1 window semantics (inclusive last look): agreed and probed. 2 erroring observer cannot prove absence: agreed, in the spirit of MP14. 3 failed step -> `not_run`: agreed. 4 `AssertionOutcome` not `MultiRoleFinding`: accepted, no finding class exists in the T-207 enums (MPI3); the oracle builders map it. 5 shared schema files: accepted, each docstring states one job. 6 poll bound: agreed. 7 registry on the real tree: agreed. 8 doctor: confirmed.

## Findings (non-blocking, ledger rows written to qa/issues.jsonl)
- AT-1211 medium: a present match first seen after the window is PASSED with `observed_s > within_s` (runner:103-117, _verdict:86-88). Probe: observe() that blocks 3 s, view up at 2 s, within_s=1 -> passed, observed_s=3.0. Reachable only through a port whose look blocks, which the Protocol forbids ("once") and no port yet exists; needs the late-match rule decided before T-210's port is wired. Not a FAIL: the MP13 fixture and any prompt port are correct.
- AT-1212 low: a non-Observation return from a port raises AttributeError out of run_scenario (runner:113, outside `_look`'s try); `Observation.detail` over 200 chars raises in the port so the runner's truncation is unreachable and the swallowed raise looks like "never matched"; `RoleStep` omits the platform / flow ref / handles that intent.md:157 lists. Oracle-builder documentation points, not MP13-15.
- The ids AT-1211/1212 were chosen outside the sequential range because 15 sibling wave worktrees mint from 1025; renumber at merge if the AT-676 guard objects.
- Process: wall time passes the L 45 min deadline in `date` terms (the machine clock; `autotester doctor` alone took over 2 min and tool latency was high); all mandatory evidence finished, so no CONTINUE-NEEDED.

VERDICT: PASS
SCOREBOARD: 3/3 criteria met, 3/3 invariants hold
TIER: L (concurrency/timing: polling to within_s, src/autotester/stages/cross_role_runner.py:103-117)
CAPABILITY-COVERAGE: 3/3 rows reproduced
LIVE-BROWSER: not-applicable (schema and stage modules plus tests only)
ISSUES-WRITTEN: AT-1211, AT-1212
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
Metrics: start=2026-10-18T18:36:10Z end=2026-10-18T20:09:00Z wall_min=93 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=3 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=5570 mutants=0 defects_unit=0 defects_6c=0
