# Verdict: t136-acceptance-comparison (checker c)
Cycle checked: 2
Verdict: PASS

Re-verified both cycle-1 defects fresh.

1. Dangling citations: manifest line and the b verdict reworded; `uv run autotester doctor` shows no hit from any t136 file (remaining hits are only `qa/verdicts/t196-citation.*`). Manifest no longer claims the unit adds no hits wrongly.
2. FP flag: `AcceptanceComparison.fp_rate_unadjudicated` (extra="forbid" via Artifact) is true with no human list, false with one; CLI prints `FP rate: <n> (unadjudicated: no human list)` only in the former. Tests cover both modes.

tests/test_acceptance_comparison.py + tests/test_bench.py: 43 passed. ruff clean.
