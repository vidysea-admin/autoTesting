# Manifest - t168-damage-control-report

**Unit:** T-168, the damage-control report: regression diff, API failures, workflows and change history (plus the crawl's coverage) on one surface, built from stored evidence only.
**Brief:** `qa/briefs/t168-damage-control-report.md`. **Contract:** `qa/contracts/damage-control-report.md` (DRAFT, DC1-DC4), plus `core-invariants.md`.
**Branch / base:** `wave/t168-damage-control-report` on T-167's code commit `00fae668` (T-167 is built, NOT yet checked; this unit cannot merge before it).
**Code commit (pre-check sha):** cdb0ae53 (the manifest commit after it adds only this file).
Policy-Version: proportional-verification/2026-10-10.9
Tier: M (multi-file behaviour reading five existing evidence owners, one new report module set, a CLI and an HTTP surface; no L trigger)
Dual check: no (no auth, tenancy, security or production-write path: read-only over stored evidence, one report file written; the report is scrubbed with the existing `Redactor`, no new secret-handling path)
Fix cycle: 0
Executor: claude-sonnet-subagent (maker build subagent)
Status: ready-for-check
Persona walk: required (lead: project list -> project page -> "Damage-control report", 2 steps; negative path: a project with no runs shows an empty state, a low-coverage crawl is amber and never green). UI surface changed: a new route `GET /projects/{slug}/damage-report` and one button on the project page. Browser check: not run by the builder (offline, no browser); route and link are covered by TestClient in `tests/test_unified_report.py`.

## Criteria (verbatim from the contract)

### DC1 - Blocked or unvisited is NEVER rendered as pass
**Verify:** a fixture crawl that stopped on a bound with a sub-100% V7 figure, rendered through the unified report, shows the **same** figure and the same reason breakdown as the crawl page - never rounded to "PASS", never omitted. A `not_visited` control or screen never appears as a passed row anywhere in the report.

### DC2 - It READS existing evidence; it does not recompute
**Verify:** every figure on the unified report traces to one of the four named sources. No number-computing function bypasses all four loaders.

### DC3 - "Unified" means one artifact, not four files stapled together
**Verify:** one invocation -> one artifact (or one cross-linked pair) containing all four data classes.

### DC4 - No secret reaches the unified report [C5 + `report-export.md` RE5]
**Verify:** `scripts/check_no_secrets.py` passes clean on the unified report artifact, run against a project that touches real credentials. (AT-694: the scanner is wired to no automated path, so the test runs it explicitly as a subprocess and asserts its output.)

## What changed

| Path | Lines | One job |
|---|---|---|
| `src/autotester/schema/unified_report.py` (new) | 124 | The typed report: five sections, each with `unavailable: reason`; embeds `RegressionDiff`, `FlowOutcome`, `ReleaseIssue`, `PersonaRevision` rather than redefining them. |
| `src/autotester/stages/unified_report.py` (new) | 218 | Five loaders (regression, api, workflows, history, coverage) over the existing owners; `build_report`, `unified_html`, `export_unified_html`. |
| `src/autotester/stages/unified_report_render.py` (new) | 170 | One self-contained HTML document; formats only, computes nothing. |
| `src/autotester/ui/routes_unified_report.py` (new) | 33 | `GET /projects/{slug}/damage-report[?run=]`; empty state when nothing ran. |
| `tests/test_unified_report.py` (new) | 260 | 12 tests (the brief's `done_check` file). |
| `src/autotester/cli_release.py` (edit, T-167 file) | 90 -> 108 | Appends `release_report_cmd` (`autotester release-report <project> [run] --out f.html`). |
| `src/autotester/cli.py` (edit, T-167 file) | 299 -> 300 | One registration line. |
| `src/autotester/ui/routes_report.py` (edit) | 299 -> 297 | Collapses one import tuple (-4), adds one import and `router.include_router(...)` (+2). |
| `src/autotester/ui/project_view.py` (edit) | 105 -> 106 | One button. |
| `docs/MAP.md` | regenerated | `uv run autotester map`. |

## T-167 files this unit depends on (a T-167 fix cycle may force a rebase)

READ: `schema/release.py` (`ReleaseRecord`, `RegressionDiff`, `FlowOutcome`, `ReleaseIssue`), `store/run_store.py` (`load_release_record`, `list_release_records`, `save_release_scope/record`), `core/paths.py` (`run_release_record`), `stages/release.py::build_scope` and `stages/release_compare.py::build_record` (tests only, to seed a record the way COMPARE does).
EDITED: `cli_release.py` (appended block + docstring line + 2 import lines) and `cli.py` (one line after the `release-log` registration). Both are the only places the brief's "2 lines in cli.py" fits at the 300-line cap; I put the command in `cli_release.py` instead of a new `cli_unified_report.py` because a new module needs one more import line in `cli.py` and that makes it 301.

## Design notes and honesty rules as built

- Run chosen: explicit id, else the newest of the latest release record and the latest `Run`. Crawl chosen: `list_crawl_ids()[0]`.
- Regression: a record with no baseline renders "No trusted baseline, so no regression claim is made" and omits the Regressed/Fixed lists (an empty list would read as "none regressed"). An unfinished or flagged-bad record is amber. Flows with no plan show `not run` (RR6).
- Workflows: every scoped case; no verdict is `no verdict`, no result is `not run`, never PASS. FAIL/INCONCLUSIVE carry criterion, reason, fix_hint and repro steps (RE6) via `report_export`'s own helpers.
- API failures: stored first-party NETWORK evidence (run results and the latest crawl) with status outside 100-399; an unparseable row is kept as `unreadable`. Third-party rows never reach evidence (T-170 owns that filter).
- History: `PersonaRevision` rows newest first with `counts()`; `missing_unjudged` draws an "Incomplete diff" banner and is never listed as missing (CR5).
- Coverage: `crawl_summary(crawl)` rows verbatim (same figure and reason breakdown as the crawl page) plus every hole, not-entered screen and permitted hole; amber unless the crawl completed with no gaps.
- Absence: each section says `Unavailable: <reason>`; no persona, no crawl, no release record is never a zero.
- Secrets: repro steps are scrubbed by `_repro_steps`; the whole HTML is scrubbed again with the project `Redactor` last.

## Pre-check (final code commit cdb0ae53, worktree clean; no full suite, no directory-wide run)

Pre-check: cdb0ae53 uv run pytest tests/test_unified_report.py -p no:xdist t=18s -> 12 passed
Pre-check[C1]: cdb0ae53 uv run pytest tests/test_unified_report.py -k dc1 -p no:xdist t=2s -> 1 passed
Pre-check[C2]: cdb0ae53 uv run pytest tests/test_unified_report.py -k dc2 -p no:xdist t=1s -> 1 passed
Pre-check[C3]: cdb0ae53 uv run pytest tests/test_unified_report.py -k "one_invocation or regression_reads or no_baseline" -p no:xdist t=2s -> 3 passed
Pre-check[C4]: cdb0ae53 uv run pytest tests/test_unified_report.py -k dc4 -p no:xdist t=33s -> 1 passed (the test runs `scripts/check_no_secrets.py` as a subprocess: clean artifact exit 0 with "0 leak(s)", a planted raw secret exit 1)
Pre-check[lint]: cdb0ae53 uv run ruff check src tests scripts -> All checks passed
Pre-check[doctor]: cdb0ae53 uv run autotester doctor -> doctor: clean
Regression nodes (shared files edited): `uv run pytest tests/test_ui_report.py tests/test_ui_report_no_runs.py tests/test_cli_release.py tests/test_cli_surface.py tests/test_goal_contract_registration.py -p no:xdist` -> 71 passed

The per-criterion lines use `C1`-`C4` for DC1-DC4 (the lint only recognises `C<n>` tags); the untagged `Pre-check:` line is the whole new test file on cdb0ae53.

## Falsifications (one per criterion; green before, red after; each in a throwaway copy under the scratchpad, never the worktree; discarded)

| Criterion | Edit in the copy | Before | Red node after |
|---|---|---|---|
| DC1 | `_unreached` drops the `not_visited` holes | 12 passed | `test_dc1_crawl_coverage_figure_and_reasons_survive_and_unvisited_is_never_passed` |
| DC2 | render adds `len(sec.failures)` failure count | 12 passed | `test_dc2_every_section_comes_from_its_loader_and_render_computes_nothing` |
| DC3 | export also writes a `.json` sidecar | 12 passed | `test_one_invocation_one_artifact_with_all_four_classes` |
| DC4 | scrub removed from `unified_html` and the workflow redactor replaced by an empty one | 12 passed | `test_dc4_no_secret_reaches_the_artifact_and_the_scanner_says_so` |

## Findings for the checker (not issues filed)

- PROPOSED-ISSUE: `report_export.py` private helpers (`_failure_rows`, `_load_redactor`, `_needs_developer_detail`, `_repro_steps`, `_run_sort_key`) are imported across modules because `report_export.py` is at the 300-line cap and AT-582 owns it; a public re-export belongs with that owner.
- The brief said `cli.py` could take 2 lines; at 299 after T-167 it can take 1. `docs/ARCHITECTURE.md` has no row for the new modules (prose changes need a DECISIONS entry; not done here).
- The brief's new-module gate (`qa/gates/new-module-authorization.md`) does not name these files; D-081 "run all remaining work" was treated as covering them as the dispatcher directed. Confirm.
- Not done: no browser/persona walk executed; no T-204 `require_permission("report.view")` (T-204 has not landed in this base); the AI-test section is deferred (D-059).
