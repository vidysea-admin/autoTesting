# Manifest - at840-judge-pii

**Status:** ready-for-check
**Fix cycle:** 1
**Unit:** AT-840 grade.py sent judge prompts with no mask_pii
**Branch:** wave/at840-judge-pii

## Changes
- stages/grade.py: after the existing `_withheld` gate (Redactor.assert_clean + SecretStore.guard_prompt, which calls assert_no_raw_secrets), the prompt goes through `mask_pii` before `judge.judge`. The prompt is the only text channel (rubric, evidence labels incl. assertion messages with page text, any visual_text/OCR). Emails -> `<email>`, phones -> `<phone>`.
- tests/test_grade_pii.py (2 tests, MockProvider records the prompt).

## Known gap (HUMAN_GATE for Umesh)
Images are still sent as captured. The repo has no image PII masking (only secret-input masking before capture); no OCR was invented. AT-840 image policy (blur/block/accept) remains open.
Not touched: stages/ai_judge.py (separate judge path), not audited here.

## Verify
PYTHONPATH=<worktree>\src python -m pytest tests/test_grade*.py tests/test_redact_pii.py ; ruff check src tests scripts ; doctor
Result: 290 passed, ruff clean. Doctor: 1 violation (not from this change; likely stale docs/MAP.md).
