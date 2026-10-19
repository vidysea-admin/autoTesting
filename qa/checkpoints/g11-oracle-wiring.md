# Checkpoint - g11-oracle-wiring (coordinator a, cycle 0)

Checker: claude-sonnet-subagent (Mode A, dual coordinator a). Code state: head 79e98ef35766485ebae7d9277c15d0053a10fd7e, base 8b93e475770d138d49d232dc9b925965ffba3e92, tree clean for src/tests. Env: Windows, worktree `.venv` python (pytest 9.1), Chromium via the project fixtures, dependency lock `uv.lock` unchanged by the diff.

| Check | Command + scope | Result |
|---|---|---|
| Affected run (importer set, 21 files, 269 tests collected) | `.venv/Scripts/python.exe -m pytest <21 files>` in the worktree | 265 passed, 4 failed; same 4 fail at base (git archive 8b93e475) |
| Second importer set (10 files, 239 tests) | same, head and base | 21 failed / 218 passed at both; identical ids |
| Lint | `.venv/Scripts/python.exe -m ruff check src tests scripts` | All checks passed |
| Doctor | `.venv/Scripts/autotester.exe doctor` | 2 violations (stale SNAPSHOT.md x2, also at base) |
| Falsify W1..W5 | copies under scratchpad check-g11-ow-a/mut-W*, PYTHONPATH=<copy>/src, one named node each | green in copy, red on the named assertion x5 |
| Probe P1 (request cap) | `test_p1_cap_one_read_then_controls_are_not_navigated` in a copy with `/assign*` GETs recorded | FAIL (2 loads after cap), run twice |
| Probe P2 (nested hide_input) | `test_p2_nested_context_validation_does_not_echo_input` | FAIL (input echoed via OracleContext) |

Remaining: none. Verdict: qa/verdicts/g11-oracle-wiring.md (FAIL, one blocking finding W3). Evidence: qa/evidence/g11-oracle-wiring-a/.
