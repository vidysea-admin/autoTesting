# Manifest — at567-file-splits

**Contract:** qa/contracts/core-invariants.md C2 (300-line cap, no file exceeds it; every module
has a docstring stating its one job)
**Issues addressed:** AT-567 (medium, open -> fixed for helpers/session/routes_runs; explore_node
deferred, AT-335 on hold, deliberately untouched)
**Date:** 2026-09-25
**Fix cycle:** 1 of 3
**Dual check:** no
**Executor:** claude-sonnet-subagent (maker build subagent)
**Branch/worktree:** `wave/at567-file-splits`, `D:/autoTesting/.worktrees/at567-file-splits`
**Base:** master `5bef92f` (merged in mid-task -- master had moved 2 commits, `d30b996`/`5bef92f`,
both docs/qa only, no overlap with the touched files; fast-forward, no conflicts)
**Commit:** `446b9e5`

## What AT-567 said

Three files sat exactly at the 300-line C2 cap after heavy churn with no headroom for the next
fix: `src/autotester/ui/helpers.py`, `src/autotester/browser/session.py`,
`src/autotester/ui/routes_runs.py`. `note_2026_09_25_at576` on the issue records that a previous
unit (77346cb, at576-577-serial-runs cycle 2) already trimmed docstrings under pressure to stay
at 300 lines, dropping contract anchors: "E5 holds" in `settle`, "C7: facts recorded, the grader
still owns the verdict" in `assert_expected` (both `session.py`), the AT-036 history pointer, and
the exact Playwright error text in the AT-576 note (`routes_runs.py`). `explore_node.py` (also
named in the original AT-567 sweep finding) is out of scope here -- AT-335 touches explore files
and is on hold.

## Before/after line counts

| File | Before | After | New sibling | Sibling lines |
|---|---:|---:|---|---:|
| `src/autotester/ui/helpers.py` | 300 | 184 | `src/autotester/ui/credential_guard.py` | 162 |
| `src/autotester/browser/session.py` | 300 | 270 | `src/autotester/browser/evidence.py` | 61 |
| `src/autotester/ui/routes_runs.py` | 300 | 149 | `src/autotester/ui/run_execution.py` | 173 |

All six files are now well under the 300-line cap. `session.py` has less headroom (270, ~10%)
than the other two by design: the natural responsibility seam here is evidence/screenshot
concerns (moved) vs. lifecycle + the dozen small page-action methods (`goto`/`fill`/`click`/etc.),
and further splitting the action methods would fragment `BrowserSession`'s single cohesive public
API across three files for no functional reason. 270/300 still gives real room for the next fix.

## Moved functions/methods (by responsibility)

**`ui/helpers.py` -> `ui/credential_guard.py`** (credential-guard concern, vs. the slug/id/url
validation and lookup helpers that stay):
- `_credential_variants`, `_refuse_direction_override`, `_refuse_unsafe_value`,
  `_refuse_unsafe_submission`
- Re-exported from `ui/helpers.py` (`from autotester.ui.credential_guard import ...` +
  `__all__`) so every existing `from autotester.ui.helpers import _refuse_unsafe_submission` (etc.)
  importer across `ui/app.py`, `ui/routes_cases.py`, `ui/routes_credentials.py`,
  `ui/routes_project_edit.py`, `ui/routes_sources.py`, `ui/routes_learn.py`,
  `ui/routes_crawl_approval.py` keeps working unchanged -- verified by running every one of
  those modules' tests (see Verify below).

**`browser/session.py` -> `browser/evidence.py`** (screenshot capture + evidence-recording, vs.
lifecycle/page-action methods that stay):
- `BrowserSession.screenshot`, `BrowserSession._record` -> `EvidenceMixin.screenshot`,
  `EvidenceMixin._record`
- `MASK_CSS`, `MASK_ATTR` constants moved with them
- `BrowserSession` now inherits `EvidenceMixin`, so both methods behave as ordinary instance
  methods on `self` unchanged (`self.page`, `self.state`, `self.secrets` are all still set in
  `BrowserSession.__init__`, defined in `session.py`)
- `MASK_CSS`/`MASK_ATTR` re-exported from `session.py`'s `__all__` -- `tests/test_browser.py`
  imports both directly from `autotester.browser.session`, unchanged.

