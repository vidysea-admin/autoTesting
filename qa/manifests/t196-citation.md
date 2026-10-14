# Manifest - t196-citation (resume 2026-10-12)

Contract: qa/contracts/living-ledger.md L10. Brief: qa/briefs/t196-citation-subject-check.md. Detail manifest: qa/manifests/t196-citation-subject-check.md.
Fix cycle: 1
Status: superseded
Superseded-by: qa/verdicts/t196-citation.r1.b.md (merge 137ceace)

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

## Fix cycle 1 (D-087 item 3)
- Per D-087 item 3 (docs/DECISIONS.md), T-196 merges in ADVISORY mode. Coverage and declaration findings (2314 / 372) are non-blocking warnings; wrong-subject, subject-unavailable and dangling citations stay blocking. Supersedes the BLOCKED-needs-owner section above.
- Mechanism: src/autotester/ledger/advisory.py (ADVISORY_CITATION, NON_BLOCKING, blocking, warning_summary); doctor CLI prints counts per rule plus first 5 items. Promote later by emptying ADVISORY_CITATION.
- Tests: tests/test_citation_advisory.py (5); seal fixtures use the strict view. 146 passed across the 5 per-file runs; ruff clean; `autotester doctor` clean with warnings.
