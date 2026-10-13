# Manifest — t136b-bench-from-run

**Unit:** T-136b: generic step turning a real project's executed+graded run into the acceptance bench corpus + AutoTester trial.
**Contract:** `qa/contracts/bench.md` K3, K5, K8, K10 K11 (folded 2026-10-13)
**Branch:** wave/t136b-bench-from-run
**Status:** checked-PASS
**Fix cycle:** 1

## Files
- `src/autotester/stages/bench_from_run.py` (new; reuses `stages.bench.run_autotester_trial`)
- `scripts/bench_from_run.py` (thin CLI)
- `tests/test_bench_from_run.py` (fixture runs only)
- `qa/feedback-inbox.md` (proposed K11)

## Design
No-list mode (D-090): empty `mode=unknown` corpus, findings unadjudicated, recall unavailable. A stored human corpus is used untouched. Duration measured or None. No browser, no live site.
