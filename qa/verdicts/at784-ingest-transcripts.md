# Verdict - at784-ingest-transcripts (AT-783, AT-784, AT-785)

Policy: proportional-verification/2026-10-07.7, tier M (one checker, no full suite).
Commit checked: cc7d9324 on `wave/at784-ingest-transcripts`.

## Check plan
1. Read the src diff; confirm each of the 4 criteria is evidenced end to end.
2. Correctness: `load_transcript` reused; sidecar precedence; drop report content; `dropped` default; line caps.
3. Overlap with `wave/at780-pii` on `reconcile.py::build_judge_prompt`.
4. Run the 6 affected test files, ruff, `autotester doctor`.
5. One falsification per capability in a throwaway copy (scratchpad `cp/`), worktree untouched.
6. Process note on test-after-source order.

## Verdict: PASS
Cycle checked: 0

## Evidence
- C1 (orchestrate): `orchestrate_runners.py::make_ingest_runner` now passes `transcript=load_transcript(ctx.store, source)`. Test `test_orchestrated_ingest_keeps_a_narration_the_transcript_contains` passes.
- C2 (CLI): `cli_video.py::run_cmd` calls `load_transcript(store, source)`. Test `test_cli_ingest_uses_the_transcript_media_prep_persisted` passes.
- Reuse, not duplication: `analyze_video.load_transcript` (line 67) is imported in both places. No new loader.
- Precedence: `load_transcript` returns `store.load_transcript(source.id)` first and only falls back to `load_sidecar(source)`. The brief asked whether the sidecar wins. It does not: a stored media-prep transcript wins and the sidecar is the fallback. This is the pre-existing `analyze` behaviour, and it is what the unit's own docstring and the manifest ("store first, sidecar fallback") state. The sidecar is still used when no stored transcript exists. Recorded as an observation, not a defect; a human who wants sidecar-over-store would need a separate decision.
- C3 report: `reconcile.py::narration_drop_report` renders only `len(dropped)` and `flow_id#order` from each `StepRef`. It never reads `reason` or any narration text; `StepRef` holds no narration field. The runner additionally scrubs through `ctx.secrets.redactor()` when present. `dropped: list[StepRef] | None = None` is an immutable-default out-param; the callers create the list.
- Line caps: `ingest.py` 300, `reconcile.py` 298 (both within the 300 cap).
- Overlap with at780-pii: this diff adds `narration_drop_report` after `verify_narration` (hunk `@@ -145,0 +146,6`). It does not touch `build_judge_prompt` (line 92). No overlapping hunk. Merge order cannot conflict textually, though `reconcile.py` is at 298 of 300 lines, so at780 growth there could trip the doctor cap.
- Tests: 6 affected files, `63 passed, 5 warnings` (warnings are the AT-561 StageContext notices, pre-existing). `uv run ruff check src tests scripts`: All checks passed. `uv run autotester doctor`: clean. Confirmed `autotester` imports from the worktree `src`.
- Falsification (copy, `tests/test_ingest_transcripts.py`, baseline 7 passed, restored 7 passed):
  | Mutation | Result |
  |---|---|
  | F1 runner drops `transcript=` | 3 failed |
  | F2 CLI back to `load_sidecar` | 2 failed |
  | F3a `dropped.extend` -> `pass` | 4 failed |
  | F3b runner `_LOG.warning` -> no-op | 2 failed |
  | F3c leak: append `repr(dropped[0])` to report | 7 passed (no effect: `StepRef` carries ids and `reason`, no text, and the repr adds nothing the report omits). The no-text guarantee holds by type, not by a test mutation. |
- Process note: the builder edited source before writing tests (TDD order not followed). The tests were written and each fix was falsified, so criterion 4 holds.

Metrics: criteria 4/4 evidenced · affected tests 63 passed · falsifications 4/4 meaningful red, 1 vacuous by design · ruff clean · doctor clean · ingest.py 300, reconcile.py 298 lines

PROPOSED-ISSUE: low - process: AT-783/784/785 source was edited before tests (TDD order); ledger row only.
PROPOSED-ISSUE: low - merge order: `reconcile.py` is 298/300 lines; `wave/at780-pii` edits the same file (`build_judge_prompt`, no hunk overlap) and may push it past the doctor cap. Merge order or a split should be settled before both land.
PROPOSED-ISSUE: low - precedence: the media-prep transcript wins over the sidecar on both paths (pre-existing `load_transcript`); confirm this is the intent for `ingest run`, which previously read only the sidecar.
