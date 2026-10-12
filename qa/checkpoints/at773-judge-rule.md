# Checkpoint - at773-judge-rule (checker, cycle 0, HEAD 4acce31b)

Evidence identity for all checks: code = git tree of 4acce31b; no config, conftest, fixture or lock change in the diff; env = Windows 11, worktree .venv, `uv run`; no browser or data checks.

Completed:
- C1 contract read and D-074 authority on origin/master (docs/DECISIONS.md:2218, commit 74da197e). Result: authorized.
- C2 bypass-path hunt (git grep Verdict( / grade( / Result.PASS in src and scripts). Result: no bypass.
- C3 falsification, 8 isolated copies (scratchpad/at773chk/M1..M8) of tests/test_grade_assertion_rule.py + tests/test_grade.py (19 collected, base 19 passed). Result: M1, M2, M4-M8 red; M3 survived (outcome-only limb).
- C4 affected tests: 17 files importing stages.grade or run_case_pipeline, `-m "not harness"`: 119 passed in 222.8 s.
- C5 `uv run ruff check src tests scripts`: clean.
- C6 `uv run autotester doctor`: 1 violation, stale-generated docs/SNAPSHOT.md (not in this diff).

Remaining: full suite (queued 6th) under D:/autoTesting/.work/suite.lock; then the merge, re-run of grade tests, issue rows and push. Lock not taken: held by the t203 checker at 19:29 IST, and the coordinator set the queue order.
Attribution: claude-sonnet-subagent checker; verdict qa/verdicts/at773-judge-rule.md.

## Resume 1 of 2 (2026-10-11, head 7a1509ee; code identity unchanged from 4acce31b)
- R1 branch head 7a1509ee = cycle-0 verdict commit on top of 4acce31b; diff between them is qa files only. Result: unchanged code identity.
- R2 `tick.mjs --lint-manifest` on the branch manifest: exit 1 (ERROR no-pre-check, ERROR mutant-cap). Result: not dispatchable, BLOCKED-PROCESS written. C1-C6 above are reusable on resume 2 only if src/tests hashes stay as at 4acce31b.
- R3 merge forecast: merge-tree clean (tree 79391b0d), merged-tree grade tests 54 passed. Evidence: qa/evidence/at773-judge-rule/resume1-2026-10-11.md.
- Still remaining after the maker fixes the manifest: acceptance end to end re-run by this checker (reuse per .9-5 once Pre-check lines carry t= and blobs=), class attack (every assertion kind, multiple assertions with one unmet, missing/unreadable evidence, retired/errored case), one falsification per criterion in a throwaway copy, P1/P4 follow-up decision.

## Retry 1 (2026-10-11, head 1e0aed21; judged PASS, cycle 0)
Evidence identity: code = grade.py blob 3adecbc, test_grade_assertion_rule.py 0810af0, test_grade.py 7bc75db (branch tree 1e0aed21; execute.py unchanged vs master); contracts grade.md d597b13, execute.md eecb10b; env Windows 11, worktree .venv via uv --directory; no browser or data checks. Attribution: claude-sonnet-subagent, verdict qa/verdicts/at773-judge-rule.md.
- T1 tick.mjs --lint-manifest exit 0. Result: dispatchable.
- T2 affected tests, 23 files, -p no:xdist -o addopts= -m "not harness": 331 passed (2131 s). Evidence qa/evidence/at773-judge-rule/affected-tests.txt.
- T3 class attack, 65 probes through real assert_expected labels: no unmet-to-PASS path. Evidence class-attack-output.txt.
- T4 falsifications G6 and E1 in isolated copies: green, red, restored. Evidence falsifications.txt.
- T5 ruff clean; doctor: stale-generated docs/SNAPSHOT.md only (inherited; the diff touches no docs).
- Cycle-0 C1-C6 are superseded by T1-T5. Nothing remaining. Next: maker close-out (manifest flip, merge, issue rows P1-P3, goal task) and the 6c integration check.
