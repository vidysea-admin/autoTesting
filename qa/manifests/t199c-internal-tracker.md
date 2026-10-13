# Manifest - t199c-internal-tracker

**Unit:** T-199 internal bug tracker page + Tracker-layout export (D-090). No write to the real Google sheet.
**Branch / base:** worktree-agent-a4690a7f2a7bbd31b, merged master bdb351af.
Fix cycle: 2
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

## Fix cycle 2 (TB7 scoping, answering the cycle-1 verdict)
Merged master (T-204 login gate). Added, reusing `auth.access.authorize/resource_for` and the middleware gate, no parallel logic:
| Path | One job |
|---|---|
| `src/autotester/auth/policy.py` | central `ROUTE_POLICY` rows: tracker list/csv/xlsx/detail = `report.view` over the project; `POST .../tracker/{bug_key}/assignee` = `project.edit`. The gate gives login redirect/401, 404 for no view scope (AU13), 403 without the key. |
| `src/autotester/ui/routes_tracker.py` | `POST /projects/{slug}/tracker/{bug_key}/assignee` (an ASSIGN event, actor `user:<email>`, free text or project member, blank clears, 400 over 120 chars); handler re-checks `authorize`; edit form (with member suggestions) shown only to a `project.edit` holder. |
| `tests/test_tracker_auth.py` | 16 table cases (admin/sub-admin/developer/tester x own/assigned/shared/none: list, export, detail, assignee edit, value unchanged on 403/404) + no-session refusal incl. the evidence run link + central policy rows. |
| `tests/test_tracker_page.py` | route-policy test now also expects the POST row as `project.edit`. |

Note for the checker: this tree has project-level `shared` only (no per-run share), so a `report.view@shared` holder sees the project's bugs when the project is shared with them; there is no finer "latest evidence run shared" state to consult.
Header names in `TRACKER_COLUMNS` remain the maker's guess of the PathLynks Tracker headers (no sheet read).
