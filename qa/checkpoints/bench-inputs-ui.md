# Checkpoint - bench-inputs-ui (coordinator A), cycle 0
Verdict: FAIL (C1 concurrency defect). All mandatory checks completed; nothing remaining. Checker: coordinator A, claude-sonnet-subagent.
Reviewed SHA c4c3dccc, code 16bcf2b4, base 8956c9bc. Environment: Windows 11, worktree .venv python, uv, Playwright MCP browser. Dependency lock: worktree uv.lock as checked out (unchanged by the diff).
Data: synthetic project `demo` under AUTOTESTER_ROOT=D:/autoTesting/.work/tmp/bi-A/root (seed qa/evidence/bench-inputs-ui-A/seed.py); server python -m uvicorn autotester.ui.app:app on 127.0.0.1:8765, PIDs 31240 and 46024 (mine, stopped).

| check | command / scope | result |
|---|---|---|
| affected tests | uv run pytest tests/test_bench_marks.py tests/test_ui_bench_inputs.py tests/test_ui_auth_policy_table.py (36 collected) | 36 passed |
| lint | uv run ruff check src tests scripts | All checks passed |
| falsification C1 | copy m1, acceptance_comparison.py:124 `ai = ai`; test_one_real_one_false_one_unmarked_... | green-before 1 passed, red-after assert 1.0 == 0.5 |
| falsification C2 | copy m2, bench_inputs.py:59 sha256(raw[:-1]); test_c2_an_editor_uploads_... | red on pin.sha256 == digest |
| falsification C3 | copy m3, label removed in bench_inputs_view.py; test_c3_every_new_control_... | red on label regex |
| Mode D | Playwright, editor and viewer sessions, 8 screenshots | qa/evidence/browser-bench-inputs-ui-2026-10-21-checker/ |
| HTTP probes | probe1..probe5.py | qa/evidence/bench-inputs-ui-A/*.out |
| scorer e2e | e2e.py with scripts/check_acceptance_comparison.py | e2e.out |
