# Checkpoint - t204-team-login r1 seat A (cycle 1, head 6ea9b688, product sha df1b0d57)

Environment: Windows 11, worktree venv .worktrees/t204-team-login/.venv (argon2 present); root .venv lacks argon2. Suite lock: %LOCALAPPDATA%/aios/suite.lock.

- advice guard: `pytest tests/test_cli_advice_resolves.py` (-p no:xdist -o addopts=) -> 31 passed. Code: git 6ea9b688, src/autotester/auth/config.py. Attribution: seat A, qa/verdicts/t204-team-login.r1.a.md
- targeted set (19 files, listed in the verdict) -> 359 passed, 1 skipped, 0 failed (508.91 s). Evidence qa/evidence/t204-team-login-r1-A/targeted-run.txt
- AU20 matrix: check_startup, 9 binds x 7 lists -> au20-matrix.txt (concrete bind enforced, wildcard not)
- falsification rows 1-4: green before, red after (falsification.txt)
- env-reader audit sub-checker and browser leg (AU26, 7 of 7) -> subchecker-summaries.md, qa/evidence/browser-t204-team-login-r1-A/
- full suite: NOT RUN (lock busy 901 s, holder pid 57556, D:/autoTesting ref dba80100). Remaining R1: shard_suite at 6ea9b688 (use --python worktree venv; root venv lacks argon2).

Reuse: valid while the src/ and tests/ blobs at 6ea9b688 are unchanged.
