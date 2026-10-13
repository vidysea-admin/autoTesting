# Manifest - t136-acceptance-comparison

**Unit:** T-136 `done_check` script and its logic, built in no-human-list mode (D-089 item 3).
**Status:** ready-for-check
**Fix cycle:** 2
**Contract:** `qa/contracts/bench.md` K3, K5-K9. Recall is judged "unavailable allowed" per D-089 item 3.
**Goal task:** T-136 stays `pending`: no Pathlynks bench data exists locally.

## Files

- `scripts/check_acceptance_comparison.py` - thin CLI (exit 0 complete, 1 incomplete, 2 input missing).
- `src/autotester/stages/acceptance_comparison.py` - builds the comparison from stored bench files, calls `stages.bench.scorecard` (so `BenchTrial.score` verbatim), and checks completeness.
- `src/autotester/schema/acceptance.py` - `Measure` (value XOR unavailable reason), `ParticipantColumn`, `BugRow`, `AcceptanceComparison`.
- `src/autotester/core/paths.py` - `bench_comparison`, `bench_human_trial` (documents where the human list plugs in).
- `tests/test_acceptance_comparison.py` - fixture tests, no browser.

## What it prints on pathlynks today

`projects/pathlynks/` has only project.json, cases.jsonl, knowledge.md, approvals.jsonl: no `bench/`, no runs, no verdicts. Exit 2:
`missing bench corpus projects\pathlynks\bench\pathlynks-acceptance.json ... No numbers are invented.`

## Human list plugs in as files, no code change

Convention: corpus id `<slug>-acceptance`. Drop a `human_confirmed` corpus at `projects/<slug>/bench/<slug>-acceptance.json` and a `kind=human_live` `BenchTrial` at `projects/<slug>/bench/<slug>-acceptance.human.trial.json`. `list_bench_trials` already globs `*.trial.json`.

## Known gap, stated

Nothing yet turns a real Pathlynks run's verdicts into the corpus + AutoTester trial files (`run_autotester_trial` exists; no CLI calls it for Pathlynks). Also `BenchTrial.score` counts any finding matching no corpus bug as a false positive, so in no-list mode FP rate is only meaningful once findings are adjudicated against a bug list.

## Verify

- `uv run pytest tests/test_acceptance_comparison.py tests/test_bench.py` -> 43 passed
- `uv run ruff check src tests scripts` -> clean
- `uv run autotester doctor` -> 3 pre-existing hits, all in `qa/verdicts/t196-citation.*` (placeholder decision ids in that unit's verdicts); no hit from t136 files after this cycle's reword
- `uv run python scripts/check_acceptance_comparison.py pathlynks` -> exit 2, as above

## Fix cycle 2

- Reworded the doctor line above (dangling citations removed; the earlier 'none from this unit' claim was wrong).
- `AcceptanceComparison.fp_rate_unadjudicated: bool` (true when no human list). CLI prints `FP rate: <n> (unadjudicated: no human list)`; with a list the suffix is absent. Tests cover both modes.
