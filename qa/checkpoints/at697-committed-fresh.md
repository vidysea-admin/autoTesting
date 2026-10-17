# Checkpoint - at697-committed-fresh (cycle 0)
- pytest tests/test_committed_fresh.py tests/test_doctor.py @92649717 (code d0774e62): 48 passed; ruff clean; doctor exit 1 = 2 dangling D-104 (base-lag, D-104 present on int/1017).
- E2E stale-commit scenario in scratchpad copy (git archive of HEAD docs+src): stale-committed docs/MAP.md reported while stale-generated absent; cleared after commit.
- Falsification: _compare `return []` -> 3 red / 5 green; unmutated 8 green. Copy only.
- Result: PASS. Checker: claude-sonnet-5-5 subagent, verdict qa/verdicts/at697-committed-fresh.md.