**`ui/routes_runs.py` -> `ui/run_execution.py`** (serial-vs-parallel case-execution helpers, vs.
the route entry point + coverage-request tail that stay):
- `_run_and_grade_resilient`, `_run_entry_case`, `_run_cases_serially`, `_run_cases_in_parallel`
- `routes_runs.py::_execute_with_trace` imports `_run_cases_serially`/`_run_cases_in_parallel`
  from the new module (one-directional import, no cycle)
- **Not a simple re-export case**: four test files monkeypatch `run_and_grade_case_resilient`
  and `default_session_factory` as attributes of `autotester.ui.routes_runs` (the AT-574 seam) --
  since the functions that actually call those names moved to `run_execution.py`, patching the
  old module no longer intercepts the real call site. Updated instead of re-exporting (re-export
  would not have fixed the monkeypatches, since Python resolves a function's globals from its
  *own* `__module__`, not the importer's): `tests/test_coverage_wiring.py`, `tests/test_ui_runs.py`,
  `tests/test_ui_runs_parallel_crash_recovery.py`, `tests/test_ui_runs_parallel_trace.py` now
  `import autotester.ui.run_execution as run_execution_module` and patch
  `run_and_grade_case_resilient`/`default_session_factory` there; `LangChainFallbackProvider` and
  `plan_parallel_run` patches stay on `routes_runs_module` (those two names are still looked up
  there -- `trigger_run`/`_execute_with_trace` didn't move). No test deleted.

## Restored contract anchors

| Anchor | Function | New location |
|---|---|---|
| "E5 holds either way" | `settle` | `browser/session.py` (unmoved, docstring restored) |
| "C7: facts recorded, the grader still owns the verdict" | `assert_expected` | `browser/session.py` (unmoved, docstring restored) |
| AT-036 full history pointer ("full history: execute.md's amendment log") | `screenshot` | `browser/evidence.py::EvidenceMixin.screenshot` (moved + restored) |
| Exact Playwright error text (`Playwright raises "Sync API inside the asyncio loop"`) | `_run_cases_serially`'s AT-576 note | `ui/run_execution.py::_run_cases_serially` (moved + restored) |

Exact restored text taken from `git show 77346cb -- <path>` (the commit that trimmed them), diffed
against the pre-restoration committed state to confirm the wording matches what was dropped.

## Mechanical behaviour-preservation proof

`inspect`/`ast`-based comparison: for all 32 moved-or-kept functions/methods, extracted the exact
source segment via `ast.get_source_segment` from pre-refactor master (`8d75434`) and from the new
location, then compared:

```
BYTE-IDENTICAL | ui/helpers.py::_credential_variants -> ui/credential_guard.py::_credential_variants
BYTE-IDENTICAL | ui/helpers.py::_refuse_direction_override -> ui/credential_guard.py::_refuse_direction_override
BYTE-IDENTICAL | ui/helpers.py::_refuse_unsafe_value -> ui/credential_guard.py::_refuse_unsafe_value
BYTE-IDENTICAL | ui/helpers.py::_refuse_unsafe_submission -> ui/credential_guard.py::_refuse_unsafe_submission
BYTE-IDENTICAL | ui/helpers.py::_require_slug (unmoved)
BYTE-IDENTICAL | ui/helpers.py::_require_project_name (unmoved)
BYTE-IDENTICAL | ui/helpers.py::_require_safe_id (unmoved)
BYTE-IDENTICAL | ui/helpers.py::_require_reachable_base_url (unmoved)
BYTE-IDENTICAL | ui/helpers.py::_require_reachable_navigate_steps (unmoved)
BYTE-IDENTICAL | ui/helpers.py::_project_slugs (unmoved)
BYTE-IDENTICAL | ui/helpers.py::_load_project_or_404 (unmoved)
BYTE-IDENTICAL | ui/helpers.py::_reserved_temp_path (unmoved)
AST-IDENTICAL (docstring intentionally restored) | session.py::BrowserSession.screenshot -> evidence.py::EvidenceMixin.screenshot
BYTE-IDENTICAL | session.py::BrowserSession._record -> evidence.py::EvidenceMixin._record
AST-IDENTICAL (docstring intentionally restored) | session.py::BrowserSession.settle (unmoved)
AST-IDENTICAL (docstring intentionally restored) | session.py::BrowserSession.assert_expected (unmoved)
BYTE-IDENTICAL | session.py::BrowserSession.__init__/start/close/goto/fill/click/request_human (unmoved)
BYTE-IDENTICAL | routes_runs.py::_run_and_grade_resilient -> run_execution.py::_run_and_grade_resilient
BYTE-IDENTICAL | routes_runs.py::_run_entry_case -> run_execution.py::_run_entry_case
AST-IDENTICAL (docstring intentionally restored) | routes_runs.py::_run_cases_serially -> run_execution.py::_run_cases_serially
BYTE-IDENTICAL | routes_runs.py::_run_cases_in_parallel -> run_execution.py::_run_cases_in_parallel
BYTE-IDENTICAL | routes_runs.py::_is_entry_case/_require_declared_values/_execute_with_trace/trigger_run/_ask_for_what_it_did_not_recognise (unmoved)

TOTAL: 32  BAD: 0
```

"AST-IDENTICAL (docstring intentionally restored)" = code AST identical, docstring text differs
only because the restoration in this unit added back the four anchors listed above (confirmed by
stripping the docstring node before the AST comparison). Every other moved or unmoved function's
source is byte-for-byte identical to pre-refactor master.

## Verify

```
$ uv run ruff check src tests scripts
All checks passed!

$ uv run autotester doctor
doctor: clean
```
(`docs/MAP.md` was stale after the split -- regenerated via `uv run autotester map`, doctor clean
after.)

Targeted test set -- every test file that imports `ui.helpers`, `ui.credential_guard`,
`browser.session`, `browser.evidence`, `ui.routes_runs`, or `ui.run_execution` (found via grep
across `tests/*.py`, 71 files), plus `test_goal_done_checks.py` and `test_ledger_checks.py` (73
files total):

```
$ uv run pytest <73 files>
........................................................................ [ 12%]
........................................................................ [ 24%]
........................................................................ [ 37%]
........................................................................ [ 49%]
........................................................................ [ 61%]
.....................................................s.................. [ 74%]
........................................................................ [ 86%]
..s..................................................................... [ 99%]
.....                                                                    [100%]
579 passed, 2 skipped, 6 warnings in 574.28s (0:09:34)
```
The 2 skips are pre-existing, real-Chromium-gated tests (`test_explore_live.py`-style; unrelated
to this refactor, self-skip when Chromium/consent conditions aren't met).

**First pass found 12 failures**, all monkeypatch-target breakage (see "Not a simple re-export
case" above) in `test_coverage_wiring.py` (4), `test_ui_runs.py` (2),
`test_ui_runs_parallel_crash_recovery.py` (2), `test_ui_runs_parallel_trace.py` (4) -- fixed by
repointing those tests' `monkeypatch.setattr` calls at `ui.run_execution` for the two names that
moved there (`run_and_grade_case_resilient`, `default_session_factory`); rerun of the full 73-file
set above is the post-fix result, all green.

## Gap

**Full non-browser suite not run.** RAM check at task end: `1.72 GB` free (`Get-CimInstance
Win32_OperatingSystem`), well under the required 3.5 GB threshold, and multiple other
python/pytest processes were active on the host (`pytest`, several `python`/`python3.13` PIDs) --
both conditions in the brief for skipping it were met, not just one. The targeted 73-file run
above already covers every test that imports any of the six touched files (old or new), so the
refactor's actual blast radius is exercised; the gap is coverage of code elsewhere in the repo
that this refactor cannot affect (no import of the touched modules).

**Live browser: SKIP**, as instructed -- this is a behaviour-preserving move, not a UI-behaviour
change. Noting explicitly since `ui/routes_runs.py` (and its new sibling `ui/run_execution.py`)
is a UI route file: no route path, request/response shape, template, or redirect target changed;
`_execute_with_trace`'s call signature into `_run_cases_serially`/`_run_cases_in_parallel` is
unchanged (same positional args, same order), and `trigger_run`'s body is byte-identical to
pre-refactor master (see mechanical proof above).

## Capability row

This is a refactor: the discriminator is the full targeted test set passing (579/579, 2
pre-existing skips) plus the source-identity check (32/32 functions BYTE- or AST-identical modulo
the four instructed docstring restorations).

`NO ISOLATING FALSIFICATION -- behaviour-preserving move` -- evidence: the `ast.get_source_segment`
comparison table above (pre-refactor master `8d75434` vs. this branch), and the 73-file/579-test
pytest run, both pasted in full above.

Status: checked-PASS (qa/verdicts/at567-file-splits.md, Cycle checked: 1, f438243)
