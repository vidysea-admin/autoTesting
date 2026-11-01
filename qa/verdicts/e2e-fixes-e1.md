# Verdict - e2e-fixes-e1

**Verdict:** PASS
**Cycle checked:** 0
**Contract:** `qa/contracts/e2e-fixes.md` E1.1-E1.3 (AT-1412), criticality MEDIUM
**Checked commit:** `1470a169` on `feat/e2e-e1` (base `dccc65e9`). Fresh checker, read-only toward `src/` and `tests/`.
Not merged, not pushed. No `.env` value read or printed. Full suite NOT run (machine low on memory, instruction); only the files below, two per call.

## Criteria

| Crit | Result | Evidence |
|---|---|---|
| E1.1 page renders | PASS | `routes_report.py:117-120` catches `TraceParseError` in `_trace_card` (not in `read_spans`). Own probe, valid line then `not json <canary>`: GET run page = 200 (see Probe). Test `test_ui_report_corrupt_trace.py:61`. |
| E1.2 honest degradation | PASS | Card "Trace" states "The trace could not be read: trace.jsonl:2: not valid JSON" (`routes_report.py:120`, `str(exc)` from `core/trace.py:166` = file name + line number only). Canary absent from body (probe: `canary_in_body=False`); no `<td>EXECUTE` / `1.50s` row on the degraded path (test `:68`). No trace file -> no `<h2>Trace</h2>` (test `:78`; `core/trace.py:155-156` unchanged). Clean trace unchanged (test `:86`). The folded `tables` list (`:132-138`) yields identical HTML and the same "no rows -> no card" result (diff read). |
| E1.3 detection not weakened | PASS | `git diff dccc65e9 HEAD --name-status` shows `core/trace.py`, `stages/run_artifacts.py`, `schema/run.py`, `qa/contracts/` untouched. `tests/test_trace_numeric_secret.py` unmodified and green. `run_launcher.py:170-176` `phase_fields` returns `{"phase_totals_s": None, "unaccounted_s": None}` on `TraceParseError` (NOT RECORDED, not zero). Test `:98` drives the real `launch_run`, the Run is saved and reloaded with both fields None. |

## Commands run by the checker (all in the worktree, `env -u ANTHROPIC_BASE_URL`)

```
uv run pytest tests/test_ui_report_corrupt_trace.py -o addopts=            -> 6 passed
uv run pytest tests/test_trace_numeric_secret.py tests/test_run_trace.py -o addopts=  -> 16 passed
uv run pytest tests/test_ui_report.py tests/test_run_launcher_approval.py -o addopts= -> 31 passed
uv run pytest tests/test_run_teardown_stall.py tests/test_run_launcher.py -o addopts= -> 24 passed
uv run ruff check src tests scripts                                         -> All checks passed!
uv run autotester doctor > .work/e1-chk-doctor.txt                          -> exit 0, "doctor: clean"
wc -l: routes_report.py 300 (cap 300), run_launcher.py 291, new test 113
git diff dccc65e9 HEAD --name-status: 2 src files modified (M), 1 test + manifest + 2 evidence files added (A). No new src module.
git diff dccc65e9 HEAD -- qa/contracts | wc -l -> 0
```

## Own mutants (not the maker's), each run against `tests/test_ui_report_corrupt_trace.py`, worktree restored with `git checkout -- <file>` after each (`git status --short` clean)

| Mutant | Result |
|---|---|
| M1 `_trace_card` returns `""` on parse error (corrupt trace looks clean) | KILLED (`test_e1_2_the_trace_card_states_the_failure_and_leaks_no_line_content`) |
| M2 `phase_fields` returns `{}` / `0.0` instead of None | KILLED (`test_e1_3_a_corrupt_trace_does_not_lose_the_saved_run`) |
| M3 card appends `exc.__cause__.doc` (raw line content) | KILLED (canary assertion `:74`) |
| M4 `phase_fields` catch changed to a different exception (run lost) | KILLED (`test_e1_3_a_corrupt_trace_does_not_lose_the_saved_run`) |

The maker's `qa/evidence/e2e-fixes-e1/mutation-run.txt` (8/8 killed, claimed vs actual failing tests listed) was read and is consistent with the above.

## Probe: adjacent bad-line shapes (temporary test file in `tests/`, run once, deleted; tree clean afterwards)

Each case = one valid StageSpan line followed by the bad line. `page` is `GET /projects/demo/runs/run_1`; `phase_fields` is `run_launcher.py:170`.

```
invalid-json          page=200 canary_in_body=False | phase_fields={'phase_totals_s': None, 'unaccounted_s': None}
valid-json-bad-span   page=500 canary_in_body=False | phase_fields RAISES ValidationError
json-array            page=500                      | phase_fields RAISES AttributeError
json-number           page=500                      | phase_fields RAISES AttributeError
bad-llm (kind llm_call, fields missing) page=500    | phase_fields RAISES ValidationError
bad-phase (kind phase) page=200 (phases skipped without include_phases) | phase_fields RAISES ValidationError
```

## Findings

1. **WARNING (non-blocking, outside E1's text): a line that is valid JSON but is not a valid span still 500s the run page, and still loses the Run at completion.** Cause: `core/trace.py:167` (`raw.get` on a non-dict raises `AttributeError`) and `:170-174` (`model_validate` raises pydantic `ValidationError`) are neither wrapped into `TraceParseError`; `routes_report.py:119` and `run_launcher.py:174` catch only `TraceParseError`. Worse than the page case: `phase_fields` is called unguarded for the Run being saved (`run_launcher.py:273`), so `launch_run` raises for such a trace before the Run is saved, which is the same loss E1.3 forbids for the invalid-JSON case. Does it break E1.1's intent? The contract's text, falsifier and the issue (AT-1412) are all about a line that is "not valid JSON", and that case is fully fixed; the maker flagged the gap honestly in the manifest rather than hiding it. But the intent (one bad trace line must not take the report page or the saved Run down, C12) is only half met: the likely real-world corruption is a torn/truncated write (invalid JSON, covered); schema-invalid JSON arises from version drift or hand edits (rare, same blast radius). Recommended follow-up (not a FAIL of E1): file an issue; the smallest fix is in `read_spans` to wrap `ValidationError` and non-dict rows into `TraceParseError("trace.jsonl:N: not a valid span")`. Do NOT render `str(ValidationError)` in the card: pydantic includes `input_value`, which would leak line content (AT-1304 C3).
2. **Note (no action): `routes_report.py` is exactly at the 300-line cap**; any future edit there needs a split. Doctor is clean today.
3. **Note (no action): the maker's mutant "E1.3: read_spans stops raising" names one claimed-killing test but three failed;** harmless (the extra kills are real consequences of the same mutation).

## Disposition

PASS at cycle 0. All three criteria hold on a fresh re-run, doctor/ruff are clean, no new module, the file-size caps hold, detection (`read_spans`, `phase_summary`, `run_artifacts.py`) is unchanged, and four independent mutants are killed. Finding 1 is a residual WARNING for a follow-up issue, not a defect against E1's contract text. Maker may close out the manifest (`checked-PASS`). Merge/push is left to the caller (this checker did not merge or push).
