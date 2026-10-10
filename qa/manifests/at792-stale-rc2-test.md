# Manifest — at792-stale-rc2-test

**Unit:** repair a stale test, `tests/test_reconcile_schema.py::test_rc2_ingest_video_keeps_narration_on_screen_text_and_exit_screen` (AT-792). Test-only diff; no product file, contract or issues ledger touched.
**Contract:** `qa/contracts/reconcile.md` RC2 and RC3
**Status:** ready-for-check
**Policy-Version:** proportional-verification/2026-10-10.9
**Tier:** S (test-only diff)
**Dual check:** no
**Fix cycle:** 0
**Date:** 2026-10-11
**Issues addressed:** AT-792

## Criterion text (verbatim, `qa/contracts/reconcile.md`)

- **RC2 — `_to_flow` stops dropping evidence.** *serves: O1, O3.* A produced `Step` preserves
  `ObservedStep.narration` and `on_screen_text` (new optional fields on `Step`), and a produced `Flow`
  carries `exit_screen` resolved through the same map as RC1. *Check:* an observation with narration,
  on-screen text and an exit screen on every step/flow round-trips through `ingest_video` with all three
  present and equal; an observation without them yields `None`, not `""` and not an invented string.
- **RC3 — narration is a quote, not a paraphrase.** *serves: O3, O7.* A narration kept on a step, or cited
  by the report, must be a substring of the transcript it came from (whitespace-normalised, case-folded)
  **or** is rejected and recorded as `narration_unverified` with the step left intact. Values pass
  `Redactor.scrub` before they are stored.

## Ruling confirmed

The checker's ruling stands: the test is stale, the product is right. `ingest_video`
(`src/autotester/stages/ingest.py:270-272`) builds `heard = {}` when no transcript is passed, and
`verify_narration` (`src/autotester/stages/reconcile.py:136-141`) then drops the narration as
`narration_unverified`, exactly as RC3 requires. The test was written before RC3 was enforced on the
save path (1ea43123, 2dce14c9).

## Change

`tests/test_reconcile_schema.py`, `test_rc2_ingest_video_keeps_narration_on_screen_text_and_exit_screen`:
now passes `transcript=Transcript(source_id=source.id, segments=[... "First, type your email here, then continue."])`
to `ingest_video`, as a real video ingest has. Every assertion is unchanged (narration, on_screen_text,
exit_screen). No other test in the file had the stale assumption (`test_rc2_absent_evidence_...` expects
`None`). File is 258 lines.

## Evidence

- Before: `uv run pytest tests/test_reconcile_schema.py -p no:xdist` -> `1 failed, 18 passed`
  (`assert None == 'type your email here'`, line 125).
- After: same command -> `19 passed`.
- `uv run ruff check src tests scripts` -> `All checks passed!`

## Falsification record (throwaway copy of the final tree, discarded)

- B, transcript removed from the repaired test, product intact: `tests/test_reconcile_schema.py` ->
  `1 failed, 18 passed` (the same RC2 test, same assertion). The repaired test therefore needs the
  transcript and exercises the RC3 keep-path.
- A, `verify_narration` mutated to keep every narration (`if step.narration:`): `test_reconcile_schema.py`
  stays `19 passed`, because this file's RC2 test is the positive keep-path and cannot see that
  mutation. The RC3 reject-path guard is `tests/test_reconcile.py::test_rc3_narration_not_in_transcript_is_rejected_and_the_step_kept`,
  which under the same mutation goes `1 failed, 22 passed`. So RC3 stays guarded, by that test.

Pre-check[RC3]: PRECHECK_SHA uv run pytest tests/test_reconcile_schema.py -p no:xdist -> 19 passed
