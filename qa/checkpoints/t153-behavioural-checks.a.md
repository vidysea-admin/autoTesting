# Checkpoint A — t153-behavioural-checks (coordinator A), cycle 0, Retry 0
Code identity: HEAD 2653bbcb97bd58dbab24f6556deb74946ddf18bb, product ff901f72; src/ and tests/ equal master 354bd31f. Test blobs: test_ai_capture 4fd639e, test_grade_evidence 2af58c0, test_approval_signing 709601f. uv.lock and pyproject unchanged vs base. Env: Windows 11, worktree .venv python.
Done (reusable while the code identity is unchanged):
- criterion commands: pytest of 6 files -> 189 passed, 2026-10-11T01:45 (checker A); ruff clean; contract grep exit 1.
- doctor on git archive of master 354bd31f and of 2653bbcb: only stale-generated docs/SNAPSHOT.md.
- falsifications AI6a AI6b AI7a AI7b AI7c AI7d AI7e AI7f: all green-before / red-after (see verdict).
- step 4c diff scope: clean.
Remaining: ONE checker full suite (shard_suite.py --repo D:/autoTesting --ref 2653bbcb --shards 1 ... -- -o addopts=), blocked 15 min on the suite lock (holders pid 20200 then 38884, not ours; shard_suite exit 3).
