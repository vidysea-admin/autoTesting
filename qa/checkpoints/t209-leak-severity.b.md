# Checkpoint B - t209-leak-severity (cycle 0)

Base 722bf3df, code 7746a2b8. Interpreter: worktree .venv python, TMP=D:/autoTesting/.work/tmp. pyproject/uv.lock unchanged since base.

| check | command / scope | code hashes | result |
|---|---|---|---|
| verify cmd 1 | pytest tests/test_finding_priority.py tests/test_report_banner.py tests/test_leak_evidence.py tests/test_leak_repro_replay.py tests/test_unified_report.py (49 collected) | src files at 7746a2b8 | 49 passed |
| verify cmd 2 | git diff --name-only 722bf3df..7746a2b8 | - | no forbidden file |
| ruff | ruff check src tests scripts | 7746a2b8 | clean |
| render equivalence | probe_render (base src vs candidate src), render_html(report) | - | identical sha f77b37a13b9ec138 |
| MP7/MP8/MP9/MP10 falsification | run_falsify.py in copies D:/chk-scratch-t209b/r2/* | - | each green before, red after on the named node |
| leak probe | probe_leak.py, probe_ids.py (qa/evidence/t209-leak-severity/b/) | - | F1 reproduced |

Attribution: coordinator B (this agent). Nothing from coordinator A read or counted.
