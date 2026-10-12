# Tests, lint, doctor (all run from inside the worktree with its own .venv; autotester.__file__ inside the tree)

- pytest affected files: 195 passed in 535 s (tests/test_video_pointers.py, test_video_review.py, test_video_review_gates.py, test_video_review_redaction.py, test_video_review_cleanup.py, test_cli_video_review.py, test_cli_video_review_exits.py and the other repair-touched files)
- ruff check src tests scripts: RED, 1 error: E501 Line too long (103 > 100) at tests/test_video_pointers.py:199:101
  `fat = _parse(("0:10 | " + "z" * 400 + "
") * MAX_POINTER_LINES)   # every line valid, file too big`
- autotester doctor: clean
