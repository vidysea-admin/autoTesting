# Manifest - t200c-schedule-ui

**Unit:** T-200 phase C, the TS1 surface the task-level check found missing (`qa/verdicts/t-200-team-loop.task-check.md` gap 1): the schedule routes, the project schedule card, and the `schedule.manage` rows in the central route policy. This unit does not close goal task T-200 by itself (see "Still open").
**Branch / base:** `wave/t200c-schedule-ui` on master 87c7c9b8 (T-204 auth, t200a, t200b, schedule-wiring all merged).
**Code commit (pre-check sha):** see `git log` for the commit that adds this manifest; the code commit precedes it and no source file changes after it.
Policy-Version: proportional-verification/2026-10-10.9
Tier: L (auth surface: a state-changing route family gated by a permission key)
Dual check: required
dual-trigger: security src/autotester/auth/policy.py
Fix cycle: 3
Executor: claude-sonnet-subagent (maker build subagent)
Status: checked-PASS
UI surface: changed (new page `GET /projects/{slug}/schedule`, new card on the project page). Persona walk needs a browser and is NOT done here.

## What changed

| Path | Lines | One job |
|---|---|---|
| `src/autotester/ui/routes_schedule.py` (NEW) | ~115 | `GET /projects/{slug}/schedule`; `POST` save / `pause` / `resume` / `delete`. Save goes through `ScheduleConfig.parse_for_save` (the one door), a refusal is a 400 naming the field and stores nothing. Delete calls the existing `purge_project` for markers and records, then clears `Project.schedule` |
| `src/autotester/ui/schedule_view.py` (NEW) | ~125 | The card: mode and times, next slot (`slot_instants`), scheduler health (`scheduler_health` + heartbeat), TS5 credential state (`credential_state`, read-only), last five slot records. Edit forms render only for a viewer holding `schedule.manage` |
| `src/autotester/auth/policy.py` | +4 | `GET .../schedule` -> `project.view`; the four POSTs -> `schedule.manage` (project scope), inside the existing `ROUTE_POLICY` that T-204's login gate walks. No new permission key, no parallel auth check |
| `src/autotester/ui/routers.py` | +3 -1 | the empty `schedule` stub removed from `STUBS`; `routes_schedule.router` registered |
| `src/autotester/ui/app.py` | +3 | the card is appended to the project page |
| `tests/test_schedule_routes.py` (NEW) | ~190 | TestClient + T-204 auth fixtures (`auth_harness`): 4 groups x 3 projects save table; 403 for a viewer without `schedule.manage` on save / pause / resume / delete; refused POST leaves `project.json` byte-identical; 14 invalid-value rows name their field; pause/resume/delete round trip; delete purges claims and records; cross-origin POST refused first; policy rows present |
| `tests/test_routers_list.py` | -1 | `schedule` is no longer a stub |
| `docs/MAP.md` | regenerated | `uv run autotester map` |

## Design notes for the checker

1. The 403 for a missing key comes from the T-204 login gate (`ui/auth_middleware.py`), which says "you do not have permission for this action" and does not print the key name. The contract's wording "403 naming `schedule.manage`" is therefore only met in the sense that the policy row names it; I did not change the gate's message (it is T-204's, shared by every route). Flagging for the checker to rule on.
2. Routes are `POST .../schedule/pause|resume|delete`, not HTTP `DELETE`: the card uses plain HTML forms, and the gate's Origin guard covers every unsafe method alike.
3. A save replaces the whole schedule from the form and stamps `owner` with the saving user (the contract's "owner = user who last saved"). `since`-bound `saved_at` (mentioned in `schedule_wiring.py`) is not added here.
4. Delete purges through `purge_project` before clearing the field, so a failed purge leaves the schedule in place.

## Still open for T-200 after this unit (TS1 routes and card are now built)

- Persona walk (Mode D, unnumbered TS12 in the contract): needs a real browser on the schedule page.
- HO24: owner disabled / deleted / lacking `project.run` -> slot `refused` (not part of TS1).
- Owner inbox delivery and email for failed or blocked slots (TS5 / TS7 owner-visible half): waits on the T-201 delivery unit and the email-sender gate.
- Project-delete wiring: `purge_project` is called only from the schedule delete route; no whole-project delete path exists to call it.
- The checker's dual-check, and the task-level re-check of T-200.

## Pre-check

- `uv run pytest tests/test_schedule_routes.py tests/test_routers_list.py`: 39 passed.
- Neighbour auth/policy tests: `tests/test_ui_auth_groups.py tests/test_ui_auth_surface.py tests/test_ui_auth_escalation.py tests/test_policy_merge.py tests/test_project_schema_team.py` 95 passed after pinning the 5 new policy rows in `tests/test_ui_auth_escalation.py` (the AU14 pinned-key table fails on any new row by design).
- `uv run ruff check src tests scripts`: all checks passed.
- `uv run autotester doctor`: clean (after `autotester map`).
- No browser, no full suite (shared CPU-bound machine).

## Fix cycle 2
- Split tests/test_ui_auth_escalation.py (now 251 lines); policy table moved to tests/test_ui_auth_policy_table.py.
- Shared gate 403 for key routes now names the permission key (TS1); schedule 403 tests assert schedule.manage.
- HO24 owner guard: stages/schedule_owner.py, TickDeps.owner_guard, tests/test_schedule_owner_guard.py.
- Project-delete wiring: no project-delete path exists in the codebase; schedule delete route already purges. Not built.
