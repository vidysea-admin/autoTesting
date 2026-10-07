# Manifest — ingest-fields
**Contract:** none — bug fix, issue row proposed (nearest: qa/contracts/ingest.md I1/I7; no criterion names this bug)
**Goal task:** none
**Date:** 2026-10-07
**Fix cycle:** 0 of max 2
**Hold fix cycles:** 0 of 2
**Hold-reopens:** 0
**Resume-reset:** unused
**Capability-redispatch:** 0
**Dual check:** no
**Persona walk:** skip (backend-only: stages/ingest.py and tests/test_ingest.py, no human screen)
**Issues addressed:** new — PROPOSED-ISSUE: ingest `_to_screen` passes list[str] into `Screen.fields` (list[InputField]); every real video with visible inputs fails with ValidationError
**Executor:** claude-sonnet-subagent
**Executor rationale:** tiny S fix found during a live Gemini run; one function in one file plus its test

## What changed
- src/autotester/stages/ingest.py:`_to_screen` (~L133-146) — `fields=[InputField(name=label, label=label) for label in observed.fields]`; `InputField` added to the flowspec import; docstring notes labels become InputFields and repeats are kept (not deduped). `ObservedScreen.fields` and `Screen`/`InputField` untouched.
- tests/test_ingest.py — new `test_ingest_video_wraps_observed_field_labels_as_inputfields` (+ `InputField` import).
- falsified (unchanged): none (the falsifying edit reverted the changed line itself, in a throwaway copy outside D:/autoTesting)

## Verification scope
Policy-Version: proportional-verification/2026-10-06.6
Tier: S (one product function in one file + its tests)
Base / checked state: fe6eb98a + this unit's commit on wave/ingest-fields
Gate answers: none — no qa/gates file covers the stages/ingest.py fields conversion
Affected tests / full-suite trigger: tests/test_ingest.py, tests/test_ingest_persist.py, tests/test_ingest_real_cli.py; no full-suite trigger. The builder runs no full suite.
Metrics: start=2026-10-07T04:50:00Z end=2026-10-07T05:00:00Z wall_min=10 agent_min=unavailable blocked_min=0 suite_runs=0 repeat_runs=1 mutations=1 cycle=0 resumes=0 tokens=unavailable policy=proportional-verification/2026-10-06.6

## How to verify (commands + expected)
- `uv run pytest tests/test_ingest.py tests/test_ingest_persist.py tests/test_ingest_real_cli.py` → expected: 39 passed
- `uv run ruff check src tests scripts` → expected: All checks passed!
- `uv run autotester doctor` → expected: only the 2 pre-existing stale-generated lines (docs/MAP.md, docs/SNAPSHOT.md), identical on base fe6eb98a with the change stashed

## Actual outputs (from maker's own run)
- red before fix: `FAILED tests/test_ingest.py::test_ingest_video_wraps_observed_field_labels_as_inputfields` / `1 failed, 8 deselected` / `fields.0 Input should be a valid dictionary or instance of InputField [type=model_type, input_value='Email', input_type=str]`
- after fix: `39 passed in 3.92s`
- ruff: `All checks passed!`
- doctor: `stale-generated: docs/MAP.md` + `stale-generated: docs/SNAPSHOT.md` / `2 violation(s)` (same two on base; generated docs, not this unit's)

## Capability coverage (each new claim -> its isolating falsification)
| Criterion | capability | the check that covers it | the falsifying edit | observed |
|---|---|---|---|---|
| C1 | string field labels from an observation become `InputField(name=label, label=label)`; `ingest_video` no longer raises | tests/test_ingest.py::test_ingest_video_wraps_observed_field_labels_as_inputfields | in a throwaway copy, `fields=observed.fields` restored in `_to_screen` | before: `1 passed, 8 deselected`; after edit: `E Input should be a valid dictionary or instance of InputField [type=model_type, input_value='Email', input_type=str]` / `1 failed, 8 deselected` |
| C2 | `ObservedScreen.fields` stays list[str]; no loosening validator added to `Screen`/`InputField`; conversion only in `_to_screen` | git diff touches only stages/ingest.py and tests/test_ingest.py (schema/ untouched) | adding a str-accepting validator to `Screen` would show in the diff | `git diff --stat` lists 2 files; the same falsification above proves `Screen` still rejects raw str |
| C3 | existing ingest tests unchanged and green | tests/test_ingest.py, tests/test_ingest_persist.py, tests/test_ingest_real_cli.py | n/a (regression criterion) | `39 passed in 3.92s` |

## Live browser evidence
Not UI-touching — stages/ingest.py, tests/test_ingest.py

## Status: checked-PASS (cycle 0, qa/verdicts/ingest-fields.md)
