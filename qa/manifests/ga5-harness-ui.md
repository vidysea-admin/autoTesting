# Manifest: ga5-harness-ui

Status: checked-PASS
Fix cycle: 1
Contract: qa/contracts/generic-acceptance.md (GA5)
Branch: wave/ga5-harness-ui

## Changed
- `src/autotester/stages/generic_acceptance.py`: removed `ModeSeams.review_proposals`; `run_mode` now stages and bulk-approves proposals through `GET /projects/{slug}/proposals`, `POST .../proposals/stage` and `POST .../proposals/review`.
- `tests/test_generic_acceptance.py`: removed the `_review` stand-in; both modes (teaching, url_only) use the UI route.

## Evidence
- `tests/test_generic_acceptance.py` + `tests/test_proposal_review_ui.py`: 13 passed.
- `ruff check src tests scripts`: clean. `autotester doctor`: clean.
