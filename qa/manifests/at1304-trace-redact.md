# Manifest - at1304-trace-redact (AT-1304: a short numeric secret broke trace.jsonl, so every failure bundle was assembly_failed)

**Status:** ready-for-check
**Fix cycle:** 0
**Contract:** qa/contracts/run-trace.md (RT6), qa/contracts/core-invariants.md (redaction: no raw secret reaches disk); no contract edited
**Goal task:** T-136 (live r3 defect D4, `.work/t136-live-report-r3.md`)
**Dual check:** required
dual-trigger: security src/autotester/core/trace.py:46
**Persona walk:** skip (no UI surface)
**Issues addressed:** AT-1304 (high, open -> fixed)
**Executor:** claude-sonnet-subagent
**Base SHA:** 8f2b6df3 (worktree .worktrees/at1304-trace-redact, branch wave/at1304-trace-redact from int/1017)

## What changed
- `src/autotester/core/trace.py:39-60` - `TraceWriter._append` no longer scrubs the already-encoded JSON line. `_scrub_value` (new, 39-52) walks the span's python dump and runs `Redactor.scrub` then the `assert_clean` hard gate on every STRING value (line 46-47), then `_LINE.dump_json` (line 59) encodes. Numbers and datetimes are never text, so a secret of `587` cannot edit a latency of `0.587` or a `.587` timestamp. Enum members (the fixed stage/status vocabulary) are passed through. A side effect: a secret with a quote or backslash is now matched before JSON escaping, where the old encoded-line scrub missed its escaped form.
- `src/autotester/core/trace.py:25-28,87-95` - `TraceParseError(ValueError)`; `read_spans` raises it with `<file>:<line>: not valid JSON` (file name and 1-based line, never line content) instead of a bare `JSONDecodeError`.
- `src/autotester/stages/run_artifacts.py:92-97` - the swallowing `except` keeps `assembly_failed`, now also logs the reason and stores it in `BundleAssembly.reason` (only for `TraceParseError`; any other exception stays value-free).
- `src/autotester/schema/failure_bundle.py:92-93` - `BundleAssembly.reason: str | None` (default None, max 200, `extra="forbid"` kept), so stored indexes without it still load.
- `core/redact.py` NOT changed: `Redactor.scrub` / `assert_clean` are byte-for-byte the same for every caller.
- Tests: `tests/test_trace_numeric_secret.py` (new, 6 tests) and `tests/test_run_failure_artifacts.py::test_unparseable_trace_line_is_recorded_with_file_and_line_not_swallowed`.

