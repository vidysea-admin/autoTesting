# Manifest - t199c-internal-tracker

**Unit:** T-199 internal bug tracker page + Tracker-layout export (D-090). No write to the real Google sheet.
**Branch / base:** worktree-agent-a4690a7f2a7bbd31b, merged master bdb351af.
Fix cycle: 1
Status: ready-for-check

## What changed
| Path | One job |
|---|---|
| `src/autotester/ui/routes_tracker.py` | Tracker page: list + status/severity filter, bug detail with event history, CSV/xlsx download routes, `ROUTE_POLICY` (report.view). |
| `src/autotester/stages/tracker_export.py` | TB15: CSV/xlsx bytes in the Tracker layout; reuses `SheetColumns`, `bug_values`, `safe_cell`; deterministic bytes. |
| `src/autotester/stages/sheet_plan.py` | `_safe` renamed `safe_cell` (public, shared; no second copy). |
| `src/autotester/ui/routers.py`, `tests/test_routers_list.py` | Real tracker router replaces the `tracker` stub. |
| `tests/test_tracker_page.py` | 13 tests. |
| `docs/MAP.md` | regenerated. |

## Known gap for the checker to rule on
TB7 permission scoping (report.view over project, report.view@shared, not-found for no scope, `project.edit` assignee edit with 403) needs T-204's session/user model, which is not in this tree (`auth/` holds only `policy.py`). Routes declare `ROUTE_POLICY` with `report.view`; no session check and no assignee-edit route exist. Header names in `TRACKER_COLUMNS` are the maker's guess of the PathLynks Tracker headers (no sheet read).
