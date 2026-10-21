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
