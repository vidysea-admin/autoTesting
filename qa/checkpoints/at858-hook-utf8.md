# Checkpoint - at858-hook-utf8 (cycle 0)
Checker: claude-sonnet-subagent, bound .worktrees/at858-hook-utf8, head 664fe839, product 209bcb86.
- scope/diff read: files = qa/hooks/mc-sessionstart.ps1, tests/test_mc_sessionstart_loop_status.py (+manifest); result PASS.
- `AUTOTESTER_TIMING_SCALE=4 uv run pytest tests/test_mc_sessionstart_loop_status.py tests/test_mc_sessionstart_unclosed.py` (17 collected): run1 16p/1f (load timeout of existing healthy-log test), rerun 17p; hook sha1 of content at 209bcb86; uv.lock unchanged; env: Windows 11, powershell.exe 5.1, host CPU 90-100%.
- falsification F1 in scratchpad copy: red on named assertion; result PASS.
- ruff PASS; doctor exit 0.
