# Manifest - e2e-fixes-e1

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** `qa/contracts/e2e-fixes.md`, unit E1 (AT-1412), criteria E1.1-E1.3. **Criticality:** MEDIUM.
**Branch:** `feat/e2e-e1`, cut from master `dccc65e9` (the contract commit). Not merged, not pushed.
**Base SHA:** `dccc65e9`
**Code SHA:** see the commit that carries this manifest (`git log -1 feat/e2e-e1`).
No `src/` module added; no D-entry needed. `qa/contracts/` untouched. `core/trace.py`, `stages/run_artifacts.py`, `schema/run.py` unchanged.

## What changed

| File | Kind | Change |
|---|---|---|
| `src/autotester/ui/routes_report.py` (300 lines, cap 300) | E in place | `_trace_card` `:115` catches `TraceParseError` from `read_spans` `:117-119` and returns a "Trace" card saying "The trace could not be read: <str(exc)>" (escaped). `str(exc)` is `trace.jsonl:N: not valid JSON` only (`core/trace.py:166`), never line content. No spans are rendered on that path. The two `if` table blocks were folded into one `tables` list `:132-138` (same HTML, same "no rows -> no card" result) to pay for the 3 added lines and keep the file at the cap. `read_spans` is untouched. |
| `src/autotester/stages/run_launcher.py` (291 lines) | E in place | `phase_fields` `:170-176` catches `TraceParseError` and returns `{"phase_totals_s": None, "unaccounted_s": None}` (NOT RECORDED, `schema/run.py:153-165`), never a fabricated zero. Needed: before this, `launch_run` `:273` called `phase_fields` unguarded, so a corrupt trace raised before/while saving the `Run` (the new launcher test failed with `TraceParseError: trace.jsonl:5` on the unfixed code). |
| `tests/test_ui_report_corrupt_trace.py` | N (test) | 6 tests, below. Reuses the `world` launcher fixture from `tests/test_run_launcher_approval.py` (no second copy). |
| `qa/evidence/e2e-fixes-e1/mutations.json`, `mutation-run.txt` | N | 8 mutants and their run |

## Criteria map

| Crit | Code | Test (falsifier it kills) |
|---|---|---|
| E1.1 page renders | `routes_report.py:117-120` (handling is in `_trace_card`, not `read_spans`) | `test_ui_report_corrupt_trace.py:61` `test_e1_1_a_corrupt_trace_line_still_renders_the_run_page`: valid line then `not json <canary>`; GET `/projects/demo/runs/run_1` -> 200, body has run id, "Run bounds", case title. Mutant "except KeyError" (re-raise) -> killed. |
| E1.2 honest degradation | `routes_report.py:119-120` | `:68` `..._states_the_failure_and_leaks_no_line_content`: body has `trace.jsonl:2`, `not valid JSON`, "could not be read"; the canary is absent; no stage row `<td>EXECUTE` / `1.50s` shown. `:78` `..._no_trace_file_shows_no_trace_card`: no `<h2>Trace</h2>` when no file. `:86` `..._clean_trace_still_renders_its_rows`: unchanged clean path. Mutants: card dropped, raw `JSONDecodeError.doc` leaked, empty card on no trace, rows dropped -> all killed. |
| E1.3 detection not weakened | `core/trace.py:149-177` unchanged; `run_artifacts.py:56` unchanged (it already imports and handles `TraceParseError`, `:11`); fix is `run_launcher.py:172-175` | `:92` `test_e1_3_read_spans_still_raises_on_a_bad_line` (`pytest.raises(TraceParseError, match=r"trace\.jsonl:2")`) and the pre-existing `tests/test_trace_numeric_secret.py:94`, which passes unmodified. `:98` `test_e1_3_a_corrupt_trace_does_not_lose_the_saved_run`: real `launch_run` through the real launcher with `run_cases_traced` wrapped to append a corrupt line; the `Run` is saved and reloaded with `phase_totals_s is None` and `unaccounted_s is None`. Mutants: catch removed, fabricated `{}`/`0.0` -> killed. |

## Verification (run in this worktree; `env -u ANTHROPIC_BASE_URL`, two test files per call, never the full suite)

```
uv run pytest tests/test_ui_report_corrupt_trace.py -o addopts=
  6 passed
uv run pytest tests/test_run_trace.py tests/test_trace_numeric_secret.py -o addopts=
  16 passed
uv run pytest tests/test_ui_report.py tests/test_run_launcher_approval.py -o addopts=
  31 passed
uv run pytest tests/test_run_teardown_stall.py tests/test_run_launcher.py -o addopts=
  24 passed
uv run ruff check src tests scripts
  All checks passed!
uv run autotester doctor > .work/e1-doctor.txt
  doctor: clean (exit 0)
```
Red-first: before the source edits, 3 of the 6 new tests failed (E1.1, E1.2 degradation, E1.3 launcher with `TraceParseError: trace.jsonl:5`); the other 3 passed as controls. The full suite was NOT run (machine low on memory, instruction); the checker runs it.

## Mutation evidence (C7)

`uv run python scripts/mutation_check.py qa/evidence/e2e-fixes-e1/mutations.json` -> `8/8 mutations killed` (`qa/evidence/e2e-fixes-e1/mutation-run.txt`). Every named test failed in its mutant; the harness's baseline-green and named-test-collected refusals passed. Working tree was restored after the run (`git status` shows only the two src files, the test and the evidence).

## Notes for the checker

- Every file:line above was read at this commit. `routes_report.py` is exactly at the 300-line cap; that is why the table-building tail was condensed rather than extended.
- Only `TraceParseError` is caught. A span that parses as JSON but fails model validation raises pydantic `ValidationError`, which is out of E1's contract text (it names "not valid JSON"); left as is, not widened. Say so if you want it covered.
- `unaccounted_s` is also None on a corrupt trace: it is computed from the same trace, so NOT RECORDED is the honest value (contract: `phase_totals_s` None, never a fabricated zero).
