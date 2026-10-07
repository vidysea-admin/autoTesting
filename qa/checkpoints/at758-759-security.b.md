# Checkpoint - at758-759-security (coordinator B, blind)

Bound: D:/autoTesting/.worktrees/at758-759-security. Unit tip b9ce7983 (tree 4afe5be6134e), base af8f3218. Cycle 0. Policy-Version: proportional-verification/2026-10-06.6. Resume 1 of 2 used.

Evidence identity common to all rows below: code hashes (sha256 prefix) helpers.py 93aeeba646bd3d60, explore_consent.py da5daf5ddb225787, conftest.py a87e3c5cc39846fb; dependency lock uv.lock 0f25d574ae096863; environment Windows 11, CPython 3.11 via uv, venv D:/autoTesting/.worktrees/at758-b-suite/.venv; attribution coordinator B (claude-sonnet-subagent); evidence under the session scratchpad (rb/, copy/, mutB*/) and the detached worktree D:/autoTesting/.worktrees/at758-b-suite (b9ce7983).

DONE (reuse while the hashes are unchanged):
- Live uvicorn Host/Origin attack matrix, h11 and httptools: no bypass (scratchpad rb/attack.py). PASS for AT-758/760/761.
- Host fuzz 252,059 strings and Origin fuzz 166,275 strings against strict oracles: no non-loopback accepted (rb/fuzz.py, rb/fuzz2.py). PASS.
- AT-759 attack set, 115 tests, 5 entry paths, 3 kinds, 7 removal modes (copy/tests/test_b_attack759.py): no account row covers after removal; human rows cover; ADVERSARIAL refused. PASS (a base_url change mints a new row by design).
- Falsification in separate copies (mut.py first pass, mut2.py second pass): see verdict item 5; one non-equivalent survivor (userinfo clause), low.
- Protected conftest fixture review: justified (test_ui_runs.py 6 passed -> 5 failed without it).
- Diff scope 4c: clean. ruff: All checks passed. doctor: clean.
- Hang probe: tests/test_mc_sessionstart_loop_status.py + test_media_real_ffmpeg.py + test_crawl_inventory_live.py under timeout 400 gave no output on both b9ce7983 and base af8f3218.

REMAINING:
1. One uninterrupted full `uv run pytest` at b9ce7983 (no -q, no -x, tests/test_crawl_inventory_live.py deselected by name with the hang cause recorded). Run 1 aborted silently at 56% (log .work_pytest_run1_aborted.log in the suite worktree; 3 F at indices 524/1300/1348); run 2 aborted silently at 727 tests; neither is a completed suite. Needs about 85-90 min wall.
2. Compare the early F tests (likely test_mc_sessionstart_loop_status [5], test_media_real_ffmpeg [0]) against base af8f3218.

The detached suite worktree D:/autoTesting/.worktrees/at758-b-suite is still present for the remaining suite run; remove it with `git -C D:/autoTesting worktree remove --force D:/autoTesting/.worktrees/at758-b-suite` after.
