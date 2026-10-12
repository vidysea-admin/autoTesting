# Checkpoint A - at887-crawl-to-flows (cycle 0), head 6d70c0ec, base 3748cb83
Verdict: qa/verdicts/at887-crawl-to-flows.a.md (FAIL).
Environment: check tree D:/autoTesting/.worktrees/check-at887-a (autotester.__file__ inside; pytest rootdir the same); falsification copies on C: under scratchpad fal-887a (deleted); uv via `uv --directory`.
Code hashes: product commit 75b23672, head 6d70c0ec. Dependency lock: the tree's uv.lock at that commit (unchanged by the diff).
Completed checks (evidence identity = command + scope + head):
- ruff check src tests scripts -> All checks passed; autotester doctor -> clean (head 6d70c0ec).
- AT-890 provider-spy matrix: 79 cases x expand, expand_flow, compile_evals; attack.py, gaps.py, gaps.txt in qa/evidence/at887-crawl-to-flows-A/ (sub-checker, MockProvider spy, store-backed project).
- AT-887 hostile graphs and three doors: h1_pure.py, h2_merge.py, h3_doors.py, h4_leak.py; h2 re-run by the coordinator -> h2-rerun.txt (dangling screen ids reproduced).
- Falsifications R1-R13: falsifications.md (11 killed, R9 equivalent, R13 survived, R6 weak).
- Diff scope 3748cb83..6d70c0ec: 12 files, all in the manifest.
Not done: full suite (owed only if every criterion met; B7 not met). At the repair re-check: B7, the generate_cases refusal, rerun R6/R13 with the new tests, then the one full suite via shard_suite.py --ref <new head> (extracts on C:).
