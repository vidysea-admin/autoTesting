# Verdict - t196-citation, checker A (blind, cycle 1)

Cycle checked: 1
Bound to: worktree .worktrees/chk-t196-A, detached at origin/wave/t196-citation = 3616517575b72098fb929fd8719e0fe196165b7a. Date 2026-10-12. Mode: ADVISORY per D-087 item 3.

VERDICT: PASS

## Criteria (adjusted by D-087 item 3)
- Advisory list (met): ADVISORY_CITATION in ledger/advisory.py = {decision-citation-coverage, decision-citation-declaration}. NON_BLOCKING adds only sealed and known-disputed (as the brief intends). dangling, subject-mismatch and subject-unavailable are not listed, so they block.
- Probes (scratch tree, doctor.run + blocking()):
  - dangling a nonexistent decision id in qa/gates: blocking `decision-citation-dangling`; real CLI `autotester doctor` exit 1 (met).
  - reviewed canonical claim with wrong quote: blocking `subject-mismatch` (met).
  - duplicate full bodies for one id: blocking `subject-unavailable` (met).
  - coverage-only gap (resolving id, no review row) and non-canonical claim: only coverage/declaration, blocking list empty (met).
  - reviewed correct quote: clean.
- Warning summary caps output (met): real run prints per rule a count plus first 5 and "... and N more"; test_the_warning_summary_shows_counts_and_only_the_first_items passes.
- seal_fixtures `blocking` helper (met): now the strict view, excluding only sealed and known-disputed, i.e. the same set doctor.blocking filtered before the advisory split. It does not weaken the seal tests; coverage still counts there.
- Mutation (met for subject): disabling the subject-mismatch comparison in citations.py gave 8 failed in tests/test_citations.py; reverted with git checkout.
- Temp merge of the branch onto current origin/master (ab9b6fef): merged clean, `autotester doctor` = clean (exit 0), warnings only: coverage 2323, declaration 372, known-disputed 2.
- Branch doctor: clean, warnings coverage 2317, declaration 372, known-disputed 2.

## Gaps (non-blocking, advisory merge)
1. Mutation: adding `decision-citation-dangling` to ADVISORY_CITATION (masking a blocking rule) made NO test fail (test_citation_advisory 5 + test_citations 62 all pass). Nothing pins the advisory set to exactly coverage/declaration, nor dangling as blocking at the CLI. Recommend a one-line equality test.
2. By design an UNREVIEWED canonical claim with a wrong quote is judged only as a coverage warning (_judge skips occurrences with no review row), so a new wrong-subject claim blocks only once a review row exists. Fine under D-087 but worth knowing.
3. Manifest says 2314 coverage; actual is 2317 on the branch (2323 after merge). Cosmetic.

## Gate
- Full suite `uv run pytest -o addopts=`: 5 failed, 5632 passed, 7 skipped, 14 xfailed (42:53). All 5 failures are the known symlink tests (test_discover, 2 in test_report_export, test_ui_crawls, test_ui_video_route_traversal). No asyncio, flake or citation failures.
- `ruff check src tests scripts`: clean.
- `autotester doctor`: clean with warnings (branch and temp merge).
