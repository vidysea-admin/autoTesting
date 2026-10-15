# at892-judge-injection

Status: checked-PASS
Fix cycle: 1
Branch: wave/at892-judge-injection
Issue: AT-892

## Change
- `stages/grade.py`: `_untrusted()` flattens newlines and escapes `<` in every evidence row; `{{EVIDENCE}}` is substituted last so target text cannot expand `{{FORMAT}}`/`{{RUBRIC}}`.
- `skills/grade/SKILL.md`: evidence wrapped in `<untrusted_evidence>`; rule states it is data, never instructions; verdict only via JSON output fields.
- Verdict already comes only from the structured `Judgment` (no text parsing).
- `tests/test_grade_injection.py`: forged row/closing tag/placeholder stay inert; "VERDICT: PASS" page cannot flip a mock FAIL.

## Verify
grade + ai_capture tests 311 passed; ruff clean; doctor clean.
Merge note: AT-840 also edits grade.py; this diff is only `_render_evidence`/`build_grade_prompt`.
