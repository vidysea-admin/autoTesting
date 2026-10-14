# Manifest - approval-residual-callers

Unit: close the residual bare `require_approval` callers flagged by both approval-prod-gate checkers
Contract: qa/contracts/ (production-gate criteria used by approval-prod-gate; no contract edited)
Fix cycle: 1
Status: checked-PASS
Branch: wave/approval-residual-callers

## Change

- `stages/ai_capture.py::capture_run` now takes a `Project` and gates with `require_project_approval`
  (a production project refuses account-derived and `production:false` rows before any send).
- `stages/discover.py` (local directory reads) and `cli_video_review.py` (provider-id target) keep
  bare `require_approval`, each with a one-line comment saying why.
- Tests: `tests/test_approval_residual_callers.py` (production refusal on ai_capture for derived
  and production_false rows, valid human row accepted; discovery cannot take a URL root or a
  live-target row; video-review gate ignores live-target rows). Existing ai_capture/signing tests
  updated to pass a Project via `run_approval_fixture.project_of`.
- Not done: bare `require_approval` does not refuse production projects (it only receives a slug).

## Evidence (maker, scoped)

256 tests pass across the approval, consent, ai_capture, discover and prod-gate files; the
video-review CLI tests passed earlier (371 total). ruff clean; doctor shows no violations.
