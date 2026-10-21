# Verdict — at1381-fp-coverage

**Verdict: PASS.** Cycle checked: 0. Checker: Mode A, fresh context. Bound root `D:/autoTesting/.worktrees/at1381-fp-coverage`.
Base c437d3a5, head 8f23e561 (code 92421187), integration branch int/1019. Policy proportional-verification/2026-10-19.17.
Contract: manifest brief criteria C1-C3, `qa/gates/at1381-fp-denominator.md` Answered line, `qa/issues.jsonl` AT-1381, `qa/contracts/bench.md` K9/K10.

## Check plan
TIER: M (schema read `schema/bench.py` + `schema/acceptance.py`, public script output; no L trigger, no auth/data-write/config). Dual check: no.
Logic changed: affected tests + falsification floor. UI changed: no (0 UI files in the diff), so no Mode D walk. No LLM, no live call.

## Re-run (my own)
1. Manifest verify command on head 8f23e561: `uv run pytest tests/test_bench_marks.py tests/test_acceptance_comparison.py tests/test_ui_bench_inputs.py tests/test_bench_from_run.py tests/test_crawl_findings.py tests/test_generic_acceptance.py` -> 80 passed (23 s), matches the manifest.
2. `uv run ruff check src tests scripts` -> All checks passed. Doctor not re-run: manifest says the only 2 violations are SNAPSHOT staleness present on base, untouched by this diff.
3. Tests[] review: C1/C2 selections name the 6 new tests covering partial (2/3), zero (0/3), full (3/3), corpus-matched and scorecard-key cases. Importers (`agents/comparison.py`, `ceo_benchmark.py`) use `false_positive_rate`/`adjudicated_fp_rate` keys, which are unchanged; only keys were added, so no downstream signature/return-shape trigger.

## Diff scope (4c)
`git diff c437d3a5 8f23e561 --stat`: 6 files (manifest, script, schema/acceptance.py, schema/bench.py, stages/acceptance_comparison.py, tests/test_bench_marks.py), exactly the manifest's list. Read in full. `false_positive_rate` / `adjudicated_fp_rate` values are untouched (decision A kept). No test deleted or weakened.

## Criteria
- C1 expose adjudicated and total counts: `score()` adds `findings_total=reported`, `adjudicated_findings=reported-unruled` (schema/bench.py:195-196); `_column` copies it (stages/acceptance_comparison.py:91); `fp_coverage()` / `fp_rate_provisional()` (schema/acceptance.py:101-115). A human list rules every finding unless marks made the population adjudicated-only; otherwise ruled = marks + corpus-matched. Unadjudicated findings are never silently counted: the number stays over rulings, the unruled count is reported and the rate is labelled. MET.
- C2 script: prints `coverage: adjudicated N/M findings`, appends ` PROVISIONAL` to the `FP rate:` line, and `--claim` exits 1 with a stderr PROVISIONAL message while any finding is unruled (script lines 62-65, 100-104). Tests cover 2/3, 0/3 and 3/3 (no label, claim exits 0). MET. Reading of "exits non-zero": K10 (bench.md:111-117, 136) requires exit 0 and a numeric FP rate in no-human-list mode, which is the mode where most findings are unruled, so an unconditional exit 1 would contradict the contract; the opt-in `--claim` is the reconciliation, and the maker disclosed it. See PROPOSED-ISSUE 1.
- C3 UI shows the same coverage: `git grep -i "fp\|false.pos\|adjudic" src/autotester/ui` finds only `bench_inputs_view.py`, which shows ruled-real and ruled-false mark counts and says unmarked findings "are not counted in the false-positive rate". It shows no fp_rate value. No UI surface displaying fp_rate exists today, so the "UI shows the same" criterion is not triggered. MET (n/a).

## Falsification (floor, in throwaway copies of `git archive HEAD` under the scratchpad, `autotester.__file__` confirmed inside each copy; bound tree untouched)
Green before: pristine copy, tests/test_bench_marks.py 16 passed.
- C1: `"adjudicated_findings": reported` (drop `- unruled`) -> 5 failed (including the scorecard and corpus-matched tests).
- C2 label: `label = ""` in the script -> 2 failed.
- C2 exit: `if False and args.claim:` -> 2 failed (claim exits 0 on a provisional rate).
- Extra: `fp_rate_provisional` returns False -> 3 failed.
Metrics mutants=3 within the S/M cap; the 4th is the schema-level extra on the same criterion.

## PROPOSED-ISSUE (non-blocking, low, candidates not units)
1. T-136's `done_check` in `.goal/goal.json` (`uv run python scripts/check_acceptance_comparison.py pathlynks`) and the acceptance baselines in qa/contracts/video-learning.md do not pass `--claim`, so they still exit 0 on a PROVISIONAL rate (the output is labelled, so it is not silent). Whether the acceptance path should add `--claim` is Umesh's/checker contract call (K10 amendment), not this unit.
2. `stages/real_acceptance.py:125` writes `FP <rate>` into the GR2 line of the evidence `checklist.md`, and `stages/ceo_benchmark.py:177` writes "false positive rate (adjudicated findings only)", both without the coverage count or PROVISIONAL. These are evidence/report text, not UI, so outside the C3 trigger; they could show the same coverage.
3. Test gap (low): no test for `fp_coverage()` with `human_list == "present"` (the `by_human_list` branch). Logic read and judged correct.

## Process
Fan-out: n/a (single owner, no independent step). TMP/TEMP=D:/autoTesting/.work/tmp. No push, no merge.

Metrics: start=2026-10-21T19:38:00+05:30 end=2026-10-21T19:52:00+05:30 wall_min=14 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=4 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-19.17 check_s=840 mutants=3 defects_unit=0 defects_6c=0
slow: read-and-judge (contract K10 vs delegated request, surface sweep) 8