## Verification scope
Policy-Version: proportional-verification/2026-10-18.15
Tier: L (redaction is a security boundary; `Redactor.scrub`/`assert_clean` call site changed)
Round: 4 src files, 2 test files, 3 criteria, est 25 min - one writer, one reader, one catch site, one schema field
Owners: OG-TRACE
Base / checked state: 8f2b6df3 / 1d9d2cd3, clean tree
Gate answers: none apply (no gate touches trace redaction; no new src module)
Affected tests / full-suite trigger: no conftest or shared schema file changed; `TraceWriter` callers are `providers/base.py`, `stages/orchestrate.py`, `agents/lead*.py`; their trace tests ran. Builder ran no full suite.
Tests[C1]: tests/test_trace_numeric_secret.py::test_smtp_port_587_secret_while_a_step_latency_is_0_587_stays_valid_json, ::test_a_timestamp_containing_the_secret_digits_still_parses; regression tests/test_run_trace.py, tests/test_provider_attempts.py, tests/test_ui_runs_parallel_trace.py — a short numeric secret must leave numbers and timestamps untouched, and the existing trace readers keep working
Tests[C2]: tests/test_trace_numeric_secret.py::test_string_fields_are_still_scrubbed_with_the_same_numeric_secret, ::test_no_raw_long_secret_reaches_disk_even_with_json_special_characters, ::test_the_assert_clean_gate_still_refuses_a_line_scrub_failed_to_mask; regression tests/test_run_trace.py (RT6) — string values are still scrubbed, JSON-escaped secrets no longer slip past, the assert_clean gate still raises
Tests[C3]: tests/test_trace_numeric_secret.py::test_an_unparseable_trace_line_names_the_file_and_line, tests/test_run_failure_artifacts.py::test_unparseable_trace_line_is_recorded_with_file_and_line_not_swallowed; regression tests/test_run_failure_artifacts.py, tests/test_failure_bundle.py, tests/test_failure_bundle_escape.py, tests/test_failing_step_bundle.py — a bad trace line is named by file and line and recorded in the bundle index, and the bundle family stays green
Pre-check[C1]: 1d9d2cd3 uv run pytest tests/test_trace_numeric_secret.py tests/test_run_trace.py tests/test_provider_attempts.py tests/test_ui_runs_parallel_trace.py -> 28 passed t=3 blobs=tests/test_trace_numeric_secret.py:fbe03fd,tests/test_run_trace.py:5dc7522,tests/test_provider_attempts.py:d73e3d9,tests/test_ui_runs_parallel_trace.py:fa362c2
Pre-check[C2]: 1d9d2cd3 uv run pytest tests/test_trace_numeric_secret.py tests/test_run_trace.py -> 16 passed t=1 blobs=tests/test_trace_numeric_secret.py:fbe03fd,tests/test_run_trace.py:5dc7522
Pre-check[C3]: 1d9d2cd3 uv run pytest tests/test_trace_numeric_secret.py tests/test_run_failure_artifacts.py tests/test_failure_bundle.py tests/test_failure_bundle_escape.py tests/test_failing_step_bundle.py -> 71 passed (full affected set: test_trace_numeric_secret, test_run_failure_artifacts, test_run_trace, test_provider_attempts, test_ui_runs_parallel_trace, test_failure_bundle, test_failure_bundle_escape, test_failing_step_bundle) t=8 blobs=tests/test_trace_numeric_secret.py:fbe03fd,tests/test_run_failure_artifacts.py:2a11374
Falsification[C1]: golden ::test_smtp_port_587_secret_while_a_step_latency_is_0_587_stays_valid_json red@8f2b6df3 (JSONDecodeError: `"input_tokens":[REDACTED...`), green@1d9d2cd3; copy-mutant in scratchpad at1304/fz restoring the encoded-line scrub at trace.py:59 -> 4 failed (JSONDecodeError, datetime_from_date_parsing), restored -> 21 passed
Falsification[C2]: copy-mutant in scratchpad at1304/fz replacing the string scrub+gate (trace.py:46-48) with `return value` -> 5 failed (fed_id stays `case-587-x`, long secret reaches disk, RT6 test red); restored -> 21 passed. A second copy-mutant deleting only `assert_clean` (trace.py:47) -> 1 failed (`DID NOT RAISE ValueError` in the gate test)
Falsification[C3]: golden ::test_unparseable_trace_line_is_recorded_with_file_and_line_not_swallowed red@8f2b6df3 (no `reason` field), green@1d9d2cd3; copy-mutant dropping `reason=reason` (run_artifacts.py:97) -> 1 failed (`assert None == 'trace.jsonl:2: not valid JSON'`), restored -> 21 passed
Lint: 1d9d2cd3 `uv run ruff check src tests scripts` -> All checks passed; `uv run autotester doctor` -> 4 violations, identical to the base checkout (stale-generated and stale-committed for docs/MAP.md and docs/SNAPSHOT.md, regenerated by the merge owner); no new violation (an `undeclared-dependency: pydantic_core` I introduced was removed by using `pydantic.TypeAdapter`).
Metrics: start=2026-10-18T20:50:00Z end=2026-10-18T21:20:00Z wall_min=30 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=4 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-18.15 lane=normal check_s=8 mutants=4 defects_unit=0 defects_6c=0 tests=7 tests_min=1

## Residual risk and boundaries
- A short numeric secret still masks a digit run inside a free-text STRING field and inside `trace_id` (a run id can contain `587`); that is the unchanged, conservative string rule (C2) and the line stays valid JSON.
- Enum members are not scrubbed (fixed vocabulary); a hypothetical secret equal to a stage name would not be masked in the `stage` field.
- Other stores that scrub encoded JSON text were not audited (out of scope for AT-1304).
- Process note: a `git stash`/`pop` by this unit raced a sibling worktree (stash stack is repo-wide); this worktree was restored from saved patches. See the hand-off line.
