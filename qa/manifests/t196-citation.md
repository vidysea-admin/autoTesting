# Manifest - t196-citation (resume 2026-10-12)

Contract: qa/contracts/living-ledger.md L10. Brief: qa/briefs/t196-citation-subject-check.md. Detail manifest: qa/manifests/t196-citation-subject-check.md.
Fix cycle: 0
Status: BLOCKED-needs-owner (NOT ready-for-check)

## Result
- Branch wave/t196-citation merged with origin/master (clean). Code slice (scanner, seals, known-disputed split, doctor wiring) already present.
- Per-file tests: test_citations, test_citation_seals, test_citation_known_disputed, test_doctor = 141 passed. ruff check src tests scripts: clean.
- `uv run autotester doctor` on the real tree: RED, 2685 violations = 2313 decision-citation-coverage + 372 decision-citation-declaration (+2 non-blocking known-disputed K1/K2, as designed).
- Zero real subject mismatches, zero dangling ids found. Every violation is a missing review row or a non-canonical claim line, not a wrong citation. So there are no wrong citations to fix.

## Why doctor cannot be made clean by this builder
1. Coverage (2313): L10 requires inventory/seal rows whose reviewer is /checker or Umesh; a builder or maker row does not count. Writing them here would forge review attribution.
2. Declaration (372): migrating mutable claims to canonical form touches qa/contracts/* (checker-owned, barred to this builder), qa/gates/*, and 36 lines in docs/DECISIONS.md (immutable history).
3. Weakening the check or exempting files is forbidden by L10 (no whole-file exemption).

## Needs
- /checker or Umesh: independent review plus seal rows for closed manifests, verdicts and decision entries; independent classification of the rest.
- /checker: canonical migration of contract claims; record K1/K2 ruling in L10; resolve the K1/K2 issue row.
- Until then merging this branch turns doctor red for every unit. Do not merge.
