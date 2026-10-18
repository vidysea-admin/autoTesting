# Verdict - t218-ceo-bench (T-218 fixture leg)

Cycle checked: 0
Checked: 2026-10-19 by /checker (claude-sonnet-subagent), bound to D:/autoTesting/.worktrees/t218-ceo-bench
Head checked: bba48b2e (code d6fb0ed8); base cff3ffe6 = `git merge-base HEAD int/1017`
Policy-Version: proportional-verification/2026-10-18.15

## Check plan
Logic + schema, no UI, no auth/tenancy/data-write code: re-run the 43 new tests, falsify one clause per criterion
in copies outside the worktree, read the full diff (step 4c), judge MP29/MP30/MP31-fixture against the contract
and the intent "Scoring" rule. No full suite (no existing module edited). Quick lane: not applicable (3 criteria).

## Evidence
- `uv run pytest tests/test_ceo_benchmark.py tests/test_ceo_run_evidence.py` -> 43 passed (0.41 s).
- `uv run ruff check src tests scripts` -> All checks passed. `autotester doctor` -> 2 violations, both stale-generated (docs/MAP.md, docs/SNAPSHOT.md), none from the new files.
- Step 4c: `git diff cff3ffe6..HEAD --stat` = the 7 manifest files + the manifest; 1093 insertions, 0 deletions; nothing removed or renamed, no unlisted file. File sizes 48-298 lines (<= 300).
- MP29: `stages/ceo_benchmark.py:96` and `:111` call `bench.scorecard` (same call as `acceptance_comparison.py:57`); no division in the module (AST test); tests assert 3/6 overall, 1/1, 1/3, 1/2 per priority (P0 first), FP 1/4 over adjudicated only, equal to a hand-built `bench.scorecard` result, 14 technique lines with owner units, `not run` (never 0) when an owner is not built/not run/errored/absent.
- MP30: `ordering_detail` (`ceo_benchmark.py:79-88`) requires matching sha256 and strictly earlier commit time, else the trial ordering is `unknown` and bench itself answers `ordering not recorded`; derived-scenario matches leave recall (2/5, `derived_excluded` 1); the dumped scorecard holds only counts, the sha256 and fixed-vocabulary strings (test walks every string).
- MP31 fixture: `run_evidence_problems` checks 8 accounts, one login per account on its own platform, every declared platform, approval found / same project / intact / signature verifies (missing key is a problem) / unexpired at start, headed, all 13 `OracleName` once.

## Falsification (floor: 1 per criterion; copies under scratchpad/chk218, PYTHONPATH to the copy, module path printed from the copy, green before)
| Criterion | Named test | Edit in copy | Green before | Red after |
|---|---|---|---|---|
| MP29 | test_mp29_unadjudicated_is_neither_tp_nor_fp | FP trial takes every finding (`if True`, ceo_benchmark.py:110) | 1 passed | red: `assert 1.0 is None` (FP rate read 1.0) |
| MP30 | test_mp30_without_the_recorded_ordering_recall_is_unavailable | commit-after-start check removed (`if False`, :86) | 4 passed | red x2 on `card.ordering == "list committed after run start"` |
| MP30 (derived) | test_mp30_a_derived_from_finding_scenario_is_excluded_from_recall | `derived: set[str] = set()` (:102) | 1 passed | red: `assert (3, 6) == (2, 5)` |
| MP31 | test_mp31_the_run_must_be_headed | headed check removed (`if False`, ceo_run_evidence.py:94) | 1 passed | red on `any(... "headed" ...)` |
Each red is on the assertion the test is named for, not an import error. Bound tree untouched.

## Judgement calls in the manifest
1. Extra ceo_* schema/stage files: accepted. Design rule (shape in schema/, file <= 300) requires them; names are disjoint from every other group; the AST test pins no extra scorer module.
2. Derived match removed from numerator AND denominator: accepted. Contract/intent say the match is "excluded from recall"; both readings satisfy the Verify clause, and removing the item from both sides does not penalise the run for contamination it did not cause. Not a FAIL.
3. Technique `ran` only if every owner ran: accepted (conservative; reads `not run`, never 0, as MPI6 demands).
4. `committed_at` supplied by the caller: accepted for the fixture leg; the real commit-time lookup belongs to MP35.

## Not FAIL, recorded as low ledger rows
- AT-1220: scorecard `wall_time_s` is `run.duration_s` passed through (ceo_benchmark.py:153-154), not read from the bench score's `duration_s`; MP29 prose says wall time comes from `stages/bench.py`. Same value today (bench echoes it), so no wrong behaviour.
- AT-1221: `_approval_problems` (ceo_run_evidence.py:60-76) does not require `production=True` or a matching target; MP35 asks for a signed production RunApproval. MP31 fixture text asks only for a valid signed one, so this is open for the MP35 live leg, not this unit.

## Result
MP29, MP30 and the MP31 fixture leg are met on evidence I produced. MP31 live and MP35 stay pending (credential and RunApproval gates), which is not a FAIL; T-218 must not close until MP35 or Umesh's written acceptance of the fixture leg. MPI1-MPI6: no violation found in the changed code (no raw ids, text or secrets in any committed shape).

VERDICT: PASS
SCOREBOARD: 3/3 criteria met (build leg; MP31 live and MP35 gated, pending), 6/6 invariants hold
TIER: L (live acceptance is a production run; the leg checked is fixture scoring only, no L trigger in the changed files)
FAILURES: none
CAPABILITY-COVERAGE: 4/4 rows reproduced (green before, red after, in copies)
LIVE-BROWSER: not-applicable (schema and stage modules plus tests only)
ISSUES-WRITTEN: AT-1220, AT-1221
EXECUTOR: claude-sonnet-subagent (checker: claude-sonnet-subagent)
EXPLANATION: Scoring goes through bench.scorecard with no division, ordering and derived-scenario rules behave as the contract says, and the run-evidence check rejects each missing role, platform, approval property, headed flag and oracle. Falsifications went red on the named assertions.
Metrics: start=2026-10-19T01:54:30+05:30 end=2026-10-19T02:03:00+05:30 wall_min=9 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=4 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=510 mutants=1 defects_unit=0 defects_6c=0
