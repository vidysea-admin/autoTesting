# Checkpoint - at888-session-survives-failure (cycle 0, single checker coordinator)

Policy-Version: proportional-verification/2026-10-10.9
Verdict: PASS (non-blocking findings). Attribution: checker coordinator, qa/verdicts/at888-session-survives-failure.md.

## Environment fingerprint
- Head eea903d8ff64 (code 9286a25d, parent 55816796), branch wave/at888-session-survives-failure; merge base master 3748cb83. Checked from the detached checkout `D:/autoTesting/.worktrees/check-at888` (read-only, clean at eea903d8); `autotester.__file__` resolved inside it (probe_*.json `autotester_file`, pytest rootdir `D:\autoTesting\.worktrees\check-at888`).
- Base reproduction: `git archive 3748cb83` extracted on C: with its own venv on C:; pytest traceback paths run through `..\base-venv\Lib\site-packages` (evidence base-headed.txt).
- Python 3.11.15, pytest 9.1.1, Windows 11 (10.0.26300), Playwright Chromium build 1234 (`ms-playwright\chromium-1234`), headed and headless. Machine heavily loaded by other agents (real-browser tests 190-570 s).
- `uv.lock` blob 4882ef560a75; `qa/adapter.json` coding adapter.

## Code hashes (blobs at eea903d8)
- src/autotester/browser/video.py 246fba63e906
- src/autotester/stages/run_case_pipeline.py 89cd287adbc2
- tests/test_session_survives_failure.py 6d0b360ed089
- tests/test_session_survives_failure_live.py b34fd93258267b4

## Evidence identities (all under qa/evidence/at888-session-survives-failure/, all at head eea903d8)
| Check | Command / scope | Collected | Result |
|---|---|---|---|
| Unit + pipeline | `pytest tests/test_session_survives_failure.py tests/test_run_case_pipeline.py tests/test_run_case_pipeline_resilient.py tests/test_ui_runs_serial_resilience.py -p no:xdist -p no:cacheprovider -o addopts=` (head-unit.txt) | 39 | 39 passed, 21 s |
| Live headless | `pytest tests/test_session_survives_failure_live.py` (head-live-headless.txt) | 4 (1 deselected) | 3 passed, 567 s |
| Headed repro, head | `AUTOTESTER_HEADED_TESTS=1 pytest ... -k headed` (head-headed.txt) | 4 (3 deselected) | 1 passed, 273 s |
| Headed repro, merge base | same test run against the base extraction (base-headed.txt) | 4 (3 deselected) | 1 failed: `TargetClosedError` at the second case launch, 191 s |
| Video / mask regression | `pytest tests/test_video_evidence.py tests/test_video_masking_live.py` (head-video-masking.txt) | 5 | 5 passed, 511 s |
| Real-pipeline probes | probe_at888.py through `_run_and_grade_resilient`: matrix (11 cases, headed), killbetween headed + headless, latched, budget (probe-*.json/txt) | n/a | see verdict |
| Plain Playwright control | exp_kill.py, no product code (exp-plain-playwright-kill.txt) | n/a | hard-kill relaunch 14-162 s or timeout on this machine |
| Scrub probe | scrubprobe.py (scrub-probe.txt) | n/a | secret redacted; profile path present in short messages |
| Floors | falsify.py rows F1 F2 F2b F3 F5 F6 (falsify-unit.txt), F7 (falsify-live-C4.txt) | per row | all red-after for the named assertion; F3b survived |
| Lint / doctor | `ruff check src tests scripts` (ruff-head.txt); `autotester doctor` (doctor-head.txt, doctor-base.txt) | n/a | ruff clean; doctor 1 violation `stale-generated: docs/SNAPSHOT.md`, same on base |
| Diff scope | `git diff --name-status 3748cb83 wave/at888-session-survives-failure` (diff-name-status.txt) | n/a | 5 files: video.py, run_case_pipeline.py, 2 tests, manifest; 0 test lines removed |

Sizes: video.py 224, run_case_pipeline.py 243, tests 229 and 114 lines; longest function in the changed files 36 lines (`run_and_grade_case_resilient`), `end_case_video` 31.

## Not run
- No full suite (brief). Hard kill of the browser mid-case in HEADLESS through the pipeline was not run (headed mid-case and headless between-case were). Floor F3b (scrub) shows no test pins `_scrubbed`.
