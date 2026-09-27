# Manifest — t183-export-reason

**Contract:** qa/contracts/report-export.md RE6 (added by D-045)
**Goal task:** T-183
**Date:** 2026-09-26
**Fix cycle:** 1 of 3
**Dual check:** no
**Issues addressed:** AT-582

## Why this unit

AT-582 (checker goal-coverage review, 2026-09-25 counselor-tool meeting): a `Verdict` failure
already carries a `reason` and a `fix_hint` (`schema/verdict.py:54-62`), but neither developer
export shows them — `stages/report_export.py:76` (Excel columns) and `report_export.py:135-142`
(HTML case section) rendered only the scoreboard/error, with no repro steps and no way for a
developer to act on a FAIL/INCONCLUSIVE without re-opening the live UI's per-run page.

## What changed (file:line, on `wave/t183-export-reason`, commit `8c1f05c`)

`src/autotester/stages/report_export.py` (184 → 244 lines):

- **New imports** (line 22-24): `Result` (from `schema.enums`), `Verdict` (from `schema.verdict`).
- **New helpers** (after `_case_lookup`, ~line 64-88):
  - `_needs_developer_detail(verdict) -> bool` — `True` only for `Result.FAIL` /
    `Result.INCONCLUSIVE` (RE6's own wording: "For every FAIL or INCONCLUSIVE verdict"), so a
    PASS gets no failure/repro noise.
  - `_failure_rows(verdict) -> list[tuple[criterion_id, reason, fix_hint]]` — reads
    `verdict.failures` verbatim (RE1: nothing recomputed).
  - `_repro_steps(case) -> list[str]` — formats each `Step` as `"<order>. <action> <target>[ =
    <value>]"`, straight off `case.steps`.
- **`export_excel`** (~line 100-125): header gains two trailing columns, `"Failures"` and `"Repro
  steps"` — **existing 9 columns keep their exact order** (RE2 unchanged); each row's new cells
  are `""` unless `_needs_developer_detail` is true, in which case they're the joined
  `criterion: reason (fix: fix_hint)` lines / joined repro-step lines (`\n`-separated, multiple
  failures or steps in one cell).
- **`_case_section`** (~line 148 area): now calls `_failure_detail_html(verdict, case)` and
  splices its output between the scoreboard/error paragraph and the screenshots `<div>`.
- **New `_failure_detail_html(verdict, case) -> str`**: for FAIL/INCONCLUSIVE, emits
  `<div class='detail'>` with an `<h3>Failures</h3><ul>` (one `<li>` per failure: `<code>` criterion
  id, escaped reason, and `<em>fix: …</em>` when `fix_hint` is set) and/or `<h3>Repro
  steps</h3><ol>` (one `<li>` per case step); empty string for PASS or when a case has neither.
- **CSS**: added a 3-line `.detail`/`.detail h3`/`.detail li` block to the export's existing
  inline `<style>` — no external stylesheet, no touch to `ui/theme.py` (no-fire list unchanged).

`tests/test_report_export_reason.py` (new, 160 lines, 7 tests) — see below.

**No change** to `schema/verdict.py`, `cli.py`, `ui/routes_report.py`, or any other exporter
consumer. `ui/routes_report.py::_failure_list` (the live per-run page's own failure renderer) was
read for reference but not imported — `stages/` must not depend on `ui/` (existing layering; only
`ui/` imports from `stages/report_export.py`, e.g. `png_base64`), so a small local
`_failure_rows`/`_failure_detail_html` pair was written instead of sharing code across that
boundary. Both use the same underlying `Failure` fields, just formatted independently.

## Redaction (RE5 — no new secret-handling path)

Checked how the current exports scrub: **they don't, directly.** `report_export.py` has never
called `Redactor.scrub` on `scoreboard`/`error` — RE5's own text says exports "inherit the existing
guarantee": redaction happens upstream, at `session._record` (evidence) and inside `grade.py`'s
prompt construction, before a `Judgment` (and therefore its `failures[].reason`/`fix_hint`, which
the model writes back from already-redacted evidence) is ever persisted as a `Verdict`. Confirmed
by reading `stages/grade.py:140-184` — the judge only ever sees the pre-scrubbed prompt, so
whatever it emits (`scoreboard`, `note`, and now the fields this unit renders) carries the same
guarantee `scoreboard`/`error` already relied on. This unit adds no new redaction call, matching
RE5's "adds no new secret-handling path" — it is the same source of truth (`Verdict.failures`,
`Case.steps`), just displayed where it wasn't before.

## Real verification performed

```
$ uv run pytest tests/test_report_export_reason.py -v
7 passed
$ uv run pytest tests/test_report_export_reason.py tests/test_report_export.py tests/test_ui_report.py tests/test_crawl_report.py tests/test_ui_report_no_runs.py
40 passed, 1 warning in 6.68s (1 warning is a pre-existing anyio deprecation notice, unrelated)
$ uv run ruff check src tests scripts
All checks passed!
$ uv run autotester doctor
doctor: clean
```

## Capability coverage table

| Claim | Falsifying edit (single hunk) | Check that goes red |
|---|---|---|
| Excel shows criterion+reason+fix_hint for a FAIL | revert `failures_text = "\n".join(...) if detail else ""` to `""` | `test_export_excel_shows_failure_reason_and_fix_hint_for_a_fail` |
| Excel shows repro steps for a FAIL/INCONCLUSIVE | revert `steps_text = "\n".join(...) if detail else ""` to `""` | `test_export_excel_shows_failure_reason_and_fix_hint_for_a_fail`, `test_export_excel_shows_repro_steps_for_inconclusive_even_with_no_failures` |
| Excel keeps existing 9 columns' order unchanged | reorder the header list, e.g. swap `"Result"`/`"Outcome"` | `test_export_excel_existing_columns_are_unchanged` |
| Excel emits no failure/repro text for a PASS | change `_needs_developer_detail` to `return verdict is not None` (fire on every verdict) | `test_export_excel_leaves_failure_columns_blank_for_a_pass` |
| HTML shows criterion/reason/fix_hint for a FAIL | make `_failure_detail_html` return `""` unconditionally | `test_export_html_shows_failure_criterion_reason_and_fix_hint` |
| HTML shows repro steps for a FAIL | remove the `steps_html` branch from `_failure_detail_html` | `test_export_html_shows_repro_steps` |
| HTML omits the detail block for a PASS | change `_needs_developer_detail` to always return `True` | `test_export_html_omits_detail_block_for_a_pass` |
| INCONCLUSIVE (no failures) still gets repro steps, not a stray failures cell | change `_needs_developer_detail` to require `verdict.failures` non-empty | `test_export_excel_shows_repro_steps_for_inconclusive_even_with_no_failures` |

Each row was hand-verified red-first: the whole suite failed exactly this way against the
pre-fix code (5 of 7 new tests red; the 2 that passed — "existing columns unchanged" and "PASS
omits detail" — passed because the old code already had no new columns/detail block to break,
which is itself the correct red/green split for those two).

## Live-browser section (for the checker's Mode D)

Not run in this session — RAM was ~2.4 GB free for the whole box (shared with a checker sweep),
and `export_excel`/`export_html` are plain functions with no browser dependency of their own; the
only "live browser" surface is `ui/routes_report.py`'s `/projects/{slug}/report.html` and
`/report.xlsx` download routes, which call these same two functions unchanged. Reproduction
recipe:

```bash
# from the repo/worktree root, in a Python REPL or a throwaway script:
uv run python - <<'PY'
from autotester.schema.case import Case
from autotester.schema.enums import Action, CaseClass, CaseKind, Outcome, Result
from autotester.schema.flowspec import Step
from autotester.schema.project import Project
from autotester.schema.run import RawResult, Run
from autotester.schema.verdict import Failure, Verdict
from autotester.store import ProjectStore

store = ProjectStore("mode-d-demo", None)  # or pass a tmp root
store.save_project(Project(slug="mode-d-demo", name="Mode D demo",
                            base_url="https://demo.test", allowed_domains=["demo.test"]))
case = Case(project="mode-d-demo", flow_id="flow-login", kind=CaseKind.BEST,
            case_class=CaseClass.HAPPY, title="Login works",
            steps=[Step(order=1, action=Action.NAVIGATE, target="/login")])
store.add_case(case)
store.save_run(Run(id="run-moded", project="mode-d-demo", case_ids=[case.id]))
store.save_result("run-moded", RawResult(case_id=case.id, outcome=Outcome.COMPLETED))
store.save_verdict("run-moded", Verdict(
    run_id="run-moded", case_id=case.id, result=Result.FAIL, criteria_met=0, criteria_total=1,
    grader_provider="gemini",
    failures=[Failure(criterion_id="c1", reason="login form still visible",
                       fix_hint="check the redirect wait")],
))
PY

# then serve the UI and open a real browser:
uv run uvicorn autotester.ui.app:app --port 8765
# navigate to http://127.0.0.1:8765/projects/mode-d-demo/report.html
#   -> confirm a "Failures" <h3> with "c1 — login form still visible" and
#      "fix: check the redirect wait", plus a "Repro steps" <h3> with "1. navigate /login"
# navigate to http://127.0.0.1:8765/projects/mode-d-demo/report.xlsx and download it
#   -> open in Excel/openpyxl, confirm the "Failures" and "Repro steps" columns are populated
#      for the FAIL row and would be blank for a PASS row
```

## Gaps

- Full `uv run pytest` suite was **not** run — free RAM measured ~2.4-2.6 GB for the whole box
  during this session (below the 3.5 GB gate), shared with a checker sweep and sibling maker
  units (t182, t184) in their own worktrees. Only the targeted report/export/UI-report test files
  were run (40 tests, all green). The checker should run the full suite when RAM allows, or accept
  targeted coverage as sufficient given the change is scoped to one file.
- The live-browser recipe above was written but not executed in this session (same RAM
  constraint) — left for the checker's Mode D run.
- No must-fix/suggestion split was added — AT-582's title mentions it but RE6 (the actual,
  authorized contract text) only asks for criterion + reason + fix_hint + repro steps. Adding a
  severity split would be scope creep beyond what D-045 authorized; flagging in case the checker
  wants a follow-up issue instead.
- Multi-failure cells (Excel) use `\n`-joined text in one cell rather than one row per failure —
  chosen to preserve RE2's "one row per case" invariant; not separately covered by a
  multi-failure test (only single-failure cases were seeded). Worth a follow-up test if the
  checker wants that path pinned.

Status: checked-PASS (cycle 1, 17fe44f)
