# Manifest — t184-pinned-regression

**Unit:** A known bug becomes a PINNED `Case` that is included in every regression run and cannot
be pruned (AT-585).
**Contract:** no dedicated `qa/contracts/*.md` exists for this path yet (issues.py is covered by
`qa/contracts/video-learning.md` VL5/VL6, which only speaks to the Excel export; expand.py by
`qa/contracts/expand.md`, which the closed-`CaseClass` decision in D-005/D-014 answers to) — flagged
for the checker to decide whether a new contract or an amendment is warranted.
**Goal task:** T-184
**Date:** 2026-09-26
**Fix cycle:** 1 of 3
**Dual check:** no
**Issues addressed:** AT-585

## The gap (AT-585, as filed)

`stages/issues.py` turned an adjudicated video analysis into `Issue` rows for the Excel sheet a
human tester reads — and nothing else. `stages/expand.py::REGRESSION_ANCHOR`
(`applicable_classes`, `CLASS_DESCRIPTIONS`) only ever replays a flow's own happy-path steps. A
confirmed bug ("Google sign-in drops the data filled at signup") had no path to a case that must
survive every future regression run — T-167's release trigger can only re-run what already exists
in `cases.jsonl`, and nothing ever put a bug-derived case there.

**Measured, not assumed:** every regression run already runs *every* case on file —
`ui/routes_runs.py::trigger_run` calls `store.list_cases()` with no filtering, and no
case-selection UI exists (checked `case_form.py`, `routes_runs.py` — no `case_ids`/checkbox
selection anywhere). So "included in every regression run" falls out of `ProjectStore.add_case`
for free once a case exists; the two real gaps were **(1)** no constructor from `Issue` to `Case`,
and **(2)** nothing stopped `ProjectStore.delete_case`/the UI delete route from silently pruning
one.

## Explicitly NOT built (per the brief, and D-005/D-014)

