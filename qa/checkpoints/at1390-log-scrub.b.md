# Checkpoint - at1390-log-scrub (coordinator B), cycle 0
Head aae034d2 (code 1994f61a), base c437d3a5. Env: Windows, .venv python 3.11, uvicorn 0.52.4, deps per uv.lock.
- pytest tests/test_access_log_scrub.py tests/test_container_supervision.py tests/test_auth_deploy_files.py (3 files, 17 collected) -> 17 passed. Inputs: access_log_scrub.py, app.py, test_access_log_scrub.py (git blobs at aae034d2).
- ruff check src tests scripts -> pass.
- real uvicorn CLI probe, port 18931, 9 requests -> 9 scrubbed lines (own PID, stopped).
- dictConfig-after-import filter retention -> [AccessLogScrub].
- falsification a (install call removed), b (/v/ sub removed), c (query mask removed): green-before 3 passed in the base copy, red-after each; copies under D:/autoTesting/.work/tmp/at1390b.
- Attribution: coordinator B (claude-sonnet-subagent), file qa/verdicts/at1390-log-scrub.b.md. Result: PASS.
