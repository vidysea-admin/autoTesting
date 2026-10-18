# Checkpoint - fix6c-r4-routeword (coordinator A) - cycle 0, head 3045e909, code 58c0361e
- affected tests (13 files, listed in verdict) -> 334 passed; inputs: src/autotester/schema/leak_evidence.py, tests/test_leak_url_ids.py, test_leak_evidence.py, test_oracle_responsive.py at 58c0361e; env: win32, wt .venv; agent: checker A (claude-sonnet-subagent)
- F1/F3 falsification m1 (11 words removed): 26 failed / 120 passed -> red
- F2 falsification m2 (base test versions): 2 failed / 17 passed -> red
- security probe: qa/evidence/fix6c-r4-routeword/probe-a.py -> all id/PII shapes refused, query values templated
- result: PASS
