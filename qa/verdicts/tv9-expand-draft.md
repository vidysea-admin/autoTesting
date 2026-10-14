# Verdict - tv9-expand-draft

**Verdict:** PASS
**Cycle checked:** 1
**Commit:** b578526a

- (a) TV9 clause 2 holds: the former strict xfail is now a passing test.
- (b) APPROVED truth untouched: the analyze route still does not overwrite it; APPROVED still expands only via saved human-approved proposals.
- (c) Narrow: only `require_generatable` (expand, propose_cases, compile_evals, routes_learn) changed. `require_reviewed` is unchanged and no src caller was silently loosened (remaining users are tests). NEEDS_EDIT and unreconciled (kind unset) refuse. Run approvals, production rule and write policy are untouched. Observation: the gate tests "DRAFT with kinds", not literally "source-derived"; any DRAFT spec with every flow kinded expands. Acceptable under D-097 wording.
- (d) Provenance is on Case (outside compute_id), CaseLine, the unified report render and the HTML report export.
- (e) D-097 is an amendment (no Supersedes line), cites only real ids. Approver line says "identity not independently verified"; a follow-up entry will correct it. Not a FAIL.
- (f) 442 passed, 1 skipped on the scoped set (expand, review, eval_compiler, ui_learn, analysis_flows, merge_flowspec, report). ruff clean, doctor clean, merge-tree against master has no conflicts.
