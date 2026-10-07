# Manifest — at784-ingest-transcripts (AT-783, AT-784, AT-785)

Status: checked-PASS
Fix cycle: 0
Policy-Version: proportional-verification/2026-10-07.7
Tier: M
Branch: `wave/at784-ingest-transcripts` (from origin/master 5d29d497)

## Changes (all edited in place)
- AT-783: `stages/orchestrate_runners.py::make_ingest_runner` passes `transcript=load_transcript(ctx.store, source)` (existing `analyze_video.load_transcript`).
- AT-784: `cli_video.py::run_cmd` uses `load_transcript(store, source)` instead of `load_sidecar(source)` (store first, sidecar fallback).
- AT-785: `stages/ingest.py::ingest_video` gains optional `dropped: list[StepRef] | None` out-param (collects the `StepRef`s `verify_narration` already returns); `stages/reconcile.py::narration_drop_report` renders `N narration(s) dropped as unverifiable: flow_id#order, ...`; CLI prints it (yellow), runner logs it (`logging`, scrubbed through `ctx.secrets` redactor when present). No schema change; no narration text anywhere in the report. `ingest.py` = 300 lines, `reconcile.py` = 298.

## Criteria (verbatim)
1. On the orchestrate ingest path, a narration whose quote is present in the source's transcript survives.
2. On the CLI path with no sidecar but with a media-prep transcript, a verifiable narration survives.
3. Dropped narrations are reported with a count and step ids. No raw narration text and no secrets appear in that report.
4. Removing each fix turns its test red.

## Tests (`tests/test_ingest_transcripts.py`, 7)
- C1: `test_orchestrated_ingest_keeps_a_narration_the_transcript_contains`
- C2: `test_cli_ingest_uses_the_transcript_media_prep_persisted`
- C3: `test_ingest_lists_the_steps_whose_narration_it_dropped`, `test_the_report_names_a_count_and_step_ids_never_the_text`, `test_the_runner_logs_the_drop_without_the_narration_text`, `test_the_cli_prints_the_drop_without_the_narration_text`, `test_a_secret_in_a_dropped_narration_never_reaches_the_report`

## Falsifications (throwaway copy in scratchpad `cp/`, PYTHONPATH to copy `src`; worktree untouched)
| ID | Criterion | Mutation | Result |
|---|---|---|---|
| F1 | 1 | runner call without `transcript=` | 2 failed (C1 test, runner-log test) |
| F2 | 2 | CLI uses `load_sidecar(source)` only | 2 failed (C2 test, CLI-print test) |
| F3a | 3 | `dropped.extend(...)` -> `pass` in ingest | 3 failed |
| F3b | 3 | runner `_LOG.warning(...)` -> `pass` | 1 failed |
| F3c | 3 | CLI `typer.secho(report...)` -> `pass` | 1 failed |
Baseline in copy 6 passed (before the 7th, secret-guard test, was added; that test asserts absence and has no mutation of its own). Restored copy: 6 passed.

## Commands run
- `uv run pytest tests/test_ingest_transcripts.py tests/test_ingest_narration.py tests/test_ingest.py tests/test_ingest_persist.py tests/test_ingest_real_cli.py tests/test_reconcile.py tests/test_orchestrate_runners.py tests/test_run_trace.py` -> `87 passed, 10 warnings` (AT-561 StageContext notices, pre-existing)
- `uv run ruff check src tests scripts` -> `All checks passed!`
- `uv run autotester doctor` -> `doctor: clean`

Metrics: files changed 4 src + 1 test + 1 manifest · tests added 7 · affected tests 87 passed · falsifications 5/5 red in throwaway copy · ruff clean · doctor clean · ingest.py 300 lines
