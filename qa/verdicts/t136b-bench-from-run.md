# Verdict - t136b-bench-from-run

**Cycle checked:** 1
**Verdict:** PASS
**Head checked:** 046be194 (branch wave/t136b-bench-from-run)

## Contract
K11a-d folded into `qa/contracts/bench.md` (inbox marked folded). Consistent with D-089 item 3 and D-090.

## Checks (fresh)
- K11a / K3: stage calls `bench.run_autotester_trial` only; no scoring arithmetic; rerun replaces trial (test). PASS.
- K11b: ungraded or missing run raises RunNotUsable, script exits 2, no corpus written (test). PASS.
- K11c: stored human corpus used untouched; absent gives empty `mode=unknown` corpus; recall unavailable, FP rate 1.0 a number, check script exit 0. PASS.
- K11d / K8: duration from run span, else sum of results, else None; untimed run gives None and the check fails on duration_s. PASS.
- Design: files within 300 lines, docstrings present, no new schema model (nothing to forbid-extra), no duplicate concept.
- Run: test_bench_from_run + test_bench + test_acceptance_comparison = 49 passed; ruff clean; doctor clean.

## Advisory (non-blocking)
`_duration_s` sums whatever results exist; if results were stored for only some case_ids it understates time. The real chain stores all results, so it cannot occur there. Tightened K11d now forbids it; fix in the next touch of the stage.

## Chain question (run_pathlynks_first_cases.py)
- Takes no run args (only `--no-grade`, which yields no verdicts so bench_from_run refuses, exit 2).
- Run id is generated (`run-<ulid>`) and printed only as the last line `run: <run_dir>`; the id is the directory name. Not printed as a bare id.
- Saves Run with `case_ids` only: `started_at`/`finished_at` are NOT stored. Duration therefore comes from the fallback, the sum of stored per-case `RawResult.duration_s` (measured by execute.py), which is valid but excludes inter-case/browser start-up time.
- Chain works end to end: run_pathlynks_first_cases.py (graded) -> `bench_from_run.py pathlynks --run <id from run: path>` -> `check_acceptance_comparison.py pathlynks`, in no-list mode.
- Gaps: (1) run id must be copied from the printed path; (2) Run.started_at/finished_at never set, so duration is the case-sum, not wall-clock; (3) needs real credentials and a live browser, not exercised here.
