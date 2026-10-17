# Checkpoint - at712-ledger-store (cycle 0)
- pytest tests/test_ledger_backref.py tests/test_ledger.py @ head 161aeffb, code 81970378: 33 passed. Inputs: blobs tests/test_ledger_backref.py, tests/test_ledger.py, src/autotester/ledger/store.py, src/autotester/cli_loop.py at that head; uv.lock unchanged; Windows, .venv python 3.11. Checker: claude-sonnet-subagent, qa/verdicts/at712-ledger-store.md.
- ruff check src tests scripts: clean. autotester doctor: clean.
- Falsification C1: gate scan loop -> `[]` in copy outside worktree: green 1 passed, red on 'qa/gates/at674-approval-key.md:4' assertion.
- Real-data run: ledger-backref b2d6558f --exclude AT-660 listed at674 gate line 260.
