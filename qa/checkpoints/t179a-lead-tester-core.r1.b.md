# Checkpoint: t179a-lead-tester-core, repair check r1, coordinator B

Cycle checked: 1 | Verdict: FAIL (AL6) | AL2 PASS | AL3 PASS | Resumes: 0 | Policy-Version: proportional-verification/2026-10-10.9

## Evidence identities (one per completed check)
Common: code tree c489e201 (code SHA 67a94fb1), base 638d788a; copies `git archive` extracted under C:/Users/Lenovo/AppData/Local/Temp/claude/chk-t179r1b-716fbf97/{base,head,fals-al3c,fals-f2,fals-f3}; each probe prints `autotester.__file__` from its own copy; own `.venv` per copy (python 3.11); lock hash = uv.lock in the archive; agent: claude-sonnet-subagent (this coordinator, files under qa/evidence/t179a-lead-tester-core-r1-B/).

| Check | Command and scope | Scripts (sha256 prefix) | Result |
|---|---|---|---|
| S1 21,744 run_case rows x {base, head, head again} | s1-table/run_shards.sh, s1_table.py, s1_analyze.py, s1_nav.py, s1_extra.py; raw out.tar.gz (78600f5c) | probe_lib.py 99e8d5d6 | head = head again; tables in s1-table/summary.md |
| S2 118 destinations x 3 policies | s23-nav-login/s2_nav.py, s2_analyze.py | same lib | s2-summary.txt |
| S3 176 login-abuse rows | s23-nav-login/s3_login.py, s3_analyze.py | same lib | s3-summary.txt |
| S4 138 dispatcher robustness rows, base and head | s45-robust-secrets/s4_robust.py (8f65d5d8) | same lib | s4-head.json, s4-base.json |
| S5 174 secret rows + 41-row direct guard table + 10 returned-text gate rows | s5_secrets.py (34672e71), s5b_returned_text_gate.py | same lib | s5-*.json, s5b-*.json; grep positive control passed (7 planted hits found, decoy clean) |
| S6 static | `uv --directory head run --frozen --offline` ruff check src tests scripts (clean), autotester doctor (clean), pytest tests/test_agent_tools.py tests/test_agent_read_only.py (131 passed), importers (218 passed), test_agent_loop + test_explore_safety (71 passed) | s6-static/*.txt | no full suite, no suite lock |
| Falsify AL3(c), F2, F3 | s6-static/fals_runner.py in a fresh `git archive c489e201 src tests scripts pyproject.toml` each; PYTHONPATH `<copy>/src;<copy>/scripts` (`;` on Windows) | s6-static/falsifications.txt | green, red on the named assertion, restored green (3 of 3) |

Not reusable by a later check without re-running: S4/S5 depend on tools.py:86-101 and 158-170 (the fix for PI-1 changes them); S1-S3 depend on guards.py and stay valid unless guards.py changes.
Copies deleted after the check (C:/Users/Lenovo/AppData/Local/Temp/claude/chk-t179r1b-716fbf97 no longer exists).
