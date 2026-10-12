# Falsification results (chkA t179 r1, sub-checker "falsify")
Method: each row mutated in its own copy of HEAD under scripts/falsify/row*/; python = HEAD venv python with
PYTHONPATH="<copy>/src;<copy>/tests" (';' on Windows), pytest --rootdir/-c <copy>. Every log prints autotester.__file__ inside the copy.
(uv run python alone let the editable install from HEAD win; first attempt was discarded.)
Raw: row1.log/diff, row2.log/diff (_dispatch hunk only), row2b.log/diff (both hunks), row3, row4 (-k carve_out), row4c (full RO node).
Driver: scripts/falsify/runrow.sh, probe.sh, mutate.py.
| row | before | after mutation | restored |
| 1 AL3c return None | 32 passed | 24 failed, 8 passed (assert not out.ok ..., test_agent_read_only.py:76) | 32 passed, file cmp identical |
| 2 F2 (_dispatch only) | 1 passed | FAILED  assert "RuntimeError" in out.summary (:186), got 'the tool call failed' | 1 passed |
| 2b F2 (both excepts) | 1 passed | FAILED  RuntimeError escapes from _raise at :184 (raised through dispatch, no assert reached) | 1 passed |
| 3 F3 drop _withhold_if_credential | 1 passed | FAILED  :228 load_results("run-f3") == [] (one RawResult stored) | 1 passed |
| 4 drop walk.login (-k carve_out) | 8 passed | 8 passed: MUTANT SURVIVES that node | 8 passed |
| 4c same mutant, node ..::test_read_only_refuses_each_state_changing_step | 32 passed | 2 failed, 30 passed: [fill-Password-{{SECRET:APP_PASS}}], [fill-Name-   ] | 32 passed |
