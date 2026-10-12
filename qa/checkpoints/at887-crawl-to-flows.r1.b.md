# Checkpoint - at887-crawl-to-flows, coordinator B, cycle 1

Head b3a365a1 (product 54dced40), repair base 6d70c0ec, base 3748cb83. Policy proportional-verification/2026-10-10.9. Attribution: claude-sonnet-subagent (checker B); verdict qa/verdicts/at887-crawl-to-flows.r1.b.md. Result of the whole check: PASS.

Environment fingerprint: `git archive b3a365a1` extracted to scratchpad `at887-r1b-x7q3k9-copy` (C:), `uv sync --frozen` (uv.lock unchanged from the commit), Python from `.python-version`; `autotester.__file__` inside the copy; 581 src/tests/scripts/pyproject/uv.lock files hash-equal to the git tree before and after the probes.

| Check | Command and scope | Code hashes (git blob) | Result |
|---|---|---|---|
| Data path, three merge doors | `python -I probes/p1_merge_doors.py` (synthetic graphs, 39 runs) | explore_merge.py 59938448, explore_flows.py (b3a365a1 tree), cli_crawl.py fdd86f5e, routes_crawls.py 5dbe87b0, orchestrate_runners.py d694a2d1 | all OK, 0 dangling |
| Orchestrated-door duplicates | `probes/p1b_orch_dups.py` | same | cli 5 screens, orch 7 screens, no dangling |
| Generation, masking, guard, route | `python -I probes/p2_generation.py` (MockProvider spy) | expand.py f5851810, routes_learn.py (b3a365a1 tree) | exact 10 prompt lines match; 6/6 encoded -> themed 400; unrelated ValueError -> misattributed sentence (P1) |
| F1 falsification | `probes/falsify.py F1` | explore_merge.py | green 3 passed / red 3 failed |
| F2 falsification | `probes/falsify.py F2` | routes_learn.py | green 1 passed / red 1 failed |
| F3 falsification | `probes/falsify.py F3` | expand.py | green 1 passed / red 1 failed |
| Affected tests | pytest tests/test_explore_flows.py tests/test_explore_flows_doors.py tests/test_expand_redaction.py tests/test_ui_learn_guard.py (-p no:xdist -o addopts=) | tests at b3a365a1 | 55 passed |
| Lint / design rules | `ruff check src tests scripts`; `autotester doctor`; wc -l | tree b3a365a1 | clean; routes_learn.py 300 |

Not run (by instruction): full suite, suite lock. Lane: normal (cycle 1, dual check). Evidence: qa/evidence/at887-crawl-to-flows-r1-B/.
