# Manifest - t136-known-bugs

**Status:** checked-PASS
**Fix cycle:** 1
**Unit:** T-136 known-bugs oracle (D-094)
**Branch:** wave/t136-known-bugs
**Contract:** qa/contracts/bench.md K12

## Changes
- schema/bench.py: mode `known_bugs_ai_assisted`, provenance `ai_video_review`, one `DENOMINATOR_PROVENANCE` table.
- stages/known_bugs.py + scripts/known_bugs_corpus.py: converter (High/Medium only; refuses a tracked output path).
- stages/acceptance_comparison.py, schema/acceptance.py, scripts/check_acceptance_comparison.py: `recall_basis` label, `--corpus`.
- tests/test_acceptance_comparison.py: synthetic fixtures only.
- Source data (.work/mail-intake/karun-bugs.json) and the generated corpus (.work/known-bugs/) stay gitignored; nothing internal is tracked.

## Verify
uv run pytest tests/test_acceptance_comparison.py tests/test_bench.py ; uv run ruff check src tests scripts ; uv run autotester doctor
