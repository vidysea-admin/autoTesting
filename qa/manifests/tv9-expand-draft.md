# Manifest - tv9-expand-draft

**Status:** ready-for-check
**Fix cycle:** 1
**Unit:** TV9 clause 2 - generate cases from source-derived DRAFT flows with no human review step
**Branch:** wave/tv9-expand-draft
**Contract:** qa/contracts review-gate R5, expand X1, team-video-review TV9; decision D-097

## Changes
- docs/DECISIONS.md: D-097 appended once via scripts/append_decision.ps1. Written as an amendment of D-073/R5 (not a Supersedes line, which would retire all of D-073). Approver line reads "Answered in-session ... identity not independently verified". The orchestrator later relayed that the session user confirmed they are Umesh; DECISIONS.md is append-only so the entry was NOT edited. Decide whether a follow-up entry is wanted.
- stages/review.py: `require_generatable` (APPROVED ok; DRAFT ok when every flow has `kind`; NEEDS_EDIT and unreconciled refuse), `case_provenance`, `is_unreviewed_draft`. `require_reviewed` unchanged.
- stages/analysis_flows.py: assigns `kind` via reconcile's `assign_kinds` to flows that have none.
- stages/expand.py, stages/eval_compiler.py: use `require_generatable`; a DRAFT spec uses the full taxonomy with no saved approvals; APPROVED path unchanged.
- schema/case.py `Case.provenance` (not in compute_id); shown in report_export HTML and unified report (schema, builder, render).
- ui/routes_learn.py: Generate cases offered and allowed for a reconciled DRAFT.
- tests/test_analysis_flows.py: xfail flipped to pass; added kind, provenance, report line, NEEDS_EDIT/unreconciled refusal, APPROVED-untouched tests.

## Evidence
pytest (analysis_flows, expand_cli, ui_learn*, expand, eval_compiler, review): 79 passed; wider related run earlier 227 passed. ruff clean. doctor clean.
