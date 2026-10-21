# Checkpoint - bench-inputs-ui (coordinator A), cycle 1
Verdict: PASS. All mandatory checks completed; nothing remaining. Checker: coordinator A, claude-sonnet-subagent.
Reviewed SHA 99eed54d, code 2203990e, repair base 8e8e0fae, base 8956c9bc. Environment: Windows 11, worktree .venv python, uv, Playwright MCP browser. Dependency lock: worktree uv.lock as checked out (unchanged by the diff).
Data: synthetic project `demo` under AUTOTESTER_ROOT=D:/autoTesting/.work/tmp/bi-A1/root (seed qa/evidence/bench-inputs-ui-A/c1-seed.py); server uvicorn autotester.ui.app:app on 127.0.0.1:8771, PIDs 12988 and 61769 (mine, stopped).

| check | command / scope | result |
|---|---|---|
| affected tests | uv run pytest tests/test_bench_marks.py tests/test_ui_bench_inputs.py tests/test_bench_inputs_stage.py tests/test_ui_auth_policy_table.py (39 collected) | 39 passed |
| lint | uv run ruff check src tests scripts | All checks passed |
| shared callers | test_ui_intake, test_ui_project_intake, test_ui_env_editor, test_schedule_tick, test_issue_ids, test_ui_origin_guard | 198 passed, 1 skipped |
| C1 race repro | c1-probe4/5/6/7 (30 parallel; 25 pairs; 60 + readers; 24 x 10) | 0 acknowledged marks lost; 5 read-side 500s only with reader load (proposed issue) |
| C2 upload | c1-probe2/3/8 (120 MB, MAX and MAX+1, names, 12 concurrent) | 413 in 0.3 s no spool; boundary exact; pin consistent |
| scorer e2e | c1-e2e.py | FP rate 1 -> 0.5 -> 0.3333 -> unadjudicated |
| falsification C1 | copy m1, set_mark lock -> nullcontext | green-before 1 passed, red-after 1 failed |
| falsification C2 cap | copy m2, cap MAX_BYTES*1000 | green-before 1 passed, red-after 400 != 413 |
| falsification C2 pin lock | copy m3, atomic-list lock -> nullcontext | green-before 2 passed, red-after 1 failed |
| browser | Playwright upload + mark on 99eed54d | pass, 0 console errors |
Evidence dir: qa/evidence/bench-inputs-ui-A/c1-*.
