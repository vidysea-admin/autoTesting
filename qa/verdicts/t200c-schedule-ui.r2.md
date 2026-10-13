# Verdict - t200c-schedule-ui, cycle 2

Cycle checked: 2
Verdict: FAIL (one defect, HO24 fail-open when auth is ON and the account store is absent)
Head checked: 70751a25

| Criterion | Result | Evidence |
|---|---|---|
| Cycle-1 (a) file length | PASS | `tests/test_ui_auth_escalation.py` 251 lines, new `tests/test_ui_auth_policy_table.py` 71; doctor clean, ruff clean |
| Split changed no assertion | PASS | Diffed old vs new: the moved `assert actual == EXPECTED` and the EXPECTED table are identical; the only additions are the new 403-names-key test |
| Cycle-1 (b) / TS1 403 names `schedule.manage` | PASS | `ui/auth_middleware.py:104` appends `(<key>)` only; `test_schedule_routes.py:76` asserts `schedule.manage`; `test_ui_auth_policy_table.py` asserts `live.view` named and the viewer email absent. No test pins the old message |
| TS1 other (policy rows, save/pause/resume/delete, routers list) | PASS | 81 passed (routes, owner_guard, wiring, both auth files, routers list) |
| HO24 owner disabled/deleted/lacks project.run -> paused + `refused` | PASS | `tests/test_schedule_owner_guard.py` 3 tests |
| HO24 fails closed when auth is ON | FAIL | `stages/schedule_owner.py:54` |
| Project delete removes schedule + markers | N/A | no project-delete feature exists; `purge_project` is wired to `/schedule/delete`, tested |

## Ruling on the no-store skip

`auth_disabled()` alone is legitimate: AU17 honours it only when not hosted and bound to loopback.
`or not db.store_exists()` is a bypass: with auth ON (including hosted) a deleted, moved or never-created
account store makes the guard return None, so a schedule whose owner can no longer be verified
fires. HO24 says a deleted owner pauses and refuses. Confirmed by experiment: removing the clause makes
7 of `test_schedule_wiring` fail, i.e. those tests exercise exactly auth-ON-no-store and passed only
because of the skip. Fix: guard on `auth_disabled()` only (no store with auth ON -> `owner_refusal`
already returns the owner-missing refusal), and make `test_schedule_wiring` either set
`AUTOTESTER_AUTH_DISABLED=1` or seed the owner account. Add a test: auth ON, no store -> REFUSED + paused.
Do not weaken the 7 wiring tests.

Cost of the defect is low (needs the store lost) but it is the one place the contract says fail closed.
