# Checkpoint - crawl-approval-by-id (cycle 0, checker)
- pytest tests/test_check_crawl_approval.py: head 98ecbb38, script blob de5af1b, test blob 89418b5, worktree .venv, 4 passed rc 0.
- ruff check src tests scripts: rc 0. autotester doctor: clean rc 0.
- falsify C1 row1 (base script) 4 failed; row2 (all on-disk ids) 3 failed 1 passed; both green before, copies outside the worktree.
