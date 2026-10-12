# Manifest - t199c-dry-run (T-199 third slice: mapping preview, sheet binding, tracker page; DRY RUN ONLY)

**Contract:** qa/contracts/team-bug-loop.md TB7 (read-only page), TB8, TB12, TB13 (rest), TB14, TB9 (first-write confirmation record); never edits qa/contracts
**Brief:** qa/briefs/t199-bug-loop-dry-run.md (G8), after t199b-bug-loop-run (merged c015593c)
**Status:** ready-for-check
**Fix cycle:** 0 of max 2
**Tier:** L (outward-facing write PLAN to a team sheet; CRITICAL rows TB9, TB10, TB13). Dual check: no (no live client exists; the only `SheetClient` is a test fake; `LiveWriteRefused` still stands).
**Branch:** wave/t199c-dry-run   **Base:** 737fcc9d (master when cut; t199b already inside)
**Writing to the real sheet:** OFF. HG-TB1 (`qa/gates/t199-first-live-write.md`) is untouched and OPEN.

## What was built

| File | One job |
|---|---|
| `schema/tracker_binding.py` | `ColumnMapping` (proposed / confirmed / stale, who and when), `TrackerBinding` (project, sheet id, tab, mapping, first-write `PlanConfirmation`, `SyncMemory`, `SyncState`), `MappingReply` |
| `stages/tracker_mapping.py` | propose from the header alone (synonyms first, header-only scrubbed provider fallback), confirm (injected `project.edit` check), `check_header` (stale), `rebind` (new sheet id resets to proposed), `mapping_columns` (the one door to a write, asserts confirmed) |
| `stages/tracker_sync.py` | `preview_sync` (dry run), `confirm_first_write` (against plan hash), `sync_confirmed` (via t199b `write_confirmed_plan`, live refused), outage handling (`sync_status=error`, scrubbed last error, retry time), `check_link` |
| `store/tracker_store.py` | per-project binding file; a file for another project is refused |
| `ui/routes_tracker.py` | `GET /projects/{slug}/tracker`: bugs, mapping preview with unmapped candidates, sync status and error, conflicts, "nothing written"; `ROUTE_POLICY` (`report.view`) |
| `prompts/tracker_mapping_v1.md` | fallback prompt (header cells only) |
| edits | `core/paths.py` (+`bugs_dir`, `tracker_file`), `schema/sheet_plan.py` (`check_person`, one rule for named confirmers), `ui/routers.py` (router added; the empty `tracker` stub left in place because `tests/test_routers_list.py` pins it), `tests/sheet_fake.py` (+`read_header`), MAP and SNAPSHOT regenerated |
| tests | `tests/test_tracker_mapping.py` (14), `test_tracker_sync.py` (10), `test_tracker_page.py` (3), `tests/tracker_fakes.py` |

## Criteria

- TB8 met on a fake: header-only read asserted from the call log; provider payload has header cells only (secret in a header is scrubbed; a data-row value never appears); two or no candidates = unmapped with candidates listed; only a holder of the injected `project.edit` check confirms, status unchanged on refusal; machine actor refused; renamed or moved header = stale and writes refused.
- TB9 (dry run): zero write calls before confirmation and after a one-cell plan change; confirmation recorded against the plan hash with who and when; live client still refused.
- TB12: a failing client gives `sync_status=error`, scrubbed `last_error`, `retry_at`; bugs untouched; a healthy client then converges; status and error shown on the page.
- TB13: planted secret absent from plan, rendering, stored binding and page; sheet id swap resets to unconfirmed and the write is refused; `check_link` accepts only https on the product host with no signed-URL parameter.
- TB14: two layouts, one code path; per-project file; no product name in `stages/tracker_*.py` (grep test).

## Contract gaps and limits (checker to rule)

- G1 `project.edit` is not enforced by a route: there is no authorize engine on master (T-204 unmerged). The check is an injected callable `holds_project_edit(user, project)`; no shim was invented. The tracker page is read-only and declares `report.view` in `ROUTE_POLICY`; it is not yet merged into a central table or guarded by middleware.
- G2 No bind / confirm POST routes and no `cli_tracker.py`: both need T-204 (session user for the confirmer) and a live-capable client for a real preview. Held to the next slice.
- G3 `screenshot_link` is proposed but never written (no authenticated link in a plan); `check_link` is built and tested but not wired into a plan.
- G4 `TrackerClient` (adds `read_header`) is a sub-protocol in `tracker_sync.py`; t199b's pinned `SheetClient` attributes are unchanged.
- G5 The page shows the stored `SyncState`; nothing yet persists it from a run (no scheduler hook; no live client).
- G6 Carried from t199b, unchanged: AT-981..AT-989 (unscrubbed sheet-side text in plan `before`, self-declared `live` flag, memory persistence on crash). The page scrubs everything it prints.
- G7 Persona walk (subadmin, 5 steps) not possible: no confirm UI (G2).

## Verification

Per-file only, no full suite, no browser:

- `uv run pytest tests/test_tracker_mapping.py tests/test_tracker_sync.py tests/test_tracker_page.py tests/test_sheet_plan.py tests/test_routers_list.py -p no:xdist -o addopts=` -> 56 passed
- `uv run ruff check src tests/tracker_fakes.py tests/test_tracker_mapping.py tests/test_tracker_sync.py tests/test_tracker_page.py tests/sheet_fake.py` -> All checks passed
- `uv run autotester doctor` -> only the 6 `ledger-row-missing` rows (T-154, T-168, T-178, T-197, T-202, T-205) that exist on master; none from this unit
