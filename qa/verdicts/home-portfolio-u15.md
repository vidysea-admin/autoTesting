# Verdict - home-portfolio-u15

Verdict: PASS
Cycle checked: 0
Policy-Version: proportional-verification/2026-10-15.12
Bound to: D:/autoTesting/.worktrees/home-portfolio-u15 (base 69ebfae7 via git merge-base with master, head bec60ac1, code 70a71ed9)
Tier: M (UI, one shared module). LANE: normal (lane disabled / not entered). Lane exit: none

## Check plan
- Logic changed (ui/project_view.py home block): affected tests + falsification floor.
- UI rendered output changed: live browser (Mode D) - Playwright MCP is down, so BLOCKED-CAPABILITY for the visual pass. The U15 criterion text is observable in server-rendered HTML, so it was evidenced via TestClient; the visual pass is a PROPOSED-ISSUE (low), not a blocker.
- Not triggered: security/auth, data write, prompt/LLM, data artifact.

## Criterion U15 / AT-664 C1 - evidenced
Contract qa/contracts/ui.md U15 compared line by line against src/autotester/ui/project_view.py (diff 69ebfae7..70a71ed9 read in full, 4c):
- Aggregate: tiles `projects`, `have run`, plus `never run`/`stale`/`skipped` (project_view.py portfolio_stats). Per-project outcome badge + age + `no runs` (project_card/_status_html).
- No invented zero: idle -> `no runs`; failing/stale/never-run/skipped tiles render only when nonzero; `latest run clean` needs a non-empty verdict set.
- Unreadable: any ValueError/OSError in cases, project, run or verdict load -> state `unreadable`, named and counted in `skipped (unreadable): <slugs>`; `_has_corrupt_run` closes the old silent drop (valid_runs_newest_first skips a bad run.json).
- Stale: run time < mtime of project config/cases -> `stale` note and tile.
- Reuses theme.badge / theme.stat; no new PASS/FAIL/NOT_RUN spelling.
Files stay within caps (project_view.py 256 lines).

## Commands I ran
- `uv run pytest tests/test_ui_dashboard.py` -> 17 passed, 1 warning (10.7 s)
- `uv run ruff check src tests scripts` -> All checks passed!
- `uv run autotester doctor` -> doctor: clean
- Mutation-isolated copies outside the worktree (git archive of HEAD under the scratchpad), `-k u15`:
  - green before: 4 passed
  - M1 flip stale comparison (`when < changed` -> `when > changed`): 1 failed on `assert 'stale' in <aging card>` (test_u15_home_labels_a_run_older...), 3 passed
  - M2 `_has_corrupt_run` returns False on a bad run.json: 1 failed on `assert 'unreadable' in <rotten card>`, card showed `no runs`, 3 passed
  - Both red on the named assertion (not import errors); copies discarded, tree untouched. Floor (1 per changed criterion) met, 2 run.
- Own counterexample probe (throwaway copy): corrupt cases.jsonl, and a corrupt `*.verdict.json` -> `/` returns 200 (old code 500'd on bad cases), both cards render `unreadable`, tile `skipped (unreadable)` present -> passed.

## Findings (none blocking)
PROPOSED-ISSUE (low, ui): no live-browser check of `/` with an idle, failed, stale and corrupt project (Playwright MCP down); visual layout of the added tile text `skipped (unreadable): <slugs>` with many slugs is unverified and could wrap/overflow.
PROPOSED-ISSUE (low, ui): `stale` keys on file mtime of project.json/cases.jsonl; a git checkout or copy resets mtimes and can mark a current run stale or hide a stale one. Maker noted this as a known limit (Project has no updated_at).
Note: any corrupt run dir, even an old one, makes the whole project `unreadable` (conservative, consistent with "never a zero").

Invariants: [I*] none-touched (no schema, credential or provider change).
Metrics: start=2026-10-17T10:41:00Z end=2026-10-17T11:05:00Z wall_min=6 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=0 mutations=2 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-15.12 lane=normal check_s=360 mutants=0 defects_unit=0 defects_6c=0
