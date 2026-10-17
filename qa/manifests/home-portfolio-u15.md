# Manifest - home-portfolio-u15

**Contract:** qa/contracts/ui.md U15 (AT-664 criterion C1 below)
**Goal task:** none
**Date:** 2026-10-17
**Status:** checked-PASS (qa/verdicts/home-portfolio-u15.md, cycle 0)
**Fix cycle:** 0 of max 2
**Hold fix cycles:** 0 of 2
**Hold-reopens:** 0
**Resume-reset:** unused
**Capability-redispatch:** 0
**Dual check:** no
**Persona walk:** required (cold operator opening `/` with 2+ projects; observed via TestClient HTML only, see Live browser)
**Issues addressed:** AT-664
**Executor:** claude-sonnet-subagent
**Executor rationale:** two owned files, no external executor worthy.

## What changed
- src/autotester/ui/project_view.py (256 lines, cap 300) - edited in place, no new module. Replaced `_latest_run_status` + `project_card` + `portfolio_stats` (the home-page block) with: `_ago`, `_last_change`, `_has_corrupt_run`, `_standing` (one project's state: none / unreadable / ok with counts, age, stale), `_status_html`, and rewritten `project_card` / `portfolio_stats` (same public signatures, same caller `ui/app.py:96,98`). Card now shows latest verdict badges plus age, `no runs` for an idle project, `unreadable` for a project whose cases/project/run evidence fails to load (a corrupt run.json used to be dropped silently so the project read as never run, and a corrupt cases.jsonl 500'd the whole home page), and a `stale` note when the run is older than the project's config/cases mtime. Tiles add `have run`, `latest run stale`, and `skipped (unreadable): <slugs>`; `latest run clean` now requires a non-empty verdict set.
- tests/test_ui_dashboard.py (237 lines) - added helpers `_onboard`, `_run_with`, `_card` and four U15 tests. Nothing existing deleted or renamed; the old `never run` tile text is kept (existing test still green).
- Not done: relative "age" is wall-clock at render time (not persisted); the project "last change" is file mtime of project.json / cases.jsonl, since `Project` has no updated_at field and a schema change was out of scope.

## Verification scope
Policy-Version: proportional-verification/2026-10-15.12
Tier: M
Base / checked state: base 69ebfae7, code at 70a71ed9, clean tree
Gate answers: none; qa/gates/new-module-authorization.md not needed (no new src file).
Affected tests / full-suite trigger: tests/test_ui_dashboard.py only (callers of `project_view.project_card`/`portfolio_stats` are ui/app.py:96,98 only; `_latest_run_status` had no other reference, grep over src and tests).
Pre-check[C1]: 70a71ed9 uv run pytest tests/test_ui_dashboard.py -> 17 passed, 1 warning t=9 blobs=src/autotester/ui/project_view.py:cc24993,tests/test_ui_dashboard.py:43b75ad
Metrics: start=2026-10-17T10:00:00Z end=2026-10-17T10:40:00Z wall_min=40 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=9 mutants=1 defects_unit=0 defects_6c=0

## How to verify (commands + expected)
- `uv run pytest tests/test_ui_dashboard.py` -> expected: 17 passed
- `uv run ruff check src tests scripts` -> expected: All checks passed!
- `uv run autotester doctor` -> expected: doctor: clean

## Actual outputs (from maker's own run)
- tests/test_ui_dashboard.py: `17 passed, 1 warning`
- ruff: `All checks passed!`; doctor: `doctor: clean`

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | check | falsifying edit | observed |
|---|---|---|---|---|
| C1 | outcome + age per project, `no runs` for idle, no invented 0 | tests/test_ui_dashboard.py::test_u15_home_shows_latest_outcome_and_age_per_project_and_no_runs_for_the_idle_one | base project_view.py (`git show 69ebfae7:src/autotester/ui/project_view.py`) in a throwaway copy outside the worktree | before (red, base): `E assert 'no runs' in "class='project-card' href='/projects/idle'>...` (tests/test_ui_dashboard.py:188 AssertionError); after (green, 70a71ed9): 17 passed |
| C1 | aggregate counts projects that have ever run | ::test_u15_home_counts_how_many_projects_have_ever_had_a_run | same | before (red): `E assert "<div class='stat'><div class='value'>1</div><div class='label'>have run</div></div>" in ...` (:203); after: green |
| C1 | unreadable run evidence is named and counted skipped, not `no runs` | ::test_u15_home_names_a_project_with_unreadable_run_evidence_and_counts_it_skipped | same | before (red): `E assert 'unreadable' in "class='project-card' href='/projects/rotten'>...` (:219); after: green |
| C1 | run older than project's last change is labelled stale | ::test_u15_home_labels_a_run_older_than_the_projects_last_change_as_stale | same | before (red): `E assert 'stale' in "class='project-card' href='/projects/aging'>...` (:235); after: green |

Red-before in the copy: `4 failed, 13 passed` (the 13 are the existing tests, unchanged); after restoring the fix in the same copy: `17 passed, 1 warning in 17.38s`. The copy ran with PYTHONPATH pointing at the copy's src and scripts, so the base file was the one imported. The tests were also red-first against the base file in the worktree before the edit (4 failed, 13 passed), though the first version of the `_card` helper matched the sidebar link, which I fixed before the green run.

## Live browser
Not run: the playwright MCP server failed to connect in this session and no browser was driven by the maker. The page was exercised only through FastAPI TestClient HTML (card text and stat-tile markup). Checker Mode D should open `/` in a real browser with one idle, one failed-run, one stale and one corrupt-run project.
