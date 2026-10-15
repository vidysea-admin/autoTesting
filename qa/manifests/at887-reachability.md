# AT-887 clause 2: pre-run reachability warning

Status: ready-for-check
Fix cycle: 2
Branch: wave/at887-reachability

## Built
- `CrawlSummary` gains `reached_paths` / `unreached_paths` (url templates only; the frontier).
  Written by `stages/explore_summary.py`. Old summaries load with empty lists.
- `stages/reachability.py`: warns per case whose first URL target the latest crawl never reached
  (frontier) or never saw. Locator/secret first steps are not judged. Never removes a case.
- `Run.preflight_warnings` stored by `launch_run`; shown on the run report via `ui/preflight_view.py`.
- Tests: `tests/test_reachability_warning.py` (fixture summary).

## Verify
scoped pytest (reachability, run_launcher*, crawl-summary tests: 120 passed), ruff clean, doctor clean.
Known limit: matches URL first steps only.

## Fix cycle 2
PII: `core/path_pii.py::safe_path` folds email/phone (via mask_pii), UUID, JWT, long digit runs and tokens to {var}; applied to stored reached/unreached paths and warnings. Tests added.
