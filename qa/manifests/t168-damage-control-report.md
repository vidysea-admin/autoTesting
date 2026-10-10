# Manifest - t168-damage-control-report

**Unit:** T-168, the damage-control report: regression diff, API failures, workflows and change history (plus the crawl's coverage) on one surface, built from stored evidence only.
**Brief:** `qa/briefs/t168-damage-control-report.md`. **Contract:** `qa/contracts/damage-control-report.md` (DRAFT, DC1-DC4), plus `core-invariants.md`.
**Branch / base:** `wave/t168-damage-control-report` on T-167's code commit `00fae668` (T-167 is built, NOT yet checked; this unit cannot merge before it).
**Code commit (pre-check sha):** 72a7ecae (cycle-2 repair of DC4 F1; cycle-1 product was 82ba1f1e, cycle-0 cdb0ae53). The manifest commit after it adds only this file.
Repair base: fb47735c
Policy-Version: proportional-verification/2026-10-10.9
Tier: M (multi-file behaviour reading five existing evidence owners, one new report module set, a CLI and an HTTP surface; no L trigger)
Dual check: required
dual-trigger: security src/autotester/stages/unified_report.py:265
Round cap: SECURITY CLASS -- redaction of report output
Fix cycle: 2
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
| `src/autotester/stages/unified_report.py` (new) | 285 | Five loaders (regression, api, workflows, history, coverage) over the existing owners; `build_report`, `unified_html`, `export_unified_html`. |
| `src/autotester/stages/unified_report_render.py` (new) | 170 | One self-contained HTML document; formats only, computes nothing. |
| `src/autotester/ui/routes_unified_report.py` (new) | 38 | `GET /projects/{slug}/damage-report[?run=]`; empty state when nothing ran. |
| `tests/test_unified_report_secrets.py` (new, cycle 1; cycle 2 adds 4) | 182 | 7 tests: special-character secret in every text field (HTML, CLI output, report object, workflow loader) and, cycle 2, on the ERROR path (CLI, route, `build_report`, malformed JSON). |
| `tests/test_unified_report.py` (new) | 260 | 12 tests (the brief's `done_check` file). |
| `src/autotester/cli_release.py` (edit, T-167 file) | 90 -> 108 | Appends `release_report_cmd` (`autotester release-report <project> [run] --out f.html`); cycle 2: catches only `ReportUnavailable`/`ReportUnreadable`. |
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
- Secrets: repro steps are scrubbed by `_repro_steps`; the whole report object is scrubbed with the project `Redactor` before render (cycle 1; cycle 0 scrubbed the HTML after render, which missed secrets containing HTML-special characters).

## Pre-check (final code commit 72a7ecae, worktree clean; no full suite, no directory-wide run)

Pre-check: 72a7ecae uv run pytest tests/test_unified_report.py tests/test_unified_report_secrets.py -p no:xdist t=14s -> 19 passed
Pre-check[C1]: 72a7ecae uv run pytest tests/test_unified_report.py -k dc1 -p no:xdist t=1s -> 1 passed
Pre-check[C2]: 72a7ecae uv run pytest tests/test_unified_report.py -k dc2 -p no:xdist t=1s -> 1 passed
Pre-check[C3]: 72a7ecae uv run pytest tests/test_unified_report.py -k "one_invocation or regression_reads or no_baseline" -p no:xdist t=1s -> 3 passed
Pre-check[C4]: 72a7ecae uv run pytest tests/test_unified_report.py tests/test_unified_report_secrets.py -k dc4 -p no:xdist t=5s -> 7 passed (success path: plain and special-character secret `p&ss<w>o'rdQ9` absent raw and HTML-escaped from HTML, CLI output, report object; error path: a stored `release.json` with the secret in a mistyped field, CLI and route outputs hold none of its raw, HTML-escaped or URL-encoded forms and no `input_value`)
Pre-check[lint]: 72a7ecae uv run ruff check src tests scripts -> All checks passed
Pre-check[doctor]: 72a7ecae uv run autotester doctor -> doctor: clean
Regression nodes (files this cycle touched: `cli_release.py`, `routes_unified_report.py`, `stages/unified_report.py`): `uv run pytest tests/test_cli_release.py tests/test_ui_report.py tests/test_ui_report_no_runs.py tests/test_goal_contract_registration.py -p no:xdist` -> 24 passed on 72a7ecae.

Cycle 2 repair (checker r1 B finding F1): the error path printed unscrubbed exception text built from stored data (pydantic's `input_value`). Output channels closed:
- `stages/unified_report.py:243-251` `build_report` converts every non-`ReportUnavailable` exception into `ReportUnreadable`, whose text (`_unreadable`, `_where`, `_file_of`, :54-97) is fixed wording plus the stored file's last two path parts or identifier-shaped field names and the exception type, passed through the project `Redactor`; never pydantic's message; raised `from None`.
- `stages/unified_report.py:273-281` `export_unified_html`: a corrupt `project.json` is wrapped the same way.
- `cli_release.py:109-111` and `ui/routes_unified_report.py:30-38`: catch only the two typed errors; the route returns HTTP 500 with the fixed text for `ReportUnreadable` and keeps the 200 empty state for `ReportUnavailable` (no runs yet, DC1-DC4 are silent and `test_cli_and_ui_with_no_runs_show_an_empty_state...` requires it). Unexpected errors no longer reach a handler that prints `str(exc)`.
- The loaders' `Unavailable: <reason>` strings sit inside the report object, so `scrub_obj` already covers them (cycle 1); no log line is written by this feature.
Advice sites: `tests/test_cli_advice_resolves.py` on this branch lists 3 new sites: `('cli_release.py','release')` and `('cli_release.py','release-log')` (parent unit T-167, which registers them in its own repair) and `('stages/unified_report.py','release')` (this unit, the pre-existing text "a release is started with `autotester release`" in `load_regression`). The advice names `autotester release`, which resolves; the registry entry for `stages/unified_report.py` / `release` is left to be added after the parent merges (that file was not edited here). The other 30 tests of that file pass.

Cycle 1 repair (ISS-t168-damage-control-report-1 and -3): `build_report` (`stages/unified_report.py:203-207`) now scrubs the report OBJECT with the project `Redactor.scrub_obj` before `render_html`, so the secret never reaches the renderer in any form; the post-render scrub in `unified_html` is removed (it added nothing, and was the layer that ran too late). Layers: the object scrub is load-bearing for `test_dc4_special_character_secret_is_absent_raw_and_escaped_in_html_and_cli` and `test_dc4_report_object_is_clean_before_it_is_rendered`; the workflow loader's repro-step scrub is load-bearing for `test_dc4_workflow_loader_scrubs_repro_steps_on_its_own`.

The per-criterion lines use `C1`-`C4` for DC1-DC4 (the lint only recognises `C<n>` tags); the untagged `Pre-check:` line is the new and existing unified-report test files on 82ba1f1e.

## Falsifications (one per criterion; green before, red after; each in a throwaway copy under the scratchpad, never the worktree; discarded)

| Criterion | Edit in the copy | Before | Red node after |
|---|---|---|---|
| DC1 | `_unreached` drops the `not_visited` holes | 12 passed | `test_dc1_crawl_coverage_figure_and_reasons_survive_and_unvisited_is_never_passed` |
| DC2 | render adds `len(sec.failures)` failure count | 12 passed | `test_dc2_every_section_comes_from_its_loader_and_render_computes_nothing` |
| DC3 | export also writes a `.json` sidecar | 12 passed | `test_one_invocation_one_artifact_with_all_four_classes` |
| DC4 (cycle 0) | scrub removed from `unified_html` and the workflow redactor replaced by an empty one | 12 passed | `test_dc4_no_secret_reaches_the_artifact_and_the_scanner_says_so` (superseded by cycle 1) |
| DC4 (cycle 2, one hunk, `git archive` copy under the scratchpad run with `PYTHONPATH` on the copy, discarded) | `build_report` raises `ReportUnreadable(str(exc))` instead of `_unreadable(store, exc)` | 19 passed | `test_dc4_cli_error_path_does_not_echo_a_stored_secret` (AssertionError: `input_value="p&ss<w>o'rdQ9"` in the CLI output) and `test_dc4_build_report_failure_message_names_the_file_never_the_value`. Before the fix the same three error-path tests were red by assertion on this branch (CLI, route 200, message) |
| DC4 (cycle 1, one hunk, throwaway copy under the scratchpad, discarded) | `build_report` returns `report` instead of the scrubbed copy (the `scrub_obj` call removed) | 15 passed | `test_dc4_special_character_secret_is_absent_raw_and_escaped_in_html_and_cli` and `test_dc4_report_object_is_clean_before_it_is_rendered` (AssertionError, special-character secret in the HTML/report). A second single-hunk copy, `_repro_steps` scrub bypassed, goes red on `test_dc4_workflow_loader_scrubs_repro_steps_on_its_own` |

## Findings for the checker (not issues filed)

- PROPOSED-ISSUE: `report_export.py` private helpers (`_failure_rows`, `_load_redactor`, `_needs_developer_detail`, `_repro_steps`, `_run_sort_key`) are imported across modules because `report_export.py` is at the 300-line cap and AT-582 owns it; a public re-export belongs with that owner.
- The brief said `cli.py` could take 2 lines; at 299 after T-167 it can take 1. `docs/ARCHITECTURE.md` has no row for the new modules (prose changes need a DECISIONS entry; not done here).
- The new modules (`schema/unified_report.py`, `stages/unified_report.py`, `stages/unified_report_render.py`, `ui/routes_unified_report.py`) are not named in the brief, the contract or `qa/gates/new-module-authorization.md`, and D-081 does not authorise them (checker ruling 1, cycle 0): they await the owner's confirmation before merge.
- Not done: no browser/persona walk executed; no T-204 `require_permission("report.view")` (T-204 has not landed in this base); the AI-test section is deferred (D-059).