- **No p0-p3 priority system.** T-178 ("Atomic failure bundle + case priority p0-p3 + human
  pruning of proposed cases before LLM spend", `deps: [T-125]`, still `pending`) owns that. This
  unit adds a single boolean marker (`Case.pinned`) plus a traceability field
  (`Case.pinned_issue_id`), nothing graded.
- **No new `CaseClass` member.** D-005 rejected opening `CaseClass` ("the completeness guarantee
  is the product"); D-014 confirms: "`CaseClass` stays closed -- Issue is a separate artifact
  (D-005's rejection stands)." A pinned case reuses the existing
  `CaseClass.REGRESSION_ANCHOR`/`CaseKind.ANCHOR` pair — the taxonomy's own "must survive every
  regression run" bucket — rather than inventing a new class for "pinned bug regression."

### How T-178 should subsume this (written for that unit's author)

Once T-178's p0-p3 priority lands on `Case`, `priority == p0` should become the single source of
truth for "must run every regression, cannot be pruned," and `Case.pinned`/`pinned_issue_id` should
either (a) be retired in favor of `priority` + a still-needed `source_issue_id` traceability field,
or (b) stay as the issue-traceability half while `pinned` itself is derived from `priority is p0`
(a computed property, not a second stored flag) so the two can never drift apart. Whichever way
T-178 goes, `ProjectStore.delete_case`'s guard (currently keyed on `case.pinned`) needs to be
re-keyed on the surviving field in the same unit — flagged here so it isn't missed.

## What changed

- `src/autotester/schema/case.py:5,33-51` — `Case` gains `pinned: bool = False` and
  `pinned_issue_id: str | None = None`, plus a `model_validator(mode="after")`
  (`_pinned_issue_id_needs_the_flag`) that rejects `pinned_issue_id` set without `pinned=True` —
  the marker and its traceability field cannot go out of sync. `extra="forbid"` (inherited from
  `Artifact`) already fails loudly on a typo'd key.
- `src/autotester/stages/issues.py:29-31,111-143` — new `pin_issue_as_case(issue, flow_id, steps,
  *, project=None) -> Case`: the missing `Issue -> Case` bridge. Takes human-confirmed repro
  `steps` (never a guess derived from the issue's narrative — a pinned case that cannot actually
  reproduce the bug would be worse than none), sets `kind=CaseKind.ANCHOR`,
  `case_class=CaseClass.REGRESSION_ANCHOR`, `pinned=True`, `pinned_issue_id=issue.id`, and carries
  `issue.severity` through.
- `src/autotester/store/project_store.py:37-41,135-149` — new `PinnedCaseError(RuntimeError)`;
  `delete_case` now checks `case.pinned` first and raises `PinnedCaseError` (never a silent
  `False`) instead of removing the row.
- `src/autotester/ui/routes_cases.py:30,281-296` — the delete route's only human-reachable prune
  path now catches `PinnedCaseError` and returns **409** (the case was found and is specifically
  protected) rather than letting the exception escape as a 500 or, worse, silently deleting.
- `tests/test_pinned_regression.py` (new, 9 tests) — the constructor's contract, the closed-taxonomy
  invariant, the schema validator, "on file like any other case" (proving run-inclusion), and the
  delete refusal at the store layer.
- `tests/test_ui_case_management.py:+15` — one new test driving the real delete route end-to-end
  against a pinned case (409, case still on file after).

No file crossed 300 lines; `project_store.py` landed at exactly 300 after two docstrings were
tightened to make room (see "Actual outputs" — `doctor` was red once at 305 lines mid-session,
fixed before this manifest).

## How to verify (commands + expected)

- `uv run pytest tests/test_pinned_regression.py` (the goal task's own `done_check`) → all pass
- `uv run pytest tests/test_pinned_regression.py tests/test_ui_case_management.py tests/test_ui_cases.py tests/test_issues.py tests/test_expand.py tests/test_expand_cli.py tests/test_run_case_pipeline.py tests/test_ui_case_navigate_reachability.py` → all pass
- `uv run ruff check src tests scripts` → `All checks passed!`
- `uv run autotester doctor` → `doctor: clean`

## Actual outputs (from maker's own run)

```
$ uv run pytest tests/test_pinned_regression.py
.........
9 passed in 0.12s

$ uv run pytest tests/test_pinned_regression.py tests/test_ui_case_management.py tests/test_ui_cases.py tests/test_issues.py tests/test_expand.py tests/test_expand_cli.py tests/test_run_case_pipeline.py tests/test_ui_case_navigate_reachability.py
.............................................................................. [ 79%]
...................                                                            [100%]
90 passed, 1 skipped, 1 warning in 3.21s

$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```

**Red before the fix** — the new `tests/test_pinned_regression.py` was run with `uv run pytest`
against the **unmodified** worktree (before any of the four `src/` edits above), via `uv sync
--frozen` inside the worktree's own venv:

```
$ uv run pytest tests/test_pinned_regression.py
ImportError while importing test module '...\tests\test_pinned_regression.py'.
E   ImportError: cannot import name 'pin_issue_as_case' from 'autotester.stages.issues'
1 error in 13.32s
```

## Capability coverage (each claim -> its isolating falsification)

Throwaway copy built OUTSIDE the worktree: `src/`, `tests/{conftest.py, tests_mutation_fixtures.py,
test_pinned_regression.py, test_ui_case_management.py}`, `scripts/`, `pyproject.toml`, `uv.lock`,
`.python-version` copied into the session scratchpad (`scratchpad/falsify-t184`), `uv sync
--frozen` run there (own venv), confirmed green (20 passed) before any falsification. Every
falsifying edit below was a single hunk, applied, run, then reverted and re-confirmed green before
the next row — never touching the tracked worktree.

| capability | check | falsifying edit (single hunk) | observed |
|---|---|---|---|
| a pinned case is marked `pinned` and traces to its issue | `test_pin_issue_as_case_marks_it_pinned_and_traces_to_the_issue` | `issues.py`: `pinned=True,` -> `pinned=False,` (in `pin_issue_as_case`'s `Case(...)` call) | PASS before: part of 20/20. FAIL after: `pydantic_core...ValidationError: pinned_issue_id is set but pinned is False` |
| the pinned case stays inside the closed taxonomy (D-005/D-014) | `test_the_pinned_case_stays_inside_the_closed_taxonomy` | `issues.py`: `case_class=CaseClass.REGRESSION_ANCHOR,` -> `case_class=CaseClass.HAPPY,` | PASS before. FAIL after: `assert <CaseClass.HAPPY> is <CaseClass.REGRESSION_ANCHOR>` |
| `pinned_issue_id` without `pinned=True` is rejected by the schema | `test_pinned_issue_id_without_the_pinned_flag_is_rejected` | `case.py`: `if self.pinned_issue_id and not self.pinned:` -> `if self.pinned_issue_id and False:` | PASS before. FAIL after: `Failed: DID NOT RAISE ValidationError` |
| a pinned case refuses deletion at the store layer | `test_deleting_a_pinned_case_is_refused` | `project_store.py`: `if case is not None and case.pinned:` -> `if False:` | PASS before. FAIL after: `Failed: DID NOT RAISE PinnedCaseError` |
| the same guard is reachable end-to-end through the real UI delete route (409, case survives) | `test_deleting_a_pinned_case_through_the_ui_is_refused_with_409` | same single hunk as the row above (the route has no guard of its own — it relies on the store raising) | PASS before. FAIL after: `assert 303 == 409` |
| the guard is scoped to `pinned` only — ordinary cases still delete (no over-fire) | `test_an_unpinned_case_still_deletes_normally` + 3 pre-existing `test_ui_case_management.py` delete tests | `project_store.py`: `if case is not None and case.pinned:` -> `if case is not None:` (unconditional) | PASS before (all 4). FAIL after (all 4): e.g. `assert ['Keep me', 'Delete me'] == ['Keep me']`, `assert 400 == 303` |

The "on file like any other case" claim (`test_a_pinned_case_is_on_file_like_any_other_case`) is
not separately falsified — it asserts a pre-existing, unmodified code path (`ProjectStore.add_case`
/ `list_cases`) that this unit never touches; its coverage is that `pin_issue_as_case` produces a
valid `Case` at all, already exercised by the first row above.

## Live browser evidence

**No UI surface for creating a pinned case exists yet** — `pin_issue_as_case` has no caller in
`cli.py` or any `ui/routes_*.py` this cycle (mirrors the shape of `expand.md`'s own X6 finding: a
stage with no entry point is an absent feature). The one UI surface this unit *does* touch — the
existing case-delete button — was driven through FastAPI's `TestClient`
(`test_deleting_a_pinned_case_through_the_ui_is_refused_with_409`), not a real browser: it is a
plain POST + redirect/409 with no client-side behavior to observe, and RAM this session was kept
for non-browser work per the dispatch brief. **LIVE-BROWSER: not run — no browser-relevant surface
changed** (the delete route's response code is fully covered by TestClient; nothing here touches
rendering, JS, or a real page).

## Known limits / gaps (disclosed, not claimed)

- **No entry point to call `pin_issue_as_case` yet.** A human currently has no button/CLI command
  that goes "confirm this Issue's repro steps -> pin it as a Case." This unit builds the bridge and
  the cannot-be-pruned guarantee; wiring a caller (an "Pin as regression case" action on the issues
  page, or a CLI command) is a follow-on, not silently assumed done. Flagged rather than hidden —
  same discipline `expand.md` X6 demands of a stage's reachability.
- **`Case.severity` inherits `Issue.severity` directly** (both `Severity` enums, same values) —
  simple field carry-over, not re-derived or re-judged.
- **Full suite not run** (dispatch brief: RAM shared with a concurrent checker; targeted
  non-browser tests + ruff + doctor only, per the hard rule). All tests actually touching the
  changed modules (case schema, issues stage, project_store, routes_cases, plus expand/run-pipeline
  as consumers of `Case`) were run and are green — see "Actual outputs" above.
- **No dedicated contract row.** Flagged above under "Contract" — the checker should decide whether
  this needs a new `qa/contracts/pinned-regression.md` or an amendment to an existing one (my brief
  said do not edit `qa/contracts/`).

## Status: checked-PASS (cycle 1, 3830ba1)
