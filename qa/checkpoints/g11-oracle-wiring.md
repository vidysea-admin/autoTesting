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

# Cycle 1 (repair check, coordinator a)

Code state: head 9cca3e6d57e616e525009a337558c1e4240509e8 (base 8b93e475, repair base 79e98ef3 verified an ancestor), tree clean for src/tests. Env: Windows, worktree `.venv` python, TMP/TEMP=D:/autoTesting/.work/tmp, scratch on D:/autoTesting/.work/tmp/check-g11-ow-a-c1 (C: had 0.03 GB free, so the C: scratchpad could not hold the copies). Dependency lock unchanged.

| Check | Command + scope | Result |
|---|---|---|
| Affected set (grep importer set, 27 test files, 449 tests; shard_suite said integration-required because tests/conftest.py is a changed importer) | `.venv/Scripts/python.exe -m pytest <27 files>` | 413 passed, 36 failed; all 36 in test_network_oracles (3), test_oracle_answer_key (19), test_oracle_copy_lint (1), test_oracle_responsive (1), test_oracle_state_after (12); none in a file this unit adds or edits |
| Same 5 red files at pre-unit base 8b93e475 (git archive copy) | pytest of those 5 files | 36 failed, node ids IDENTICAL to head (cycle1/reds-pre-8b93e475.txt vs reds-head-9cca3e6d.txt) |
| Lint | `ruff check src tests scripts` | All checks passed |
| Doctor | `autotester doctor` | 2 violations, both stale generated docs/SNAPSHOT.md (stale at base too) |
| Falsify W3 x3, W1, W4 | copies under D:/autoTesting/.work/tmp/check-g11-ow-a-c1/mut-*, runner qa/evidence/g11-oracle-wiring-a/cycle1/mutants-runner.py | green before (8 passed), red after on the named tests x5 (cycle1/mutants.out) |
| Probe P1b (cap 1: no /assign page may load) | copy of 79e98ef3 src vs copy of 9cca3e6d src | 79e98ef3: 2 loads, FAIL; 9cca3e6d: 0 loads, pass |
| Probe P2 (nested validation echo) | copy of 9cca3e6d src | pass |

Remaining: none. Verdict: qa/verdicts/g11-oracle-wiring.md (Cycle checked: 1).
