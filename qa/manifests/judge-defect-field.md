# Manifest — judge-defect-field
**Contract:** qa/contracts/core-invariants.md (C12 fail closed)
**Goal task:** none (follow-up to the T-169 real PathLynks run, inconclusive-analysis Cause 2)
**Date:** 2026-10-13
**Fix cycle:** 2
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

## Fix cycle 2
- `grade_note_guard._negated` rewritten: negation binds only to the defect word it directly governs.
  Walking back from the term, only fillers ("an", "evidence of", "product"), "," / "or", copulas and
  other defect words may sit between negator and term; "and", a verb or a non-defect noun ends the
  scope (14-word window removed). "no spinner and an error message is shown" and the 3 sibling
  phrases are now held; conservative: when in doubt, flag.
- Tests use the VERBATIM judge notes from run-01M4TS6A79X14E32AQ3KA7HJ9T
  (`tests/fixtures/t169_real_judge_notes.json`, clean of secrets). 7 of the 8 are not held; the 8th
  (7a978722a38c, "validation errors appeared ... No defect observed") stays guard-held when the field
  is absent (accepted conservative case, as in the analysis) and passes with defect_observed=false.
- ACCEPTED RISK: `defect_observed=false` is trusted over the note, so a judge that sets false while
  its note describes a defect yields PASS. Not mitigated: holding on an un-negated defect word would
  re-hold the legitimate negative-case notes the field exists to release. Decision for Umesh.
