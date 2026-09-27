# Manifest — at608-609-scrub-leftovers

**Contract:** `qa/contracts/core-invariants.md` C5, C2; `qa/contracts/ui.md`; `qa/contracts/report-export.md` RE5
**Goal task:** none — issue-driven
**Date:** 2026-09-26
**Fix cycle:** 1 of max 3
**Persona walk:** skip (a UI surface changed — see "Persona walk" section below; checker needs Mode D for AT-608)
**Dual check:** no
**Issues addressed:** AT-608 (medium, secret-leak), AT-609 (low, secret-leak)
**Executor:** claude-opus-subagent

## Why this unit

Both issues are the same shape as AT-593/AT-594 (already fixed, merged): a field that reaches a
rendered artifact without going through the project's existing `Redactor`/`SecretStore` path (C5 —
"secrets never reach a model, a log, or an artifact"), even though every neighbouring field on the
same surface already does.

- **AT-608**: `routes_crawls.py::_coverage_card` renders `_load_flowspec_safe`'s stated read-failure
  text with `escape()` only. That text is built from a caught pydantic `ValueError` (`f"the FlowSpec
  could not be read -- {type(exc).__name__}: {exc}"`), and pydantic's own validation error echoes
  `input_value=...` — so a declared secret pasted into a broken `flowspec.json` reaches the browser
  raw. `_queue_coverage_gap` in the same file already scrubs the identical read-failure string
  before logging it (AT-593); `_coverage_card` was the other caller of `_load_flowspec_safe` and was
  missed.
- **AT-609**: `report_export.py`'s `export_excel`/`export_html` already thread a `Redactor` through
  `_repro_steps` (AT-594), but two other operator-authored fields on the same exported artifacts
  were never passed through it: `Case.title` (the Excel "Case" column, and the HTML `<h2>`) and
  `Evidence.label` (the HTML `<figcaption>`).

## What changed

`src/autotester/ui/routes_crawls.py` (298 → 286 lines):

- **Import added**: `from autotester.browser.secrets import SecretStore` moved to the top-level
  import block (was previously a lazy import inside `start_crawl` only — `SecretStore` has no heavy
  dependency, unlike the browser-session imports it was grouped with, so hoisting it is not a
  behaviour change).
- **`_coverage_card`** (line ~93): gained a trailing `redactor: Redactor` parameter. The read-failure
  branch now renders `escape(redactor.scrub(spec_error))` instead of `escape(spec_error)` — the same
  `Redactor.scrub` call `_queue_coverage_gap` already makes for the identical string, just applied at
  its other call site.
- **`crawl_page`** (line ~176): renamed the discarded `_project` binding to `project` (now used),
  builds `redactor = SecretStore.load(project, store.paths.env_file, strict=False).redactor()` —
  the identical `SecretStore.load(...).redactor()` path every other route/stage already uses — and
  passes it into `_coverage_card`.
- **`_bounds_form` moved out** to `crawl_view.py` as public `crawl_view.bounds_form` (see below).
  This was needed only to bring the file back under C2's 300-line cap after the AT-608 fix pushed it
  to 305 lines; it changes no behaviour, only its home. The two call sites in `crawls()` were updated
  to `crawl_view.bounds_form(...)`.

`src/autotester/ui/crawl_view.py` (209 → 233 lines):

