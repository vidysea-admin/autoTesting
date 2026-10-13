# Manifest — t136c-run-script

**Status:** checked-PASS
**Fix cycle:** 2
**Contract:** qa/contracts/bench.md (K10/K11 — run feeds scripts/bench_from_run.py)
**Branch:** wave/t136c-run-script

## Gap (from checker)
`scripts/run_pathlynks_first_cases.py` (a) printed only `run: <run_dir>`, no explicit run id;
(b) saved a `Run` without `started_at` / `finished_at`.

## What changed
- `src/autotester/stages/run_record.py` (new): `now_utc()`, `record_run()` (saves Run with measured
  started/finished; rejects a backwards clock), `run_id_lines()` (`run: <dir>` + `run_id: <id>`).
- `scripts/run_pathlynks_first_cases.py`: takes `started_at` before browser start, `finished_at`
  after the cases/close, saves via `record_run`, prints `run_id: <id>`.
- `Run.started_at/finished_at` already exist (optional); schema unchanged.

## Tests
`tests/test_run_record.py` (4, fakes/tmp store), plus one source-shape test in
`tests/test_run_pathlynks_first_cases.py`. No browser, no live site.

## Fix cycle 2
- Correction: the cycle-1 claim that doctor's violation was a "pre-existing decision-citation violation" was wrong. Decision-citation findings are advisory warnings only; the one blocking violation was `stale-generated: docs/MAP.md`, caused by this branch's new `stages/run_record.py`.
- Ran `uv run autotester map`; `uv run autotester doctor` is now `doctor: clean`.
