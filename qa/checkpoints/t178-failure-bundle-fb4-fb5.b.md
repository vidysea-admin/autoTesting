# Checkpoint, coordinator B, t178-failure-bundle-fb4-fb5, cycle 0, commit a7d3fa6c

Environment: Windows 11, Python 3.11.15, uv 0.11.27, `git archive a7d3fa6c` copies; code tree hash 826cbdeeb9c7; uv.lock sha256[:12] 25a972903d45; tests/conftest.py sha256[:12] 6b47a1771131.
Attribution: coordinator B (claude-sonnet-subagent); 4c diff read by a read-only sub-checker (findings only); evidence qa/evidence/t178-failure-bundle-fb4-fb5-b/.

| Check | Command / scope | Collected | Result |
|---|---|---|---|
| FB4 set | pytest test_schema test_store test_pinned_regression test_ui_runs | 60 | 60 passed |
| FB5 set | pytest test_expand test_expand_cli test_ui_learn test_eval_compiler | 61 | 61 passed |
| Containment + queue set | pytest test_failure_bundle test_run_queue test_run_queue_resilience test_ui_runs_queue test_regression_proof test_cli_issues | 87 | 87 passed |
| lint | ruff check src tests scripts; autotester doctor | - | clean |
| Falsify FB4 | list_cases filter forced True | 3 nodes | green 3 -> red 3 |
| Falsify FB5 | approved_batch lets pruned through | 2 nodes | green 2 -> red 2 (5==2, 5==0) |
| Falsify CONTAIN x2 | drop is_relative_to; drop ".." from validator | 1, 8 | green -> red on assertion |
| Adversarial | tests/test_attack_b.py, test_attack_b2.py in the copy | 51 | passed as designed, plus findings P1-P4 |
| Step 4c | full diff 3d8f7d5a..a7d3fa6c (21 src, 9 test files) | - | no deletion, no weakened assertion |
No full suite and no browser check run (coordinator A owns both).