- **New public function `bounds_form(slug, label)`** — the exact body of the old
  `routes_crawls._bounds_form`, moved verbatim (docstring updated to note the move and why). This
  module already exists for exactly this reason (its own docstring: "split from `routes_crawls.py`
  to keep both under the 300-line cap (C2)"), so this is the same split, applied a second time to
  the same pair of files, not a new module (C3: no new file was created).

`src/autotester/stages/report_export.py` (272 → 281 lines):

- **`export_excel`** (~line 138): the `Case` column value is now `case_title = redactor.scrub(case.title)
  if case else result.case_id` instead of `case.title if case else result.case_id`.
- **`_case_section`** (~line 195): `title = escape(redactor.scrub(case.title) if case else
  result.case_id)` (was `escape(case.title if case else result.case_id)`), and the figcaption is now
  `escape(redactor.scrub(shot.label or shot.path))` (was `escape(shot.label or shot.path)`).
  `redactor` was already an existing parameter of `_case_section` (threaded in from `_load_redactor`
  by AT-594) — no new plumbing needed, only two more call sites use it.

`tests/test_ui_crawl_approval.py` (214 → 235 lines): one new test,
`test_crawl_page_scrubs_a_secret_from_a_broken_flowspecs_read_error` — see coverage table.

`tests/test_report_export_secrets.py` (133 → 196 lines): one new fixture
(`_seed_title_and_label`) and two new tests,
`test_export_excel_redacts_a_raw_secret_value_in_the_case_title` and
`test_export_html_redacts_a_raw_secret_value_in_the_case_title_and_evidence_label` — see coverage
table. New imports: `base64`, `EvidenceKind`, `Evidence` (all already used elsewhere in the test
suite for the same PNG-fixture pattern, e.g. `tests/test_report_export.py`).

**No change** to `schema/`, `core/redact.py`, `browser/secrets.py`, `qa/contracts/`, or
`qa/issues.jsonl` (maker never edits either) — this unit reuses the existing `Redactor`/`SecretStore`
mechanism at two more call sites; it does not add a second redaction mechanism (C3/C5).

## Persona walk

`skip` — no new user-facing flow or screen was added; the crawl page and the two export formats
already existed and are covered by existing UI/export tests. **Flagged for the checker anyway**:
AT-608's fix changes what a rendered page shows (the coverage-card error text) in a code path a
Playwright-driven Mode D walk could hit differently than the TestClient-based unit test does (e.g.
HTML entity handling in a live browser DOM vs. `response.text`), so the checker should run Mode D
against a project with a broken `flowspec.json` containing a declared secret, not rely on the
TestClient assertion alone.

## Real verification performed (no `-q`)

```
$ uv run pytest tests/test_ui_crawl_approval.py tests/test_report_export_secrets.py
...............                                                          [100%]
15 passed, 1 warning in 0.95s

$ uv run pytest tests/ -k "redact or export or crawl"
........................................................................ [ 30%]
........................................................................ [ 60%]
........................................................................ [ 90%]
.......................                                                  [100%]
239 passed, 1658 deselected, 1 warning in 423.96s (0:07:03)

$ uv run pytest tests/test_cli_advice_resolves.py
...........................                                              [100%]
27 passed in 4.55s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

The unfiltered, whole-suite `uv run pytest tests/` was not part of this unit's Verify list and was
not required; it was additionally launched in the background as a bonus check (the `-k` subset above
took 7 minutes for 239/~1900 tests, so the full suite runs considerably longer on this machine) but
was still running when this manifest was written and is not blocking on it — see Gaps.

## Falsification (throwaway copy, never `git stash`)

Performed in `C:/Users/Lenovo/AppData/Local/Temp/claude/d--autoTesting/<session>/scratchpad/falsify/repo`,
a `cp -r` of this worktree, never the worktree itself, then deleted after use. Baseline confirmed
green in the copy first (15 passed) before any falsifying edit.

**AT-608** — anchor `escape(redactor.scrub(spec_error))` at `routes_crawls.py:105`, reverted (single
hunk, matched exactly once, file confirmed changed) to `escape(spec_error)`:

```
$ uv run pytest tests/test_ui_crawl_approval.py -k test_crawl_page_scrubs_a_secret_from_a_broken_flowspecs_read_error
FAILED tests/test_ui_crawl_approval.py::test_crawl_page_scrubs_a_secret_from_a_broken_flowspecs_read_error
AssertionError: assert 'hunter2' not in '<!doctype h.../main></div>'
'hunter2' is contained here:
  lue=&#x27;hunter2&#x27;, input_type=str]
1 failed, 7 deselected, 1 warning in 0.40s
```

Real red, for the right reason — the raw `hunter2` value inside pydantic's own `input_value=...`
text, exactly the AT-608 leak.

**AT-609 (Excel)** — anchor `case_title = redactor.scrub(case.title) if case else result.case_id`
at `report_export.py:142`, reverted to `case_title = case.title if case else result.case_id`:

```
$ uv run pytest tests/test_ui_crawl_approval.py tests/test_report_export_secrets.py
FAILED tests/test_report_export_secrets.py::test_export_excel_redacts_a_raw_secret_value_in_the_case_title
AssertionError: assert 'hunter2-super-secret' not in 'Login works...super-secret'
'hunter2-super-secret' is contained here:
  Login works hunter2-super-secret
1 failed, 14 passed, 1 warning in 1.14s
```

Only the named test failed; all 14 others (including the placeholder-passthrough regression guards
from AT-594) stayed green — the mutation is scoped to exactly the property it claims.

**AT-609 (HTML)** — two anchors reverted together (both are the single AT-609 HTML hunk):
`title = escape(redactor.scrub(case.title) if case else result.case_id)` →
`title = escape(case.title if case else result.case_id)`, and
`f"<figcaption>{escape(redactor.scrub(shot.label or shot.path))}</figcaption></figure>"` →
`f"<figcaption>{escape(shot.label or shot.path)}</figcaption></figure>"`:

```
$ uv run pytest tests/test_report_export_secrets.py -k test_export_html_redacts_a_raw_secret_value_in_the_case_title_and_evidence_label
FAILED tests/test_report_export_secrets.py::test_export_html_redacts_a_raw_secret_value_in_the_case_title_and_evidence_label
AssertionError: assert 'hunter2-super-secret' not in '<!doctype h...v></section>'
'hunter2-super-secret' is contained here:
  gin works hunter2-super-secret <span class='badge' ...>PASS</span></h2>...
  <figcaption>before hunter2-super-secret</figcaption>
1 failed, 6 deselected
```

Both leaks (the `<h2>` title and the `<figcaption>` label) visible raw in the same failure output,
confirming the test's assertion actually exercises both fields the fix touches.

## Capability coverage table

| Claim | Falsifying edit (single hunk) | Check that goes red |
|---|---|---|
| A broken `flowspec.json`'s stated read-failure text on the crawl page is scrubbed, never the raw declared secret | revert `_coverage_card`'s `redactor.scrub(spec_error)` to `spec_error` | `test_crawl_page_scrubs_a_secret_from_a_broken_flowspecs_read_error` — reproduced above |
| A `Case.title` containing a raw declared secret is redacted in the Excel "Case" column | revert `export_excel`'s `case_title = redactor.scrub(...)` | `test_export_excel_redacts_a_raw_secret_value_in_the_case_title` — reproduced above |
| A `Case.title` (HTML `<h2>`) and `Evidence.label` (HTML `<figcaption>`) containing a raw declared secret are both redacted in the HTML export | revert both `redactor.scrub(...)` calls in `_case_section` | `test_export_html_redacts_a_raw_secret_value_in_the_case_title_and_evidence_label` — reproduced above |

Each red line above is pasted verbatim from the actual throwaway-copy run against the pre-fix code,
not asserted from memory.

## Gaps / disclosed residuals

- The full, unfiltered `uv run pytest tests/` was launched in the background as a bonus check beyond
  this unit's required Verify list, and had not finished by the time this manifest was written (it
  runs well beyond several minutes at this scale). Every test file that actually imports or exercises
  `routes_crawls.py` or `report_export.py` was independently confirmed — `grep -rl "routes_crawls\|
  report_export" tests/*.py` names `test_goal_done_checks.py` (a string literal in a goal-task table,
  not an import), `test_grade_evidence.py` (a docstring mention, not an import),
  `test_report_export.py`, `test_report_export_reason.py`, `test_report_export_secrets.py`,
  `test_ui_crawl_approval.py`, and `test_ui_report_no_runs.py` — all six real ones are covered by the
  `-k "redact or export or crawl"` run (239 passed) or the two named files run directly (15 passed).
  The checker should re-run the full suite independently rather than trust this disclosed gap.
- `AT-608`'s fix is judged only by a `TestClient`-driven HTML-text assertion in this manifest — see
  "Persona walk" above for why the checker should also run a live Mode D check.
- `SecretStore.load` is called once per `GET /projects/{slug}/crawls/{crawl_id}` request in
  `crawl_page` now (previously zero times on this route) — this re-reads and re-parses the project's
  `.env` on every page load, same cost `report_export._load_redactor` already pays per export call
  and `routes_runs.py` pays per run-detail page load elsewhere in this codebase, so it is an existing
  accepted cost pattern, not a new one.
- `shot.path` is scrubbed as a side effect of `redactor.scrub(shot.label or shot.path)` (the
  fallback branch when `label` is unset) — harmless (a screenshot path is never a secret value) and
  avoids a second conditional; not exercised by a dedicated test since no existing test asserts on
  an unlabelled screenshot's figcaption content.

## Status: checked-PASS (cycle 1, qa/verdicts/at608-609-scrub-leftovers.md 928b37a)
