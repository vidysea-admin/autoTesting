# Manifest — judge-defect-field
**Contract:** qa/contracts/core-invariants.md (C12 fail closed)
**Goal task:** none (follow-up to the T-169 real PathLynks run, inconclusive-analysis Cause 2)
**Date:** 2026-10-13
**Fix cycle:** 0
**Status:** ready-for-check
**Executor:** claude-sonnet-subagent

## What changed
- `schema/verdict.py`: `Judgment.defect_observed: bool | None` and `defect_summary`; bool-like
  strings coerced, other values fail validation (fail closed).
- `skills/grade/SKILL.md`: judge must return `defect_observed`.
- `stages/grade.py::_defect_decision`: PASS stands only with defect_observed=False; True ->
  INCONCLUSIVE; field absent -> note guard decides (existing fakes/providers keep working).
- `stages/grade_note_guard.py`: negation is clause-scoped (clause break at . ; : ! ? or contrast
  word, 14-word cap, "rather than"/"instead of" added); a negator inside a negated-success phrase
  ("did not load") never negates a later defect term.
- `tests/test_grade_defect_field.py`: misfire phrases stay PASS; recorded T-181 broken-login
  notes still INCONCLUSIVE; AT-998 set unchanged in `tests/test_grade_note_guard.py`.

## Open for the checker
- Missing field is NOT an automatic INCONCLUSIVE: it falls back to the guard (decision for Umesh
  whether to make it strict; would need ~50 test constructions updated).
- "validation errors appeared ... No defect observed" stays guard-held when the field is absent
  (expected error word, accepted conservative case); with defect_observed=false it passes.
