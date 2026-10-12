# Manifest - t201b-test-button

**Unit:** T-201 / G7 `t201b-test-button`: the team Test button (TT1-TT6).
**Contract:** `qa/contracts/team-test-button.md` TT1-TT6 (plus `hosting.md` HO16-HO21, `auth.md`, `consent.md`).
**Branch / base:** `wave/t201b-test-button`.
Tier: L (auth, outward-facing run)
Dual check: required (TT1, TT5, TT6)
Fix cycle: 0
Executor: claude-sonnet-subagent (maker build subagent)
Code commit (pre-check sha): 4566ae12
Status: ready-for-check

## What changed

| Path | One job |
|---|---|
| `src/autotester/ui/routes_team_run.py` (new) | `POST /projects/{slug}/test` (gates, then one queue entry, 303) and `GET /projects/{slug}/test/{run_id}` (persisted status). |
| `src/autotester/ui/team_run_view.py` (new) | Button (shown only to `project.run` holders) and status page markup. |
| `schema/run.py`, `schema/run_queue.py`, `stages/run_launcher.py`, `ui/run_queue.py` | Additive: `Run.requested_at`, `QueueEntry.via`, `launch_run(requested_at)`. |
| `auth/policy.py`, `ui/auth_middleware.py`, `ui/routers.py`, `ui/project_view.py`, `ui/routes_report.py`, `ui/routes_runs.py` | Policy rows, router wiring, button on project page, report header names the starter. |
| `tests/test_team_run_{gate,approval,attribution,launcher,queue_seam,status}.py`, `tests/team_run_fakes.py` | TT1-TT6 evidence. |

## Evidence (per-file, run in the worktree; no full suite)

- test_team_run_gate.py 11 passed; approval 4 passed; attribution 4 passed; launcher 6 passed; queue_seam 3 passed; status 4 passed.
- `uv run ruff check src tests scripts`: All checks passed.
- `uv run autotester doctor`: clean.

## Owed to checker

- Full suite (single slot held by checker); mutation runs for TT1, TT3, TT5, TT6.
- Headed-browser persona walk of the button and status page (browser slot taken).
- Real-queue integration is T-203's (BLOCKED-CAPABILITY before it lands, per TT5).
- No SMTP involved; no secret value read.
