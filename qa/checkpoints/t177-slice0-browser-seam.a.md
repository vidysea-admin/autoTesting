# Checkpoint (coordinator A) - t177-slice0-browser-seam, cycle 0

Attribution: coordinator A (claude-sonnet-subagent) + two read-only sub-checkers; verdict `qa/verdicts/t177-slice0-browser-seam.a.md`.
Environment: Windows 11, Python 3.11.15, headless Chromium (Playwright), uv; machine heavily loaded. Dependency lock: worktree `uv.lock` unchanged by the unit.
Code identity: head 3495ee61 (code d2d463a9), files `src/autotester/browser/{launch,session,assertions,secrets,video}.py`; tests `tests/test_browser_session_cdp.py`, `tests/test_browser_session_cdp_live.py`, `tests/test_browser_navigation_secrets.py`. No conftest/fixture/config change.
Build/data id: none (local about:blank pages only).

| Check | Command / scope | Result |
|---|---|---|
| Affected tests (redone with `uv --directory`, rootdir in tree) | pytest -p no:xdist -o addopts= -v: test_browser_session_cdp, _live, test_browser, test_video_parallel_sweep, test_secrets, test_browser_navigation_secrets, test_browser_settle, test_browser_actions; 163 collected | 162 passed, 1 load-flake (passes alone on the same head) |
| Video sweep alone | tests/test_video_parallel_sweep.py | 1 passed (396 s) |
| P1/P3 live probe | probe-p1-p3.py, real headless Chromium | cdp_url loopback, 127.0.0.2 refused, closed at teardown; _reaches_past_loopback False on timeout/cannot-assign |
| P2 live probe | probe-p2-start-leak.py | leak after exception in start(): file present, port open until caller close() |
| _answers_as probe | probe-answers-as-escape.py | BadStatusLine and AttributeError escape |
| Falsifications (copies, deleted) | B5, B6, AF3, B9 x2 + 3 extra mutants | all red on the named assertion except the equivalent order-swap |
| bad_scheme attack | 120 URLs, head vs master | no regression, no new bypass |
| Refactor identity / test diff / owed gap on master | ast body diff; git diff; ported test on 808cdf7f | identical / +357 -0 / gap pre-existing |
| Full suite | not run | owed on re-check (criterion-level security defect open) |

Superseded (discarded): sub-checker head test runs made with `uv run --project` from another cwd.
