# Manifest — t169-generic-acceptance

**Unit:** T-169 generic two-mode acceptance harness (teaching sources -> INGEST; URL + credentials only -> DISCOVER), no CLI.
**Contract:** none exists for T-169; proposed GA1-GA4 appended to `qa/feedback-inbox.md` (2026-10-13, maker t169). Also `qa/contracts/bench.md` K3/K9/K10/K11, `orchestrator.md` OR1.
**Goal task:** T-169 (deps T-136, T-145, T-168). done_check: `uv run pytest tests/test_generic_acceptance.py`
**Status:** ready-for-check
**Fix cycle:** 1
**Branch:** wave/t169-generic-acceptance

## Built
- `src/autotester/stages/generic_acceptance.py` — `ModeSpec`/`ModeSeams`/`run_mode`: `/onboard` form -> orchestrator (`run_or_resume`) -> flowspec approve -> cases/generate -> run -> `bench_from_run` -> `build_comparison` + `completeness_problems`. No scoring of its own; slug-driven (`onboard=False` for a real target).
- `tests/test_generic_acceptance.py` — both modes on `tests/fixtures/regression_site` served locally (Mode 2 crawl reads its pages over HTTP; vision/agent/judge/executor are fakes; no browser, no network beyond 127.0.0.1).
- Fix found by the e2e: `store/run_store.py::RUN_AUX_FILES` now lists `ingest.flowspec.json`/`discover.flowspec.json`; before, any UI run after an orchestrated run crashed in `prune_old_videos` -> `load_results`.
- `docs/MAP.md` regenerated.

## Evidence
- `uv run pytest tests/test_generic_acceptance.py` 3 passed; orchestrate/bench/acceptance/video-retention neighbours green; `ruff check src tests scripts` clean; `autotester doctor` clean.

## Not in this unit
- Real Pathlynks run (waits on T-145 data and the independent human list, D-089/D-090); real browser/model seams; UI route for case-proposal review (gap logged in inbox).
