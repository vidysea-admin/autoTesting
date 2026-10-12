# Checkpoint - at887-crawl-to-flows, repair check cycle 1, coordinator A (blind dual check)

Head b3a365a1 (product 54dced40), Repair base 6d70c0ec (ancestor of head, verified), merge-base with master 3748cb83.
Policy-Version: proportional-verification/2026-10-10.9. Tier L (dual-trigger security src/autotester/stages/expand.py:183).
Environment: `git archive b3a365a1` extracted to the session scratchpad on C: (`.../scratchpad/at887r1a-copy`), own `.venv` (uv sync --frozen, Python 3.11.15, uv.lock blob 4882ef560a);
`autotester.__file__` and the pytest rootdir confirmed inside that copy. No checkout, worktree or venv on D:.
Code blobs: explore_merge.py 5993844809 · expand.py f585181010 · explore_flows.py 4bff32fff2 · routes_learn.py 664a4221d1 · tests/test_explore_flows.py 827948a4fa · test_explore_flows_doors.py cb3734d7ad · test_expand_redaction.py 2e8b875987 · test_ui_learn_guard.py a66eb7c06d · tests/conftest.py 6e574e9606.
Data snapshot / build id: not applicable (no live site, no browser, no model call). Checker: claude-sonnet-subagent, coordinator A.

| Check | Command / scope | Result |
|---|---|---|
| Lint | `ruff check src tests scripts`; `autotester doctor`; `autotester map` | all checks passed; doctor clean; map exit 0 |
| Affected tests | 16 files (explore_flows, doors, expand, expand_cli, expand_redaction, explore_merge, eval_compiler, ui_learn, ui_learn_guard, ui_crawls, orchestrate_runners, cli_orchestrate_resume, coverage_wiring, merge_flowspec, cli_advice_resolves, redact_pii), `-p no:xdist -o addopts=`, 340 collected | 340 passed |
| F1 probe | `evidence/.../f1_probe.py` (library, CLI, UI via TestClient in a pytest probe, orchestrated DISCOVER+MODEL) | all scenarios OK, dangling_references == [] after every door |
| F2/F3 probe | `evidence/.../f2_f3_probe_test.py` (throwaway test inside the copy) | see verdict |
| Falsification X13c | drop alias rewrite in explore_merge.py | green 31 passed -> red 4 failed |
| Falsification X6 | narrow except to ProviderError in routes_learn.py | green 1 passed -> red 1 failed |
| Falsification PII2 | mask joined steps text in expand.py | green 23 passed -> red 1 failed (ordinal test) |
| Mutant m4 | always bump version in merge_screens_and_flows | green 31 -> red 1 (bumps exactly once) |
| Mutant m5 | negate rediscovery condition in _rediscovered_ids | green 31 -> red 4 |
| Full suite (A, 1) | `shard_suite.py --repo D:/autoTesting --ref b3a365a1 --shards 4 -- -o addopts=` | 3539 passed, 4 failed, 20 skipped of 3563 (collect proof ok); see verdict for the 4 |

Original attribution: this file, coordinator A, fix cycle 1. Evidence directory: qa/evidence/at887-crawl-to-flows-r1-A/.
