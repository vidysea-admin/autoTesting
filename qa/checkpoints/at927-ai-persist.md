# Checkpoint - at927-ai-persist (cycle 0, checker, head 78288698)
- pytest tests/test_ai_persist.py tests/test_ai_report.py tests/test_ai_capture.py -> 111 passed; paths: those 3 files; code hashes: HEAD 78288698; env: worktree .venv; result PASS
- ruff check src tests scripts -> pass; autotester doctor -> clean (HEAD 78288698)
- falsification F1/F2 in copies outside the worktree: green-before 11 passed, red-after 3 failed each (named in verdict)
- probe stale verdict: reproduced (AT-1025)
