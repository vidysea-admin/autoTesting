# Manifest - at840-judge-pii

**Status:** ready-for-check
**Fix cycle:** 2
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

## Fix cycle 2
- grade(): masking extracted to `_pii_masked` (function now under 50 lines). Rebased onto master after AT-892.
- core/redact_pii_forms.py (new, small, called from `mask_pii`): obfuscated emails `[at]`, `(at)`, `(dot)`, `%40`, `%2540`, fullwidth at-sign (NFKC), `a at b dot c`; labelled name fields (`first_name:`, `last_name=`, `name:`, `full_name`, JSON form) via `mask_name_value`. Regexes linear. Free-text names ("Ravi Kumar") are out of scope.
- Double-encoding: handled with a literal `%2540` replace here. `core/redact_escaped.py` (wave/scrub-escaped) was not on master yet, so it was NOT reused; when it lands, swap this for its decode helper (one concept, one place).
- Other model paths now masked: ux_advisory.judge_case_ux, video_review._analyse, expand (provider.act). discover/classify sends counts only; reconcile already masked (AT-780); relitigation/ingest/analyze_video send repo docs or video, not target text.
- AT-892 follow-ups: SKILL.md stray newline fixed to `
`; rubric criteria and no-fire text go through `_untrusted`.
- docs/MAP.md regenerated (`autotester map`).
- Remaining: AT-840 stays OPEN for IMAGE PII only (no image masking exists).
