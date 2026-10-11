# Checkpoint t205-g10-headroom mr1 A (coordinator A, merge-reconcile): PASS at ecaaf7e4

Code identity: head ecaaf7e4 (product 39b42ca5; merge b841c232 = fb93776b + master 1c52bf71). Repair base fb93776b (ancestor, verified). Lock hash: uv.lock identical to the archive (uv sync OK). Env: Windows 11, Python via copy venv on C:, `autotester.__file__` and pytest rootdir inside the C: copy (asserted in every probe).

Checks (all in `git archive ecaaf7e4` copy on C:, `git init`ed; no checkout/worktree/venv on D:):
- git diff 1c52bf71 ecaaf7e4: 37 files, all T-205's; only tests/test_ui_runs.py (1 line) and schema/intake.py (kind literals) are not new files -> nothing master added was dropped
- affected tests: 67 reconcile-related files + test_cli*/test_schema*/test_store/doctor -> 1694 passed, 1 skipped (playwright), 268 s (affected.log)
- ruff check src tests scripts -> clean; autotester doctor -> clean; run_launcher.py 299, cli.py 293, routes_runs.py 81, app.py 271 lines
- autotester map / snapshot in the copy -> git status clean (byte-identical to the committed files)
- live CLI listing at master 1c52bf71 == head == tests/golden/cli_commands.json (same rows, same order)
- Source.origin matrix: master-written and fb93-written JSON load at head and re-serialise byte-identically; edge table in origin_edge.txt
- falsifications M1..M7 in throwaway copies (green before, red after): see verdict section 5
- sharded full suite (4 shards, ref ecaaf7e4, lock wait ~15 min): 4603 collected, 4576 passed, 6 failed, 21 skipped; the 6 are load-sensitive or fail identically on master 1c52bf71
- git merge-tree vs master 41349022: clean

Attribution: coordinator A (claude-sonnet-subagent), verdict qa/verdicts/t205-g10-headroom.mr1.a.md, evidence qa/evidence/t205-g10-headroom-mr1-A/. Result: PASS. Remaining: none.
