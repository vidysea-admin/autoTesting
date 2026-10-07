# Checkpoint — t176-script-replay (checker coordinator, cycle 0)

All mandatory checks complete; verdict PASS written to `qa/verdicts/t176-script-replay.md`.

Evidence identity (checker: claude-sonnet-subagent, this session; code state fe6eb98a + 677bfbe4 + 417bd71c):

| check | command / scope | code hashes (sha256 prefix) | lock | env | result |
|---|---|---|---|---|---|
| full suite | `uv run pytest` in worktree, collected 2235 | script_replay fd794e953add · locators 6ad0357cef66 · locator_derive 223cfbbaffb0 · session 76614cce543d · case 4a90c5625cee · project d6cbb493ecf7 | uv.lock 188681b3a300 | win32, `.venv` (uv sync: 80 packages) | 2 failed (not-this-unit), 2213 passed, 6 skipped, 14 xfailed |
| ruff | `uv run ruff check src tests scripts` | same | same | same | All checks passed |
| doctor | `uv run autotester doctor` | same | same | same | 1 violation (docs/SNAPSHOT.md stale, not this unit) |
| falsification x10 | `scratchpad/falsify.py`, one copy per row, single named test node each | same | same | same | 10/10 green-before, red-after on the named assertion, green-restored |
| redact perf re-run | `uv run pytest tests/test_redact_wrap_perf.py` x2 + base archive copy x2 | core/redact.py unchanged | same | same | 18 passed each (earlier red = load flake) |
