# Checkpoint - at1390-log-scrub (coordinator A) - Cycle 0, head aae034d2

Env: Windows 11, Python 3.11.15, uvicorn 0.52.4, uv.lock sha256 d7ff32b5ab4a, pyproject 8d5896164e3d. Checker: claude-sonnet-subagent (checker-at1390-A).
Code hashes (sha256 prefix): ui/access_log_scrub.py c2885004579b, ui/app.py f045b1b78f61, tests/test_access_log_scrub.py a013e9c36645.

| Check | Command / scope | Result |
|---|---|---|
| C1 verify | `uv run pytest tests/test_access_log_scrub.py tests/test_container_supervision.py tests/test_auth_deploy_files.py -p no:cacheprovider` (17 collected) | 17 passed |
| C1 deployed | real `python -m uvicorn autotester.ui.app:app` on a free loopback port, pristine git-archive copy, 8 httpx requests incl. 1 WebSocket upgrade | HTTP lines scrubbed; WebSocket handshake line on uvicorn.error not scrubbed (P1) |
| Falsification row1/2/3 | copies under D:/autoTesting/.work/tmp/chkA1390/row1..3; green-before 3 passed each; edits: app.py call -> pass; `/v/` sub -> pass; query branch -> return path | all RED on the named assertions |
| Entry/hosting siblings | tests/test_container_entrypoint_behaviour.py tests/test_container_writable_root.py tests/test_hosting_gaps.py | 45 passed, 1 skipped |
| Lint | `uv run ruff check src tests scripts`; `tick.mjs --lint-manifest`; `autotester doctor` | clean; exit 0; 2 violations = pre-existing docs/SNAPSHOT.md |

No full suite run: a unit check runs none; the 6c integration step owns the L-security full-suite decision (.13-2a).
