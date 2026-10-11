# Checkpoint - t198a-zip-drive-intake, seat B, cycle 2 (head dba80100, product 39533108)

| check | command / scope | code hash (git) | result | attribution |
|---|---|---|---|---|
| failed-criterion tests | `pytest -p no:xdist -o addopts= tests/test_zip_intake_{register,atomic,limits,names}.py tests/test_ui_intake.py` (133 collected) | dba80100 | 133 passed | seat B coordinator |
| falsification | scratch copy, `except Exception` block in `expand_zip` removed, `-k "utf8 or no_mutation or invalid_utf8"` | zip_intake.py @ dba80100 | 3 passed before, 2 failed after | seat B coordinator |
| hostile sweep, expand_zip | qa/evidence/t198a-zip-drive-intake-r2-B/test_hostile.py `-k test_expand` (1773) | dba80100 | 1773 passed | seat B coordinator |
| hostile sweep, upload route | same file `-k test_route` (1773) | dba80100 | 1773 passed | seat B coordinator |
| differential | diff.py on 3918a8aa zip_intake.py overlay vs fixed | both | old: 19 UnicodeDecodeError; new: 0 | seat B coordinator |
| catch-site probes | probe3.py | dba80100 | KeyboardInterrupt/SystemExit/MemoryError and our-bug exceptions propagate | seat B coordinator |
| entry points / limits | read-only Sonnet sub-checker, lines re-read | dba80100 | one door (expand_zip); MAX_FIELDS/FIELDS_TOTAL_CAP intact | seat B coordinator |
Environment: Windows 11, Python 3.11.15 (worktree venv), no network. Dependency lock: uv.lock unchanged since 3918a8aa.
