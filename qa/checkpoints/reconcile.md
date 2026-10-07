# Checkpoint: reconcile (cycle 0, single checker)

Source: b78baf79 on wave/reconcile (code 82ad6255). Relevant blob hashes: reconcile.py 054113fd, ingest.py eb3ea179, screen_identity.py 31b575c8, flowspec.py 8a36c0c4, uv.lock e9bfb886. Tree 12bc1fab. Environment: Windows 11, worktree .venv, no browser, no network. No build/deploy id; no data snapshot (fixture frozen_sample.json).
Attribution: claude-sonnet-subagent checker, cycle 0, verdict qa/verdicts/reconcile.md.

| Check | Command / scope | Result |
|---|---|---|
| verify | pytest test_reconcile, test_reconcile_schema, test_ingest, test_merge_flowspec, test_schema (74 collected) | 74 passed |
| ruff | ruff check src tests scripts | pass |
| doctor | autotester doctor | clean |
| importers | 22 test files importing the changed modules, no live-browser | 272 passed, 1 failed (test_goal_contract_registration, .goal dashboard drift, not in diff) |
| frozen sample run | reconcile over frozen_sample.json, mock judge 0.9 | 27 screens, 2 matched, 25 new, 2 judge calls, 6/6 flows, 92/93 steps resolve |
| falsification | 27 rows, isolated copies (src, tests, docs, scripts, pyproject), named nodes | 27 red after green; RC3b alone survives (second scrub layer), RC3c both layers red |
| public data | full read of frozen_sample.json + grep of diff | no personal or credential data |

Mandatory evidence: complete. Full suite: not run (full-suite trigger: none).
