# Manifest — at594-export-secret-test

**Contract:** `qa/contracts/report-export.md` RE5, core-invariants C5
**Goal task:** none — issue-driven
**Date:** 2026-09-26
**Fix cycle:** 1 of max 3
**Persona walk:** skip (test/redaction)
**Dual check:** no
**Issues addressed:** AT-594 (low)
**Executor:** claude-sonnet-subagent

## Why this unit

AT-594: T-183 made `Case.steps` (including a FILL step's `Step.value`) the first thing rendered
into an exported artifact (`report_export._repro_steps`, added by T-183/AT-582). It was "safe only
because the credential design keeps `{{SECRET:KEY}}` placeholders in stored cases" — no test pinned
that a stored `Case` step value never holds a raw `.env` value, and `report_export.py` added no
`Redactor.scrub` call on repro steps (`qa/verdicts/t183-export-reason.md`'s own Redaction section
says this explicitly: "This unit adds no new redaction call").

## What changed (file:line, on `wave/at594-export-secret-test`, commit `03494cf`)

`src/autotester/stages/report_export.py` (244 → 273 lines):

- **New imports**: `SecretStore` (`browser.secrets`), `Redactor` (`core.redact`).
- **New helper `_load_redactor(store) -> Redactor`** (after `_case_lookup`): loads the project via
  `store.load_project()` and returns `SecretStore.load(project, store.paths.env_file,
  strict=False).redactor()` — the identical `SecretStore.load(...).redactor()` path every other
  stage/route already uses (`cli_crawl.py`, `cli_orchestrate.py`, `ui/routes_*.py`,
  `stages/manual_login.py`). No project (defensive) → an empty, harmless `Redactor({})`.
- **`_repro_steps(case, redactor)`** — signature gained `redactor: Redactor`; the formatted step
  line now passes through `redactor.scrub(...)` before being returned. A `{{SECRET:KEY}}`
  placeholder is not a known secret *value*, so `scrub` leaves it untouched (exports as the
  placeholder, unchanged behaviour); a raw declared secret value is masked to `[REDACTED]:<KEY>`
  (this is the behaviour change — see "Real leak found" below).
- **`export_excel`** — builds `redactor = _load_redactor(store)` once per call, passes it into
  `_repro_steps(case, redactor)`.
- **`export_html`** — same: builds `redactor` once, threads it through `_case_section(...,
  redactor)` → `_failure_detail_html(verdict, case, redactor)` → `_repro_steps(case, redactor)`.
- **`_case_section`** and **`_failure_detail_html`** — both gained a trailing `redactor: Redactor`
  parameter, pure plumbing, no other behaviour change.

`tests/test_report_export_secrets.py` (new, 133 lines, 5 tests) — see coverage table below.

**No change** to `schema/`, `cli.py`, `ui/`, `browser/secrets.py`, or `core/redact.py` — this unit
reuses the existing redaction mechanism, it does not add a second one (C3/C5: one concept, one
place). `qa/contracts/report-export.md` and `qa/issues.jsonl` were read but not edited (maker never
edits either).

## Real leak found and fixed (not a hypothetical)

The task brief asked to prove two things and fix in place if a test exposed a real leak. It did:
`_repro_steps` had **no redaction call at all** before this change. Falsified in a throwaway copy
outside the worktree (`.../scratchpad/at594-falsify`, never `git stash`, tracked files here
untouched) by restoring the pre-fix `report_export.py` via `git show HEAD:...` and running the new
test file against it:

```
$ uv run pytest tests/test_report_export_secrets.py -v
...
FAILED tests/test_report_export_secrets.py::test_export_excel_redacts_a_raw_secret_value_in_a_step
  AssertionError: assert 'hunter2-super-secret' not in '1. navigate...super-secret'
FAILED tests/test_report_export_secrets.py::test_export_html_redacts_a_raw_secret_value_in_a_step
  AssertionError: assert 'hunter2-super-secret' not in '<!doctype h...v></section>'
FAILED tests/test_report_export_secrets.py::test_export_excel_redacted_value_never_reaches_any_cell_in_the_workbook
  AssertionError: assert 'hunter2-super-secret' not in 'Case\nKind\...super-secret'
3 failed, 2 passed in 0.97s
```

The 2 that passed unconditionally are the placeholder-passthrough tests — correct, since a
`{{SECRET:KEY}}` placeholder was already exported verbatim before this fix (nothing resolves it in
a stored `Case`). The 3 that failed are exactly the ones asserting redaction, and they failed with
the real fake secret value (`hunter2-super-secret`, a test-only fixture value, never a real
credential) landing verbatim in both the Excel repro-steps cell and the HTML page. Same test file,
against the fixed code in this worktree, is fully green (see Real verification below). Throwaway
copy deleted after use.

## Real verification performed

```
$ uv run pytest tests/test_report_export_secrets.py tests/test_report_export.py tests/test_report_export_reason.py
.......................                                                  [100%]
23 passed in 1.44s
$ uv run ruff check src tests scripts
All checks passed!
$ uv run autotester doctor
doctor: clean
```

## Capability coverage table

| Claim | Falsifying edit (single hunk) | Check that goes red |
|---|---|---|
| A `{{SECRET:KEY}}` placeholder exports verbatim in Excel repro steps, never resolved | n/a — pre-existing behaviour, pinned as a regression guard | `test_export_excel_repro_steps_show_the_placeholder_never_the_secret_value` |
| A `{{SECRET:KEY}}` placeholder exports verbatim in HTML repro steps, never resolved | n/a — pre-existing behaviour, pinned as a regression guard | `test_export_html_repro_steps_show_the_placeholder_never_the_secret_value` |
| A raw declared secret value in a step is redacted in the Excel repro-steps cell | revert `_repro_steps` to drop the `redactor.scrub(...)` call (the actual pre-fix code) | `test_export_excel_redacts_a_raw_secret_value_in_a_step` — reproduced above, real red: `AssertionError: assert 'hunter2-super-secret' not in '1. navigate...super-secret'` |
| A raw declared secret value in a step is redacted in the HTML export | same revert | `test_export_html_redacts_a_raw_secret_value_in_a_step` — reproduced above, real red: `AssertionError: assert 'hunter2-super-secret' not in '<!doctype h...v></section>'` |
| The raw value never reaches any cell in the workbook (not just the Repro-steps column) | same revert | `test_export_excel_redacted_value_never_reaches_any_cell_in_the_workbook` — reproduced above, real red: `AssertionError: assert 'hunter2-super-secret' not in 'Case\nKind\...super-secret'` |

Each red line above is pasted verbatim from the actual throwaway-copy run against the pre-fix
`report_export.py` (see "Real leak found and fixed"), not asserted from memory.

## Live browser: not UI-touching

`export_excel`/`export_html` are plain functions with no browser dependency; this unit touches only
`stages/report_export.py` and adds a new test file, no route or template. Paths touched:
`src/autotester/stages/report_export.py`, `tests/test_report_export_secrets.py`.

## Gaps

- Full `uv run pytest` was not run this session — only the report-export test files (23 tests, all
  green) plus ruff and doctor, per the targeted-tests instruction. The checker should run the full
  suite as its own independent re-run.
- Scope is deliberately narrow to AT-594's own ask (repro steps only). `Verdict.scoreboard`/`error`
  and `Failure.reason`/`fix_hint` are untouched — RE6's `qa/verdicts/t183-export-reason.md` already
  established those are pre-scrubbed upstream (the judge only ever sees redacted evidence), so no
  new redaction path was needed there; only `Case.steps`, which is stored data never routed through
  a judge, was the actual gap this issue identified.

## Status: checked-PASS (cycle 1, qa/verdicts/at594-export-secret-test.md 8ac6ae2)
