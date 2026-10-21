# Checkpoint - bench-inputs-ui (coordinator B), cycle 0
Verdict: FAIL (C1 concurrent marks lose rulings). All mandatory checks completed; nothing remaining. Checker: coordinator B, claude-sonnet-subagent.
Reviewed SHA c4c3dccc, code 16bcf2b4, base 8956c9bc. Environment: Windows 11, worktree .venv python, uv, own Playwright (headless chromium). Lockfile unchanged by the diff.
Data: synthetic project `demo` under AUTOTESTER_ROOT=D:/autoTesting/.work/tmp/bi-chkB/root; server uvicorn on localhost:8791 (my PIDs, stopped). The worktree later gained uncommitted maker edits; every B check ran on a copy or on 16bcf2b4 content.

| check | command / scope | result |
|---|---|---|
| scoped tests | pytest test_bench_marks, test_ui_bench_inputs, test_ui_auth_policy_table | 36 passed (pytest-scoped.txt) |
| affected tests | 18 files (sidebar, permissions, auth, acceptance, crawls, report, bench) | 274 passed (pytest-affected-tail.txt) |
| lint / doctor | ruff check src tests scripts; autotester doctor | clean; 2 MAP.md violations |
| candidates tool | shard_suite --list --candidates | integration-required, 406 of 543 (candidates-summary.json) |
| HTTP probes | http-probes.py | http-probes.txt |
| Mode D | browser-drive.py | report.json, 6 screenshots; 2 console errors, both deliberate |
| mutants | mutants.py, 8 copies | mutants.json: 6 red, S-cap and S-echo survived |
| race | race.py on git archive 16bcf2b4 | race-16bcf2b4.txt: 10/10 rounds lost acknowledged marks |

# Cycle 1 (repair) - coordinator B
Verdict: PASS (verdict qa/verdicts/bench-inputs-ui.b.md; cycle-0 FAIL kept at bench-inputs-ui.b.r0-1.md). All mandatory repair checks complete; nothing remaining.
Reviewed SHA 99eed54d (repair base 8e8e0fae). Environment: Windows 11, worktree .venv python, own Playwright, uvicorn on localhost:8791 (PIDs mine, stopped), data roots under D:/autoTesting/.work/tmp/bi-chkB2.

| check | command / scope | result |
|---|---|---|
| scoped tests | pytest test_bench_marks, test_ui_bench_inputs, test_bench_inputs_stage, test_ui_auth_policy_table | 39 passed |
| downstream set | 14 files (file_lock + upload_stream users) | 302 passed, 1 skipped (c1-pytest-affected.txt) |
| lint / doctor | ruff check src tests scripts; autotester doctor | clean; clean |
| race repro | race-cycle1.py on git archive 99eed54d | race-99eed54d.txt: 10 rounds x 20, 0 lost, 0 errors |
| harder race | race-more-cycle1.py | race-more-99eed54d.txt: 60 threads set + undo, 5 rounds, 0 discrepancies |
| HTTP | probe-c2-cycle1.py, probe-cap-cycle1.py, http-probes-cycle1.py | cap boundary 262144 ok / 262145 413; 40 MB 413; .exe 400; 12 uploads consistent; 40 marks stored |
| Mode D | browser-drive (copy) + browser-upload-cycle1.py | browser-cycle1/: 16/20 script steps, the 4 others are script artifacts; upload re-run passes |
| falsification | mutants-cycle1.py (5 copies) | mutants-cycle1.json: all red |
| repeats | 8 x 4 concurrency tests | repeat-concurrency-99eed54d.txt: 8 x 4 passed |
