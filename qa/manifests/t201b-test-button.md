# Manifest - t201b-test-button

**Unit:** T-201 / G7 `t201b-test-button`: the team Test button (TT1-TT6).
**Contract:** `qa/contracts/team-test-button.md` TT1-TT6 (plus `hosting.md` HO16-HO21, `auth.md`, `consent.md`).
**Branch / base:** `wave/t201b-test-button`.
Tier: L (auth, outward-facing run)
Dual check: required (TT1, TT5, TT6)
Fix cycle: 2
Executor: claude-sonnet-subagent (maker build subagent)
Code commit (pre-check sha): 4566ae12
Status: checked-PASS

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

## Fix cycle 1

- TT1/AU14: pinned `GET /projects/{slug}/test/{run_id}` (report.view) and `POST /projects/{slug}/test` (project.run) in `EXPECTED` of `tests/test_ui_auth_escalation.py`, no net lines (file stays at 300). `test_au14_every_policy_row_requires_exactly_its_pinned_key` passes.
- Merged origin/master (conflicts in cli_subapps, routes_runs, run_queue, golden, hook test: kept both `auth` and `schedule`, and both `slot_key` and `via`); regenerated MAP/SNAPSHOT. Trimmed one comment line in `run_launcher.py` to stay under the 300-line doctor limit.
- TT3 not done, deliberate: `requested_by` stores the email only. Storing the user id needs a new id field on `QueueEntry` and `Run` plus launcher plumbing (schema change), not small. Report header "Started by <email>" unchanged. Left for the checker/orchestrator to decide.
- Per-file results: auth escalation + six `test_team_run_*` files 54 passed; `test_cli_subapp_hook` 4 passed; ruff clean; doctor clean.

## Fix cycle 2

- TT3 (r2.a FAIL): added optional `requested_by_id: int | None` to `Run` and `QueueEntry`; `routes_team_run.press_test` fills it from the session (`who.user_id`); `RunQueue.submit`, `_run_queued` and `launch_run` carry it onto the saved `Run`. The status page and report header show "(user #N)" beside the email. A pre-change `run.json` still loads (field optional, golden test asserts `None`).
- `tests/test_team_run_attribution.py` now asserts two different ids on queue entry and `Run`, the id in the report header, and the id surviving a forged body; `tests/team_run_fakes.py` FakeQueue accepts the field.
- r1 AU14 defect stays fixed (`test_ui_auth_escalation.py`).
- Scoped results: 94 passed (six team_run files, auth escalation, cli subapp hook, run_queue, run_launcher, ui_runs_queue); ruff clean; doctor: only 3 pre-existing dangling-citation hits in qa/verdicts/t196-citation.* (untouched).
