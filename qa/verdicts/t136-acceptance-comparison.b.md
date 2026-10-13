# Verdict: t136-acceptance-comparison (checker b)
Cycle checked: 1
Verdict: PASS (with two non-blocking defects)

Checked at e3f18c0f. Ran tests/test_acceptance_comparison.py (10 passed), ruff (clean), doctor (5 hits).

| Criterion | Result | Note |
|---|---|---|
| K3 no duplicated scoring | PASS | `_column` takes every figure from `bench.scorecard`/`BenchTrial.score`; no rate arithmetic in the stage or script |
| K4 comparative | PASS | both columns rendered side by side |
| K5 persisted | PASS | corpus and trials via ProjectStore; comparison written to `bench_comparison` path |
| K6 kind in artifact | PASS | typed `kind` carried per column; human kind unknown/autotester flagged |
| K7 ordering / independent vs prompted | PASS | counts recorded; prompted excluded from recall by `score`; unknown ordering flagged |
| K8 unavailable not default | PASS | `Measure` validator forbids value+reason both/neither; untimed and zero-finding tests red as designed |
| K9 completeness script | PASS | exit 2 on missing input naming it, 1 incomplete, 0 complete; never asserts a winner |
| K10 no-list mode | PASS | human column "unavailable (no human list)"; AutoTester recall carries the reason; FP rate and time are numbers; removing FP rate fails |
| Human list as files | PASS | `bench_human_trial` path + `list_bench_trials` pickup, tested with no code change |
| extra="forbid" | PASS | `Measure`, `ParticipantColumn`, `BugRow`; `AcceptanceComparison` inherits `Artifact` (not re-verified here) |
| Design rules | PASS | all files <=300 lines, docstrings present |

## Known issue: FP rate 1.0 with no adjudicated list
Acceptable, documented limitation, not a K6-K10 violation. K10 demands FP rate be a number "from `BenchTrial.score`" and score defines FP as any finding matching no corpus bug; the code obeys that and invents nothing. Weakness: the number is semantically "unadjudicated", and the artifact does not flag it (only the manifest does). Recommend (non-blocking): add a note field on the AutoTester FP measure when `human_list == "absent"`, e.g. "unadjudicated: no ground-truth bug list". Judging it is Umesh's.

## Defects
1. Doctor: qa/manifests/t136-acceptance-comparison.md:34 cites D-9999 and D-999 (dangling) -> 2 of 5 doctor hits come from this unit; the manifest claims "none from this unit". Reword the line.
2. Minor: stage `_column` override applies "no human list" to AutoTester detection/recall only when value is None; fine, but FP population label not annotated (see above).
