# Manifest: runrecord-callsite

Status: ready-for-check
Fix cycle: 1
Branch: wave/runrecord-callsite

## Finding
`tests/test_run_launcher.py::test_exactly_one_non_test_call_site_builds_a_run` failed on master:
`stages/run_record.py` (T-136c) built and saved a `Run` itself, a second site beside the launcher.

## Ruling
Not allow-listed. The test's intent is one door for runs; `record_run` bypassed it, so a run saved
by `scripts/run_pathlynks_first_cases.py` skipped `record_run_bugs` (the T-199d bug wiring).

## Change
- `stages/run_launcher.py`: new `save_tracked_run(store, **fields)` builds the `Run`, saves it and
  calls `record_run_bugs`. `launch_run` now uses it (behaviour unchanged). Docstrings tightened to
  keep the file at 300 lines.
- `stages/run_record.py`: `record_run` delegates to `save_tracked_run`; keeps the backwards-clock refusal.
- `tests/test_run_record.py`: `test_record_run_feeds_the_bug_loop_like_launch_run` proves a failing
  verdict recorded via `record_run` creates a tracked bug.

## Verification
test_run_launcher, test_run_record, test_run_pathlynks_first_cases, test_bench_from_run,
test_bug_wiring: all pass; ruff clean; doctor clean.
