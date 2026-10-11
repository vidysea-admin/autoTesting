# Checkpoint - t178-failure-bundle-fb4-fb5 - r1 seat B

Env: Windows, worktree .venv python, pytest -p no:xdist -p no:cacheprovider, uv.lock sha256 d795000fb0e2, no conftest edits. Code identity: HEAD 297207ff, product c142f8f1, repair base a7d3fa6c. Checker: claude-sonnet-subagent (seat B, cycle 1). Data/deploy id: n/a.

| Check | Command + scope | Result |
|---|---|---|
| FB4 verify | pytest tests/test_schema.py tests/test_store.py tests/test_pinned_regression.py tests/test_ui_runs.py (60 collected) | 60 passed |
| FB5 verify | pytest tests/test_expand.py tests/test_expand_cli.py tests/test_ui_learn.py tests/test_eval_compiler.py (61) | 61 passed |
| CONTAIN / C5 | pytest tests/test_failure_bundle.py (23) | 23 passed |
| ADVICE | pytest tests/test_cli_advice_resolves.py (32) | 32 passed |
| Merge-affected | test_cli_surface 46, test_cli_harness_safety 4, test_ui_origin_guard 87, test_cli_release 4 | all passed |
| Differential | evidence/diff_harness.py base vs head, 22 scenarios | 21 identical, 1 expected (new function) |
| Falsify FB5 | copy fals-m3, approved_batch != "x" | red 5==2, 5==0 |
| Falsify ADVICE | copy fals-adv, delete EXPECTED_SITES entry | red |
| Guidance mutants | fals-m1, fals-m2 on stage_and_review | survive (P1) |
| Containment hunk | git diff a7d3fa6c c142f8f1 on failure_bundle files | empty |

Scratch (outside the repo, session scratchpad t178r1B) holds the archives and copies; deleted on completion. Evidence: qa/evidence/t178-failure-bundle-fb4-fb5-r1-B/.
